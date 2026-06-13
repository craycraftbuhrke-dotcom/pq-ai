from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.scope_policy import (
    ScopeViolation,
    require_approved_quality_type,
    require_approved_quality_types,
)
from app.models.domain import (
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicApplicability,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MaterialTestMethod,
    ProcessStage,
)
from app.schemas.material import (
    MaterialBatchTestResultCreate,
    MaterialBatchTestResultRead,
    MaterialBatchTestResultUpdate,
    MaterialCharacteristicApplicabilityCreate,
    MaterialCharacteristicApplicabilityRead,
    MaterialCharacteristicApplicabilityUpdate,
    MaterialCharacteristicDefinitionCreate,
    MaterialCharacteristicDefinitionRead,
    MaterialCharacteristicDefinitionUpdate,
    MaterialSpecificationCreate,
    MaterialSpecificationRead,
    MaterialSpecificationUpdate,
    MaterialTestMethodCreate,
    MaterialTestMethodRead,
    MaterialTestMethodUpdate,
)
from app.services.material_governance import refresh_material_result_reliability

router = APIRouter(prefix="/material-governance", tags=["material-governance"])


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


def _delete(db: Session, resource, label: str) -> Response:
    try:
        db.delete(resource)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{label}已被材料结果或下游配置引用，请保留追溯") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _quality_type(value: str) -> None:
    try:
        require_approved_quality_type(value)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _quality_types(values: list[str]) -> None:
    try:
        require_approved_quality_types(values)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _process_stage(value: str) -> None:
    try:
        ProcessStage(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="材料适用工序不属于五个批准喷涂执行阶段") from exc


def _time_range(start: datetime | None, end: datetime | None) -> None:
    if start and end:
        start_value = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
        end_value = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
        if end_value <= start_value:
            raise HTTPException(status_code=422, detail="材料规格有效截止时间必须晚于开始时间")


def _validate_method(db: Session, values: dict) -> None:
    definition = _required(
        db,
        MaterialCharacteristicDefinition,
        values["characteristic_definition_id"],
        "材料特性定义",
    )
    if values["result_unit"] != definition.canonical_unit:
        raise HTTPException(status_code=422, detail="检测方法结果单位必须与材料特性规范单位一致")
    if values.get("status") == "ACTIVE" and not values.get("procedure_uri"):
        raise HTTPException(status_code=422, detail="生效材料检测方法必须维护批准规程来源")


def _validate_specification(db: Session, values: dict) -> None:
    definition = _required(
        db,
        MaterialCharacteristicDefinition,
        values["characteristic_definition_id"],
        "材料特性定义",
    )
    method = _required(db, MaterialTestMethod, values["method_id"], "材料检测方法")
    if method.characteristic_definition_id != definition.id:
        raise HTTPException(status_code=422, detail="材料规格的检测方法与特性定义不匹配")
    if (
        values.get("lower_limit") is not None
        and values.get("upper_limit") is not None
        and values["upper_limit"] < values["lower_limit"]
    ):
        raise HTTPException(status_code=422, detail="材料规格上限不能低于下限")
    _time_range(values.get("effective_from"), values.get("effective_to"))
    if values.get("status") in {"APPROVED", "ACTIVE"}:
        if not values.get("source_uri") or not values.get("effective_from") or not values.get(
            "approved_by"
        ):
            raise HTTPException(
                status_code=422,
                detail="批准或生效材料规格必须维护来源、生效时间和审批人",
            )


def _validate_applicability(db: Session, values: dict) -> None:
    definition = _required(
        db,
        MaterialCharacteristicDefinition,
        values["characteristic_definition_id"],
        "材料特性定义",
    )
    _process_stage(values["process_stage"])
    _quality_type(values["target_family"])
    if values["target_family"] not in definition.target_families:
        raise HTTPException(status_code=422, detail="目标族未包含在材料特性定义的批准目标族中")
    if values.get("status") in {"APPROVED", "ACTIVE"} and not values.get("approved_by"):
        raise HTTPException(status_code=422, detail="批准或生效材料适用关系必须维护审批人")


def _validate_result(db: Session, values: dict) -> None:
    _required(db, MaterialBatch, values["material_batch_id"], "材料批次")
    definition = _required(
        db,
        MaterialCharacteristicDefinition,
        values["characteristic_definition_id"],
        "材料特性定义",
    )
    method = _required(db, MaterialTestMethod, values["method_id"], "材料检测方法")
    if method.characteristic_definition_id != definition.id:
        raise HTTPException(status_code=422, detail="批次结果的检测方法与特性定义不匹配")


def _refresh_results(db: Session, *conditions) -> None:
    query = select(MaterialBatchTestResult)
    if conditions:
        query = query.where(*conditions)
    for result in db.scalars(query):
        refresh_material_result_reliability(db, result)
    db.commit()


