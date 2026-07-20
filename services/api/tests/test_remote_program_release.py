from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import domain  # noqa: F401
from app.models.domain import (
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    MeasurementPoint,
    Part,
    ProgramColor,
    ProgramVehicleModel,
    RemoteProgramRelease,
    RemoteReleaseEvent,
    RemoteStationConnection,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
)
from app.services.program_versioning import derive_complete_program_version
from app.services.remote_protocol import payload_hash
from app.services.remote_station import (
    commit_release,
    create_release,
    pull_upper_snapshot,
    refresh_release_status,
    serialize_program_version,
    stage_release,
    transition_release,
    verify_release_readback,
)
from tests.schema_guard import create_transient_test_schema


def _engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    create_transient_test_schema(engine)
    return engine


def _program_context(db: Session):
    factory = Factory(code="F", name="工厂")
    model = VehicleModel(code="M", name="车型")
    color = Color(code="C", name="颜色", color_type="BASECOAT")
    part = Part(code="P", name="零件")
    db.add_all([factory, model, color, part])
    db.flush()
    point = MeasurementPoint(
        code="MP", name="点位", vehicle_model_id=model.id, part_id=part.id
    )
    program = SprayProgram(
        program_code="CC2",
        name="清漆二站",
        factory_id=factory.id,
        process_stage="CLEARCOAT_2",
        station_code="CC2",
        station_name="清漆二站",
    )
    db.add_all([point, program])
    db.flush()
    base = SprayProgramVersion(
        spray_program_id=program.id, version="1.0", status="ACTIVE", source_type="MANUAL"
    )
    db.add(base)
    db.flush()
    db.add_all(
        [
            ProgramVehicleModel(program_version_id=base.id, vehicle_model_id=model.id),
            ProgramColor(program_version_id=base.id, color_id=color.id),
        ]
    )
    for brush_index in range(2):
        brush = Brush(
            program_version_id=base.id,
            brush_no=f"B{brush_index + 1}",
            brush_table_no="BT1",
            part_id=part.id,
        )
        db.add(brush)
        db.flush()
        db.add_all(
            [
                BrushParameter(
                    brush_id=brush.id,
                    parameter_code="clearcoat_2_spray_flow",
                    parameter_name="喷涂流量",
                    configured_value=300 + brush_index,
                    unit="ml/min",
                    hard_min=200,
                    hard_max=400,
                ),
                BrushParameter(
                    brush_id=brush.id,
                    parameter_code="clearcoat_2_bell_speed",
                    parameter_name="旋杯转速",
                    configured_value=40_000,
                    unit="rpm",
                    hard_min=20_000,
                    hard_max=60_000,
                ),
                BrushPointContribution(
                    brush_id=brush.id,
                    measurement_point_id=point.id,
                    overlap_ratio=0.5,
                    contribution_weight=0.5,
                    is_approved=True,
                ),
            ]
        )
    db.commit()
    return factory, base


def test_single_parameter_edit_derives_complete_program_version() -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        _, base = _program_context(db)
        result = derive_complete_program_version(
            db,
            base.id,
            "1.1",
            [SimpleNamespace(brush_no="B1", parameter_code="clearcoat_2_spray_flow", new_value=320)],
        )
        assert result["brush_count"] == 2
        assert result["parameter_count"] == 4
        assert result["contribution_count"] == 2
        assert result["changed_parameter_count"] == 1
        derived_brushes = list(
            db.scalars(select(Brush).where(Brush.program_version_id == result["program_version_id"]))
        )
        assert len(derived_brushes) == 2
        derived_values = {
            (brush.brush_no, parameter.parameter_code): parameter.configured_value
            for brush in derived_brushes
            for parameter in db.scalars(
                select(BrushParameter).where(BrushParameter.brush_id == brush.id)
            )
        }
        assert derived_values[("B1", "clearcoat_2_spray_flow")] == 320
        assert derived_values[("B2", "clearcoat_2_spray_flow")] == 301
        base_brush = db.scalar(
            select(Brush).where(Brush.program_version_id == base.id, Brush.brush_no == "B1")
        )
        base_flow = db.scalar(
            select(BrushParameter).where(
                BrushParameter.brush_id == base_brush.id,
                BrushParameter.parameter_code == "clearcoat_2_spray_flow",
            )
        )
        assert base_flow.configured_value == 300


