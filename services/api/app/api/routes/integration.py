from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referential_integrity import check_fk, check_delete_safe
from app.db.session import get_db
from app.models.domain import IntegrationEndpoint, IntegrationEvent
from app.schemas.integration import (
    IntegrationEndpointCreate,
    IntegrationEndpointRead,
    IntegrationEndpointUpdate,
    IntegrationEventCreate,
    IntegrationEventRead,
)
from app.services.integration import process_integration_event

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


@router.get("/summary")
def integration_summary(db: Session = Depends(get_db)) -> dict:
    counts = {
        event_status: count
        for event_status, count in db.execute(
            select(IntegrationEvent.status, func.count()).group_by(IntegrationEvent.status)
        )
    }
    return {
        "endpoints": int(db.scalar(select(func.count()).select_from(IntegrationEndpoint)) or 0),
        "active_endpoints": int(
            db.scalar(
                select(func.count())
                .select_from(IntegrationEndpoint)
                .where(IntegrationEndpoint.is_active.is_(True))
            )
            or 0
        ),
        "events": int(db.scalar(select(func.count()).select_from(IntegrationEvent)) or 0),
        "events_by_status": counts,
        "failed_events": counts.get("FAILED", 0) + counts.get("DEAD_LETTER", 0),
    }


@router.get("/endpoints", response_model=list[IntegrationEndpointRead])
def list_endpoints(db: Session = Depends(get_db)) -> list[IntegrationEndpoint]:
    return list(db.scalars(select(IntegrationEndpoint).order_by(IntegrationEndpoint.code)))


@router.post(
    "/endpoints",
    response_model=IntegrationEndpointRead,
    status_code=status.HTTP_201_CREATED,
)
def create_endpoint(
    payload: IntegrationEndpointCreate, db: Session = Depends(get_db)
) -> IntegrationEndpoint:
    if db.scalar(select(IntegrationEndpoint).where(IntegrationEndpoint.code == payload.code)):
        raise HTTPException(status_code=409, detail="集成端点代码已存在")
    endpoint = IntegrationEndpoint(**payload.model_dump())
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.patch("/endpoints/{endpoint_id}", response_model=IntegrationEndpointRead)
def update_endpoint(
    endpoint_id: str,
    payload: IntegrationEndpointUpdate,
    db: Session = Depends(get_db),
) -> IntegrationEndpoint:
    endpoint = _required(db, IntegrationEndpoint, endpoint_id, "集成端点")
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes and db.scalar(
        select(IntegrationEndpoint).where(
            IntegrationEndpoint.code == changes["code"],
            IntegrationEndpoint.id != endpoint_id,
        )
    ):
        raise HTTPException(status_code=409, detail="集成端点代码已存在")
    for field, value in changes.items():
        setattr(endpoint, field, value)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(endpoint_id: str, db: Session = Depends(get_db)) -> Response:
    endpoint = _required(db, IntegrationEndpoint, endpoint_id, "集成端点")
    check_delete_safe(db, IntegrationEvent, IntegrationEvent.endpoint_id, endpoint_id, "集成端点")
    try:
        db.delete(endpoint)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="端点已有集成事件，请停用而不是删除") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/events", response_model=list[IntegrationEventRead])
def list_events(
    event_status: str | None = None,
    endpoint_id: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> list[IntegrationEvent]:
    query = select(IntegrationEvent).order_by(IntegrationEvent.created_at.desc())
    if event_status:
        query = query.where(IntegrationEvent.status == event_status)
    if endpoint_id:
        query = query.where(IntegrationEvent.endpoint_id == endpoint_id)
    return list(db.scalars(query.limit(min(max(limit, 1), 500))))


@router.get("/events/{event_id}", response_model=IntegrationEventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> IntegrationEvent:
    return _required(db, IntegrationEvent, event_id, "集成事件")


@router.post("/events", response_model=IntegrationEventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: IntegrationEventCreate, db: Session = Depends(get_db)) -> IntegrationEvent:
    check_fk(db, IntegrationEndpoint, payload.endpoint_id, label="集成端点")
    endpoint = _required(db, IntegrationEndpoint, payload.endpoint_id, "集成端点")
    if not endpoint.is_active:
        raise HTTPException(status_code=409, detail="集成端点已停用")
    existing = db.scalar(
        select(IntegrationEvent).where(
            IntegrationEvent.endpoint_id == payload.endpoint_id,
            IntegrationEvent.source_event_id == payload.source_event_id,
        )
    )
    if existing:
        return existing
    event = IntegrationEvent(
        event_no=f"INT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}",
        endpoint_id=payload.endpoint_id,
        source_event_id=payload.source_event_id,
        event_type=payload.event_type,
        direction=payload.direction,
        payload=payload.payload,
        max_attempts=payload.max_attempts,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return process_integration_event(db, event) if payload.process_immediately else event


@router.post("/events/{event_id}/process", response_model=IntegrationEventRead)
def process_event(event_id: str, db: Session = Depends(get_db)) -> IntegrationEvent:
    event = _required(db, IntegrationEvent, event_id, "集成事件")
    if event.status == "DEAD_LETTER":
        raise HTTPException(status_code=409, detail="死信事件需要使用重放操作")
    return process_integration_event(db, event)


@router.post("/events/{event_id}/replay", response_model=IntegrationEventRead)
def replay_event(event_id: str, db: Session = Depends(get_db)) -> IntegrationEvent:
    event = _required(db, IntegrationEvent, event_id, "集成事件")
    if event.status == "SUCCEEDED":
        raise HTTPException(status_code=409, detail="成功事件无需重放")
    event.status = "PENDING"
    event.last_error = None
    event.next_retry_at = None
    db.commit()
    return process_integration_event(db, event)
