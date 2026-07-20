from __future__ import annotations

from datetime import UTC, datetime
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    Brush,
    BrushParameter,
    Factory,
    RemoteParameterSnapshot,
    RemoteProgramRelease,
    RemoteReleaseEvent,
    RemoteStationConnection,
    RemoteStationReconciliation,
    SprayProgram,
    SprayProgramVersion,
)
from app.services.remote_protocol import payload_hash, send_agent_request


def _decimal_text(value: float | int | str) -> str:
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail="刷子表包含无法识别的参数值") from exc
    if not decimal_value.is_finite():
        raise HTTPException(status_code=422, detail="刷子表参数值必须是有限数字")
    text = format(decimal_value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def _normalize_complete_brush_table(table: dict) -> dict:
    normalized = deepcopy(table)
    brushes = normalized.get("brushes")
    if not isinstance(brushes, list):
        return normalized
    try:
        for brush in brushes:
            if not isinstance(brush, dict):
                continue
            parameters = brush.get("parameters")
            if not isinstance(parameters, list):
                continue
            for parameter in parameters:
                if not isinstance(parameter, dict) or parameter.get("value") is None:
                    continue
                parameter["value"] = _decimal_text(parameter["value"])
    except HTTPException as exc:
        raise HTTPException(
            status_code=502,
            detail="上位机返回的刷子表包含无法识别的参数值",
        ) from exc
    return normalized


def actor_name(request) -> str:
    actor = request.state.actor
    return actor.display_name or actor.username


def serialize_program_version(db: Session, program_version_id: str) -> dict:
    version = db.get(SprayProgramVersion, program_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="喷涂程序版本不存在")
    program = db.get(SprayProgram, version.spray_program_id)
    if not program:
        raise HTTPException(status_code=422, detail="喷涂程序版本缺少程序主数据")
    brushes = list(
        db.scalars(
            select(Brush)
            .where(Brush.program_version_id == version.id)
            .order_by(Brush.brush_table_no, Brush.brush_no)
        )
    )
    if not brushes:
        raise HTTPException(status_code=422, detail="喷涂程序版本没有完整刷子表")
    brush_payload = []
    for brush in brushes:
        parameters = list(
            db.scalars(
                select(BrushParameter)
                .where(BrushParameter.brush_id == brush.id)
                .order_by(BrushParameter.parameter_code)
            )
        )
        brush_payload.append(
            {
                "brushTableNo": brush.brush_table_no,
                "brushNo": brush.brush_no,
                "sprayPosition": brush.spray_position,
                "parameters": [
                    {
                        "code": parameter.parameter_code,
                        "name": parameter.parameter_name,
                        "value": _decimal_text(parameter.configured_value),
                        "unit": parameter.unit,
                    }
                    for parameter in parameters
                ],
            }
        )
    return {
        "schema": "PQ-AI-COMPLETE-BRUSH-TABLE/1",
        "programCode": program.program_code,
        "programName": program.name,
        "processStage": program.process_stage,
        "stationCode": program.station_code,
        "stationName": program.station_name,
        "version": version.version,
        "programVersionId": version.id,
        "brushes": brush_payload,
    }


def validate_connection_for_version(
    db: Session, connection: RemoteStationConnection, version_id: str
) -> None:
    version = db.get(SprayProgramVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="喷涂程序版本不存在")
    program = db.get(SprayProgram, version.spray_program_id)
    if not program:
        raise HTTPException(status_code=422, detail="喷涂程序不存在")
    if program.factory_id != connection.factory_id:
        raise HTTPException(status_code=422, detail="喷涂程序与目标连接不属于同一工厂")
    if program.process_stage != connection.process_stage:
        raise HTTPException(status_code=422, detail="喷涂程序工段与目标工作站不一致")
    if program.station_code != connection.station_code:
        raise HTTPException(status_code=422, detail="喷涂程序站点与目标工作站不一致")


def capture_snapshot(
    db: Session,
    connection: RemoteStationConnection,
    source_type: str,
    program_version_id: str,
    version_label: str | None,
    actor: str,
) -> RemoteParameterSnapshot:
    validate_connection_for_version(db, connection, program_version_id)
    table = serialize_program_version(db, program_version_id)
    snapshot = RemoteParameterSnapshot(
        connection_id=connection.id,
        source_type=source_type,
        program_version_id=program_version_id,
        version_label=version_label or table["version"],
        payload_hash=payload_hash(table),
        parameter_payload=table,
        collection_ref=f"PROGRAM_VERSION:{program_version_id}",
        status="VERIFIED",
        collected_by=actor,
        collected_at=datetime.now(UTC),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def pull_upper_snapshot(
    db: Session, connection: RemoteStationConnection, actor: str
) -> RemoteParameterSnapshot:
    if connection.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="远程连接尚未审批启用")
    response = send_agent_request(connection, "INVENTORY_REQUEST", {})
    table = response.get("completeBrushTable")
    if not isinstance(table, dict):
        raise HTTPException(status_code=502, detail="上位机代理没有返回完整刷子表")
    wire_digest = payload_hash(table)
    if response.get("payloadHash") != wire_digest:
        raise HTTPException(status_code=502, detail="上位机参数回读哈希校验失败")
    table = _normalize_complete_brush_table(table)
    digest = payload_hash(table)
    snapshot = RemoteParameterSnapshot(
        connection_id=connection.id,
        source_type="UPPER_COMPUTER",
        program_version_id=None,
        version_label=str(response.get("versionLabel") or "REMOTE-LATEST"),
        payload_hash=digest,
        parameter_payload=table,
        collection_ref=str(response.get("collectionRef") or "PQRP:INVENTORY"),
        status="VERIFIED",
        collected_by=actor,
        collected_at=datetime.now(UTC),
    )
    connection.last_seen_at = datetime.now(UTC)
    connection.last_inventory_hash = digest
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _parameter_index(payload: dict | None) -> dict[str, float | str | None]:
    if not payload:
        return {}
    values: dict[str, float | str | None] = {}
    for brush in payload.get("brushes", []):
        brush_key = f"{brush.get('brushTableNo')}/{brush.get('brushNo')}"
        for parameter in brush.get("parameters", []):
            values[f"{brush_key}/{parameter.get('code')}"] = parameter.get("value")
    return values


def generate_reconciliation(
    db: Session, connection: RemoteStationConnection, actor: str
) -> RemoteStationReconciliation:
    latest: dict[str, RemoteParameterSnapshot | None] = {}
    for source_type in ("CLOUD", "VIRTUAL_LINE", "UPPER_COMPUTER"):
        latest[source_type] = db.scalar(
            select(RemoteParameterSnapshot)
            .where(
                RemoteParameterSnapshot.connection_id == connection.id,
                RemoteParameterSnapshot.source_type == source_type,
                RemoteParameterSnapshot.status == "VERIFIED",
            )
            .order_by(RemoteParameterSnapshot.collected_at.desc())
        )
    indexes = {
        source: _parameter_index(snapshot.parameter_payload if snapshot else None)
        for source, snapshot in latest.items()
    }
    keys = sorted(set().union(*(set(index) for index in indexes.values())))
    rows = []
    for key in keys:
        values = {source: index.get(key) for source, index in indexes.items()}
        present = [value for value in values.values() if value is not None]
        rows.append(
            {
                "parameter": key,
                "cloud": values["CLOUD"],
                "virtualLine": values["VIRTUAL_LINE"],
                "upperComputer": values["UPPER_COMPUTER"],
                "status": (
                    "MISSING"
                    if len(present) != 3
                    else "SAME"
                    if len(set(present)) == 1
                    else "DIFFERENT"
                ),
            }
        )
    reconciliation = RemoteStationReconciliation(
        connection_id=connection.id,
        cloud_snapshot_id=latest["CLOUD"].id if latest["CLOUD"] else None,
        virtual_snapshot_id=(
            latest["VIRTUAL_LINE"].id if latest["VIRTUAL_LINE"] else None
        ),
        upper_snapshot_id=(
            latest["UPPER_COMPUTER"].id if latest["UPPER_COMPUTER"] else None
        ),
        status="CONSISTENT" if rows and all(row["status"] == "SAME" for row in rows) else "DIFFERENT",
        diff_payload={
            "summary": {
                "parameterCount": len(rows),
                "sameCount": sum(row["status"] == "SAME" for row in rows),
                "differentCount": sum(row["status"] == "DIFFERENT" for row in rows),
                "missingCount": sum(row["status"] == "MISSING" for row in rows),
            },
            "rows": rows,
        },
        generated_by=actor,
        generated_at=datetime.now(UTC),
    )
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)
    return reconciliation


