import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.domain.scope_policy import ScopeViolation, require_approved_quality_type
from app.models.domain import (
    AppUser,
    Color,
    ContributionValidationStudy,
    ControlledTrial,
    EngineeringKnowledgeEntry,
    Factory,
    FileImportJob,
    FileImportProfile,
    MaterialBatch,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementMsaStudy,
    MeasurementPoint,
    MeasurementProbe,
    ModelExplanation,
    ModelVersion,
    PointContributionVersion,
    PredictionResult,
    ProcessRoute,
    ProcessRouteApplicability,
    ProcessRouteStep,
    ProcessStage,
    ProductionRun,
    QualityIssueComment,
    QualityIssueEvidence,
    QualityIssueTask,
    QualityMeasurement,
    Recommendation,
    SupplierMaterialIssue,
    SupplierMaterialSubmission,
    TrajectoryPathSegment,
    TrajectorySegmentGeometry,
    VehicleModel,
)
from app.schemas import engineering as schemas
from app.services.file_imports import (
    build_import_preview,
    decode_base64_file,
    execute_validated_import,
)

router = APIRouter(prefix="/engineering", tags=["engineering-workflow"])
logger = logging.getLogger(__name__)

APPROVAL_STATUSES = {"APPROVED", "ACTIVE"}
CLOSED_TASK_STATUSES = {"VERIFIED", "CLOSED"}
MATERIAL_REVIEW_STATUSES = {"ACCEPTED", "REJECTED"}
DURR_IMPORT_DOMAINS = {"DURR_DXQ", "DURR_PLC"}
MATERIAL_IMPORT_DOMAINS = {"MATERIAL_COA", "MATERIAL_TDS"}
FILE_IMPORT_CLAIM_TTL = timedelta(hours=2)
FILE_IMPORT_HEARTBEAT_INTERVAL = timedelta(minutes=5)


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _save(db: Session, resource):
    db.add(resource)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="业务编号、版本或唯一关系已存在") from exc
    db.refresh(resource)
    return resource


def _apply_changes(resource, payload: BaseModel) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(resource, field, value)
    return changes


def _commit_update(db: Session, resource):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="业务编号、版本或唯一关系已存在") from exc
    db.refresh(resource)
    return resource


def _count(db: Session, model: type, *conditions) -> int:
    query = select(func.count()).select_from(model)
    if conditions:
        query = query.where(*conditions)
    return int(db.scalar(query) or 0)


def _quality_type(value: str | None) -> None:
    if not value:
        return
    try:
        require_approved_quality_type(value)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _process_stage(value: str | None) -> None:
    if not value:
        return
    try:
        ProcessStage(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="工序必须属于五个批准喷涂执行阶段") from exc


def _time_range(start: datetime | None, end: datetime | None, label: str) -> None:
    if not start or not end:
        return
    start_utc = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
    end_utc = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
    if end_utc <= start_utc:
        raise HTTPException(status_code=422, detail=f"{label}结束时间必须晚于开始时间")


def _approval_required(status_value: str | None, approved_by: str | None, label: str) -> None:
    if status_value in APPROVAL_STATUSES and not approved_by:
        raise HTTPException(status_code=422, detail=f"{label}批准或生效必须维护审批人")


def _stamp_approval(resource, status_value: str | None) -> None:
    if status_value in APPROVAL_STATUSES and getattr(resource, "approved_at", None) is None:
        resource.approved_at = datetime.now(UTC)


def _stamp_closed(resource, status_value: str | None) -> None:
    if status_value in CLOSED_TASK_STATUSES and getattr(resource, "closed_at", None) is None:
        resource.closed_at = datetime.now(UTC)


def _default_import_no(prefix: str) -> str:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    safe_prefix = "".join(char if char.isalnum() else "-" for char in prefix.upper())[:24]
    return f"{safe_prefix}-{suffix}"[:64]


def _validate_route(values: dict) -> None:
    _time_range(values.get("effective_from"), values.get("effective_to"), "路线有效期")
    _approval_required(values.get("status"), values.get("approved_by"), "工艺路线")


def _validate_route_step(values: dict) -> None:
    _process_stage(values.get("process_stage"))
    if values.get("step_type") == "SPRAY_STAGE" and values.get("is_ai_feature_source") and not values.get("process_stage"):
        raise HTTPException(status_code=422, detail="AI 特征来源喷涂步骤必须绑定五个喷涂执行工序之一")
    if values.get("process_stage") and values.get("step_type") != "SPRAY_STAGE":
        raise HTTPException(status_code=422, detail="只有喷涂步骤可以绑定喷涂执行工序")


def _validate_file_job(db: Session, values: dict) -> None:
    profile = _required(db, FileImportProfile, values["profile_id"], "文件导入 profile")
    if values.get("domain_type") != profile.domain_type:
        raise HTTPException(status_code=422, detail="导入任务 domain_type 必须与 profile 一致")
    if values.get("replay_of_job_id"):
        _required(db, FileImportJob, values["replay_of_job_id"], "被重放导入任务")
    if (values.get("valid_row_count") or 0) + (values.get("failed_row_count") or 0) > (values.get("row_count") or 0):
        raise HTTPException(status_code=422, detail="有效行数与失败行数之和不能大于总行数")


def _validate_probe(db: Session, values: dict) -> None:
    _required(db, MeasurementInstrument, values["instrument_id"], "测量仪器")
    _time_range(values.get("valid_from"), values.get("valid_until"), "探头有效期")


