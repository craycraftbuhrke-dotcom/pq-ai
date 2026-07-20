import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.bulk_io import (
    describe_bulk_columns,
    export_resource,
    import_resource,
    list_bulk_resources,
    render_template,
)
from app.services.request_body import read_limited_request_body

router = APIRouter(prefix="/bulk", tags=["bulk-import-export"])


def _parse_default_values(default_values: str | None) -> dict[str, Any] | None:
    if not default_values:
        return None
    try:
        payload = json.loads(default_values)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="页面自动带入内容格式不正确") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="页面自动带入内容格式不正确")
    return payload


@router.get("/resources")
def bulk_resources() -> list[dict[str, str | bool]]:
    return list_bulk_resources()


@router.get("/{resource_key}/columns")
def bulk_columns(
    resource_key: str,
    quality_type: str | None = Query(default=None),
) -> list[dict[str, str | bool]]:
    return describe_bulk_columns(resource_key, quality_type=quality_type)


@router.get("/{resource_key}/template")
def bulk_template(
    resource_key: str,
    file_format: Literal["csv", "xlsx"] = Query(default="xlsx", alias="format"),
    quality_type: str | None = Query(default=None),
    factory_code: str | None = Query(default=None),
    color_code: str | None = Query(default=None),
    vehicle_model_code: str | None = Query(default=None),
    shift: str | None = Query(default=None),
    brush_id: str | None = Query(default=None),
    default_values: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return render_template(
        resource_key,
        file_format,
        db=db,
        quality_type=quality_type,
        factory_code=factory_code,
        color_code=color_code,
        vehicle_model_code=vehicle_model_code,
        shift=shift,
        brush_id=brush_id,
        default_values=_parse_default_values(default_values),
    )


@router.get("/{resource_key}/export")
def bulk_export(
    resource_key: str,
    file_format: Literal["csv", "xlsx"] = Query(default="xlsx", alias="format"),
    quality_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return export_resource(resource_key, file_format, db, quality_type=quality_type)


@router.post("/{resource_key}/import")
async def bulk_import(
    resource_key: str,
    request: Request,
    filename: str = Query(default="bulk-import.csv"),
    mode: Literal["create", "upsert"] = "upsert",
    default_values: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    parsed_default_values = _parse_default_values(default_values)
    content = await read_limited_request_body(request, settings.bulk_import_max_bytes)
    return import_resource(
        resource_key,
        content,
        filename=filename,
        mode=mode,
        default_values=parsed_default_values,
        db=db,
    )
