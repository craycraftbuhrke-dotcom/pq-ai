from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.parameter_catalog import PARAMETER_CATALOG
from app.domain.scope_policy import ScopeViolation, is_out_of_scope_name, require_approved_mapping
from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    MaterialBatch,
    MeasurementPoint,
    ParameterDefinition,
    Part,
    ProcessStage,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramVehicleModel,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
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
    ProductionRunCreate,
    ProductionRunRead,
    ProductionRunUpdate,
    ProductionStageRunCreate,
    ProductionStageRunRead,
    ProductionStageRunUpdate,
    SprayProgramCreate,
    SprayProgramRead,
    SprayProgramUpdate,
    SprayProgramVersionCreate,
    SprayProgramVersionRead,
    SprayProgramVersionUpdate,
)

router = APIRouter(tags=["process-data"])


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
    try:
        db.delete(resource)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{label}已被生产数据或下游配置引用，请先解除关联",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
def seed_parameter_catalog(db: Session = Depends(get_db)) -> dict:
    existing_codes = set(db.scalars(select(ParameterDefinition.code)))
    resources = [
        ParameterDefinition(**definition)
        for definition in PARAMETER_CATALOG
        if definition["code"] not in existing_codes
    ]
    db.add_all(resources)
    db.commit()
    return {
        "catalog_size": len(PARAMETER_CATALOG),
        "created": len(resources),
        "existing": len(PARAMETER_CATALOG) - len(resources),
    }


@router.get("/spray-programs", response_model=list[SprayProgramRead])
def list_spray_programs(db: Session = Depends(get_db)) -> list[SprayProgram]:
    return list(db.scalars(select(SprayProgram).order_by(SprayProgram.program_code)))


@router.get("/spray-programs/{program_id}", response_model=SprayProgramRead)
def get_spray_program(program_id: str, db: Session = Depends(get_db)) -> SprayProgram:
    return _required(db, SprayProgram, program_id, "喷涂程序")


@router.post("/spray-programs", response_model=SprayProgramRead, status_code=status.HTTP_201_CREATED)
def create_spray_program(payload: SprayProgramCreate, db: Session = Depends(get_db)) -> SprayProgram:
    _validate_process_stage(payload.process_stage)
    _required(db, Factory, payload.factory_id, "工厂")
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
    return _delete_resource(db, _required(db, SprayProgram, program_id, "喷涂程序"), "喷涂程序")


