"""系统级固定字典的幂等 seed。

被三处共用：
- HTTP 接口 ``POST /quality/metric-definitions/seed-catalog``
- HTTP 接口 ``POST /process/parameter-definitions/seed-catalog``
- 进程启动时的 ``startup_seed.run_startup_seed`` 自动预置

统一封装在这里避免三份实现互相漂移（例如是否在无新增时 commit、返回结构的字段名等）。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.parameter_catalog import PARAMETER_CATALOG
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.models.domain import ParameterDefinition, QualityMetricDefinition


def seed_quality_metric_catalog(db: Session) -> dict:
    existing_keys = {
        (row[0], row[1])
        for row in db.execute(
            select(QualityMetricDefinition.quality_type, QualityMetricDefinition.code)
        )
    }
    to_insert = [
        QualityMetricDefinition(**definition)
        for definition in QUALITY_METRIC_CATALOG
        if (definition["quality_type"], definition["code"]) not in existing_keys
    ]
    if to_insert:
        db.add_all(to_insert)
        db.commit()
    return {
        "catalog_size": len(QUALITY_METRIC_CATALOG),
        "created": len(to_insert),
        "existing": len(QUALITY_METRIC_CATALOG) - len(to_insert),
    }


def seed_parameter_catalog(db: Session) -> dict:
    existing_codes = set(db.scalars(select(ParameterDefinition.code)))
    to_insert = [
        ParameterDefinition(**definition)
        for definition in PARAMETER_CATALOG
        if definition["code"] not in existing_codes
    ]
    if to_insert:
        db.add_all(to_insert)
        db.commit()
    return {
        "catalog_size": len(PARAMETER_CATALOG),
        "created": len(to_insert),
        "existing": len(PARAMETER_CATALOG) - len(to_insert),
    }


__all__ = ["seed_quality_metric_catalog", "seed_parameter_catalog"]
