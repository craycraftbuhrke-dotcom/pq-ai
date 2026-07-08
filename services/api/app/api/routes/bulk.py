import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.bulk_io import (
    export_resource,
    import_resource,
    list_bulk_resources,
    render_template,
)

router = APIRouter(prefix="/bulk", tags=["bulk-import-export"])


@router.get("/resources")
def bulk_resources() -> list[dict[str, str | bool]]:
    return list_bulk_resources()


@router.get("/{resource_key}/template")
def bulk_template(
    resource_key: str,
    file_format: Literal["csv", "xlsx"] = Query(default="xlsx", alias="format"),
):
    return render_template(resource_key, file_format)


@router.get("/{resource_key}/export")
def bulk_export(
    resource_key: str,
    file_format: Literal["csv", "xlsx"] = Query(default="xlsx", alias="format"),
    db: Session = Depends(get_db),
):
    return export_resource(resource_key, file_format, db)


@router.post("/{resource_key}/import")
async def bulk_import(
    resource_key: str,
    request: Request,
    filename: str = Query(default="bulk-import.csv"),
    mode: Literal["create", "upsert"] = "upsert",
    default_values: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    parsed_default_values: dict[str, Any] | None = None
    if default_values:
        try:
            payload = json.loads(default_values)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="default_values 必须是合法 JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="default_values 必须是 JSON 对象")
        parsed_default_values = payload
    return import_resource(
        resource_key,
        await request.body(),
        filename=filename,
        mode=mode,
        default_values=parsed_default_values,
        db=db,
    )
