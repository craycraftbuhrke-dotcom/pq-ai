from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.delete_policy import reject_physical_delete
from app.core.referential_integrity import check_fk
from app.db.session import get_db
from app.domain.scope_policy import ScopeViolation, is_out_of_scope_name, require_approved_mapping
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    FactoryVehicleModel,
    MaterialBatch,
    MeasurementPoint,
    ParameterConstraintSource,
    ParameterDefinition,
    Part,
    PointFeatureSnapshot,
    ProcessStage,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramVehicleModel,
    QualityIssueTask,
    SprayProgram,
    SprayProgramVersion,
    VehicleModelColor,
    VehicleModel,
    VersionStatus,
)
from app.schemas.process import (
    ActualParameterCreate,
    ActualParameterRead,
    ActualParameterUpdate,
    BrushCreate,
    BrushParameterUpdate,
    BrushParameterCreate,
    BrushParameterRead,
    BrushPointContributionRead,
    BrushPointContributionUpsert,
    BrushRead,
    BrushUpdate,
    MaterialBatchCreate,
    MaterialBatchRead,
    MaterialBatchUpdate,
    ParameterDefinitionCreate,
    ParameterDefinitionRead,
    ParameterConstraintSourceCreate,
    ParameterConstraintSourceRead,
    ParameterConstraintSourceUpdate,
    ProcessOverviewStageSummary,
    ProcessOverviewSummary,
    ProductionRunCreate,
    ProductionRunRead,
    ProductionRunUpdate,
    ProductionStageRunCreate,
    ProductionStageRunRead,
    ProductionStageRunUpdate,
    ProgramVersionDeriveRequest,
    ProgramVersionDeriveResult,
    SprayProgramCreate,
    SprayProgramRead,
    SprayProgramUpdate,
    SprayProgramVersionCreate,
    SprayProgramVersionRead,
    SprayProgramVersionUpdate,
)
from app.services.catalog_seed import seed_parameter_catalog
from app.services.point_optimization import point_optimization_workbench
from app.services.program_versioning import derive_complete_program_version

router = APIRouter(tags=["process-data"])


@router.get("/point-optimization-workbench")
def get_point_optimization_workbench(
    production_run_id: str,
    measurement_point_id: str,
    db: Session = Depends(get_db),
) -> dict:
    return point_optimization_workbench(db, production_run_id, measurement_point_id)


@router.post(
    "/program-versions/{version_id}/derive-complete",
    response_model=ProgramVersionDeriveResult,
    status_code=status.HTTP_201_CREATED,
)
def derive_program_version(
    version_id: str,
    payload: ProgramVersionDeriveRequest,
    db: Session = Depends(get_db),
) -> dict:
    return derive_complete_program_version(db, version_id, payload.version, payload.edits)


PROCESS_STAGE_LABELS = {
    ProcessStage.MIDCOAT_EXT: "中涂外喷",
    ProcessStage.BASECOAT_1: "色漆一站",
    ProcessStage.BASECOAT_2: "色漆二站",
    ProcessStage.CLEARCOAT_1: "清漆一站",
    ProcessStage.CLEARCOAT_2: "清漆二站",
}


def _validate_mapping_scope(values: dict | None, label: str) -> None:
    try:
        require_approved_mapping(values, label)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_parameter_scope(code: str, name: str | None = None) -> None:
    if is_out_of_scope_name(code) or (name and is_out_of_scope_name(name)):
        raise HTTPException(status_code=422, detail=f"参数 {code} 超出当前项目范围")


def _validate_process_stage(process_stage: str) -> None:
    try:
        ProcessStage(process_stage)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"工艺阶段 {process_stage} 不属于中涂外喷、色漆一/二遍或清漆一/二遍",
        ) from exc


def _expected_material_type(process_stage: str) -> str:
    if process_stage == ProcessStage.MIDCOAT_EXT.value:
        return "MIDCOAT"
    if process_stage in {ProcessStage.BASECOAT_1.value, ProcessStage.BASECOAT_2.value}:
        return "BASECOAT"
    return "CLEARCOAT"


def _existing_program_vehicle_model_ids(db: Session, version_id: str) -> set[str]:
    return set(
        db.scalars(
            select(ProgramVehicleModel.vehicle_model_id).where(
                ProgramVehicleModel.program_version_id == version_id
            )
        )
    )


def _existing_program_color_ids(db: Session, version_id: str) -> set[str]:
    return set(
        db.scalars(
            select(ProgramColor.color_id).where(ProgramColor.program_version_id == version_id)
        )
    )