def _approve(resource, status_value: str) -> None:
    if status_value in {"APPROVED", "ACTIVE"}:
        resource.approved_at = datetime.now(UTC)


@router.get("/summary")
def material_governance_summary(db: Session = Depends(get_db)) -> dict:
    def count(model: type) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "definitions": count(MaterialCharacteristicDefinition),
        "methods": count(MaterialTestMethod),
        "specifications": count(MaterialSpecification),
        "active_specifications": int(
            db.scalar(
                select(func.count())
                .select_from(MaterialSpecification)
                .where(MaterialSpecification.status == "ACTIVE")
            )
            or 0
        ),
        "applicabilities": count(MaterialCharacteristicApplicability),
        "active_applicabilities": int(
            db.scalar(
                select(func.count())
                .select_from(MaterialCharacteristicApplicability)
                .where(MaterialCharacteristicApplicability.status == "ACTIVE")
            )
            or 0
        ),
        "results": count(MaterialBatchTestResult),
        "verified_results": int(
            db.scalar(
                select(func.count())
                .select_from(MaterialBatchTestResult)
                .where(MaterialBatchTestResult.reliability_status == "VERIFIED")
            )
            or 0
        ),
        "failed_results": int(
            db.scalar(
                select(func.count())
                .select_from(MaterialBatchTestResult)
                .where(MaterialBatchTestResult.reliability_status == "FAILED")
            )
            or 0
        ),
    }


@router.get("/definitions", response_model=list[MaterialCharacteristicDefinitionRead])
def list_definitions(db: Session = Depends(get_db)) -> list[MaterialCharacteristicDefinition]:
    return list(db.scalars(select(MaterialCharacteristicDefinition).order_by(MaterialCharacteristicDefinition.code)))


