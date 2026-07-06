"""进程启动时的字典预置。

设计约束（非显而易见的 WHY）：

- **失败不阻断**：任何异常都被吞并写日志，避免 DB 暂时不可达时 pod 陷入
  CrashLoopBackOff。运维修好 DB 后触发一次重启即可补齐。
- **不做 DDL**：`db/session.py` 的运行时策略禁止 CREATE/DROP/ALTER；表结构必须
  由 DBA 通过 `docs/sql/pq_ai_mysql_schema.sql` 预先建好。本模块只做 INSERT。
- **只写系统级固定字典**：车型/零件/测量点/标准等业务数据不在此列，用户通过
  数据导入向导上传 Excel/CSV 完成。
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
    logger.info(
        "[startup-seed] %s OK  catalog=%d created=%d existing=%d",
        name,
        result["catalog_size"],
        result["created"],
        result["existing"],
    )


def run_startup_seed() -> None:
    logger.info("[startup-seed] 开始执行预置")
    _run("quality_metric_catalog", seed_quality_metric_catalog)
    _run("parameter_catalog", seed_parameter_catalog)
    logger.info("[startup-seed] 全部预置任务结束")


__all__ = ["run_startup_seed"]