@router.post(
    "/spray-programs/{program_id}/versions",
    response_model=SprayProgramVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_program_version(
    program_id: str, payload: SprayProgramVersionCreate, db: Session = Depends(get_db)
) -> SprayProgramVersion:
    _required(db, SprayProgram, program_id, "喷涂程序")
    if db.scalar(
        select(SprayProgramVersion).where(
            SprayProgramVersion.spray_program_id == program_id,
            SprayProgramVersion.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本已存在")
    for model_id in payload.vehicle_model_ids:
        _required(db, VehicleModel, model_id, "车型")
    for color_id in payload.color_ids:
        _required(db, Color, color_id, "颜色")

    version_data = payload.model_dump(exclude={"vehicle_model_ids", "color_ids"})
    version = SprayProgramVersion(spray_program_id=program_id, **version_data)
    db.add(version)
    db.flush()
    db.add_all(
        [
            ProgramVehicleModel(program_version_id=version.id, vehicle_model_id=model_id)
            for model_id in payload.vehicle_model_ids
        ]
        + [
            ProgramColor(program_version_id=version.id, color_id=color_id)
            for color_id in payload.color_ids
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

    vehicle_model_ids = changes.pop("vehicle_model_ids", None)
    color_ids = changes.pop("color_ids", None)
    if vehicle_model_ids is not None:
        for model_id in vehicle_model_ids:
            _required(db, VehicleModel, model_id, "车型")
        db.execute(delete(ProgramVehicleModel).where(ProgramVehicleModel.program_version_id == version_id))
        db.add_all(
            [
                ProgramVehicleModel(program_version_id=version_id, vehicle_model_id=model_id)
                for model_id in vehicle_model_ids
            ]
        )
    if color_ids is not None:
        for color_id in color_ids:
            _required(db, Color, color_id, "颜色")
        db.execute(delete(ProgramColor).where(ProgramColor.program_version_id == version_id))
        db.add_all(
            [
                ProgramColor(program_version_id=version_id, color_id=color_id)
                for color_id in color_ids
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
    version = _required(db, SprayProgramVersion, version_id, "程序版本")
    db.execute(delete(ProgramVehicleModel).where(ProgramVehicleModel.program_version_id == version_id))
    db.execute(delete(ProgramColor).where(ProgramColor.program_version_id == version_id))
    try:
        db.delete(version)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="程序版本已被刷子、生产实绩或下游数据引用，请先解除关联",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/program-versions/{version_id}/brushes",
    response_model=BrushRead,
    status_code=status.HTTP_201_CREATED,
)
def create_brush(version_id: str, payload: BrushCreate, db: Session = Depends(get_db)) -> Brush:
    _required(db, SprayProgramVersion, version_id, "程序版本")
    if payload.part_id:
        _required(db, Part, payload.part_id, "零件")
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
    return _delete_resource(db, _required(db, Brush, brush_id, "刷子"), "刷子")


@router.post(
    "/brushes/{brush_id}/parameters",
    response_model=BrushParameterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_brush_parameter(
    brush_id: str, payload: BrushParameterCreate, db: Session = Depends(get_db)
) -> BrushParameter:
    _validate_parameter_scope(payload.parameter_code, payload.parameter_name)
    _required(db, Brush, brush_id, "刷子")
    if payload.parameter_definition_id:
        _required(db, ParameterDefinition, payload.parameter_definition_id, "参数定义")
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
    _required(db, Brush, brush_id, "刷子")
    _required(db, MeasurementPoint, measurement_point_id, "测量点")
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
    _required(db, Factory, payload.factory_id, "工厂")
    _required(db, VehicleModel, payload.vehicle_model_id, "车型")
    _required(db, Color, payload.color_id, "颜色")
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
    for field, value in changes.items():
        setattr(production_run, field, value)
    return _save(db, production_run)


@router.delete("/production-runs/{production_run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_run(production_run_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(
        db,
        _required(db, ProductionRun, production_run_id, "生产事件"),
        "生产事件",
    )


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
    _required(db, ProductionRun, production_run_id, "生产事件")
    _required(db, SprayProgramVersion, payload.program_version_id, "程序版本")
    if payload.material_batch_id:
        _required(db, MaterialBatch, payload.material_batch_id, "材料批次")
    if db.scalar(
        select(ProductionStageRun).where(
            ProductionStageRun.production_run_id == production_run_id,
            ProductionStageRun.process_stage == payload.process_stage,
        )
    ):
        raise HTTPException(status_code=409, detail="生产事件工艺阶段已存在")
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
    if changes.get("program_version_id"):
        _required(db, SprayProgramVersion, changes["program_version_id"], "程序版本")
    if changes.get("material_batch_id"):
        _required(db, MaterialBatch, changes["material_batch_id"], "材料批次")
    for field, value in changes.items():
        setattr(stage_run, field, value)
    return _save(db, stage_run)


@router.delete("/production-stage-runs/{stage_run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_stage_run(stage_run_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(
        db,
        _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩"),
        "工艺阶段实绩",
    )


@router.post(
    "/production-stage-runs/{stage_run_id}/actual-parameters",
    response_model=ActualParameterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_actual_parameter(
    stage_run_id: str, payload: ActualParameterCreate, db: Session = Depends(get_db)
) -> ActualParameter:
    _validate_parameter_scope(payload.parameter_code)
    _required(db, ProductionStageRun, stage_run_id, "工艺阶段实绩")
    if payload.brush_id:
        _required(db, Brush, payload.brush_id, "刷子")
    if payload.parameter_definition_id:
        _required(db, ParameterDefinition, payload.parameter_definition_id, "参数定义")
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