def _validate_msa(db: Session, values: dict) -> None:
    instrument = _required(db, MeasurementInstrument, values["instrument_id"], "测量仪器")
    probe = _required(db, MeasurementProbe, values["probe_id"], "测量探头") if values.get("probe_id") else None
    method = _required(db, MeasurementMethod, values["method_id"], "测量方法") if values.get("method_id") else None
    _quality_type(values.get("quality_type"))
    if probe and probe.instrument_id != instrument.id:
        raise HTTPException(status_code=422, detail="MSA 探头不属于该测量仪器")
    if method and method.instrument_type != instrument.instrument_type:
        raise HTTPException(status_code=422, detail="MSA 测量方法与仪器类型不匹配")
    if method and method.quality_type != values.get("quality_type"):
        raise HTTPException(status_code=422, detail="MSA 测量方法与质量类型不匹配")
    if values.get("result") in {"PASS", "FAIL"} and not values.get("approved_by"):
        raise HTTPException(status_code=422, detail="MSA 通过或失败结论必须维护审批人")


def _validate_issue_task(db: Session, values: dict) -> None:
    for field, model, label in (
        ("factory_id", Factory, "工厂"),
        ("vehicle_model_id", VehicleModel, "车型"),
        ("color_id", Color, "颜色"),
        ("production_run_id", ProductionRun, "生产事件"),
        ("measurement_point_id", MeasurementPoint, "测量点"),
        ("quality_measurement_id", QualityMeasurement, "质量数据"),
        ("material_batch_id", MaterialBatch, "材料批次"),
        ("recommendation_id", Recommendation, "推荐记录"),
        ("controlled_trial_id", ControlledTrial, "受控试验"),
        ("owner_user_id", AppUser, "责任用户"),
    ):
        if values.get(field):
            _required(db, model, values[field], label)
    _process_stage(values.get("process_stage"))
    _quality_type(values.get("target_quality_type"))
    measurement_id = values.get("quality_measurement_id")
    point_id = values.get("measurement_point_id")
    if measurement_id and point_id:
        measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
        if measurement.measurement_point_id != point_id:
            raise HTTPException(status_code=422, detail="质量数据与任务测量点不一致")


def _validate_knowledge(values: dict) -> None:
    _quality_type(values.get("target_quality_type"))
    _approval_required(values.get("status"), values.get("approved_by"), "诊断知识")


def _validate_supplier_submission(db: Session, values: dict) -> None:
    batch = _required(db, MaterialBatch, values["material_batch_id"], "材料批次") if values.get("material_batch_id") else None
    profile = _required(db, FileImportProfile, values["profile_id"], "文件导入 profile") if values.get("profile_id") else None
    if batch and batch.material_code != values.get("material_code"):
        raise HTTPException(status_code=422, detail="供应商提交的材料代码必须与材料批次一致")
    if profile and profile.domain_type not in MATERIAL_IMPORT_DOMAINS:
        raise HTTPException(status_code=422, detail="供应商材料提交只能使用材料 COA/TDS 导入 profile")
    if values.get("status") in MATERIAL_REVIEW_STATUSES and not values.get("reviewed_by"):
        raise HTTPException(status_code=422, detail="材料提交接受或拒绝必须维护审核人")


def _validate_supplier_issue(db: Session, values: dict) -> None:
    if values.get("submission_id"):
        _required(db, SupplierMaterialSubmission, values["submission_id"], "供应商材料提交")
    if values.get("material_batch_id"):
        _required(db, MaterialBatch, values["material_batch_id"], "材料批次")
    if values.get("status") == "CLOSED" and not values.get("resolution"):
        raise HTTPException(status_code=422, detail="关闭供应商材料问题必须维护处理结论")


def _validate_contribution_validation(db: Session, values: dict) -> None:
    _required(db, PointContributionVersion, values["contribution_version_id"], "点位贡献版本")
    _quality_type(values.get("target_family"))
    _approval_required(values.get("status"), values.get("approved_by"), "点位贡献验证")


def _validate_trajectory_geometry(db: Session, values: dict) -> None:
    _required(db, TrajectoryPathSegment, values["path_segment_id"], "轨迹路径段")
    if values.get("source_import_job_id"):
        import_job = _required(db, FileImportJob, values["source_import_job_id"], "导入任务")
        if import_job.domain_type not in DURR_IMPORT_DOMAINS:
            raise HTTPException(status_code=422, detail="轨迹几何只能关联 Dürr DXQ/PLC 导入任务")


def _validate_model_explanation(db: Session, values: dict) -> None:
    _required(db, ModelVersion, values["model_version_id"], "模型版本")
    if values.get("prediction_result_id"):
        prediction = _required(db, PredictionResult, values["prediction_result_id"], "预测结果")
        if prediction.model_version_id != values["model_version_id"]:
            raise HTTPException(status_code=422, detail="模型解释与预测结果的模型版本不一致")