def test_remote_release_never_sends_before_approval_and_local_confirmation(monkeypatch) -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        factory, base = _program_context(db)
        derived_result = derive_complete_program_version(
            db,
            base.id,
            "1.1",
            [SimpleNamespace(brush_no="B1", parameter_code="clearcoat_2_spray_flow", new_value=320)],
        )
        connection = RemoteStationConnection(
            connection_code="REMOTE-CC2",
            name="清漆二站上位机",
            factory_id=factory.id,
            station_code="CC2",
            station_name="清漆二站",
            process_stage="CLEARCOAT_2",
            host="127.0.0.1",
            port=9443,
            agent_id="AGENT-CC2",
            status="ACTIVE",
            operating_mode="APPROVED_RELEASES_ONLY",
            client_certificate_ref="CLIENT_CERT_PATH",
            client_private_key_ref="CLIENT_KEY_PATH",
            trusted_ca_ref="TRUSTED_CA_PATH",
            approved_by="连接审批人",
            approved_at=datetime.now(UTC),
        )
        db.add(connection)
        db.commit()
        payload = SimpleNamespace(
            connection_id=connection.id,
            base_program_version_id=base.id,
            candidate_program_version_id=derived_result["program_version_id"],
            risk_summary="调整单点喷涂流量，原版本作为回退版本",
        )
        release = create_release(db, payload, "工艺申请人")
        calls = []

        def fake_agent_request(_connection, message_type, body):
            calls.append(message_type)
            if message_type == "PREPARE_RELEASE":
                return {"accepted": True, "localConfirmed": False}
            if message_type == "RELEASE_STATUS_REQUEST":
                return {"staged": True, "localConfirmed": True}
            if message_type == "COMMIT_RELEASE":
                return {"applied": True}
            if message_type == "INVENTORY_REQUEST":
                table = serialize_program_version(db, release.candidate_program_version_id)
                return {
                    "completeBrushTable": table,
                    "payloadHash": payload_hash(table),
                }
            raise AssertionError(message_type)

        monkeypatch.setattr(
            "app.services.remote_station.send_agent_request", fake_agent_request
        )
        with pytest.raises(HTTPException):
            stage_release(db, release, "集成操作员")
        assert calls == []
        release = transition_release(db, release, "SUBMIT", "工艺申请人", None)
        with pytest.raises(HTTPException):
            transition_release(db, release, "APPROVE", "工艺申请人", None)
        assert calls == []
        release = transition_release(db, release, "APPROVE", "独立审批人", None)
        assert calls == []
        release = stage_release(db, release, "集成操作员")
        assert release.status == "STAGED"
        assert calls == ["PREPARE_RELEASE"]
        with pytest.raises(HTTPException):
            commit_release(db, release, "机器人操作员")
        assert calls == ["PREPARE_RELEASE"]
        release = refresh_release_status(db, release, "集成操作员")
        assert release.status == "LOCAL_CONFIRMED"
        release = commit_release(db, release, "机器人操作员")
        assert release.status == "VERIFIED"
        assert calls == [
            "PREPARE_RELEASE",
            "RELEASE_STATUS_REQUEST",
            "COMMIT_RELEASE",
            "INVENTORY_REQUEST",
        ]
        persisted = db.get(RemoteProgramRelease, release.id)
        assert persisted.readback_hash == persisted.package_payload["candidatePayloadHash"]
        events = list(
            db.scalars(
                select(RemoteReleaseEvent).where(RemoteReleaseEvent.release_id == release.id)
            )
        )
        assert {event.event_type for event in events} >= {
            "CREATED",
            "SUBMIT",
            "APPROVE",
            "STAGED",
            "LOCAL_CONFIRMED",
            "APPLIED",
            "READBACK",
        }


