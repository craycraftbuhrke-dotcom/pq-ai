from datetime import UTC, datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.referential_integrity import check_fk
from app.db.session import get_db
from app.models.domain import (
    Factory,
    RemoteParameterSnapshot,
    RemoteProgramRelease,
    RemoteReleaseEvent,
    RemoteStationConnection,
    RemoteStationReconciliation,
)
from app.schemas.remote_station import (
    RemoteParameterSnapshotRead,
    RemoteProgramReleaseRead,
    RemoteReconciliationRead,
    RemoteReleaseAction,
    RemoteReleaseCreate,
    RemoteReleaseEventRead,
    RemoteSnapshotCapture,
    RemoteStationApproval,
    RemoteStationConnectionCreate,
    RemoteStationConnectionRead,
    RemoteStationConnectionUpdate,
)
from app.services.remote_protocol import send_agent_request
from app.services.remote_station import (
    actor_name,
    capture_snapshot,
    commit_release,
    create_release,
    generate_reconciliation,
    pull_upper_snapshot,
    refresh_release_status,
    stage_release,
    transition_release,
    verify_release_readback,
)

router = APIRouter(prefix="/remote-stations", tags=["remote-stations"])
logger = logging.getLogger(__name__)


def _connection(db: Session, connection_id: str) -> RemoteStationConnection:
    connection = db.get(RemoteStationConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="目标上位机连接不存在")
    return connection


def _release(db: Session, release_id: str) -> RemoteProgramRelease:
    release = db.get(RemoteProgramRelease, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="远程参数发布单不存在")
    return release


@router.get("/connections", response_model=list[RemoteStationConnectionRead])
def list_connections(db: Session = Depends(get_db)) -> list[RemoteStationConnection]:
    return list(
        db.scalars(
            select(RemoteStationConnection).order_by(RemoteStationConnection.created_at.desc())
        )
    )