@router.get("/summary")
def engineering_summary(db: Session = Depends(get_db)) -> dict:
    return {
        "process_routes": _count(db, ProcessRoute),
        "active_routes": _count(db, ProcessRoute, ProcessRoute.status == "ACTIVE"),
        "route_steps": _count(db, ProcessRouteStep),
        "issue_tasks": _count(db, QualityIssueTask),
        "open_tasks": _count(db, QualityIssueTask, QualityIssueTask.status.notin_(["VERIFIED", "CLOSED"])),
        "file_import_profiles": _count(db, FileImportProfile),
        "file_import_jobs": _count(db, FileImportJob),
        "measurement_probes": _count(db, MeasurementProbe),
        "msa_studies": _count(db, MeasurementMsaStudy),
        "supplier_submissions": _count(db, SupplierMaterialSubmission),
        "supplier_issues": _count(db, SupplierMaterialIssue),
        "contribution_validations": _count(db, ContributionValidationStudy),
        "trajectory_geometries": _count(db, TrajectorySegmentGeometry),
        "knowledge_entries": _count(db, EngineeringKnowledgeEntry),
        "model_explanations": _count(db, ModelExplanation),
    }


@router.get("/process-routes", response_model=list[schemas.ProcessRouteRead])
def list_process_routes(db: Session = Depends(get_db)) -> list[ProcessRoute]:
    return list(db.scalars(select(ProcessRoute).order_by(ProcessRoute.route_code, ProcessRoute.version)))


@router.post("/process-routes", response_model=schemas.ProcessRouteRead, status_code=status.HTTP_201_CREATED)
def create_process_route(payload: schemas.ProcessRouteCreate, db: Session = Depends(get_db)) -> ProcessRoute:
    values = payload.model_dump()
    _required(db, Factory, values["factory_id"], "工厂")
    _validate_route(values)
    resource = ProcessRoute(**values)
    _stamp_approval(resource, resource.status)
    return _save(db, resource)


@router.get("/process-routes/{route_id}", response_model=schemas.ProcessRouteRead)
def get_process_route(route_id: str, db: Session = Depends(get_db)) -> ProcessRoute:
    return _required(db, ProcessRoute, route_id, "工艺路线")


@router.patch("/process-routes/{route_id}", response_model=schemas.ProcessRouteRead)
def update_process_route(route_id: str, payload: schemas.ProcessRouteUpdate, db: Session = Depends(get_db)) -> ProcessRoute:
    resource = _required(db, ProcessRoute, route_id, "工艺路线")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "factory_id": changes.get("factory_id", resource.factory_id),
        "status": changes.get("status", resource.status),
        "approved_by": changes.get("approved_by", resource.approved_by),
        "effective_from": changes.get("effective_from", resource.effective_from),
        "effective_to": changes.get("effective_to", resource.effective_to),
    }
    _required(db, Factory, merged["factory_id"], "工厂")
    _validate_route(merged)
    _apply_changes(resource, payload)
    _stamp_approval(resource, resource.status)
    return _commit_update(db, resource)


@router.get("/process-route-steps", response_model=list[schemas.ProcessRouteStepRead])
def list_process_route_steps(process_route_id: str | None = None, db: Session = Depends(get_db)) -> list[ProcessRouteStep]:
    query = select(ProcessRouteStep).order_by(ProcessRouteStep.process_route_id, ProcessRouteStep.sequence_no)
    if process_route_id:
        query = query.where(ProcessRouteStep.process_route_id == process_route_id)
    return list(db.scalars(query))


@router.post("/process-route-steps", response_model=schemas.ProcessRouteStepRead, status_code=status.HTTP_201_CREATED)
def create_process_route_step(payload: schemas.ProcessRouteStepCreate, db: Session = Depends(get_db)) -> ProcessRouteStep:
    values = payload.model_dump()
    _required(db, ProcessRoute, values["process_route_id"], "工艺路线")
    _validate_route_step(values)
    return _save(db, ProcessRouteStep(**values))


@router.patch("/process-route-steps/{step_id}", response_model=schemas.ProcessRouteStepRead)
def update_process_route_step(step_id: str, payload: schemas.ProcessRouteStepUpdate, db: Session = Depends(get_db)) -> ProcessRouteStep:
    resource = _required(db, ProcessRouteStep, step_id, "工艺路线步骤")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "process_route_id": changes.get("process_route_id", resource.process_route_id),
        "step_type": changes.get("step_type", resource.step_type),
        "process_stage": changes.get("process_stage", resource.process_stage),
        "is_ai_feature_source": changes.get("is_ai_feature_source", resource.is_ai_feature_source),
    }
    _required(db, ProcessRoute, merged["process_route_id"], "工艺路线")
    _validate_route_step(merged)
    _apply_changes(resource, payload)
    return _commit_update(db, resource)


@router.get("/process-route-applicabilities", response_model=list[schemas.ProcessRouteApplicabilityRead])
def list_process_route_applicabilities(process_route_id: str | None = None, db: Session = Depends(get_db)) -> list[ProcessRouteApplicability]:
    query = select(ProcessRouteApplicability).order_by(ProcessRouteApplicability.created_at)
    if process_route_id:
        query = query.where(ProcessRouteApplicability.process_route_id == process_route_id)
    return list(db.scalars(query))


@router.post("/process-route-applicabilities", response_model=schemas.ProcessRouteApplicabilityRead, status_code=status.HTTP_201_CREATED)
def create_process_route_applicability(payload: schemas.ProcessRouteApplicabilityCreate, db: Session = Depends(get_db)) -> ProcessRouteApplicability:
    values = payload.model_dump()
    _required(db, ProcessRoute, values["process_route_id"], "工艺路线")
    if values.get("vehicle_model_id"):
        _required(db, VehicleModel, values["vehicle_model_id"], "车型")
    if values.get("color_id"):
        _required(db, Color, values["color_id"], "颜色")
    return _save(db, ProcessRouteApplicability(**values))


