from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    MeasurementPoint,
    Part,
    ProcessStage,
    ProductionRun,
    ProductionStageRun,
    QualityMeasurement,
    QualityMetricValue,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
)

STAGE_LABELS = {
    ProcessStage.MIDCOAT_EXT.value: "中涂外喷",
    ProcessStage.BASECOAT_1.value: "色漆一站",
    ProcessStage.BASECOAT_2.value: "色漆二站",
    ProcessStage.CLEARCOAT_1.value: "清漆一站",
    ProcessStage.CLEARCOAT_2.value: "清漆二站",
}


def point_optimization_workbench(
    db: Session, production_run_id: str, measurement_point_id: str
) -> dict:
    run = db.get(ProductionRun, production_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="生产记录不存在")
    point = db.get(MeasurementPoint, measurement_point_id)
    if not point:
        raise HTTPException(status_code=404, detail="测量点不存在")
    if point.vehicle_model_id != run.vehicle_model_id:
        raise HTTPException(status_code=422, detail="测量点不属于该生产记录的车型")
    factory = db.get(Factory, run.factory_id)
    vehicle_model = db.get(VehicleModel, run.vehicle_model_id)
    color = db.get(Color, run.color_id)
    part = db.get(Part, point.part_id) if point.part_id else None

    measurement_rows = db.execute(
        select(QualityMeasurement, QualityMetricValue)
        .join(QualityMetricValue, QualityMetricValue.measurement_id == QualityMeasurement.id)
        .where(
            QualityMeasurement.production_run_id == run.id,
            QualityMeasurement.measurement_point_id == point.id,
            QualityMeasurement.is_valid.is_(True),
        )
        .order_by(QualityMeasurement.measured_at.desc())
    ).all()
    quality_by_type: dict[str, dict] = {}
    for measurement, metric in measurement_rows:
        quality = quality_by_type.setdefault(
            measurement.quality_type,
            {
                "measurement_id": measurement.id,
                "data_no": measurement.data_no,
                "quality_type": measurement.quality_type,
                "measured_at": measurement.measured_at,
                "reliability_status": measurement.reliability_status,
                "metrics": [],
            },
        )
        if quality["measurement_id"] != measurement.id:
            continue
        quality["metrics"].append(
            {
                "code": metric.metric_code,
                "name": metric.metric_name,
                "value": (
                    metric.corrected_value
                    if metric.corrected_value is not None
                    else metric.raw_value
                ),
                "unit": metric.unit,
            }
        )

    stage_runs = {
        stage.process_stage: stage
        for stage in db.scalars(
            select(ProductionStageRun).where(ProductionStageRun.production_run_id == run.id)
        )
    }
    stages = []
    for stage_code, stage_label in STAGE_LABELS.items():
        stage_run = stage_runs.get(stage_code)
        if not stage_run:
            stages.append(
                {
                    "process_stage": stage_code,
                    "stage_name": stage_label,
                    "status": "MISSING",
                    "brushes": [],
                }
            )
            continue
        version = db.get(SprayProgramVersion, stage_run.program_version_id)
        program = db.get(SprayProgram, version.spray_program_id) if version else None
        brush_rows = db.execute(
            select(Brush, BrushPointContribution)
            .join(BrushPointContribution, BrushPointContribution.brush_id == Brush.id)
            .where(
                Brush.program_version_id == stage_run.program_version_id,
                BrushPointContribution.measurement_point_id == point.id,
            )
            .order_by(BrushPointContribution.contribution_weight.desc(), Brush.brush_no)
        ).all()
        brushes = []
        for brush, contribution in brush_rows:
            configured = list(
                db.scalars(
                    select(BrushParameter)
                    .where(BrushParameter.brush_id == brush.id)
                    .order_by(BrushParameter.parameter_code)
                )
            )
            actuals = {
                actual.parameter_code: actual
                for actual in db.scalars(
                    select(ActualParameter).where(
                        ActualParameter.production_stage_run_id == stage_run.id,
                        ActualParameter.brush_id == brush.id,
                    )
                )
            }
            brushes.append(
                {
                    "brush_id": brush.id,
                    "brush_no": brush.brush_no,
                    "brush_table_no": brush.brush_table_no,
                    "spray_position": brush.spray_position,
                    "contribution_weight": contribution.contribution_weight,
                    "overlap_ratio": contribution.overlap_ratio,
                    "contribution_source": contribution.source,
                    "contribution_approved": contribution.is_approved,
                    "parameters": [
                        {
                            "parameter_id": parameter.id,
                            "code": parameter.parameter_code,
                            "name": parameter.parameter_name,
                            "configured_value": parameter.configured_value,
                            "actual_value": (
                                actuals[parameter.parameter_code].actual_value
                                if parameter.parameter_code in actuals
                                else None
                            ),
                            "unit": parameter.unit,
                            "soft_min": parameter.soft_min,
                            "soft_max": parameter.soft_max,
                            "hard_min": parameter.hard_min,
                            "hard_max": parameter.hard_max,
                        }
                        for parameter in configured
                    ],
                }
            )
        stage_actuals = list(
            db.scalars(
                select(ActualParameter).where(
                    ActualParameter.production_stage_run_id == stage_run.id,
                    ActualParameter.brush_id.is_(None),
                )
            )
        )
        stages.append(
            {
                "process_stage": stage_code,
                "stage_name": stage_label,
                "status": stage_run.status,
                "stage_run_id": stage_run.id,
                "program_id": program.id if program else None,
                "program_code": program.program_code if program else None,
                "program_name": program.name if program else None,
                "program_version_id": version.id if version else None,
                "program_version": version.version if version else None,
                "station_code": program.station_code if program else None,
                "station_name": program.station_name if program else None,
                "brushes": brushes,
                "stage_actual_parameters": [
                    {
                        "code": actual.parameter_code,
                        "value": actual.actual_value,
                        "unit": actual.unit,
                    }
                    for actual in stage_actuals
                ],
            }
        )
    return {
        "production": {
            "id": run.id,
            "run_no": run.run_no,
            "body_no": run.body_no,
            "factory": {"id": run.factory_id, "code": factory.code, "name": factory.name},
            "vehicle_model": {
                "id": run.vehicle_model_id,
                "code": vehicle_model.code,
                "name": vehicle_model.name,
            },
            "color": {"id": run.color_id, "code": color.code, "name": color.name},
            "started_at": run.started_at,
        },
        "point": {
            "id": point.id,
            "code": point.code,
            "name": point.name,
            "area": point.region,
            "part": (
                {"id": part.id, "code": part.code, "name": part.name} if part else None
            ),
        },
        "quality": list(quality_by_type.values()),
        "stages": stages,
        "available_actions": ["DIAGNOSE", "RECOMMEND", "PREDICT", "MANUAL_EDIT"],
    }