@router.post(
    "/connections",
    response_model=RemoteStationConnectionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_connection(
    payload: RemoteStationConnectionCreate, db: Session = Depends(get_db)
) -> RemoteStationConnection:
    check_fk(db, Factory, payload.factory_id, label="工厂")
    if db.scalar(
        select(RemoteStationConnection).where(
            RemoteStationConnection.connection_code == payload.connection_code
        )
    ):
        raise HTTPException(status_code=409, detail="远程连接代码已存在")
    connection = RemoteStationConnection(
        **payload.model_dump(),
        transport="TLS_TCP",
        status="DRAFT",
        operating_mode="READ_ONLY",
        local_confirmation_required=True,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.patch(
    "/connections/{connection_id}", response_model=RemoteStationConnectionRead
)
def update_connection(
    connection_id: str,
    payload: RemoteStationConnectionUpdate,
    db: Session = Depends(get_db),
) -> RemoteStationConnection:
    connection = _connection(db, connection_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(connection, field, value)
    connection.status = "DRAFT"
    connection.operating_mode = "READ_ONLY"
    connection.approved_by = None
    connection.approved_at = None
    db.commit()
    db.refresh(connection)
    return connection


@router.post(
    "/connections/{connection_id}/approval",
    response_model=RemoteStationConnectionRead,
)
def approve_connection(
    connection_id: str,
    payload: RemoteStationApproval,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteStationConnection:
    connection = _connection(db, connection_id)
    if payload.decision == "APPROVE":
        missing = [
            label
            for value, label in (
                (connection.client_certificate_ref, "客户端证书引用"),
                (connection.client_private_key_ref, "客户端私钥引用"),
                (connection.trusted_ca_ref, "受信任根证书引用"),
            )
            if not value
        ]
        if missing:
            raise HTTPException(
                status_code=422, detail=f"审批前必须填写：{', '.join(missing)}"
            )
        connection.status = "ACTIVE"
        connection.operating_mode = "APPROVED_RELEASES_ONLY"
        connection.approved_by = actor_name(request)
        connection.approved_at = datetime.now(UTC)
    else:
        connection.status = "REJECTED"
        connection.operating_mode = "READ_ONLY"
        connection.approved_by = None
        connection.approved_at = None
    if payload.comment:
        connection.remark = payload.comment
    db.commit()
    db.refresh(connection)
    return connection


@router.post("/connections/{connection_id}/test")
def test_connection(
    connection_id: str, db: Session = Depends(get_db)
) -> dict:
    connection = _connection(db, connection_id)
    try:
        response = send_agent_request(connection, "HELLO", {"readOnly": True})
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary must not expose adapter errors.
        logger.exception("Unexpected remote station connection test failure")
        raise HTTPException(
            status_code=502,
            detail="目标上位机连接测试失败，请检查连接配置和通讯程序状态",
        ) from exc
    connection.last_seen_at = datetime.now(UTC)
    db.commit()
    return {
        "reachable": True,
        "agent_id": connection.agent_id,
        "agent_version": response.get("agentVersion"),
        "adapter_mode": response.get("adapterMode"),
        "message": "双向 TLS 连接与代理身份校验通过，未读取或修改生产参数",
    }


@router.get(
    "/connections/{connection_id}/snapshots",
    response_model=list[RemoteParameterSnapshotRead],
)
def list_snapshots(
    connection_id: str, db: Session = Depends(get_db)
) -> list[RemoteParameterSnapshot]:
    _connection(db, connection_id)
    return list(
        db.scalars(
            select(RemoteParameterSnapshot)
            .where(RemoteParameterSnapshot.connection_id == connection_id)
            .order_by(RemoteParameterSnapshot.collected_at.desc())
        )
    )


@router.post(
    "/connections/{connection_id}/snapshots/capture",
    response_model=RemoteParameterSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def capture_local_snapshot(
    connection_id: str,
    payload: RemoteSnapshotCapture,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteParameterSnapshot:
    return capture_snapshot(
        db,
        _connection(db, connection_id),
        payload.source_type,
        payload.program_version_id,
        payload.version_label,
        actor_name(request),
    )


@router.post(
    "/connections/{connection_id}/snapshots/pull-upper",
    response_model=RemoteParameterSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def pull_snapshot(
    connection_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteParameterSnapshot:
    return pull_upper_snapshot(
        db, _connection(db, connection_id), actor_name(request)
    )


@router.post(
    "/connections/{connection_id}/reconciliations",
    response_model=RemoteReconciliationRead,
    status_code=status.HTTP_201_CREATED,
)
def reconcile_station(
    connection_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteStationReconciliation:
    return generate_reconciliation(
        db, _connection(db, connection_id), actor_name(request)
    )


@router.get(
    "/connections/{connection_id}/reconciliations",
    response_model=list[RemoteReconciliationRead],
)
def list_reconciliations(
    connection_id: str, db: Session = Depends(get_db)
) -> list[RemoteStationReconciliation]:
    _connection(db, connection_id)
    return list(
        db.scalars(
            select(RemoteStationReconciliation)
            .where(RemoteStationReconciliation.connection_id == connection_id)
            .order_by(RemoteStationReconciliation.generated_at.desc())
        )
    )


@router.get("/releases", response_model=list[RemoteProgramReleaseRead])
def list_releases(db: Session = Depends(get_db)) -> list[RemoteProgramRelease]:
    return list(
        db.scalars(
            select(RemoteProgramRelease).order_by(RemoteProgramRelease.requested_at.desc())
        )
    )


@router.post(
    "/releases",
    response_model=RemoteProgramReleaseRead,
    status_code=status.HTTP_201_CREATED,
)
def add_release(
    payload: RemoteReleaseCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return create_release(db, payload, actor_name(request))


def _release_transition_route(
    release_id: str,
    action: str,
    payload: RemoteReleaseAction,
    request: Request,
    db: Session,
) -> RemoteProgramRelease:
    return transition_release(
        db, _release(db, release_id), action, actor_name(request), payload.comment
    )


@router.post("/releases/{release_id}/submit", response_model=RemoteProgramReleaseRead)
def submit_release(
    release_id: str,
    payload: RemoteReleaseAction,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return _release_transition_route(release_id, "SUBMIT", payload, request, db)


@router.post("/releases/{release_id}/approve", response_model=RemoteProgramReleaseRead)
def approve_release(
    release_id: str,
    payload: RemoteReleaseAction,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return _release_transition_route(release_id, "APPROVE", payload, request, db)


@router.post("/releases/{release_id}/reject", response_model=RemoteProgramReleaseRead)
def reject_release(
    release_id: str,
    payload: RemoteReleaseAction,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return _release_transition_route(release_id, "REJECT", payload, request, db)


@router.post("/releases/{release_id}/stage", response_model=RemoteProgramReleaseRead)
def stage_release_package(
    release_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return stage_release(db, _release(db, release_id), actor_name(request))


@router.post("/releases/{release_id}/refresh", response_model=RemoteProgramReleaseRead)
def refresh_release(
    release_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return refresh_release_status(db, _release(db, release_id), actor_name(request))


@router.post("/releases/{release_id}/commit", response_model=RemoteProgramReleaseRead)
def commit_release_package(
    release_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return commit_release(db, _release(db, release_id), actor_name(request))


@router.post(
    "/releases/{release_id}/verify-readback",
    response_model=RemoteProgramReleaseRead,
)
def verify_release_package(
    release_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RemoteProgramRelease:
    return verify_release_readback(db, _release(db, release_id), actor_name(request))


@router.get(
    "/releases/{release_id}/events", response_model=list[RemoteReleaseEventRead]
)
def list_release_events(
    release_id: str, db: Session = Depends(get_db)
) -> list[RemoteReleaseEvent]:
    _release(db, release_id)
    return list(
        db.scalars(
            select(RemoteReleaseEvent)
            .where(RemoteReleaseEvent.release_id == release_id)
            .order_by(RemoteReleaseEvent.occurred_at)
        )
    )