@router.patch("/process-route-applicabilities/{applicability_id}", response_model=schemas.ProcessRouteApplicabilityRead)
def update_process_route_applicability(applicability_id: str, payload: schemas.ProcessRouteApplicabilityUpdate, db: Session = Depends(get_db)) -> ProcessRouteApplicability:
    resource = _required(db, ProcessRouteApplicability, applicability_id, "工艺路线适用关系")
    changes = payload.model_dump(exclude_unset=True)
    if "process_route_id" in changes:
        _required(db, ProcessRoute, changes["process_route_id"], "工艺路线")
    if changes.get("vehicle_model_id"):
        _required(db, VehicleModel, changes["vehicle_model_id"], "车型")
    if changes.get("color_id"):
        _required(db, Color, changes["color_id"], "颜色")
    _apply_changes(resource, payload)
    return _commit_update(db, resource)


@router.get("/file-import-profiles", response_model=list[schemas.FileImportProfileRead])
def list_file_import_profiles(db: Session = Depends(get_db)) -> list[FileImportProfile]:
    return list(db.scalars(select(FileImportProfile).order_by(FileImportProfile.domain_type, FileImportProfile.code, FileImportProfile.version)))


@router.post("/file-import-profiles", response_model=schemas.FileImportProfileRead, status_code=status.HTTP_201_CREATED)
def create_file_import_profile(payload: schemas.FileImportProfileCreate, db: Session = Depends(get_db)) -> FileImportProfile:
    values = payload.model_dump()
    _approval_required(values.get("status"), values.get("approved_by"), "文件导入 profile")
    resource = FileImportProfile(**values)
    _stamp_approval(resource, resource.status)
    return _save(db, resource)


@router.patch("/file-import-profiles/{profile_id}", response_model=schemas.FileImportProfileRead)
def update_file_import_profile(profile_id: str, payload: schemas.FileImportProfileUpdate, db: Session = Depends(get_db)) -> FileImportProfile:
    resource = _required(db, FileImportProfile, profile_id, "文件导入 profile")
    changes = payload.model_dump(exclude_unset=True)
    _approval_required(changes.get("status", resource.status), changes.get("approved_by", resource.approved_by), "文件导入 profile")
    _apply_changes(resource, payload)
    _stamp_approval(resource, resource.status)
    return _commit_update(db, resource)


@router.get("/file-import-jobs", response_model=list[schemas.FileImportJobRead])
def list_file_import_jobs(db: Session = Depends(get_db)) -> list[FileImportJob]:
    return list(db.scalars(select(FileImportJob).order_by(FileImportJob.submitted_at.desc())))


@router.post(
    "/file-import-jobs/preview",
    response_model=schemas.FileImportJobRead,
    status_code=status.HTTP_201_CREATED,
)
def preview_file_import_job(
    payload: schemas.FileImportPreviewRequest,
    db: Session = Depends(get_db),
) -> FileImportJob:
    profile = _required(db, FileImportProfile, payload.profile_id, "文件导入 profile")
    if profile.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="只能使用已生效的导入配置")
    content = decode_base64_file(
        payload.content_base64,
        max_bytes=settings.file_import_max_bytes,
    )
    preview = build_import_preview(
        profile,
        content,
        source_filename=payload.source_filename,
        source_checksum=payload.source_checksum,
    )
    values = {
        "import_no": payload.import_no or _default_import_no(f"IMP-{profile.code}"),
        "profile_id": profile.id,
        "domain_type": profile.domain_type,
        "source_filename": payload.source_filename,
        "source_uri": payload.source_uri,
        "source_checksum": preview.source_checksum,
        "status": "VALIDATED" if preview.error_report is None else "FAILED",
        "row_count": preview.row_count,
        "valid_row_count": preview.valid_row_count,
        "failed_row_count": preview.failed_row_count,
        "preview_payload": preview.preview_payload,
        "error_report": preview.error_report,
        "submitted_by": payload.submitted_by,
        "submitted_at": datetime.now(UTC),
        "remark": payload.remark,
    }
    _validate_file_job(db, values)
    return _save(db, FileImportJob(**values))


