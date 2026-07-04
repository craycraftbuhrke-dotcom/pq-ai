"""
FastAPI dependency for automatic referential integrity validation.

Usage in route handlers:
    db: Session = Depends(get_db)
    check_fk(db, Factory, payload.factory_id, label="工厂")
    check_delete_safe(db, SprayProgram, SprayProgram.factory_id, factory_id, label="工厂")
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import HTTPException


def ensure_exists(
    db: Session,
    model: type,
    record_id: str | None,
    label: str,
) -> None:
    if record_id is None:
        return
    if not db.get(model, record_id):
        raise HTTPException(
            status_code=422,
            detail=f"{label} 不存在（ID: {record_id}），请检查关联数据是否正确",
        )


def ensure_not_referenced(
    db: Session,
    model: type,
    fk_column,
    record_id: str,
    label: str,
) -> None:
    count = db.scalar(select(func.count()).select_from(model).where(fk_column == record_id))
    if count:
        raise HTTPException(
            status_code=409,
            detail=f"无法删除：{label} 仍被 {count} 条下游数据引用，请先解除关联",
        )


def ensure_unique_in_scope(
    db: Session,
    model: type,
    filters: dict,
    label: str,
    exclude_id: str | None = None,
) -> None:
    query = select(model)
    for col, val in filters.items():
        if val is not None:
            query = query.where(col == val)
    if exclude_id:
        query = query.where(model.id != exclude_id)
    existing = db.scalar(query)
    if existing:
        raise HTTPException(status_code=409, detail=f"{label} 已存在（重复记录），请检查输入")


check_fk = ensure_exists
check_delete_safe = ensure_not_referenced
