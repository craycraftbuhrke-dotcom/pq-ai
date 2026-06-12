from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.models.domain import (
    Color,
    MeasurementGroup,
    MeasurementPoint,
    Part,
    ProductionRun,
    QualityMeasurement,
    QualityMetricDefinition,
    QualityMetricValue,
    QualityStandard,
    VehicleModel,
)
from app.schemas.quality import (
    QualityMeasurementCreate,
    QualityMeasurementRead,
    QualityMeasurementUpdate,
    QualityMetricDefinitionRead,
    QualityStandardCreate,
    QualityStandardRead,
    QualityStandardUpdate,
    QualitySummary,
)
from app.services.quality_evaluation import evaluate_quality_measurement

router = APIRouter(prefix="/quality", tags=["quality-data"])


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _measurement_dict(
    measurement: QualityMeasurement,
    metrics: list[QualityMetricValue],
    point: MeasurementPoint,
    evaluation: dict,
) -> dict:
    return {
        "id": measurement.id,
        "created_at": measurement.created_at,
        "updated_at": measurement.updated_at,
        "data_no": measurement.data_no,
        "production_run_id": measurement.production_run_id,
        "measurement_group_id": measurement.measurement_group_id,
        "measurement_point_id": measurement.measurement_point_id,
        "measurement_point_code": point.code,
        "measurement_point_name": point.name,
        "quality_type": measurement.quality_type,
        "data_type": measurement.data_type,
        "measured_at": measurement.measured_at,
        "measured_by": measurement.measured_by,
        "device_code": measurement.device_code,
        "status_score": measurement.status_score,
        "is_valid": measurement.is_valid,
        "judgement": evaluation["judgement"],
        "violations": evaluation["violations"],
        "metrics": metrics,
    }


def _measurement_result(db: Session, measurement: QualityMeasurement) -> dict:
    metrics = list(
        db.scalars(
            select(QualityMetricValue)
            .where(QualityMetricValue.measurement_id == measurement.id)
            .order_by(QualityMetricValue.metric_code)
        )
    )
    point = _required(db, MeasurementPoint, measurement.measurement_point_id, "测量点")
    return _measurement_dict(
        measurement,
        metrics,
        point,
        evaluate_quality_measurement(db, measurement, metrics),
    )


@router.get("/summary", response_model=QualitySummary)
def quality_summary(db: Session = Depends(get_db)) -> dict:
    measurements = list(db.scalars(select(QualityMeasurement)))
    judgements = []
    for measurement in measurements:
        metrics = list(
            db.scalars(
                select(QualityMetricValue).where(
                    QualityMetricValue.measurement_id == measurement.id
                )
            )
        )
        judgements.append(evaluate_quality_measurement(db, measurement, metrics)["judgement"])
    by_type = {
        quality_type: count
        for quality_type, count in db.execute(
            select(QualityMeasurement.quality_type, func.count()).group_by(
                QualityMeasurement.quality_type
            )
        )
    }
    return {
        "measurements": int(db.scalar(select(func.count()).select_from(QualityMeasurement)) or 0),
        "valid_measurements": int(
            db.scalar(
                select(func.count())
                .select_from(QualityMeasurement)
                .where(QualityMeasurement.is_valid.is_(True))
            )
            or 0
        ),
        "metric_values": int(db.scalar(select(func.count()).select_from(QualityMetricValue)) or 0),
        "standards": int(db.scalar(select(func.count()).select_from(QualityStandard)) or 0),
        "pass_measurements": judgements.count("PASS"),
        "fail_measurements": judgements.count("FAIL"),
        "no_standard_measurements": judgements.count("NO_STANDARD"),
        "measurements_by_type": by_type,
    }


@router.get("/metric-definitions", response_model=list[QualityMetricDefinitionRead])
def list_quality_metric_definitions(db: Session = Depends(get_db)) -> list[QualityMetricDefinition]:
    return list(
        db.scalars(
            select(QualityMetricDefinition).order_by(QualityMetricDefinition.display_order)
        )
    )


@router.post("/metric-definitions/seed-catalog")
def seed_quality_metric_catalog(db: Session = Depends(get_db)) -> dict:
    existing = set(
        db.execute(
            select(QualityMetricDefinition.quality_type, QualityMetricDefinition.code)
        ).all()
    )
    resources = [
        QualityMetricDefinition(**definition)
        for definition in QUALITY_METRIC_CATALOG
        if (definition["quality_type"], definition["code"]) not in existing
    ]
    db.add_all(resources)
    db.commit()
    return {
        "catalog_size": len(QUALITY_METRIC_CATALOG),
        "created": len(resources),
        "existing": len(QUALITY_METRIC_CATALOG) - len(resources),
    }