def _execute_file_import_job(
    job: FileImportJob,
    profile: FileImportProfile,
    *,
    mode: str,
    success_status: str,
    db: Session,
) -> FileImportJob:
    claim_at = datetime.now(UTC)
    stale_before = claim_at - FILE_IMPORT_CLAIM_TTL
    claim_token = str(uuid4())
    claimed_preview = dict(job.preview_payload or {})
    claimed_preview["_import_claim"] = {
        "token": claim_token,
        "claimed_at": claim_at.isoformat(),
    }
    claim = db.execute(
        update(FileImportJob)
        .where(
            FileImportJob.id == job.id,
            or_(
                FileImportJob.status == "VALIDATED",
                and_(
                    FileImportJob.status == "IMPORTING",
                    FileImportJob.updated_at < stale_before,
                ),
            ),
        )
        .values(status="IMPORTING", preview_payload=claimed_preview, updated_at=claim_at)
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="该导入任务已被处理，请刷新后查看最新状态")
    db.commit()
    db.refresh(job)

    next_heartbeat_at = claim_at + FILE_IMPORT_HEARTBEAT_INTERVAL

    def heartbeat() -> None:
        nonlocal next_heartbeat_at
        heartbeat_at = datetime.now(UTC)
        if heartbeat_at < next_heartbeat_at:
            return
        renewal = db.execute(
            update(FileImportJob)
            .where(
                FileImportJob.id == job.id,
                FileImportJob.status == "IMPORTING",
                FileImportJob.preview_payload["_import_claim"]["token"].as_string()
                == claim_token,
            )
            .values(updated_at=heartbeat_at)
            .execution_options(synchronize_session=False)
        )
        if renewal.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="导入任务执行租约已失效，请刷新任务状态")
        db.commit()
        next_heartbeat_at = heartbeat_at + FILE_IMPORT_HEARTBEAT_INTERVAL

    def finalize_claim(**values) -> FileImportJob:
        finalization = db.execute(
            update(FileImportJob)
            .where(
                FileImportJob.id == job.id,
                FileImportJob.status == "IMPORTING",
                FileImportJob.preview_payload["_import_claim"]["token"].as_string()
                == claim_token,
            )
            .values(**values, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        if finalization.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="导入任务所有权已变化，当前结果未写入")
        db.commit()
        return _required(db, FileImportJob, job.id, "文件导入任务")

    completed_preview = dict(claimed_preview)
    completed_preview.pop("_import_claim", None)

    try:
        result = execute_validated_import(
            profile,
            claimed_preview,
            source_filename=job.source_filename,
            mode=mode,
            heartbeat=heartbeat,
            db=db,
        )
    except HTTPException as exc:
        db.rollback()
        return finalize_claim(
            status="FAILED",
            preview_payload=completed_preview,
            error_report={"error_count": 1, "errors": [{"row": 0, "message": str(exc.detail)}]},
        )
    except Exception:
        logger.exception("file import execution failed", extra={"file_import_job_id": job.id})
        db.rollback()
        return finalize_claim(
            status="FAILED",
            preview_payload=completed_preview,
            error_report={
                "error_count": 1,
                "errors": [{"row": 0, "message": "导入执行异常，请检查服务日志后重试"}],
            },
        )

    preview_payload = dict(completed_preview)
    preview_payload["import_result"] = result
    if result.get("failed", 0):
        failed_row_count = int(result["failed"])
        return finalize_claim(
            status="FAILED",
            preview_payload=preview_payload,
            failed_row_count=failed_row_count,
            valid_row_count=max(0, job.row_count - failed_row_count),
            error_report={
                "error_count": failed_row_count,
                "errors": result.get("errors", []),
                "truncated_errors": bool(result.get("truncated_errors")),
            },
        )
    return finalize_claim(
        status=success_status,
        preview_payload=preview_payload,
        failed_row_count=0,
        valid_row_count=job.row_count,
        error_report=None,
        imported_at=datetime.now(UTC),
    )


@router.post(
    "/file-import-jobs/{job_id}/commit",
    response_model=schemas.FileImportJobRead,
)
def commit_file_import_job(
    job_id: str,
    payload: schemas.FileImportCommitRequest,
    db: Session = Depends(get_db),
) -> FileImportJob:
    job = _required(db, FileImportJob, job_id, "文件导入任务")
    if job.status not in {"VALIDATED", "IMPORTING"}:
        raise HTTPException(status_code=409, detail="只有校验通过且尚未写入的任务可以确认导入")
    profile = _required(db, FileImportProfile, job.profile_id, "文件导入 profile")
    if profile.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="导入配置已失效，请重新选择配置并预览")
    return _execute_file_import_job(
        job,
        profile,
        mode=payload.mode,
        success_status="IMPORTED",
        db=db,
    )


def reject_direct_file_import_job_create(
    payload: schemas.FileImportJobCreate,
    db: Session,
) -> FileImportJob:
    del payload, db
    raise HTTPException(status_code=405, detail="导入任务只能通过文件预览流程创建")


@router.post(
    "/file-import-jobs/{job_id}/replay",
    response_model=schemas.FileImportJobRead,
    status_code=status.HTTP_201_CREATED,
)
def replay_file_import_job(
    job_id: str,
    payload: schemas.FileImportReplayRequest,
    db: Session = Depends(get_db),
) -> FileImportJob:
    original = _required(db, FileImportJob, job_id, "文件导入任务")
    profile = _required(db, FileImportProfile, original.profile_id, "文件导入 profile")
    if profile.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="导入配置已失效，不能重放")
    if not original.preview_payload or original.preview_payload.get("validation_status") != "PASSED":
        raise HTTPException(status_code=409, detail="原任务未通过字段校验，修正配置后请重新上传")
    values = {
        "import_no": payload.import_no or _default_import_no(f"REPLAY-{original.import_no}"),
        "profile_id": original.profile_id,
        "domain_type": original.domain_type,
        "source_filename": original.source_filename,
        "source_uri": original.source_uri,
        "source_checksum": original.source_checksum,
        "status": "VALIDATED",
        "row_count": original.row_count,
        "valid_row_count": original.valid_row_count,
        "failed_row_count": original.failed_row_count,
        "preview_payload": original.preview_payload,
        "error_report": original.error_report,
        "submitted_by": payload.submitted_by,
        "submitted_at": datetime.now(UTC),
        "replay_of_job_id": original.id,
        "remark": payload.remark,
    }
    _validate_file_job(db, values)
    replay = _save(db, FileImportJob(**values))
    return _execute_file_import_job(
        replay,
        profile,
        mode="upsert",
        success_status="REPLAYED",
        db=db,
    )


@router.patch("/file-import-jobs/{job_id}", response_model=schemas.FileImportJobRead)
def update_file_import_job(job_id: str, payload: schemas.FileImportJobUpdate, db: Session = Depends(get_db)) -> FileImportJob:
    resource = _required(db, FileImportJob, job_id, "文件导入任务")
    _apply_changes(resource, payload)
    return _commit_update(db, resource)


