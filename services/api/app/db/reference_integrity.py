from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base


def logical_references_to(target_table_name: str) -> list[tuple[str, str]]:
    target = f"{target_table_name}.id"
    references: list[tuple[str, str]] = []
    for table in Base.metadata.tables.values():
        for column in table.c:
            if column.info.get("logical_fk") == target:
                references.append((table.name, column.name))
    return references


def ensure_not_referenced(
    db: Session,
    target_table_name: str,
    target_id: str,
    label: str,
    ignored_tables: Iterable[str] = (),
) -> None:
    ignored = set(ignored_tables)
    for table_name, column_name in logical_references_to(target_table_name):
        if table_name == target_table_name or table_name in ignored:
            continue
        table = Base.metadata.tables[table_name]
        column = table.c[column_name]
        select_column = table.c.get("id")
        if select_column is None:
            select_column = column
        existing = db.execute(select(select_column).where(column == target_id).limit(1)).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{label}已被 {table_name}.{column_name} 引用，不能物理删除；"
                    "请改用停用、归档、版本替换或先解除业务关联"
                ),
            )
