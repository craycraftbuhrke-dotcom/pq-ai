from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.process import seed_parameter_catalog
from app.api.routes.quality import seed_quality_metric_catalog
from app.db.base import Base
from app.domain.parameter_catalog import PARAMETER_CATALOG
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.models import domain  # noqa: F401
from app.models.domain import ParameterDefinition, QualityMetricDefinition


def test_authoritative_catalogs_cover_requested_process_and_quality_metrics() -> None:
    parameter_codes = {item["code"] for item in PARAMETER_CATALOG}
    assert len(PARAMETER_CATALOG) == 42
    assert {
        "midcoat_spray_flow",
        "basecoat_1_bell_speed",
        "basecoat_2_outer_air",
        "clearcoat_1_voltage",
        "clearcoat_2_inner_air",
        "basecoat_pass_ratio",
        "clearcoat_pass_ratio",
        "midcoat_viscosity",
        "basecoat_solid_ratio",
        "clearcoat_spray_speed",
    } <= parameter_codes

    metric_keys = {(item["quality_type"], item["code"]) for item in QUALITY_METRIC_CATALOG}
    assert {
        ("ORANGE_PEEL", "doi"),
        ("COLOR_DIFFERENCE", "de45"),
        ("COLOR_DIFFERENCE", "dsi75"),
        ("THICKNESS", "thickness_total"),
        ("THICKNESS", "thickness_clearcoat_pass2"),
    } <= metric_keys
    assert ("GLOSS", "gloss20") not in metric_keys
    assert ("COLOR_DIFFERENCE", "tempc") not in metric_keys
    assert ("THICKNESS", "thickness_ed") not in metric_keys


def test_catalog_seed_is_idempotent() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first_parameters = seed_parameter_catalog(db)
        second_parameters = seed_parameter_catalog(db)
        first_metrics = seed_quality_metric_catalog(db)
        second_metrics = seed_quality_metric_catalog(db)

        assert first_parameters["created"] == len(PARAMETER_CATALOG)
        assert second_parameters["created"] == 0
        assert first_metrics["created"] == len(QUALITY_METRIC_CATALOG)
        assert second_metrics["created"] == 0
        assert db.scalar(select(func.count()).select_from(ParameterDefinition)) == len(
            PARAMETER_CATALOG
        )
        assert db.scalar(select(func.count()).select_from(QualityMetricDefinition)) == len(
            QUALITY_METRIC_CATALOG
        )