@router.post("/definitions", response_model=MaterialCharacteristicDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_definition(payload: MaterialCharacteristicDefinitionCreate, db: Session = Depends(get_db)) -> MaterialCharacteristicDefinition:
    _quality_types(payload.target_families)
    if db.scalar(select(MaterialCharacteristicDefinition).where(MaterialCharacteristicDefinition.code == payload.code)):
        raise HTTPException(status_code=409, detail="材料特性代码已存在")
    return _save(db, MaterialCharacteristicDefinition(**payload.model_dump()))


@router.patch("/definitions/{resource_id}", response_model=MaterialCharacteristicDefinitionRead)
def update_definition(resource_id: str, payload: MaterialCharacteristicDefinitionUpdate, db: Session = Depends(get_db)) -> MaterialCharacteristicDefinition:
    resource = _required(db, MaterialCharacteristicDefinition, resource_id, "材料特性定义")
    changes = payload.model_dump(exclude_unset=True)
    _quality_types(changes.get("target_families", resource.target_families))
    if "code" in changes and db.scalar(select(MaterialCharacteristicDefinition).where(MaterialCharacteristicDefinition.code == changes["code"], MaterialCharacteristicDefinition.id != resource_id)):
        raise HTTPException(status_code=409, detail="材料特性代码已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    db.flush()
    _refresh_results(db, MaterialBatchTestResult.characteristic_definition_id == resource_id)
    db.refresh(resource)
    return resource


@router.delete("/definitions/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_definition(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(db, _required(db, MaterialCharacteristicDefinition, resource_id, "材料特性定义"), "材料特性定义")


@router.get("/methods", response_model=list[MaterialTestMethodRead])
def list_methods(db: Session = Depends(get_db)) -> list[MaterialTestMethod]:
    return list(db.scalars(select(MaterialTestMethod).order_by(MaterialTestMethod.code, MaterialTestMethod.version)))


@router.post("/methods", response_model=MaterialTestMethodRead, status_code=status.HTTP_201_CREATED)
def create_method(payload: MaterialTestMethodCreate, db: Session = Depends(get_db)) -> MaterialTestMethod:
    values = payload.model_dump()
    _validate_method(db, values)
    if db.scalar(select(MaterialTestMethod).where(MaterialTestMethod.code == payload.code, MaterialTestMethod.version == payload.version)):
        raise HTTPException(status_code=409, detail="材料检测方法代码与版本已存在")
    return _save(db, MaterialTestMethod(**values))


@router.patch("/methods/{resource_id}", response_model=MaterialTestMethodRead)
def update_method(resource_id: str, payload: MaterialTestMethodUpdate, db: Session = Depends(get_db)) -> MaterialTestMethod:
    resource = _required(db, MaterialTestMethod, resource_id, "材料检测方法")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "characteristic_definition_id": resource.characteristic_definition_id,
        "result_unit": resource.result_unit,
        "procedure_uri": resource.procedure_uri,
        "status": resource.status,
        **changes,
    }
    _validate_method(db, values)
    if db.scalar(select(MaterialTestMethod).where(MaterialTestMethod.code == changes.get("code", resource.code), MaterialTestMethod.version == changes.get("version", resource.version), MaterialTestMethod.id != resource_id)):
        raise HTTPException(status_code=409, detail="材料检测方法代码与版本已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    db.flush()
    _refresh_results(db, MaterialBatchTestResult.method_id == resource_id)
    db.refresh(resource)
    return resource


@router.delete("/methods/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_method(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(db, _required(db, MaterialTestMethod, resource_id, "材料检测方法"), "材料检测方法")


@router.get("/specifications", response_model=list[MaterialSpecificationRead])
def list_specifications(db: Session = Depends(get_db)) -> list[MaterialSpecification]:
    return list(db.scalars(select(MaterialSpecification).order_by(MaterialSpecification.material_code, MaterialSpecification.created_at.desc())))


@router.post("/specifications", response_model=MaterialSpecificationRead, status_code=status.HTTP_201_CREATED)
def create_specification(payload: MaterialSpecificationCreate, db: Session = Depends(get_db)) -> MaterialSpecification:
    values = payload.model_dump()
    _validate_specification(db, values)
    if db.scalar(select(MaterialSpecification).where(MaterialSpecification.material_code == payload.material_code, MaterialSpecification.characteristic_definition_id == payload.characteristic_definition_id, MaterialSpecification.method_id == payload.method_id, MaterialSpecification.version == payload.version)):
        raise HTTPException(status_code=409, detail="材料规格版本已存在")
    resource = MaterialSpecification(**values)
    _approve(resource, resource.status)
    if resource.status == "ACTIVE":
        for active in db.scalars(select(MaterialSpecification).where(MaterialSpecification.material_code == resource.material_code, MaterialSpecification.characteristic_definition_id == resource.characteristic_definition_id, MaterialSpecification.method_id == resource.method_id, MaterialSpecification.status == "ACTIVE")):
            active.status = "RETIRED"
    saved = _save(db, resource)
    _refresh_results(
        db,
        MaterialBatchTestResult.characteristic_definition_id
        == resource.characteristic_definition_id,
        MaterialBatchTestResult.method_id == resource.method_id,
    )
    return saved


@router.patch("/specifications/{resource_id}", response_model=MaterialSpecificationRead)
def update_specification(resource_id: str, payload: MaterialSpecificationUpdate, db: Session = Depends(get_db)) -> MaterialSpecification:
    resource = _required(db, MaterialSpecification, resource_id, "材料规格")
    old_definition_id = resource.characteristic_definition_id
    old_method_id = resource.method_id
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "material_code": resource.material_code,
        "characteristic_definition_id": resource.characteristic_definition_id,
        "method_id": resource.method_id,
        "version": resource.version,
        "lower_limit": resource.lower_limit,
        "upper_limit": resource.upper_limit,
        "effective_from": resource.effective_from,
        "effective_to": resource.effective_to,
        "status": resource.status,
        "source_uri": resource.source_uri,
        "approved_by": resource.approved_by,
        **changes,
    }
    _validate_specification(db, values)
    if db.scalar(select(MaterialSpecification).where(MaterialSpecification.material_code == values["material_code"], MaterialSpecification.characteristic_definition_id == values["characteristic_definition_id"], MaterialSpecification.method_id == values["method_id"], MaterialSpecification.version == values["version"], MaterialSpecification.id != resource_id)):
        raise HTTPException(status_code=409, detail="材料规格版本已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    _approve(resource, resource.status)
    if resource.status == "ACTIVE":
        for active in db.scalars(select(MaterialSpecification).where(MaterialSpecification.material_code == resource.material_code, MaterialSpecification.characteristic_definition_id == resource.characteristic_definition_id, MaterialSpecification.method_id == resource.method_id, MaterialSpecification.status == "ACTIVE", MaterialSpecification.id != resource_id)):
            active.status = "RETIRED"
    db.flush()
    affected_pairs = {
        (old_definition_id, old_method_id),
        (resource.characteristic_definition_id, resource.method_id),
    }
    for definition_id, method_id in affected_pairs:
        _refresh_results(
            db,
            MaterialBatchTestResult.characteristic_definition_id == definition_id,
            MaterialBatchTestResult.method_id == method_id,
        )
    db.refresh(resource)
    return resource


@router.delete("/specifications/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_specification(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(db, _required(db, MaterialSpecification, resource_id, "材料规格"), "材料规格")


@router.get("/applicabilities", response_model=list[MaterialCharacteristicApplicabilityRead])
def list_applicabilities(db: Session = Depends(get_db)) -> list[MaterialCharacteristicApplicability]:
    return list(db.scalars(select(MaterialCharacteristicApplicability).order_by(MaterialCharacteristicApplicability.process_stage, MaterialCharacteristicApplicability.target_family)))


@router.post("/applicabilities", response_model=MaterialCharacteristicApplicabilityRead, status_code=status.HTTP_201_CREATED)
def create_applicability(payload: MaterialCharacteristicApplicabilityCreate, db: Session = Depends(get_db)) -> MaterialCharacteristicApplicability:
    values = payload.model_dump()
    _validate_applicability(db, values)
    if db.scalar(select(MaterialCharacteristicApplicability).where(MaterialCharacteristicApplicability.characteristic_definition_id == payload.characteristic_definition_id, MaterialCharacteristicApplicability.material_type == payload.material_type, MaterialCharacteristicApplicability.process_stage == payload.process_stage, MaterialCharacteristicApplicability.target_family == payload.target_family)):
        raise HTTPException(status_code=409, detail="材料特性工序与目标族适用关系已存在")
    resource = MaterialCharacteristicApplicability(**values)
    _approve(resource, resource.status)
    return _save(db, resource)


@router.patch("/applicabilities/{resource_id}", response_model=MaterialCharacteristicApplicabilityRead)
def update_applicability(resource_id: str, payload: MaterialCharacteristicApplicabilityUpdate, db: Session = Depends(get_db)) -> MaterialCharacteristicApplicability:
    resource = _required(db, MaterialCharacteristicApplicability, resource_id, "材料适用关系")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "characteristic_definition_id": resource.characteristic_definition_id,
        "material_type": resource.material_type,
        "process_stage": resource.process_stage,
        "target_family": resource.target_family,
        "status": resource.status,
        "approved_by": resource.approved_by,
        **changes,
    }
    _validate_applicability(db, values)
    if db.scalar(select(MaterialCharacteristicApplicability).where(MaterialCharacteristicApplicability.characteristic_definition_id == values["characteristic_definition_id"], MaterialCharacteristicApplicability.material_type == values["material_type"], MaterialCharacteristicApplicability.process_stage == values["process_stage"], MaterialCharacteristicApplicability.target_family == values["target_family"], MaterialCharacteristicApplicability.id != resource_id)):
        raise HTTPException(status_code=409, detail="材料特性工序与目标族适用关系已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    _approve(resource, resource.status)
    return _save(db, resource)


@router.delete("/applicabilities/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_applicability(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(db, _required(db, MaterialCharacteristicApplicability, resource_id, "材料适用关系"), "材料适用关系")


@router.get("/results", response_model=list[MaterialBatchTestResultRead])
def list_results(material_batch_id: str | None = None, db: Session = Depends(get_db)) -> list[MaterialBatchTestResult]:
    query = select(MaterialBatchTestResult)
    if material_batch_id:
        query = query.where(MaterialBatchTestResult.material_batch_id == material_batch_id)
    return list(db.scalars(query.order_by(MaterialBatchTestResult.tested_at.desc())))


@router.post("/results", response_model=MaterialBatchTestResultRead, status_code=status.HTTP_201_CREATED)
def create_result(payload: MaterialBatchTestResultCreate, db: Session = Depends(get_db)) -> MaterialBatchTestResult:
    values = payload.model_dump()
    _validate_result(db, values)
    if db.scalar(select(MaterialBatchTestResult).where(MaterialBatchTestResult.result_no == payload.result_no)):
        raise HTTPException(status_code=409, detail="材料批次检测结果编号已存在")
    resource = MaterialBatchTestResult(**values)
    db.add(resource)
    db.flush()
    refresh_material_result_reliability(db, resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/results/{resource_id}", response_model=MaterialBatchTestResultRead)
def update_result(resource_id: str, payload: MaterialBatchTestResultUpdate, db: Session = Depends(get_db)) -> MaterialBatchTestResult:
    resource = _required(db, MaterialBatchTestResult, resource_id, "材料批次检测结果")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "material_batch_id": resource.material_batch_id,
        "characteristic_definition_id": resource.characteristic_definition_id,
        "method_id": resource.method_id,
        **changes,
    }
    _validate_result(db, values)
    if "result_no" in changes and db.scalar(select(MaterialBatchTestResult).where(MaterialBatchTestResult.result_no == changes["result_no"], MaterialBatchTestResult.id != resource_id)):
        raise HTTPException(status_code=409, detail="材料批次检测结果编号已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    refresh_material_result_reliability(db, resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/results/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(db, _required(db, MaterialBatchTestResult, resource_id, "材料批次检测结果"), "材料批次检测结果")