@router.get("/measurement-probes", response_model=list[schemas.MeasurementProbeRead])
def list_measurement_probes(db: Session = Depends(get_db)) -> list[MeasurementProbe]:
    return list(db.scalars(select(MeasurementProbe).order_by(MeasurementProbe.instrument_id, MeasurementProbe.code)))


@router.post("/measurement-probes", response_model=schemas.MeasurementProbeRead, status_code=status.HTTP_201_CREATED)
def create_measurement_probe(payload: schemas.MeasurementProbeCreate, db: Session = Depends(get_db)) -> MeasurementProbe:
    values = payload.model_dump()
    _validate_probe(db, values)
    return _save(db, MeasurementProbe(**values))


@router.patch("/measurement-probes/{probe_id}", response_model=schemas.MeasurementProbeRead)
def update_measurement_probe(probe_id: str, payload: schemas.MeasurementProbeUpdate, db: Session = Depends(get_db)) -> MeasurementProbe:
    resource = _required(db, MeasurementProbe, probe_id, "测量探头")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "instrument_id": changes.get("instrument_id", resource.instrument_id),
        "valid_from": changes.get("valid_from", resource.valid_from),
        "valid_until": changes.get("valid_until", resource.valid_until),
    }
    _validate_probe(db, merged)
    _apply_changes(resource, payload)
    return _commit_update(db, resource)


@router.get("/measurement-msa-studies", response_model=list[schemas.MeasurementMsaStudyRead])
def list_measurement_msa_studies(db: Session = Depends(get_db)) -> list[MeasurementMsaStudy]:
    return list(db.scalars(select(MeasurementMsaStudy).order_by(MeasurementMsaStudy.study_at.desc())))


@router.post("/measurement-msa-studies", response_model=schemas.MeasurementMsaStudyRead, status_code=status.HTTP_201_CREATED)
def create_measurement_msa_study(payload: schemas.MeasurementMsaStudyCreate, db: Session = Depends(get_db)) -> MeasurementMsaStudy:
    values = payload.model_dump()
    _validate_msa(db, values)
    resource = MeasurementMsaStudy(**values)
    if resource.result in {"PASS", "FAIL"}:
        resource.approved_at = datetime.now(UTC)
    return _save(db, resource)


@router.patch("/measurement-msa-studies/{study_id}", response_model=schemas.MeasurementMsaStudyRead)
def update_measurement_msa_study(study_id: str, payload: schemas.MeasurementMsaStudyUpdate, db: Session = Depends(get_db)) -> MeasurementMsaStudy:
    resource = _required(db, MeasurementMsaStudy, study_id, "MSA 研究")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "instrument_id": changes.get("instrument_id", resource.instrument_id),
        "probe_id": changes.get("probe_id", resource.probe_id),
        "method_id": changes.get("method_id", resource.method_id),
        "quality_type": changes.get("quality_type", resource.quality_type),
        "result": changes.get("result", resource.result),
        "approved_by": changes.get("approved_by", resource.approved_by),
    }
    _validate_msa(db, merged)
    _apply_changes(resource, payload)
    if resource.result in {"PASS", "FAIL"} and resource.approved_at is None:
        resource.approved_at = datetime.now(UTC)
    return _commit_update(db, resource)


@router.get("/issue-tasks", response_model=list[schemas.QualityIssueTaskRead])
def list_issue_tasks(
    status_filter: str | None = None,
    factory_id: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> list[QualityIssueTask]:
    query = select(QualityIssueTask).order_by(QualityIssueTask.created_at.desc())
    if status_filter:
        query = query.where(QualityIssueTask.status == status_filter)
    if factory_id:
        query = query.where(QualityIssueTask.factory_id == factory_id)
    return list(db.scalars(query.limit(min(max(limit, 1), 500))))


@router.post("/issue-tasks", response_model=schemas.QualityIssueTaskRead, status_code=status.HTTP_201_CREATED)
def create_issue_task(payload: schemas.QualityIssueTaskCreate, db: Session = Depends(get_db)) -> QualityIssueTask:
    values = payload.model_dump()
    _validate_issue_task(db, values)
    resource = QualityIssueTask(**values)
    _stamp_closed(resource, resource.status)
    return _save(db, resource)


@router.get("/issue-tasks/{task_id}", response_model=schemas.QualityIssueTaskRead)
def get_issue_task(task_id: str, db: Session = Depends(get_db)) -> QualityIssueTask:
    return _required(db, QualityIssueTask, task_id, "质量问题工单")


@router.patch("/issue-tasks/{task_id}", response_model=schemas.QualityIssueTaskRead)
def update_issue_task(task_id: str, payload: schemas.QualityIssueTaskUpdate, db: Session = Depends(get_db)) -> QualityIssueTask:
    resource = _required(db, QualityIssueTask, task_id, "质量问题工单")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        field: changes.get(field, getattr(resource, field))
        for field in (
            "factory_id",
            "vehicle_model_id",
            "color_id",
            "production_run_id",
            "measurement_point_id",
            "quality_measurement_id",
            "material_batch_id",
            "recommendation_id",
            "controlled_trial_id",
            "process_stage",
            "target_quality_type",
            "owner_user_id",
        )
    }
    _validate_issue_task(db, merged)
    _apply_changes(resource, payload)
    _stamp_closed(resource, resource.status)
    return _commit_update(db, resource)


