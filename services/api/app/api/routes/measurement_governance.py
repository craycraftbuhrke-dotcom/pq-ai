from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referential_integrity import check_fk, check_delete_safe
from app.db.session import get_db
from app.domain.scope_policy import (
    ScopeViolation,
    require_approved_quality_type,
    require_approved_quality_types,
)
from app.models.domain import (
    MeasurementCalibrationRecord,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementReferenceStandard,
    QualityMeasurement,
)
from app.schemas.quality import (
    MeasurementCalibrationCreate,
    MeasurementCalibrationRead,
    MeasurementCalibrationUpdate,
    MeasurementImportProfileCreate,
    MeasurementImportProfileRead,
    MeasurementImportProfileUpdate,
    MeasurementInstrumentCreate,
    MeasurementInstrumentRead,
    MeasurementInstrumentUpdate,
    MeasurementMethodCreate,
    MeasurementMethodRead,
    MeasurementMethodUpdate,
    MeasurementReferenceStandardCreate,
    MeasurementReferenceStandardRead,
    MeasurementReferenceStandardUpdate,
)
from app.services.measurement_reliability import refresh_measurement_reliability

router = APIRouter(prefix="/quality/governance", tags=["measurement-governance"])


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _scope_quality_type(quality_type: str) -> None:
    try:
        require_approved_quality_type(quality_type)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _scope_quality_types(quality_types: list[str]) -> None:
    try:
        require_approved_quality_types(quality_types)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
        raise HTTPException(
            status_code=409,
            detail=f"{label}已被测量或校准记录引用，请停用或保留追溯",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _refresh_linked_measurements(db: Session, *conditions) -> None:
    if not conditions:
        return
    for measurement in db.scalars(select(QualityMeasurement).where(or_(*conditions))):
        refresh_measurement_reliability(db, measurement)
    db.commit()


def _validate_time_range(start: datetime | None, end: datetime | None, label: str) -> None:
    if start and end:
        start_utc = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
        end_utc = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
        if end_utc <= start_utc:
            raise HTTPException(status_code=422, detail=f"{label}结束时间必须晚于开始时间")


def _validate_calibration_relations(db: Session, values: dict) -> None:
    instrument = _required(db, MeasurementInstrument, values["instrument_id"], "测量仪器")
    method = (
        _required(db, MeasurementMethod, values["method_id"], "测量方法")
        if values.get("method_id")
        else None
    )
    reference = (
        _required(
            db,
            MeasurementReferenceStandard,
            values["reference_standard_id"],
            "参考件",
        )
        if values.get("reference_standard_id")
        else None
    )
    _validate_time_range(values["calibrated_at"], values["valid_until"], "校准有效期")
    if method and method.instrument_type != instrument.instrument_type:
        raise HTTPException(status_code=422, detail="校准方法与仪器类型不匹配")
    if method and reference and method.quality_type != reference.quality_type:
        raise HTTPException(status_code=422, detail="校准方法与参考件质量类型不匹配")


@router.get("/summary")
def measurement_governance_summary(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(UTC)
    return {
        "instruments": int(
            db.scalar(select(func.count()).select_from(MeasurementInstrument)) or 0
        ),
        "active_instruments": int(
            db.scalar(
                select(func.count())
                .select_from(MeasurementInstrument)
                .where(MeasurementInstrument.status == "ACTIVE")
            )
            or 0
        ),
        "methods": int(db.scalar(select(func.count()).select_from(MeasurementMethod)) or 0),
        "references": int(
            db.scalar(select(func.count()).select_from(MeasurementReferenceStandard)) or 0
        ),
        "calibrations": int(
            db.scalar(select(func.count()).select_from(MeasurementCalibrationRecord)) or 0
        ),
        "valid_calibrations": int(
            db.scalar(
                select(func.count())
                .select_from(MeasurementCalibrationRecord)
                .where(
                    MeasurementCalibrationRecord.result == "PASS",
                    MeasurementCalibrationRecord.valid_until >= now,
                )
            )
            or 0
        ),
        "import_profiles": int(
            db.scalar(select(func.count()).select_from(MeasurementImportProfile)) or 0
        ),
    }


@router.get("/instruments", response_model=list[MeasurementInstrumentRead])
def list_instruments(db: Session = Depends(get_db)) -> list[MeasurementInstrument]:
    return list(db.scalars(select(MeasurementInstrument).order_by(MeasurementInstrument.code)))


@router.post(
    "/instruments",
    response_model=MeasurementInstrumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_instrument(
    payload: MeasurementInstrumentCreate, db: Session = Depends(get_db)
) -> MeasurementInstrument:
    _scope_quality_types(payload.supported_quality_types)
    if db.scalar(
        select(MeasurementInstrument).where(
            or_(
                MeasurementInstrument.code == payload.code,
                MeasurementInstrument.serial_no == payload.serial_no,
            )
        )
    ):
        raise HTTPException(status_code=409, detail="仪器代码或序列号已存在")
    return _save(db, MeasurementInstrument(**payload.model_dump()))


@router.patch("/instruments/{instrument_id}", response_model=MeasurementInstrumentRead)
def update_instrument(
    instrument_id: str,
    payload: MeasurementInstrumentUpdate,
    db: Session = Depends(get_db),
) -> MeasurementInstrument:
    instrument = _required(db, MeasurementInstrument, instrument_id, "测量仪器")
    changes = payload.model_dump(exclude_unset=True)
    if "supported_quality_types" in changes:
        _scope_quality_types(changes["supported_quality_types"])
    code = changes.get("code", instrument.code)
    serial_no = changes.get("serial_no", instrument.serial_no)
    if db.scalar(
        select(MeasurementInstrument).where(
            MeasurementInstrument.id != instrument_id,
            or_(
                MeasurementInstrument.code == code,
                MeasurementInstrument.serial_no == serial_no,
            ),
        )
    ):
        raise HTTPException(status_code=409, detail="仪器代码或序列号已存在")
    for field, value in changes.items():
        setattr(instrument, field, value)
    db.flush()
    _refresh_linked_measurements(db, QualityMeasurement.instrument_id == instrument_id)
    db.refresh(instrument)
    return instrument


@router.delete("/instruments/{instrument_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instrument(instrument_id: str, db: Session = Depends(get_db)) -> Response:
    instrument = _required(db, MeasurementInstrument, instrument_id, "测量仪器")
    check_delete_safe(db, MeasurementCalibrationRecord, MeasurementCalibrationRecord.instrument_id, instrument_id, "测量仪器")
    check_delete_safe(db, QualityMeasurement, QualityMeasurement.instrument_id, instrument_id, "测量仪器")
    return _delete(db, instrument, "测量仪器")


@router.get("/methods", response_model=list[MeasurementMethodRead])
def list_methods(db: Session = Depends(get_db)) -> list[MeasurementMethod]:
    return list(db.scalars(select(MeasurementMethod).order_by(MeasurementMethod.code)))


@router.post("/methods", response_model=MeasurementMethodRead, status_code=status.HTTP_201_CREATED)
def create_method(payload: MeasurementMethodCreate, db: Session = Depends(get_db)) -> MeasurementMethod:
    _scope_quality_type(payload.quality_type)
    if db.scalar(
        select(MeasurementMethod).where(
            MeasurementMethod.code == payload.code,
            MeasurementMethod.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="测量方法代码与版本已存在")
    return _save(db, MeasurementMethod(**payload.model_dump()))


@router.patch("/methods/{method_id}", response_model=MeasurementMethodRead)
def update_method(
    method_id: str, payload: MeasurementMethodUpdate, db: Session = Depends(get_db)
) -> MeasurementMethod:
    method = _required(db, MeasurementMethod, method_id, "测量方法")
    changes = payload.model_dump(exclude_unset=True)
    _scope_quality_type(changes.get("quality_type", method.quality_type))
    code = changes.get("code", method.code)
    version = changes.get("version", method.version)
    if db.scalar(
        select(MeasurementMethod).where(
            MeasurementMethod.id != method_id,
            MeasurementMethod.code == code,
            MeasurementMethod.version == version,
        )
    ):
        raise HTTPException(status_code=409, detail="测量方法代码与版本已存在")
    for field, value in changes.items():
        setattr(method, field, value)
    db.flush()
    _refresh_linked_measurements(db, QualityMeasurement.measurement_method_id == method_id)
    db.refresh(method)
    return method


@router.delete("/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_method(method_id: str, db: Session = Depends(get_db)) -> Response:
    method = _required(db, MeasurementMethod, method_id, "测量方法")
    check_delete_safe(db, MeasurementCalibrationRecord, MeasurementCalibrationRecord.method_id, method_id, "测量方法")
    check_delete_safe(db, QualityMeasurement, QualityMeasurement.measurement_method_id, method_id, "测量方法")
    return _delete(db, method, "测量方法")


@router.get("/references", response_model=list[MeasurementReferenceStandardRead])
def list_references(db: Session = Depends(get_db)) -> list[MeasurementReferenceStandard]:
    return list(
        db.scalars(
            select(MeasurementReferenceStandard).order_by(MeasurementReferenceStandard.code)
        )
    )


@router.post(
    "/references",
    response_model=MeasurementReferenceStandardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_reference(
    payload: MeasurementReferenceStandardCreate, db: Session = Depends(get_db)
) -> MeasurementReferenceStandard:
    _scope_quality_type(payload.quality_type)
    _validate_time_range(payload.valid_from, payload.valid_until, "参考件有效期")
    if db.scalar(
        select(MeasurementReferenceStandard).where(
            MeasurementReferenceStandard.code == payload.code
        )
    ):
        raise HTTPException(status_code=409, detail="参考件代码已存在")
    return _save(db, MeasurementReferenceStandard(**payload.model_dump()))


@router.patch("/references/{reference_id}", response_model=MeasurementReferenceStandardRead)
def update_reference(
    reference_id: str,
    payload: MeasurementReferenceStandardUpdate,
    db: Session = Depends(get_db),
) -> MeasurementReferenceStandard:
    reference = _required(db, MeasurementReferenceStandard, reference_id, "参考件")
    changes = payload.model_dump(exclude_unset=True)
    _scope_quality_type(changes.get("quality_type", reference.quality_type))
    _validate_time_range(
        changes.get("valid_from", reference.valid_from),
        changes.get("valid_until", reference.valid_until),
        "参考件有效期",
    )
    if "code" in changes and db.scalar(
        select(MeasurementReferenceStandard).where(
            MeasurementReferenceStandard.code == changes["code"],
            MeasurementReferenceStandard.id != reference_id,
        )
    ):
        raise HTTPException(status_code=409, detail="参考件代码已存在")
    for field, value in changes.items():
        setattr(reference, field, value)
    db.flush()
    _refresh_linked_measurements(db, QualityMeasurement.reference_standard_id == reference_id)
    db.refresh(reference)
    return reference


@router.delete("/references/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(reference_id: str, db: Session = Depends(get_db)) -> Response:
    reference = _required(db, MeasurementReferenceStandard, reference_id, "参考件")
    check_delete_safe(db, MeasurementCalibrationRecord, MeasurementCalibrationRecord.reference_standard_id, reference_id, "参考件")
    check_delete_safe(db, QualityMeasurement, QualityMeasurement.reference_standard_id, reference_id, "参考件")
    return _delete(db, reference, "参考件")


@router.get("/import-profiles", response_model=list[MeasurementImportProfileRead])
def list_import_profiles(db: Session = Depends(get_db)) -> list[MeasurementImportProfile]:
    return list(
        db.scalars(
            select(MeasurementImportProfile).order_by(
                MeasurementImportProfile.code, MeasurementImportProfile.version
            )
        )
    )


@router.post(
    "/import-profiles",
    response_model=MeasurementImportProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def create_import_profile(
    payload: MeasurementImportProfileCreate, db: Session = Depends(get_db)
) -> MeasurementImportProfile:
    _scope_quality_type(payload.quality_type)
    if db.scalar(
        select(MeasurementImportProfile).where(
            MeasurementImportProfile.code == payload.code,
            MeasurementImportProfile.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="导入模板代码与版本已存在")
    return _save(db, MeasurementImportProfile(**payload.model_dump()))


@router.patch("/import-profiles/{profile_id}", response_model=MeasurementImportProfileRead)
def update_import_profile(
    profile_id: str,
    payload: MeasurementImportProfileUpdate,
    db: Session = Depends(get_db),
) -> MeasurementImportProfile:
    profile = _required(db, MeasurementImportProfile, profile_id, "导入模板")
    changes = payload.model_dump(exclude_unset=True)
    _scope_quality_type(changes.get("quality_type", profile.quality_type))
    code = changes.get("code", profile.code)
    version = changes.get("version", profile.version)
    if db.scalar(
        select(MeasurementImportProfile).where(
            MeasurementImportProfile.id != profile_id,
            MeasurementImportProfile.code == code,
            MeasurementImportProfile.version == version,
        )
    ):
        raise HTTPException(status_code=409, detail="导入模板代码与版本已存在")
    for field, value in changes.items():
        setattr(profile, field, value)
    db.flush()
    _refresh_linked_measurements(db, QualityMeasurement.import_profile_id == profile_id)
    db.refresh(profile)
    return profile


@router.delete("/import-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import_profile(profile_id: str, db: Session = Depends(get_db)) -> Response:
    profile = _required(db, MeasurementImportProfile, profile_id, "导入模板")
    check_delete_safe(db, QualityMeasurement, QualityMeasurement.import_profile_id, profile_id, "导入模板")
    return _delete(db, profile, "导入模板")


@router.get("/calibrations", response_model=list[MeasurementCalibrationRead])
def list_calibrations(db: Session = Depends(get_db)) -> list[MeasurementCalibrationRecord]:
    return list(
        db.scalars(
            select(MeasurementCalibrationRecord).order_by(
                MeasurementCalibrationRecord.calibrated_at.desc()
            )
        )
    )


@router.post(
    "/calibrations",
    response_model=MeasurementCalibrationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_calibration(
    payload: MeasurementCalibrationCreate, db: Session = Depends(get_db)
) -> MeasurementCalibrationRecord:
    check_fk(db, MeasurementInstrument, payload.instrument_id, label="测量仪器")
    if payload.method_id:
        check_fk(db, MeasurementMethod, payload.method_id, label="测量方法")
    if payload.reference_standard_id:
        check_fk(db, MeasurementReferenceStandard, payload.reference_standard_id, label="参考件")
    if db.scalar(
        select(MeasurementCalibrationRecord).where(
            MeasurementCalibrationRecord.calibration_no == payload.calibration_no
        )
    ):
        raise HTTPException(status_code=409, detail="校准/检查记录编号已存在")
    values = payload.model_dump()
    _validate_calibration_relations(db, values)
    return _save(db, MeasurementCalibrationRecord(**values))


@router.patch("/calibrations/{calibration_id}", response_model=MeasurementCalibrationRead)
def update_calibration(
    calibration_id: str,
    payload: MeasurementCalibrationUpdate,
    db: Session = Depends(get_db),
) -> MeasurementCalibrationRecord:
    calibration = _required(db, MeasurementCalibrationRecord, calibration_id, "校准/检查记录")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "instrument_id": calibration.instrument_id,
        "method_id": calibration.method_id,
        "reference_standard_id": calibration.reference_standard_id,
        "calibrated_at": calibration.calibrated_at,
        "valid_until": calibration.valid_until,
        **changes,
    }
    _validate_calibration_relations(db, values)
    if "calibration_no" in changes and db.scalar(
        select(MeasurementCalibrationRecord).where(
            MeasurementCalibrationRecord.calibration_no == changes["calibration_no"],
            MeasurementCalibrationRecord.id != calibration_id,
        )
    ):
        raise HTTPException(status_code=409, detail="校准/检查记录编号已存在")
    for field, value in changes.items():
        setattr(calibration, field, value)
    db.flush()
    _refresh_linked_measurements(db, QualityMeasurement.calibration_record_id == calibration_id)
    db.refresh(calibration)
    return calibration


@router.delete("/calibrations/{calibration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calibration(calibration_id: str, db: Session = Depends(get_db)) -> Response:
    calibration = _required(db, MeasurementCalibrationRecord, calibration_id, "校准/检查记录")
    check_delete_safe(db, QualityMeasurement, QualityMeasurement.calibration_record_id, calibration_id, "校准/检查记录")
    return _delete(db, calibration, "校准/检查记录")