def test_remote_release_waits_for_delayed_readback(monkeypatch) -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        factory = Factory(code="FW", name="等待回读工厂")
        db.add(factory)
        db.flush()
        connection = RemoteStationConnection(
            connection_code="REMOTE-WAIT",
            name="等待回读连接",
            factory_id=factory.id,
            station_code="CC2",
            station_name="清漆二站",
            process_stage="CLEARCOAT_2",
            host="127.0.0.1",
            port=9443,
            agent_id="AGENT-WAIT",
            status="ACTIVE",
            operating_mode="APPROVED_RELEASES_ONLY",
        )
        db.add(connection)
        db.flush()
        table = {"schema": "PQ-AI-COMPLETE-BRUSH-TABLE/1", "brushes": []}
        release = RemoteProgramRelease(
            release_no="REL-WAIT",
            connection_id=connection.id,
            base_program_version_id="base-version",
            candidate_program_version_id="candidate-version",
            status="LOCAL_CONFIRMED",
            package_hash="package-hash",
            package_payload={"candidatePayloadHash": payload_hash(table)},
            risk_summary="等待厂家程序完成导入",
            requested_by="申请人",
            requested_at=datetime.now(UTC),
            approved_by="审批人",
            approved_at=datetime.now(UTC),
            local_confirmed_at=datetime.now(UTC),
        )
        db.add(release)
        db.commit()

        def fake_agent_request(_connection, message_type, _body):
            if message_type == "COMMIT_RELEASE":
                return {
                    "applied": False,
                    "waitingReadback": True,
                    "message": "参数包已交付，等待厂家导入",
                }
            if message_type == "INVENTORY_REQUEST":
                return {"completeBrushTable": table, "payloadHash": payload_hash(table)}
            raise AssertionError(message_type)

        monkeypatch.setattr(
            "app.services.remote_station.send_agent_request", fake_agent_request
        )
        release = commit_release(db, release, "机器人操作员")
        assert release.status == "WAITING_READBACK"
        assert release.applied_at is None
        release = verify_release_readback(db, release, "集成操作员")
        assert release.status == "VERIFIED"
        assert release.readback_hash == payload_hash(table)
        events = list(
            db.scalars(
                select(RemoteReleaseEvent).where(RemoteReleaseEvent.release_id == release.id)
            )
        )
        assert {event.event_type for event in events} == {"DELIVERED", "READBACK"}


def test_local_rejection_stops_remote_release(monkeypatch) -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        factory = Factory(code="FR", name="现场拒绝工厂")
        db.add(factory)
        db.flush()
        connection = RemoteStationConnection(
            connection_code="REMOTE-REJECT",
            name="现场拒绝连接",
            factory_id=factory.id,
            station_code="BC1",
            station_name="色漆一站",
            process_stage="BASECOAT_1",
            host="127.0.0.1",
            port=9443,
            agent_id="AGENT-REJECT",
            status="ACTIVE",
            operating_mode="APPROVED_RELEASES_ONLY",
        )
        db.add(connection)
        db.flush()
        release = RemoteProgramRelease(
            release_no="REL-REJECT",
            connection_id=connection.id,
            base_program_version_id="base-version",
            candidate_program_version_id="candidate-version",
            status="STAGED",
            package_hash="package-hash",
            package_payload={"candidatePayloadHash": "candidate-hash"},
            risk_summary="现场复核后拒绝",
            requested_by="申请人",
            requested_at=datetime.now(UTC),
            approved_by="审批人",
            approved_at=datetime.now(UTC),
            staged_at=datetime.now(UTC),
        )
        db.add(release)
        db.commit()
        monkeypatch.setattr(
            "app.services.remote_station.send_agent_request",
            lambda *_args: {
                "staged": True,
                "localConfirmed": False,
                "localRejected": True,
            },
        )
        release = refresh_release_status(db, release, "集成操作员")
        assert release.status == "REJECTED"
        assert release.last_error == "上位机现场人员已拒绝该发布包"
        with pytest.raises(HTTPException):
            commit_release(db, release, "机器人操作员")


