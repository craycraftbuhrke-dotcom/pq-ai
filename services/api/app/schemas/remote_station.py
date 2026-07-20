from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RemoteStationConnectionCreate(BaseModel):
    connection_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=160)
    factory_id: str
    station_code: str = Field(min_length=1, max_length=64)
    station_name: str = Field(min_length=1, max_length=120)
    process_stage: Literal[
        "MIDCOAT_EXT", "BASECOAT_1", "BASECOAT_2", "CLEARCOAT_1", "CLEARCOAT_2"
    ]
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    adapter_mode: Literal["SIMULATOR", "FILE_DROP", "DURR_APPROVED_ADAPTER"] = "SIMULATOR"
    agent_id: str = Field(min_length=1, max_length=80)
    server_name: str | None = Field(default=None, max_length=255)
    client_certificate_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    client_private_key_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    trusted_ca_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    max_package_bytes: int = Field(default=5_242_880, ge=1024, le=20_971_520)
    remark: str | None = None


class RemoteStationConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    station_code: str | None = Field(default=None, min_length=1, max_length=64)
    station_name: str | None = Field(default=None, min_length=1, max_length=120)
    process_stage: Literal[
        "MIDCOAT_EXT", "BASECOAT_1", "BASECOAT_2", "CLEARCOAT_1", "CLEARCOAT_2"
    ] | None = None
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    adapter_mode: Literal["SIMULATOR", "FILE_DROP", "DURR_APPROVED_ADAPTER"] | None = None
    agent_id: str | None = Field(default=None, min_length=1, max_length=80)
    server_name: str | None = Field(default=None, max_length=255)
    client_certificate_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    client_private_key_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    trusted_ca_ref: str | None = Field(
        default=None, max_length=160, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    connect_timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    max_package_bytes: int | None = Field(default=None, ge=1024, le=20_971_520)
    remark: str | None = None


class RemoteStationApproval(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    comment: str | None = Field(default=None, max_length=1000)


class RemoteStationConnectionRead(BaseModel):
    id: str
    connection_code: str
    name: str
    factory_id: str
    station_code: str
    station_name: str
    process_stage: str
    host: str
    port: int
    transport: str
    adapter_mode: str
    agent_id: str
    server_name: str | None
    client_certificate_ref: str | None
    client_private_key_ref: str | None
    trusted_ca_ref: str | None
    status: str
    operating_mode: str
    local_confirmation_required: bool
    connect_timeout_seconds: int
    max_package_bytes: int
    last_seen_at: datetime | None
    last_inventory_hash: str | None
    approved_by: str | None
    approved_at: datetime | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemoteSnapshotCapture(BaseModel):
    source_type: Literal["CLOUD", "VIRTUAL_LINE"]
    program_version_id: str
    version_label: str | None = Field(default=None, max_length=80)


class RemoteParameterSnapshotRead(BaseModel):
    id: str
    connection_id: str
    source_type: str
    program_version_id: str | None
    version_label: str
    payload_hash: str
    parameter_payload: dict
    collection_ref: str | None
    status: str
    collected_by: str
    collected_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemoteReleaseCreate(BaseModel):
    connection_id: str
    base_program_version_id: str
    candidate_program_version_id: str
    risk_summary: str = Field(min_length=1, max_length=4000)


class RemoteReleaseAction(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class RemoteProgramReleaseRead(BaseModel):
    id: str
    release_no: str
    connection_id: str
    base_program_version_id: str
    candidate_program_version_id: str
    status: str
    package_hash: str
    package_payload: dict
    risk_summary: str
    requested_by: str
    requested_at: datetime
    approved_by: str | None
    approved_at: datetime | None
    staged_at: datetime | None
    local_confirmed_at: datetime | None
    applied_at: datetime | None
    verified_at: datetime | None
    readback_hash: str | None
    rollback_program_version_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemoteReleaseEventRead(BaseModel):
    id: str
    release_id: str
    event_type: str
    status: str
    message: str
    event_payload: dict | None
    actor: str
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemoteReconciliationRead(BaseModel):
    id: str
    connection_id: str
    cloud_snapshot_id: str | None
    virtual_snapshot_id: str | None
    upper_snapshot_id: str | None
    status: str
    diff_payload: dict
    generated_by: str
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
