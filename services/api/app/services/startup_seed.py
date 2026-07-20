"""受控初始化任务使用的系统目录预置。

设计约束（非显而易见的 WHY）：

- **失败不阻断**：任何异常都被吞并写日志，避免 DB 暂时不可达时 pod 陷入
  CrashLoopBackOff。运维修好 DB 后触发一次重启即可补齐。
- **不做 DDL**：`db/session.py` 的运行时策略禁止 CREATE/DROP/ALTER；表结构必须
  由 DBA 通过 `docs/sql/pq_ai_mysql_schema.sql` 预先建好。本模块只做 INSERT。
- **系统字典**：质量指标 / 工艺参数由 catalog_seed 幂等补齐。
- **禁止演示数据**：本模块只维护系统目录，不写入任何业务示例记录。
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.catalog_seed import (
    seed_parameter_catalog,
    seed_quality_metric_catalog,
)

logger = logging.getLogger(__name__)


def _run(name: str, task) -> None:
    try:
        with SessionLocal() as db:
            result = task(db)
    except SQLAlchemyError:
        logger.exception("[startup-seed] %s 失败（数据库异常，进程继续启动）", name)
        return
    except Exception:  # noqa: BLE001 - 启动预置永远不能阻断进程
        logger.exception("[startup-seed] %s 失败（未预期异常，进程继续启动）", name)
        return

    if "catalog_size" in result:
        logger.info(
            "[startup-seed] %s OK  catalog=%d created=%d existing=%d",
            name,
            result["catalog_size"],
            result["created"],
            result["existing"],
        )
        return

    if result.get("skipped"):
        missing = result.get("missing_tables")
        if missing:
            logger.warning(
                "[startup-seed] %s skipped=true missing_tables=%s（请先按 docs/sql 建表）",
                name,
                ",".join(missing),
            )
        else:
            logger.info(
                "[startup-seed] %s OK  skipped=true marker=%s (已存在，不重复写入)",
                name,
                result.get("marker"),
            )
        return

    logger.info(
        "[startup-seed] %s OK  created=%d rows_per_model=%s marker=%s",
        name,
        result.get("created", 0),
        result.get("rows_per_model"),
        result.get("marker"),
    )


def run_startup_seed() -> None:
    logger.info("[startup-seed] 开始执行预置")
    _run("quality_metric_catalog", seed_quality_metric_catalog)
    _run("parameter_catalog", seed_parameter_catalog)
    logger.info("[startup-seed] 全部预置任务结束")


__all__ = ["run_startup_seed"]