def _validate_production_run_context(
    db: Session,
    factory_id: str,
    vehicle_model_id: str,
    color_id: str,
) -> None:
    if not db.scalar(
        select(FactoryVehicleModel.id).where(
            FactoryVehicleModel.factory_id == factory_id,
            FactoryVehicleModel.vehicle_model_id == vehicle_model_id,
            FactoryVehicleModel.is_active.is_(True),
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="该工厂下未启用所选车型，不能创建或更新生产事件",
        )
    if not db.scalar(
        select(VehicleModelColor.id).where(
            VehicleModelColor.vehicle_model_id == vehicle_model_id,
            VehicleModelColor.color_id == color_id,
            VehicleModelColor.is_active.is_(True),
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="该车型下未启用所选颜色，不能创建或更新生产事件",
        )


def _validate_stage_run_context(
    db: Session,
    production_run: ProductionRun,
    process_stage: str,
    program_version_id: str,
    material_batch_id: str | None,
) -> None:
    program_version = _required(db, SprayProgramVersion, program_version_id, "程序版本")
    spray_program = _required(db, SprayProgram, program_version.spray_program_id, "喷涂程序")
    if spray_program.factory_id != production_run.factory_id:
        raise HTTPException(status_code=422, detail="程序版本不属于该生产事件所在工厂")
    if spray_program.process_stage != process_stage:
        raise HTTPException(status_code=422, detail="程序版本所属工艺阶段与实绩工艺阶段不一致")

    if db.scalar(
        select(ProgramVehicleModel.id).where(
            ProgramVehicleModel.program_version_id == program_version.id
        )
    ) and not db.scalar(
        select(ProgramVehicleModel.id).where(
            ProgramVehicleModel.program_version_id == program_version.id,
            ProgramVehicleModel.vehicle_model_id == production_run.vehicle_model_id,
        )
    ):
        raise HTTPException(status_code=422, detail="程序版本不适用于该生产事件车型")

    if db.scalar(
        select(ProgramColor.id).where(ProgramColor.program_version_id == program_version.id)
    ) and not db.scalar(
        select(ProgramColor.id).where(
            ProgramColor.program_version_id == program_version.id,
            ProgramColor.color_id == production_run.color_id,
        )
    ):
        raise HTTPException(status_code=422, detail="程序版本不适用于该生产事件颜色")

    if material_batch_id:
        material_batch = _required(db, MaterialBatch, material_batch_id, "材料批次")
        expected_type = _expected_material_type(process_stage)
        if material_batch.material_type != expected_type:
            raise HTTPException(
                status_code=422,
                detail=f"{process_stage} 仅允许绑定 {expected_type} 类型材料批次",
            )


def _validate_program_version_applicability_update(
    db: Session,
    version_id: str,
    vehicle_model_ids: list[str] | None,
    color_ids: list[str] | None,
) -> tuple[list[str] | None, list[str] | None]:
    normalized_vehicle_model_ids = (
        list(dict.fromkeys(vehicle_model_ids)) if vehicle_model_ids is not None else None
    )
    normalized_color_ids = list(dict.fromkeys(color_ids)) if color_ids is not None else None

    if normalized_vehicle_model_ids is not None:
        for model_id in normalized_vehicle_model_ids:
            _required(db, VehicleModel, model_id, "车型")
        if _existing_program_vehicle_model_ids(db, version_id) - set(normalized_vehicle_model_ids):
            raise HTTPException(
                status_code=422,
                detail="程序版本适用车型缩减需新建版本，不支持在当前版本直接移除既有适用车型",
            )

    if normalized_color_ids is not None:
        for color_id in normalized_color_ids:
            _required(db, Color, color_id, "颜色")
        if _existing_program_color_ids(db, version_id) - set(normalized_color_ids):
            raise HTTPException(
                status_code=422,
                detail="程序版本适用颜色缩减需新建版本，不支持在当前版本直接移除既有适用颜色",
            )

    return normalized_vehicle_model_ids, normalized_color_ids


def _validate_constraint_source(
    db: Session,
    values: dict,
    current: ParameterConstraintSource | None = None,
) -> dict:
    lower_limit = values.get("lower_limit", current.lower_limit if current else None)
    upper_limit = values.get("upper_limit", current.upper_limit if current else None)
    if lower_limit is not None and upper_limit is not None and upper_limit <= lower_limit:
        raise HTTPException(status_code=422, detail="约束上限必须大于下限")
    parameter_definition_id = values.get(
        "parameter_definition_id", current.parameter_definition_id if current else None
    )
    if parameter_definition_id:
        _required(db, ParameterDefinition, parameter_definition_id, "参数定义")
    factory_id = values.get("factory_id", current.factory_id if current else None)
    if factory_id:
        _required(db, Factory, factory_id, "工厂")
    process_stage = values.get("process_stage", current.process_stage if current else None)
    if process_stage:
        _validate_process_stage(process_stage)
    status_value = values.get("status")
    if status_value == "ACTIVE":
        approved_by = values.get("approved_by", current.approved_by if current else None)
        if not approved_by:
            raise HTTPException(status_code=422, detail="激活约束来源必须填写审批人")
        values.setdefault("approved_at", datetime.now(UTC))
    return values


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _save(db: Session, resource):
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def _delete_resource(db: Session, resource, label: str) -> Response:
    reject_physical_delete(label)


def _validate_brush_point_contribution_context(
    db: Session,
    brush_id: str,
    measurement_point_id: str,
) -> None:
    brush = _required(db, Brush, brush_id, "刷子")
    measurement_point = _required(db, MeasurementPoint, measurement_point_id, "测量点")
    if measurement_point.point_type != "QUALITY":
        raise HTTPException(status_code=422, detail="点位贡献仅允许绑定质量测量点")
    if brush.part_id and measurement_point.part_id != brush.part_id:
        raise HTTPException(status_code=422, detail="测量点所属零件与当前刷子负责零件不一致")
    applicable_vehicle_model_ids = _existing_program_vehicle_model_ids(db, brush.program_version_id)
    if applicable_vehicle_model_ids and measurement_point.vehicle_model_id not in applicable_vehicle_model_ids:
        raise HTTPException(status_code=422, detail="测量点车型不在当前程序版本适用范围内")


@router.get("/parameter-definitions", response_model=list[ParameterDefinitionRead])
def list_parameter_definitions(db: Session = Depends(get_db)) -> list[ParameterDefinition]:
    return list(db.scalars(select(ParameterDefinition).order_by(ParameterDefinition.code)))


@router.post(
    "/parameter-definitions",
    response_model=ParameterDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_parameter_definition(
    payload: ParameterDefinitionCreate, db: Session = Depends(get_db)
) -> ParameterDefinition:
    _validate_parameter_scope(payload.code, payload.name)
    if db.scalar(select(ParameterDefinition).where(ParameterDefinition.code == payload.code)):
        raise HTTPException(status_code=409, detail="参数定义代码已存在")
    return _save(db, ParameterDefinition(**payload.model_dump()))


@router.post("/parameter-definitions/seed-catalog")
def seed_parameter_catalog_endpoint(db: Session = Depends(get_db)) -> dict:
    return seed_parameter_catalog(db)


@router.get(
    "/parameter-constraint-sources",
    response_model=list[ParameterConstraintSourceRead],
)
def list_parameter_constraint_sources(
    db: Session = Depends(get_db),
) -> list[ParameterConstraintSource]:
    return list(
        db.scalars(
            select(ParameterConstraintSource).order_by(
                ParameterConstraintSource.parameter_definition_id,
                ParameterConstraintSource.process_stage,
                ParameterConstraintSource.version,
            )
        )
    )


@router.post(
    "/parameter-constraint-sources",
    response_model=ParameterConstraintSourceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_parameter_constraint_source(
    payload: ParameterConstraintSourceCreate,
    db: Session = Depends(get_db),
) -> ParameterConstraintSource:
    values = _validate_constraint_source(db, payload.model_dump())
    if db.scalar(
        select(ParameterConstraintSource).where(
            ParameterConstraintSource.constraint_code == payload.constraint_code
        )
    ):
        raise HTTPException(status_code=409, detail="约束来源代码已存在")
    return _save(db, ParameterConstraintSource(**values))


@router.get(
    "/parameter-constraint-sources/{constraint_source_id}",
    response_model=ParameterConstraintSourceRead,
)
def get_parameter_constraint_source(
    constraint_source_id: str,
    db: Session = Depends(get_db),
) -> ParameterConstraintSource:
    return _required(db, ParameterConstraintSource, constraint_source_id, "参数约束来源")


@router.patch(
    "/parameter-constraint-sources/{constraint_source_id}",
    response_model=ParameterConstraintSourceRead,
)
def update_parameter_constraint_source(
    constraint_source_id: str,
    payload: ParameterConstraintSourceUpdate,
    db: Session = Depends(get_db),
) -> ParameterConstraintSource:
    source = _required(db, ParameterConstraintSource, constraint_source_id, "参数约束来源")
    changes = _validate_constraint_source(
        db,
        payload.model_dump(exclude_unset=True),
        current=source,
    )
    if (
        "constraint_code" in changes
        and changes["constraint_code"] != source.constraint_code
        and db.scalar(
            select(ParameterConstraintSource).where(
                ParameterConstraintSource.constraint_code == changes["constraint_code"]
            )
        )
    ):
        raise HTTPException(status_code=409, detail="约束来源代码已存在")
    for key, value in changes.items():
        setattr(source, key, value)
    return _save(db, source)


@router.get("/spray-programs", response_model=list[SprayProgramRead])
def list_spray_programs(db: Session = Depends(get_db)) -> list[SprayProgram]:
    return list(db.scalars(select(SprayProgram).order_by(SprayProgram.program_code)))


@router.get("/spray-programs/{program_id}", response_model=SprayProgramRead)
def get_spray_program(program_id: str, db: Session = Depends(get_db)) -> SprayProgram:
    return _required(db, SprayProgram, program_id, "喷涂程序")


@router.post("/spray-programs", response_model=SprayProgramRead, status_code=status.HTTP_201_CREATED)
def create_spray_program(payload: SprayProgramCreate, db: Session = Depends(get_db)) -> SprayProgram:
    _validate_process_stage(payload.process_stage)
    check_fk(db, Factory, payload.factory_id, label="工厂")
    if db.scalar(
        select(SprayProgram).where(
            SprayProgram.factory_id == payload.factory_id,
            SprayProgram.program_code == payload.program_code,
        )
    ):
        raise HTTPException(status_code=409, detail="工厂下程序编号已存在")
    return _save(db, SprayProgram(**payload.model_dump()))


@router.patch("/spray-programs/{program_id}", response_model=SprayProgramRead)
def update_spray_program(
    program_id: str, payload: SprayProgramUpdate, db: Session = Depends(get_db)
) -> SprayProgram:
    program = _required(db, SprayProgram, program_id, "喷涂程序")
    changes = payload.model_dump(exclude_unset=True)
    _validate_process_stage(changes.get("process_stage", program.process_stage))
    factory_id = changes.get("factory_id", program.factory_id)
    program_code = changes.get("program_code", program.program_code)
    _required(db, Factory, factory_id, "工厂")
    duplicate = db.scalar(
        select(SprayProgram).where(
            SprayProgram.factory_id == factory_id,
            SprayProgram.program_code == program_code,
            SprayProgram.id != program_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="工厂下程序编号已存在")
    for field, value in changes.items():
        setattr(program, field, value)
    return _save(db, program)


@router.delete("/spray-programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spray_program(program_id: str, db: Session = Depends(get_db)) -> Response:
    program = _required(db, SprayProgram, program_id, "喷涂程序")
    return _delete_resource(db, program, "喷涂程序")


@router.post(
    "/spray-programs/{program_id}/versions",
    response_model=SprayProgramVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_program_version(
    program_id: str, payload: SprayProgramVersionCreate, db: Session = Depends(get_db)
) -> SprayProgramVersion:
    check_fk(db, SprayProgram, program_id, label="喷涂程序")
    if db.scalar(
        select(SprayProgramVersion).where(
            SprayProgramVersion.spray_program_id == program_id,
            SprayProgramVersion.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本已存在")
    vehicle_model_ids = list(dict.fromkeys(payload.vehicle_model_ids))
    color_ids = list(dict.fromkeys(payload.color_ids))
    for model_id in vehicle_model_ids:
        _required(db, VehicleModel, model_id, "车型")
    for color_id in color_ids:
        _required(db, Color, color_id, "颜色")

    version_data = payload.model_dump(exclude={"vehicle_model_ids", "color_ids"})
    version = SprayProgramVersion(spray_program_id=program_id, **version_data)
    db.add(version)
    db.flush()
    db.add_all(
        [
            ProgramVehicleModel(program_version_id=version.id, vehicle_model_id=model_id)
            for model_id in vehicle_model_ids
        ]
        + [
            ProgramColor(program_version_id=version.id, color_id=color_id)
            for color_id in color_ids
        ]
    )
    db.commit()
    db.refresh(version)
    return version


@router.get(
    "/spray-programs/{program_id}/versions",
    response_model=list[SprayProgramVersionRead],
)
def list_program_versions(
    program_id: str, db: Session = Depends(get_db)
) -> list[SprayProgramVersion]:
    return list(
        db.scalars(
            select(SprayProgramVersion)
            .where(SprayProgramVersion.spray_program_id == program_id)
            .order_by(SprayProgramVersion.created_at.desc())
        )
    )


@router.get("/program-versions/{version_id}", response_model=SprayProgramVersionRead)
def get_program_version(
    version_id: str, db: Session = Depends(get_db)
) -> SprayProgramVersion:
    return _required(db, SprayProgramVersion, version_id, "程序版本")


@router.get("/program-versions/{version_id}/applicability")
def get_program_version_applicability(
    version_id: str, db: Session = Depends(get_db)
) -> dict:
    _required(db, SprayProgramVersion, version_id, "程序版本")
    return {
        "vehicle_model_ids": list(
            db.scalars(
                select(ProgramVehicleModel.vehicle_model_id).where(
                    ProgramVehicleModel.program_version_id == version_id
                )
            )
        ),
        "color_ids": list(
            db.scalars(
                select(ProgramColor.color_id).where(ProgramColor.program_version_id == version_id)
            )
        ),
    }


@router.patch("/program-versions/{version_id}", response_model=SprayProgramVersionRead)
def update_program_version(
    version_id: str,
    payload: SprayProgramVersionUpdate,
    db: Session = Depends(get_db),
) -> SprayProgramVersion:
    version = _required(db, SprayProgramVersion, version_id, "程序版本")
    changes = payload.model_dump(exclude_unset=True)
    new_version = changes.get("version", version.version)
    duplicate = db.scalar(
        select(SprayProgramVersion).where(
            SprayProgramVersion.spray_program_id == version.spray_program_id,
            SprayProgramVersion.version == new_version,
            SprayProgramVersion.id != version_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="程序版本已存在")

    vehicle_model_ids, color_ids = _validate_program_version_applicability_update(
        db,
        version_id,
        changes.pop("vehicle_model_ids", None),
        changes.pop("color_ids", None),
    )
    if vehicle_model_ids is not None:
        existing_model_ids = _existing_program_vehicle_model_ids(db, version_id)
        db.add_all(
            [
                ProgramVehicleModel(program_version_id=version_id, vehicle_model_id=model_id)
                for model_id in vehicle_model_ids
                if model_id not in existing_model_ids
            ]
        )
    if color_ids is not None:
        existing_color_ids = _existing_program_color_ids(db, version_id)
        db.add_all(
            [
                ProgramColor(program_version_id=version_id, color_id=color_id)
                for color_id in color_ids
                if color_id not in existing_color_ids
            ]
        )
    if changes.get("status") in {"APPROVED", "ACTIVE"}:
        version.approved_at = datetime.now(UTC)
        version.approved_by = changes.get("approved_by") or version.approved_by or "系统审批人"
    if changes.get("status") == "ACTIVE" and not version.effective_from:
        version.effective_from = datetime.now(UTC)
    for field, value in changes.items():
        setattr(version, field, value)
    return _save(db, version)


@router.delete("/program-versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program_version(version_id: str, db: Session = Depends(get_db)) -> Response:
    _required(db, SprayProgramVersion, version_id, "程序版本")
    reject_physical_delete("程序版本")


@router.post(
    "/program-versions/{version_id}/brushes",
    response_model=BrushRead,
    status_code=status.HTTP_201_CREATED,
)
def create_brush(version_id: str, payload: BrushCreate, db: Session = Depends(get_db)) -> Brush:
    check_fk(db, SprayProgramVersion, version_id, label="程序版本")
    if payload.part_id:
        check_fk(db, Part, payload.part_id, label="零件")
    if db.scalar(
        select(Brush).where(Brush.program_version_id == version_id, Brush.brush_no == payload.brush_no)
    ):
        raise HTTPException(status_code=409, detail="程序版本下刷子号已存在")
    return _save(db, Brush(program_version_id=version_id, **payload.model_dump()))


@router.get("/program-versions/{version_id}/brushes", response_model=list[BrushRead])
def list_brushes(version_id: str, db: Session = Depends(get_db)) -> list[Brush]:
    return list(
        db.scalars(
            select(Brush).where(Brush.program_version_id == version_id).order_by(Brush.brush_no)
        )
    )


@router.get("/brushes/{brush_id}", response_model=BrushRead)
def get_brush(brush_id: str, db: Session = Depends(get_db)) -> Brush:
    return _required(db, Brush, brush_id, "刷子")


@router.patch("/brushes/{brush_id}", response_model=BrushRead)
def update_brush(
    brush_id: str, payload: BrushUpdate, db: Session = Depends(get_db)
) -> Brush:
    brush = _required(db, Brush, brush_id, "刷子")
    changes = payload.model_dump(exclude_unset=True)
    brush_no = changes.get("brush_no", brush.brush_no)
    if changes.get("part_id"):
        _required(db, Part, changes["part_id"], "零件")
    duplicate = db.scalar(
        select(Brush).where(
            Brush.program_version_id == brush.program_version_id,
            Brush.brush_no == brush_no,
            Brush.id != brush_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="程序版本下刷子号已存在")
    for field, value in changes.items():
        setattr(brush, field, value)
    return _save(db, brush)


@router.delete("/brushes/{brush_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brush(brush_id: str, db: Session = Depends(get_db)) -> Response:
    brush = _required(db, Brush, brush_id, "刷子")
    return _delete_resource(db, brush, "刷子")


@router.post(
    "/brushes/{brush_id}/parameters",
    response_model=BrushParameterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_brush_parameter(
    brush_id: str, payload: BrushParameterCreate, db: Session = Depends(get_db)
) -> BrushParameter:
    _validate_parameter_scope(payload.parameter_code, payload.parameter_name)
    check_fk(db, Brush, brush_id, label="刷子")
    if payload.parameter_definition_id:
        check_fk(db, ParameterDefinition, payload.parameter_definition_id, label="参数定义")
    if db.scalar(
        select(BrushParameter).where(
            BrushParameter.brush_id == brush_id,
            BrushParameter.parameter_code == payload.parameter_code,
        )
    ):
        raise HTTPException(status_code=409, detail="刷子参数已存在")
    return _save(db, BrushParameter(brush_id=brush_id, **payload.model_dump()))


@router.get("/brushes/{brush_id}/parameters", response_model=list[BrushParameterRead])
def list_brush_parameters(brush_id: str, db: Session = Depends(get_db)) -> list[BrushParameter]:
    return list(
        db.scalars(
            select(BrushParameter)
            .where(BrushParameter.brush_id == brush_id)
            .order_by(BrushParameter.parameter_code)
        )
    )


@router.get("/brush-parameters/{parameter_id}", response_model=BrushParameterRead)
def get_brush_parameter(
    parameter_id: str, db: Session = Depends(get_db)
) -> BrushParameter:
    return _required(db, BrushParameter, parameter_id, "刷子参数")


@router.patch("/brush-parameters/{parameter_id}", response_model=BrushParameterRead)
def update_brush_parameter(
    parameter_id: str,
    payload: BrushParameterUpdate,
    db: Session = Depends(get_db),
) -> BrushParameter:
    parameter = _required(db, BrushParameter, parameter_id, "刷子参数")
    changes = payload.model_dump(exclude_unset=True)
    parameter_code = changes.get("parameter_code", parameter.parameter_code)
    _validate_parameter_scope(
        parameter_code,
        changes.get("parameter_name", parameter.parameter_name),
    )
    if changes.get("parameter_definition_id"):
        _required(db, ParameterDefinition, changes["parameter_definition_id"], "参数定义")
    duplicate = db.scalar(
        select(BrushParameter).where(
            BrushParameter.brush_id == parameter.brush_id,
            BrushParameter.parameter_code == parameter_code,
            BrushParameter.id != parameter_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="刷子参数已存在")
    for field, value in changes.items():
        setattr(parameter, field, value)
    return _save(db, parameter)


@router.delete("/brush-parameters/{parameter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brush_parameter(parameter_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(
        db,
        _required(db, BrushParameter, parameter_id, "刷子参数"),
        "刷子参数",
    )


@router.put(
    "/brushes/{brush_id}/contributions/{measurement_point_id}",
    response_model=BrushPointContributionRead,
)
def upsert_brush_point_contribution(
    brush_id: str,
    measurement_point_id: str,
    payload: BrushPointContributionUpsert,
    db: Session = Depends(get_db),
) -> BrushPointContribution:
    _validate_brush_point_contribution_context(db, brush_id, measurement_point_id)
    contribution = db.scalar(
        select(BrushPointContribution).where(
            BrushPointContribution.brush_id == brush_id,
            BrushPointContribution.measurement_point_id == measurement_point_id,
        )
    )
    if contribution:
        for key, value in payload.model_dump().items():
            setattr(contribution, key, value)
    else:
        contribution = BrushPointContribution(
            brush_id=brush_id, measurement_point_id=measurement_point_id, **payload.model_dump()
        )
    return _save(db, contribution)


@router.get(
    "/measurement-points/{measurement_point_id}/brush-contributions",
    response_model=list[BrushPointContributionRead],
)
def list_point_contributions(
    measurement_point_id: str, db: Session = Depends(get_db)
) -> list[BrushPointContribution]:
    return list(
        db.scalars(
            select(BrushPointContribution).where(
                BrushPointContribution.measurement_point_id == measurement_point_id
            )
        )
    )


@router.get(
    "/brushes/{brush_id}/contributions",
    response_model=list[BrushPointContributionRead],
)
def list_brush_contributions(
    brush_id: str, db: Session = Depends(get_db)
) -> list[BrushPointContribution]:
    _required(db, Brush, brush_id, "刷子")
    return list(
        db.scalars(
            select(BrushPointContribution)
            .where(BrushPointContribution.brush_id == brush_id)
            .order_by(BrushPointContribution.measurement_point_id)
        )
    )


@router.delete(
    "/brushes/{brush_id}/contributions/{measurement_point_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_brush_contribution(
    brush_id: str,
    measurement_point_id: str,
    db: Session = Depends(get_db),
) -> Response:
    contribution = db.scalar(
        select(BrushPointContribution).where(
            BrushPointContribution.brush_id == brush_id,
            BrushPointContribution.measurement_point_id == measurement_point_id,
        )
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="刷子点位贡献不存在")
    return _delete_resource(db, contribution, "刷子点位贡献")


@router.post("/material-batches", response_model=MaterialBatchRead, status_code=status.HTTP_201_CREATED)
def create_material_batch(payload: MaterialBatchCreate, db: Session = Depends(get_db)) -> MaterialBatch:
    _validate_mapping_scope(payload.coa_values, "材料 COA")
    if db.scalar(select(MaterialBatch).where(MaterialBatch.batch_no == payload.batch_no)):
        raise HTTPException(status_code=409, detail="材料批次号已存在")
    return _save(db, MaterialBatch(**payload.model_dump()))


@router.get("/material-batches", response_model=list[MaterialBatchRead])
def list_material_batches(db: Session = Depends(get_db)) -> list[MaterialBatch]:
    return list(db.scalars(select(MaterialBatch).order_by(MaterialBatch.batch_no)))


@router.get("/material-batches/{batch_id}", response_model=MaterialBatchRead)
def get_material_batch(batch_id: str, db: Session = Depends(get_db)) -> MaterialBatch:
    return _required(db, MaterialBatch, batch_id, "材料批次")


@router.patch("/material-batches/{batch_id}", response_model=MaterialBatchRead)
def update_material_batch(
    batch_id: str, payload: MaterialBatchUpdate, db: Session = Depends(get_db)
) -> MaterialBatch:
    batch = _required(db, MaterialBatch, batch_id, "材料批次")
    changes = payload.model_dump(exclude_unset=True)
    _validate_mapping_scope(changes.get("coa_values"), "材料 COA")
    if "batch_no" in changes and db.scalar(
        select(MaterialBatch).where(
            MaterialBatch.batch_no == changes["batch_no"],
            MaterialBatch.id != batch_id,
        )
    ):
        raise HTTPException(status_code=409, detail="材料批次号已存在")
    for field, value in changes.items():
        setattr(batch, field, value)
    return _save(db, batch)


@router.delete("/material-batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_batch(batch_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, _required(db, MaterialBatch, batch_id, "材料批次"), "材料批次")


@router.post("/production-runs", response_model=ProductionRunRead, status_code=status.HTTP_201_CREATED)
def create_production_run(payload: ProductionRunCreate, db: Session = Depends(get_db)) -> ProductionRun:
    _validate_mapping_scope(payload.context_values, "生产事件上下文")
    check_fk(db, Factory, payload.factory_id, label="工厂")
    check_fk(db, VehicleModel, payload.vehicle_model_id, label="车型")
    check_fk(db, Color, payload.color_id, label="颜色")
    _validate_production_run_context(
        db,
        payload.factory_id,
        payload.vehicle_model_id,
        payload.color_id,
    )
    if db.scalar(select(ProductionRun).where(ProductionRun.run_no == payload.run_no)):
        raise HTTPException(status_code=409, detail="生产事件编号已存在")
    return _save(db, ProductionRun(**payload.model_dump()))


@router.get("/production-runs", response_model=list[ProductionRunRead])
def list_production_runs(limit: int = 100, db: Session = Depends(get_db)) -> list[ProductionRun]:
    return list(
        db.scalars(
            select(ProductionRun)
            .order_by(ProductionRun.started_at.desc())
            .limit(min(max(limit, 1), 500))
        )
    )


@router.get("/production-runs/{production_run_id}", response_model=ProductionRunRead)
def get_production_run(production_run_id: str, db: Session = Depends(get_db)) -> ProductionRun:
    return _required(db, ProductionRun, production_run_id, "生产事件")


@router.patch("/production-runs/{production_run_id}", response_model=ProductionRunRead)
def update_production_run(
    production_run_id: str,
    payload: ProductionRunUpdate,
    db: Session = Depends(get_db),
) -> ProductionRun:
    production_run = _required(db, ProductionRun, production_run_id, "生产事件")
    changes = payload.model_dump(exclude_unset=True)
    _validate_mapping_scope(changes.get("context_values"), "生产事件上下文")
    if "run_no" in changes and db.scalar(
        select(ProductionRun).where(
            ProductionRun.run_no == changes["run_no"],
            ProductionRun.id != production_run_id,
        )
    ):
        raise HTTPException(status_code=409, detail="生产事件编号已存在")
    for field, model, label in (
        ("factory_id", Factory, "工厂"),
        ("vehicle_model_id", VehicleModel, "车型"),
        ("color_id", Color, "颜色"),
    ):
        if changes.get(field):
            _required(db, model, changes[field], label)
    _validate_production_run_context(
        db,
        changes.get("factory_id", production_run.factory_id),
        changes.get("vehicle_model_id", production_run.vehicle_model_id),
        changes.get("color_id", production_run.color_id),
    )
    for field, value in changes.items():
        setattr(production_run, field, value)
    return _save(db, production_run)


@router.delete("/production-runs/{production_run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_run(production_run_id: str, db: Session = Depends(get_db)) -> Response:
    production_run = _required(db, ProductionRun, production_run_id, "生产事件")
    return _delete_resource(db, production_run, "生产事件")


@router.post(
    "/production-runs/{production_run_id}/stages",
    response_model=ProductionStageRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_production_stage_run(
    production_run_id: str, payload: ProductionStageRunCreate, db: Session = Depends(get_db)
) -> ProductionStageRun:
    _validate_process_stage(payload.process_stage)
    _validate_mapping_scope(payload.actual_parameters, "工序汇总参数")
    production_run = _required(db, ProductionRun, production_run_id, "生产事件")
    if db.scalar(
        select(ProductionStageRun).where(
            ProductionStageRun.production_run_id == production_run_id,
            ProductionStageRun.process_stage == payload.process_stage,
        )
    ):
        raise HTTPException(status_code=409, detail="生产事件工艺阶段已存在")
    _validate_stage_run_context(
        db,
        production_run,
        payload.process_stage,
        payload.program_version_id,
        payload.material_batch_id,
    )
    return _save(db, ProductionStageRun(production_run_id=production_run_id, **payload.model_dump()))


@router.get(
    "/production-runs/{production_run_id}/stages",
    response_model=list[ProductionStageRunRead],
)
def list_production_stage_runs(
    production_run_id: str, db: Session = Depends(get_db)
) -> list[ProductionStageRun]:
    return list(
        db.scalars(
            select(ProductionStageRun).where(
                ProductionStageRun.production_run_id == production_run_id
            )
        )
    )


@router.get("/production-stage-runs/{stage_run_id}", response_model=ProductionStageRunRead)
def get_production_stage_run(
    stage_run_id: str, db: Session = Depends(get_db)
) -> ProductionStageRun:
    return _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩")


@router.patch("/production-stage-runs/{stage_run_id}", response_model=ProductionStageRunRead)
def update_production_stage_run(
    stage_run_id: str,
    payload: ProductionStageRunUpdate,
    db: Session = Depends(get_db),
) -> ProductionStageRun:
    stage_run = _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩")
    changes = payload.model_dump(exclude_unset=True)
    process_stage = changes.get("process_stage", stage_run.process_stage)
    _validate_process_stage(process_stage)
    _validate_mapping_scope(changes.get("actual_parameters"), "工序汇总参数")
    if db.scalar(
        select(ProductionStageRun).where(
            ProductionStageRun.production_run_id == stage_run.production_run_id,
            ProductionStageRun.process_stage == process_stage,
            ProductionStageRun.id != stage_run_id,
        )
    ):
        raise HTTPException(status_code=409, detail="生产事件工艺阶段已存在")
    production_run = _required(db, ProductionRun, stage_run.production_run_id, "生产事件")
    _validate_stage_run_context(
        db,
        production_run,
        process_stage,
        changes.get("program_version_id", stage_run.program_version_id),
        changes.get("material_batch_id", stage_run.material_batch_id),
    )
    for field, value in changes.items():
        setattr(stage_run, field, value)
    return _save(db, stage_run)


@router.delete("/production-stage-runs/{stage_run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_stage_run(stage_run_id: str, db: Session = Depends(get_db)) -> Response:
    stage_run = _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩")
    return _delete_resource(db, stage_run, "工艺阶段实绩")


@router.post(
    "/production-stage-runs/{stage_run_id}/actual-parameters",
    response_model=ActualParameterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_actual_parameter(
    stage_run_id: str, payload: ActualParameterCreate, db: Session = Depends(get_db)
) -> ActualParameter:
    _validate_parameter_scope(payload.parameter_code)
    check_fk(db, ProductionStageRun, stage_run_id, label="工艺阶段实绩")
    if payload.brush_id:
        check_fk(db, Brush, payload.brush_id, label="刷子")
    if payload.parameter_definition_id:
        check_fk(db, ParameterDefinition, payload.parameter_definition_id, label="参数定义")
    return _save(db, ActualParameter(production_stage_run_id=stage_run_id, **payload.model_dump()))


@router.get(
    "/production-stage-runs/{stage_run_id}/actual-parameters",
    response_model=list[ActualParameterRead],
)
def list_actual_parameters(
    stage_run_id: str, db: Session = Depends(get_db)
) -> list[ActualParameter]:
    _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩")
    return list(
        db.scalars(
            select(ActualParameter)
            .where(ActualParameter.production_stage_run_id == stage_run_id)
            .order_by(ActualParameter.sampled_at.desc(), ActualParameter.parameter_code)
        )
    )


@router.get("/actual-parameters/{parameter_id}", response_model=ActualParameterRead)
def get_actual_parameter(parameter_id: str, db: Session = Depends(get_db)) -> ActualParameter:
    return _required(db, ActualParameter, parameter_id, "实际参数")


@router.patch("/actual-parameters/{parameter_id}", response_model=ActualParameterRead)
def update_actual_parameter(
    parameter_id: str,
    payload: ActualParameterUpdate,
    db: Session = Depends(get_db),
) -> ActualParameter:
    parameter = _required(db, ActualParameter, parameter_id, "实际参数")
    changes = payload.model_dump(exclude_unset=True)
    _validate_parameter_scope(changes.get("parameter_code", parameter.parameter_code))
    if changes.get("brush_id"):
        _required(db, Brush, changes["brush_id"], "刷子")
    if changes.get("parameter_definition_id"):
        _required(db, ParameterDefinition, changes["parameter_definition_id"], "参数定义")
    for field, value in changes.items():
        setattr(parameter, field, value)
    return _save(db, parameter)


@router.delete("/actual-parameters/{parameter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_actual_parameter(parameter_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(
        db,
        _required(db, ActualParameter, parameter_id, "实际参数"),
        "实际参数",
    )


@router.get("/overview-summary", response_model=ProcessOverviewSummary)
def process_overview_summary(db: Session = Depends(get_db)) -> ProcessOverviewSummary:
    total_runs = int(db.scalar(select(func.count()).select_from(ProductionRun)) or 0)
    active_runs = int(
        db.scalar(
            select(func.count())
            .select_from(ProductionRun)
            .where(ProductionRun.completed_at.is_(None))
        )
        or 0
    )

    stage_summaries: list[ProcessOverviewStageSummary] = []
    for stage in ProcessStage:
        run_count = int(
            db.scalar(
                select(func.count())
                .select_from(ProductionStageRun)
                .where(ProductionStageRun.process_stage == stage.value)
            )
            or 0
        )
        stage_summaries.append(
            ProcessOverviewStageSummary(
                code=stage.value,
                name=PROCESS_STAGE_LABELS.get(stage, stage.value),
                healthy=run_count > 0,
                run_count=run_count,
            )
        )

    program_versions_active = int(
        db.scalar(
            select(func.count())
            .select_from(SprayProgramVersion)
            .where(SprayProgramVersion.status == VersionStatus.ACTIVE)
        )
        or 0
    )
    program_versions_draft = int(
        db.scalar(
            select(func.count())
            .select_from(SprayProgramVersion)
            .where(SprayProgramVersion.status == VersionStatus.DRAFT)
        )
        or 0
    )

    open_issue_tasks = int(
        db.scalar(
            select(func.count())
            .select_from(QualityIssueTask)
            .where(QualityIssueTask.status.notin_(["VERIFIED", "CLOSED"]))
        )
        or 0
    )

    recent_run_rows = list(
        db.scalars(
            select(ProductionRun).order_by(ProductionRun.started_at.desc()).limit(3)
        )
    )
    recent_runs = [
        {
            "run_no": run.run_no,
            "body_no": run.body_no,
            "shift": run.shift,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
        for run in recent_run_rows
    ]

    return ProcessOverviewSummary(
        active_runs=active_runs,
        total_runs=total_runs,
        stages=stage_summaries,
        program_versions_active=program_versions_active,
        program_versions_draft=program_versions_draft,
        open_issue_tasks=open_issue_tasks,
        recent_runs=recent_runs,
    )