@router.get("/issue-tasks/{task_id}/evidence", response_model=list[schemas.QualityIssueEvidenceRead])
def list_issue_task_evidence(task_id: str, db: Session = Depends(get_db)) -> list[QualityIssueEvidence]:
    _required(db, QualityIssueTask, task_id, "质量问题工单")
    return list(db.scalars(select(QualityIssueEvidence).where(QualityIssueEvidence.task_id == task_id).order_by(QualityIssueEvidence.created_at)))


@router.post("/issue-tasks/{task_id}/evidence", response_model=schemas.QualityIssueEvidenceRead, status_code=status.HTTP_201_CREATED)
def create_issue_task_evidence(task_id: str, payload: schemas.QualityIssueEvidenceCreate, db: Session = Depends(get_db)) -> QualityIssueEvidence:
    _required(db, QualityIssueTask, task_id, "质量问题工单")
    return _save(db, QualityIssueEvidence(task_id=task_id, **payload.model_dump()))


@router.get("/issue-tasks/{task_id}/comments", response_model=list[schemas.QualityIssueCommentRead])
def list_issue_task_comments(task_id: str, db: Session = Depends(get_db)) -> list[QualityIssueComment]:
    _required(db, QualityIssueTask, task_id, "质量问题工单")
    return list(db.scalars(select(QualityIssueComment).where(QualityIssueComment.task_id == task_id).order_by(QualityIssueComment.created_at)))


@router.post("/issue-tasks/{task_id}/comments", response_model=schemas.QualityIssueCommentRead, status_code=status.HTTP_201_CREATED)
def create_issue_task_comment(task_id: str, payload: schemas.QualityIssueCommentCreate, db: Session = Depends(get_db)) -> QualityIssueComment:
    _required(db, QualityIssueTask, task_id, "质量问题工单")
    return _save(db, QualityIssueComment(task_id=task_id, **payload.model_dump()))


@router.get("/knowledge-entries", response_model=list[schemas.EngineeringKnowledgeEntryRead])
def list_knowledge_entries(db: Session = Depends(get_db)) -> list[EngineeringKnowledgeEntry]:
    return list(db.scalars(select(EngineeringKnowledgeEntry).order_by(EngineeringKnowledgeEntry.category, EngineeringKnowledgeEntry.entry_code, EngineeringKnowledgeEntry.version)))


@router.post("/knowledge-entries", response_model=schemas.EngineeringKnowledgeEntryRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_entry(payload: schemas.EngineeringKnowledgeEntryCreate, db: Session = Depends(get_db)) -> EngineeringKnowledgeEntry:
    values = payload.model_dump()
    _validate_knowledge(values)
    resource = EngineeringKnowledgeEntry(**values)
    _stamp_approval(resource, resource.status)
    return _save(db, resource)


@router.patch("/knowledge-entries/{entry_id}", response_model=schemas.EngineeringKnowledgeEntryRead)
def update_knowledge_entry(entry_id: str, payload: schemas.EngineeringKnowledgeEntryUpdate, db: Session = Depends(get_db)) -> EngineeringKnowledgeEntry:
    resource = _required(db, EngineeringKnowledgeEntry, entry_id, "诊断知识")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "target_quality_type": changes.get("target_quality_type", resource.target_quality_type),
        "status": changes.get("status", resource.status),
        "approved_by": changes.get("approved_by", resource.approved_by),
    }
    _validate_knowledge(merged)
    _apply_changes(resource, payload)
    _stamp_approval(resource, resource.status)
    return _commit_update(db, resource)


@router.get("/supplier-submissions", response_model=list[schemas.SupplierMaterialSubmissionRead])
def list_supplier_submissions(db: Session = Depends(get_db)) -> list[SupplierMaterialSubmission]:
    return list(db.scalars(select(SupplierMaterialSubmission).order_by(SupplierMaterialSubmission.submitted_at.desc())))


@router.post("/supplier-submissions", response_model=schemas.SupplierMaterialSubmissionRead, status_code=status.HTTP_201_CREATED)
def create_supplier_submission(payload: schemas.SupplierMaterialSubmissionCreate, db: Session = Depends(get_db)) -> SupplierMaterialSubmission:
    values = payload.model_dump()
    values["submitted_at"] = values.get("submitted_at") or datetime.now(UTC)
    if values.get("status") in MATERIAL_REVIEW_STATUSES and not values.get("reviewed_at"):
        values["reviewed_at"] = datetime.now(UTC)
    _validate_supplier_submission(db, values)
    return _save(db, SupplierMaterialSubmission(**values))


@router.patch("/supplier-submissions/{submission_id}", response_model=schemas.SupplierMaterialSubmissionRead)
def update_supplier_submission(submission_id: str, payload: schemas.SupplierMaterialSubmissionUpdate, db: Session = Depends(get_db)) -> SupplierMaterialSubmission:
    resource = _required(db, SupplierMaterialSubmission, submission_id, "供应商材料提交")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "material_batch_id": changes.get("material_batch_id", resource.material_batch_id),
        "material_code": changes.get("material_code", resource.material_code),
        "profile_id": changes.get("profile_id", resource.profile_id),
        "status": changes.get("status", resource.status),
        "reviewed_by": changes.get("reviewed_by", resource.reviewed_by),
    }
    _validate_supplier_submission(db, merged)
    _apply_changes(resource, payload)
    if resource.status in MATERIAL_REVIEW_STATUSES and resource.reviewed_at is None:
        resource.reviewed_at = datetime.now(UTC)
    return _commit_update(db, resource)


