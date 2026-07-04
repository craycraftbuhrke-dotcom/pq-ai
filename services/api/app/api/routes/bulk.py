from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
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
    db: Session = Depends(get_db),
) -> dict:
    return import_resource(
        resource_key,
        await request.body(),
        filename=filename,
        mode=mode,
        db=db,
    )