def _record_event(
    db: Session,
    release: RemoteProgramRelease,
    event_type: str,
    message: str,
    actor: str,
    payload: dict | None = None,
) -> None:
    db.add(
        RemoteReleaseEvent(
            release_id=release.id,
            event_type=event_type,
            status=release.status,
            message=message,
            event_payload=payload,
            actor=actor,
            occurred_at=datetime.now(UTC),
        )
    )


def create_release(db: Session, payload, actor: str) -> RemoteProgramRelease:
    connection = db.get(RemoteStationConnection, payload.connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="目标上位机连接不存在")
    validate_connection_for_version(db, connection, payload.base_program_version_id)
    validate_connection_for_version(db, connection, payload.candidate_program_version_id)
    base = db.get(SprayProgramVersion, payload.base_program_version_id)
    candidate = db.get(SprayProgramVersion, payload.candidate_program_version_id)
    if base.spray_program_id != candidate.spray_program_id:
        raise HTTPException(status_code=422, detail="原版本与候选版本不属于同一喷涂程序")
    if candidate.status != "DRAFT":
        raise HTTPException(status_code=422, detail="只有完整的草稿版本可以发起远程发布")
    base_table = serialize_program_version(db, base.id)
    candidate_table = serialize_program_version(db, candidate.id)
    if payload_hash(base_table) == payload_hash(candidate_table):
        raise HTTPException(status_code=422, detail="候选版本与原版本没有参数差异")
    now = datetime.now(UTC)
    package = {
        "schema": "PQ-AI-REMOTE-RELEASE/1",
        "target": {
            "agentId": connection.agent_id,
            "stationCode": connection.station_code,
            "processStage": connection.process_stage,
        },
        "basePayloadHash": payload_hash(base_table),
        "candidatePayloadHash": payload_hash(candidate_table),
        "completeBrushTable": candidate_table,
    }
    release = RemoteProgramRelease(
        release_no=f"REL-{now:%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}",
        connection_id=connection.id,
        base_program_version_id=base.id,
        candidate_program_version_id=candidate.id,
        status="DRAFT",
        package_hash=payload_hash(package),
        package_payload=package,
        risk_summary=payload.risk_summary,
        requested_by=actor,
        requested_at=now,
        rollback_program_version_id=base.id,
    )
    db.add(release)
    db.flush()
    _record_event(db, release, "CREATED", "已生成完整刷子表发布包，尚未发送", actor)
    db.commit()
    db.refresh(release)
    return release