def test_upper_snapshot_normalizes_numeric_parameter_values(monkeypatch) -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        factory = Factory(code="FN", name="参数规范化工厂")
        db.add(factory)
        db.flush()
        connection = RemoteStationConnection(
            connection_code="REMOTE-NORMALIZE",
            name="参数规范化连接",
            factory_id=factory.id,
            station_code="BC1",
            station_name="色漆一站",
            process_stage="BASECOAT_1",
            host="127.0.0.1",
            port=9443,
            agent_id="AGENT-NORMALIZE",
            status="ACTIVE",
            operating_mode="READ_ONLY",
        )
        db.add(connection)
        db.commit()
        table = {
            "schema": "PQ-AI-COMPLETE-BRUSH-TABLE/1",
            "brushes": [
                {
                    "brushTableNo": "BT1",
                    "brushNo": "B1",
                    "parameters": [{"code": "spray_flow", "value": 320.0}],
                }
            ],
        }
        monkeypatch.setattr(
            "app.services.remote_station.send_agent_request",
            lambda *_args: {
                "completeBrushTable": table,
                "payloadHash": payload_hash(table),
                "versionLabel": "REMOTE-1",
            },
        )

        snapshot = pull_upper_snapshot(db, connection, "集成操作员")

        assert snapshot.parameter_payload["brushes"][0]["parameters"][0]["value"] == "320"
        assert snapshot.payload_hash == payload_hash(snapshot.parameter_payload)


def test_remote_network_failures_preserve_safe_release_states(monkeypatch) -> None:
    with Session(_engine(), expire_on_commit=False) as db:
        factory = Factory(code="FF", name="通信失败工厂")
        db.add(factory)
        db.flush()
        connection = RemoteStationConnection(
            connection_code="REMOTE-FAILURE",
            name="通信失败连接",
            factory_id=factory.id,
            station_code="CC2",
            station_name="清漆二站",
            process_stage="CLEARCOAT_2",
            host="127.0.0.1",
            port=9443,
            agent_id="AGENT-FAILURE",
            status="ACTIVE",
            operating_mode="APPROVED_RELEASES_ONLY",
        )
        db.add(connection)
        db.flush()
        release = RemoteProgramRelease(
            release_no="REL-FAILURE",
            connection_id=connection.id,
            base_program_version_id="base-version",
            candidate_program_version_id="candidate-version",
            status="APPROVED",
            package_hash="package-hash",
            package_payload={"candidatePayloadHash": "candidate-hash"},
            risk_summary="通信失败不得绕过审批状态",
            requested_by="申请人",
            requested_at=datetime.now(UTC),
            approved_by="审批人",
            approved_at=datetime.now(UTC),
        )
        db.add(release)
        db.commit()

        def fail_request(*_args):
            raise HTTPException(status_code=502, detail="无法连接目标上位机通讯程序")

        monkeypatch.setattr("app.services.remote_station.send_agent_request", fail_request)
        release = stage_release(db, release, "集成操作员")
        assert release.status == "APPROVED"
        assert "暂存未完成" in release.last_error

        release.status = "STAGED"
        db.commit()
        release = refresh_release_status(db, release, "集成操作员")
        assert release.status == "STAGED"
        assert "暂未取得" in release.last_error

        release.status = "LOCAL_CONFIRMED"
        release.local_confirmed_at = datetime.now(UTC)
        db.commit()
        release = commit_release(db, release, "机器人操作员")
        assert release.status == "WAITING_READBACK"
        assert "不要重复提交" in release.last_error
        event_types = {
            event.event_type
            for event in db.scalars(
                select(RemoteReleaseEvent).where(RemoteReleaseEvent.release_id == release.id)
            )
        }
        assert event_types == {"STAGE_FAILED", "STATUS_PENDING", "COMMIT_UNCERTAIN"}
