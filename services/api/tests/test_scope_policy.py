from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.factories import create_factory
from app.api.routes.master_data import create_measurement_group
from app.api.routes.process import create_production_run
from app.api.routes.quality import create_quality_standard
from tests.schema_guard import create_transient_test_schema
from app.domain.scope_policy import (
    CURRENT_FEATURE_SET_VERSION,
    ScopeViolation,
    approved_numeric_values,
    require_scope_safe_model,
)
from app.models.domain import Color, VehicleModel
from app.schemas.common import FactoryCreate
from app.schemas.master_data import MeasurementGroupCreate
from app.schemas.process import ProductionRunCreate
from app.schemas.quality import QualityStandardCreate


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_scope_policy_filters_legacy_features_and_rejects_legacy_models() -> None:
    assert approved_numeric_values(
        {
            "clearcoat_2_spray_flow": 320.0,
            "booth_temperature": 24.5,
            "gloss20": 88.0,
        }
    ) == {"clearcoat_2_spray_flow": 320.0}

    with pytest.raises(ScopeViolation):
        require_scope_safe_model("doi", "point-features-v1", ["clearcoat_2_spray_flow"])

    require_scope_safe_model(
        "doi",
        CURRENT_FEATURE_SET_VERSION,
        ["clearcoat_2.clearcoat_2_spray_flow"],
    )


def test_scope_policy_rejects_out_of_scope_master_process_and_quality_writes() -> None:
    db = build_session()
    factory = create_factory(FactoryCreate(code="F-SCOPE", name="范围工厂"), db)
    vehicle = VehicleModel(code="M-SCOPE", name="范围车型")
    color = Color(code="C-SCOPE", name="范围颜色", color_type="BASECOAT")
    db.add_all([vehicle, color])
    db.commit()

    with pytest.raises(HTTPException) as group_error:
        create_measurement_group(
            MeasurementGroupCreate(
                code="G-GLOSS",
                name="越界光泽度编组",
                vehicle_model_id=vehicle.id,
                quality_type="GLOSS",
            ),
            db,
        )
    assert group_error.value.status_code == 422

    with pytest.raises(HTTPException) as run_error:
        create_production_run(
            ProductionRunCreate(
                run_no="RUN-SCOPE",
                factory_id=factory.id,
                vehicle_model_id=vehicle.id,
                color_id=color.id,
                started_at=datetime.now(UTC),
                context_values={"booth_humidity": 62.0},
            ),
            db,
        )
    assert run_error.value.status_code == 422

    with pytest.raises(HTTPException) as standard_error:
        create_quality_standard(
            QualityStandardCreate(
                standard_no="STD-ED",
                version="1",
                quality_type="THICKNESS",
                metric_code="thickness_ed",
                min_value=15,
                max_value=25,
            ),
            db,
        )
    assert standard_error.value.status_code == 422
    db.close()