def transition_release(
    db: Session,
    release: RemoteProgramRelease,
    action: str,
    actor: str,
    comment: str | None,
) -> RemoteProgramRelease:
    now = datetime.now(UTC)
    if action == "SUBMIT":
        if release.status != "DRAFT":
            raise HTTPException(status_code=409, detail="只有草稿发布单可以提交审批")
        release.status = "SUBMITTED"
        message = "已提交审批，远程端未收到任何参数"
    elif action == "APPROVE":
        if release.status != "SUBMITTED":
            raise HTTPException(status_code=409, detail="发布单当前不在待审批状态")
        if release.requested_by == actor:
            raise HTTPException(status_code=422, detail="申请人与审批人必须是不同人员")
        release.status = "APPROVED"
        release.approved_by = actor
        release.approved_at = now
        message = "审批通过，仍未发送到远程端"
    elif action == "REJECT":
        if release.status not in {"SUBMITTED", "APPROVED"}:
            raise HTTPException(status_code=409, detail="当前状态不能驳回")
        release.status = "REJECTED"
        message = "发布单已驳回，远程端未发生变化"
    else:
        raise HTTPException(status_code=422, detail="不支持的发布动作")
    _record_event(db, release, action, message, actor, {"comment": comment})
    db.commit()
    db.refresh(release)
    return release


def stage_release(
    db: Session, release: RemoteProgramRelease, actor: str
) -> RemoteProgramRelease:
    if release.status != "APPROVED" or not release.approved_at:
        raise HTTPException(status_code=409, detail="发布单未经审批，禁止发送")
    connection = db.get(RemoteStationConnection, release.connection_id)
    if not connection or connection.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="目标上位机连接尚未审批启用")
    if connection.operating_mode != "APPROVED_RELEASES_ONLY":
        raise HTTPException(status_code=422, detail="目标连接当前为只读模式")
    try:
        response = send_agent_request(
            connection,
            "PREPARE_RELEASE",
            {
                "releaseNo": release.release_no,
                "packageHash": release.package_hash,
                "approvedBy": release.approved_by,
                "approvedAt": release.approved_at.isoformat(),
                "package": release.package_payload,
            },
        )
    except HTTPException as exc:
        release.last_error = f"发布包暂存未完成：{exc.detail}"
        _record_event(db, release, "STAGE_FAILED", release.last_error, actor)
        db.commit()
        db.refresh(release)
        return release
    if response.get("accepted") is not True:
        raise HTTPException(status_code=502, detail="上位机代理拒绝暂存发布包")
    release.status = "STAGED"
    release.staged_at = datetime.now(UTC)
    _record_event(db, release, "STAGED", "发布包已暂存，尚未应用到生产端", actor, response)
    db.commit()
    db.refresh(release)
    return release