@router.get("/supplier-issues", response_model=list[schemas.SupplierMaterialIssueRead])
def list_supplier_issues(db: Session = Depends(get_db)) -> list[SupplierMaterialIssue]:
    return list(db.scalars(select(SupplierMaterialIssue).order_by(SupplierMaterialIssue.created_at.desc())))


@router.post("/supplier-issues", response_model=schemas.SupplierMaterialIssueRead, status_code=status.HTTP_201_CREATED)
def create_supplier_issue(payload: schemas.SupplierMaterialIssueCreate, db: Session = Depends(get_db)) -> SupplierMaterialIssue:
    values = payload.model_dump()
    _validate_supplier_issue(db, values)
    resource = SupplierMaterialIssue(**values)
    if resource.status == "CLOSED":
        resource.closed_at = datetime.now(UTC)
    return _save(db, resource)


@router.patch("/supplier-issues/{issue_id}", response_model=schemas.SupplierMaterialIssueRead)
def update_supplier_issue(issue_id: str, payload: schemas.SupplierMaterialIssueUpdate, db: Session = Depends(get_db)) -> SupplierMaterialIssue:
    resource = _required(db, SupplierMaterialIssue, issue_id, "供应商材料问题")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "submission_id": resource.submission_id,
        "material_batch_id": resource.material_batch_id,
        "status": changes.get("status", resource.status),
        "resolution": changes.get("resolution", resource.resolution),
    }
    _validate_supplier_issue(db, merged)
    _apply_changes(resource, payload)
    if resource.status == "CLOSED" and resource.closed_at is None:
        resource.closed_at = datetime.now(UTC)
    return _commit_update(db, resource)


@router.get("/contribution-validations", response_model=list[schemas.ContributionValidationStudyRead])
def list_contribution_validations(db: Session = Depends(get_db)) -> list[ContributionValidationStudy]:
    return list(db.scalars(select(ContributionValidationStudy).order_by(ContributionValidationStudy.created_at.desc())))


@router.post("/contribution-validations", response_model=schemas.ContributionValidationStudyRead, status_code=status.HTTP_201_CREATED)
def create_contribution_validation(payload: schemas.ContributionValidationStudyCreate, db: Session = Depends(get_db)) -> ContributionValidationStudy:
    values = payload.model_dump()
    _validate_contribution_validation(db, values)
    resource = ContributionValidationStudy(**values)
    _stamp_approval(resource, resource.status)
    return _save(db, resource)


@router.patch("/contribution-validations/{study_id}", response_model=schemas.ContributionValidationStudyRead)
def update_contribution_validation(study_id: str, payload: schemas.ContributionValidationStudyUpdate, db: Session = Depends(get_db)) -> ContributionValidationStudy:
    resource = _required(db, ContributionValidationStudy, study_id, "点位贡献验证")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "contribution_version_id": resource.contribution_version_id,
        "target_family": changes.get("target_family", resource.target_family),
        "status": changes.get("status", resource.status),
        "approved_by": changes.get("approved_by", resource.approved_by),
    }
    _validate_contribution_validation(db, merged)
    _apply_changes(resource, payload)
    _stamp_approval(resource, resource.status)
    return _commit_update(db, resource)


@router.get("/trajectory-geometries", response_model=list[schemas.TrajectorySegmentGeometryRead])
def list_trajectory_geometries(db: Session = Depends(get_db)) -> list[TrajectorySegmentGeometry]:
    return list(db.scalars(select(TrajectorySegmentGeometry).order_by(TrajectorySegmentGeometry.created_at.desc())))


@router.post("/trajectory-geometries", response_model=schemas.TrajectorySegmentGeometryRead, status_code=status.HTTP_201_CREATED)
def create_trajectory_geometry(payload: schemas.TrajectorySegmentGeometryCreate, db: Session = Depends(get_db)) -> TrajectorySegmentGeometry:
    values = payload.model_dump()
    _validate_trajectory_geometry(db, values)
    return _save(db, TrajectorySegmentGeometry(**values))


@router.patch("/trajectory-geometries/{geometry_id}", response_model=schemas.TrajectorySegmentGeometryRead)
def update_trajectory_geometry(geometry_id: str, payload: schemas.TrajectorySegmentGeometryUpdate, db: Session = Depends(get_db)) -> TrajectorySegmentGeometry:
    resource = _required(db, TrajectorySegmentGeometry, geometry_id, "轨迹几何")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "path_segment_id": resource.path_segment_id,
        "source_import_job_id": changes.get("source_import_job_id", resource.source_import_job_id),
    }
    _validate_trajectory_geometry(db, merged)
    _apply_changes(resource, payload)
    return _commit_update(db, resource)


@router.get("/model-explanations", response_model=list[schemas.ModelExplanationRead])
def list_model_explanations(db: Session = Depends(get_db)) -> list[ModelExplanation]:
    return list(db.scalars(select(ModelExplanation).order_by(ModelExplanation.generated_at.desc())))


@router.post("/model-explanations", response_model=schemas.ModelExplanationRead, status_code=status.HTTP_201_CREATED)
def create_model_explanation(payload: schemas.ModelExplanationCreate, db: Session = Depends(get_db)) -> ModelExplanation:
    values = payload.model_dump()
    values["generated_at"] = values.get("generated_at") or datetime.now(UTC)
    _validate_model_explanation(db, values)
    return _save(db, ModelExplanation(**values))