@router.get("/measurements", response_model=list[QualityMeasurementRead])
def list_quality_measurements(
    limit: int = 100,
    quality_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(QualityMeasurement).order_by(QualityMeasurement.measured_at.desc())
    if quality_type:
        query = query.where(QualityMeasurement.quality_type == quality_type)
    measurements = list(
        db.scalars(query.limit(min(max(limit, 1), 500)))
    )
    return [_measurement_result(db, measurement) for measurement in measurements]


@router.get("/measurements/{measurement_id}", response_model=QualityMeasurementRead)
def get_quality_measurement(
    measurement_id: str, db: Session = Depends(get_db)
) -> dict:
    return _measurement_result(
        db,
        _required(db, QualityMeasurement, measurement_id, "质量数据"),
    )


@router.post(
    "/measurements",
    response_model=QualityMeasurementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_measurement(
    payload: QualityMeasurementCreate, db: Session = Depends(get_db)
) -> dict:
    if db.scalar(select(QualityMeasurement).where(QualityMeasurement.data_no == payload.data_no)):
        raise HTTPException(status_code=409, detail="质量数据编号已存在")
    if not db.get(ProductionRun, payload.production_run_id):
        raise HTTPException(status_code=404, detail="生产事件不存在")
    point = db.get(MeasurementPoint, payload.measurement_point_id)
    if not point:
        raise HTTPException(status_code=404, detail="测量点不存在")
    if payload.measurement_group_id and not db.get(MeasurementGroup, payload.measurement_group_id):
        raise HTTPException(status_code=404, detail="测量编组不存在")

    measurement_data = payload.model_dump(exclude={"metrics"})
    measurement = QualityMeasurement(**measurement_data)
    db.add(measurement)
    db.flush()
    metrics = [
        QualityMetricValue(measurement_id=measurement.id, **metric.model_dump())
        for metric in payload.metrics
    ]
    db.add_all(metrics)
    db.commit()
    db.refresh(measurement)
    for metric in metrics:
        db.refresh(metric)
    return _measurement_dict(
        measurement, metrics, point, evaluate_quality_measurement(db, measurement, metrics)
    )


@router.patch("/measurements/{measurement_id}", response_model=QualityMeasurementRead)
def update_quality_measurement(
    measurement_id: str,
    payload: QualityMeasurementUpdate,
    db: Session = Depends(get_db),
) -> dict:
    measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
    changes = payload.model_dump(exclude_unset=True)
    metrics_payload = changes.pop("metrics", None)
    if "data_no" in changes:
        duplicate = db.scalar(
            select(QualityMeasurement).where(
                QualityMeasurement.data_no == changes["data_no"],
                QualityMeasurement.id != measurement_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="质量数据编号已存在")
    if "production_run_id" in changes:
        _required(db, ProductionRun, changes["production_run_id"], "生产事件")
    if "measurement_point_id" in changes:
        _required(db, MeasurementPoint, changes["measurement_point_id"], "测量点")
    if changes.get("measurement_group_id"):
        _required(db, MeasurementGroup, changes["measurement_group_id"], "测量编组")
    for field, value in changes.items():
        setattr(measurement, field, value)
    if metrics_payload is not None:
        db.execute(delete(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement_id))
        db.add_all(
            [
                QualityMetricValue(measurement_id=measurement_id, **metric)
                for metric in metrics_payload
            ]
        )
    db.commit()
    db.refresh(measurement)
    return _measurement_result(db, measurement)


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quality_measurement(
    measurement_id: str, db: Session = Depends(get_db)
) -> Response:
    measurement = _required(db, QualityMeasurement, measurement_id, "质量数据")
    try:
        db.execute(delete(QualityMetricValue).where(QualityMetricValue.measurement_id == measurement_id))
        db.delete(measurement)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="质量数据已被模型快照或闭环复测引用，不能删除",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/standards", response_model=list[QualityStandardRead])
def list_quality_standards(db: Session = Depends(get_db)) -> list[QualityStandard]:
    return list(db.scalars(select(QualityStandard).order_by(QualityStandard.standard_no)))


@router.get("/standards/{standard_id}", response_model=QualityStandardRead)
def get_quality_standard(
    standard_id: str, db: Session = Depends(get_db)
) -> QualityStandard:
    return _required(db, QualityStandard, standard_id, "质量标准")


@router.post(
    "/standards",
    response_model=QualityStandardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_standard(
    payload: QualityStandardCreate, db: Session = Depends(get_db)
) -> QualityStandard:
    _validate_standard_relations(db, payload.model_dump())
    standard = QualityStandard(**payload.model_dump())
    db.add(standard)
    db.commit()
    db.refresh(standard)
    return standard


def _validate_standard_relations(db: Session, values: dict) -> None:
    for field, model, label in (
        ("vehicle_model_id", VehicleModel, "车型"),
        ("color_id", Color, "颜色"),
        ("part_id", Part, "零件"),
        ("measurement_point_id", MeasurementPoint, "测量点"),
    ):
        if values.get(field):
            _required(db, model, values[field], label)
    minimum = values.get("min_value")
    maximum = values.get("max_value")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(status_code=422, detail="质量标准下限不能大于上限")


@router.patch("/standards/{standard_id}", response_model=QualityStandardRead)
def update_quality_standard(
    standard_id: str,
    payload: QualityStandardUpdate,
    db: Session = Depends(get_db),
) -> QualityStandard:
    standard = _required(db, QualityStandard, standard_id, "质量标准")
    changes = payload.model_dump(exclude_unset=True)
    merged = {
        "vehicle_model_id": standard.vehicle_model_id,
        "color_id": standard.color_id,
        "part_id": standard.part_id,
        "measurement_point_id": standard.measurement_point_id,
        "min_value": standard.min_value,
        "max_value": standard.max_value,
        **changes,
    }
    _validate_standard_relations(db, merged)
    for field, value in changes.items():
        setattr(standard, field, value)
    db.commit()
    db.refresh(standard)
    return standard


@router.delete("/standards/{standard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quality_standard(
    standard_id: str, db: Session = Depends(get_db)
) -> Response:
    standard = _required(db, QualityStandard, standard_id, "质量标准")
    db.delete(standard)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