def refresh_release_status(
    db: Session, release: RemoteProgramRelease, actor: str
) -> RemoteProgramRelease:
    if release.status not in {"STAGED", "LOCAL_CONFIRMED"}:
        raise HTTPException(status_code=409, detail="当前发布单没有待确认的远程暂存包")
    connection = db.get(RemoteStationConnection, release.connection_id)
    if not connection:
        raise HTTPException(status_code=422, detail="发布单关联的目标上位机连接不存在")
    try:
        response = send_agent_request(
            connection, "RELEASE_STATUS_REQUEST", {"releaseNo": release.release_no}
        )
    except HTTPException as exc:
        release.last_error = f"暂未取得上位机现场确认结果：{exc.detail}"
        _record_event(db, release, "STATUS_PENDING", release.last_error, actor)
        db.commit()
        db.refresh(release)
        return release
    if response.get("localRejected") is True:
        release.status = "REJECTED"
        release.last_error = "上位机现场人员已拒绝该发布包"
        _record_event(
            db,
            release,
            "LOCAL_REJECTED",
            release.last_error,
            actor,
            response,
        )
        db.commit()
        db.refresh(release)
        return release
    if response.get("localConfirmed") is True and release.status == "STAGED":
        release.status = "LOCAL_CONFIRMED"
        release.local_confirmed_at = datetime.now(UTC)
        _record_event(db, release, "LOCAL_CONFIRMED", "上位机现场人员已确认", actor, response)
        db.commit()
        db.refresh(release)
    return release


def verify_release_readback(
    db: Session, release: RemoteProgramRelease, actor: str
) -> RemoteProgramRelease:
    if release.status not in {"WAITING_READBACK", "APPLIED"}:
        raise HTTPException(status_code=409, detail="当前发布单不需要回读核对")
    connection = db.get(RemoteStationConnection, release.connection_id)
    try:
        readback = send_agent_request(connection, "INVENTORY_REQUEST", {})
    except HTTPException as exc:
        release.last_error = f"参数已交付，暂未取得有效回读：{exc.detail}"
        _record_event(db, release, "READBACK_PENDING", release.last_error, actor)
        db.commit()
        db.refresh(release)
        return release
    table = readback.get("completeBrushTable")
    wire_digest = payload_hash(table) if isinstance(table, dict) else None
    if wire_digest is not None and readback.get("payloadHash") != wire_digest:
        table = None
    normalized_table = _normalize_complete_brush_table(table) if isinstance(table, dict) else None
    digest = payload_hash(normalized_table) if normalized_table is not None else None
    release.readback_hash = digest
    expected = release.package_payload["candidatePayloadHash"]
    if digest == expected and wire_digest is not None:
        release.status = "VERIFIED"
        release.verified_at = datetime.now(UTC)
        release.last_error = None
        message = "远程提交完成，回读参数与候选完整刷子表一致"
    else:
        release.status = "FAILED"
        release.last_error = "远程提交后的回读参数与候选版本不一致"
        message = release.last_error
    _record_event(db, release, "READBACK", message, actor, {"readbackHash": digest})
    db.commit()
    db.refresh(release)
    return release


def commit_release(
    db: Session, release: RemoteProgramRelease, actor: str
) -> RemoteProgramRelease:
    if release.status != "LOCAL_CONFIRMED" or not release.local_confirmed_at:
        raise HTTPException(status_code=409, detail="上位机现场人员尚未确认，禁止正式提交")
    connection = db.get(RemoteStationConnection, release.connection_id)
    if not connection:
        raise HTTPException(status_code=422, detail="发布单关联的目标上位机连接不存在")
    try:
        response = send_agent_request(
            connection,
            "COMMIT_RELEASE",
            {"releaseNo": release.release_no, "packageHash": release.package_hash},
        )
    except HTTPException as exc:
        release.status = "WAITING_READBACK"
        release.last_error = (
            f"提交结果暂未确认：{exc.detail}。请先执行回读核对，不要重复提交"
        )
        _record_event(db, release, "COMMIT_UNCERTAIN", release.last_error, actor)
        db.commit()
        db.refresh(release)
        return release
    if response.get("applied") is not True:
        if response.get("waitingReadback") is True:
            release.status = "WAITING_READBACK"
            release.last_error = str(
                response.get("message") or "参数已交付，等待上位机导入并回读"
            )
            _record_event(
                db,
                release,
                "DELIVERED",
                release.last_error,
                actor,
                response,
            )
            db.commit()
            db.refresh(release)
            return release
        release.status = "FAILED"
        release.last_error = str(response.get("message") or "上位机代理应用失败")
        _record_event(db, release, "FAILED", release.last_error, actor, response)
        db.commit()
        raise HTTPException(status_code=502, detail=release.last_error)
    release.status = "APPLIED"
    release.applied_at = datetime.now(UTC)
    _record_event(db, release, "APPLIED", "上位机代理已执行受控适配器", actor, response)
    db.commit()
    db.refresh(release)
    return verify_release_readback(db, release, actor)
