from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationEndpointCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    system_type: str = Field(min_length=2, max_length=32)
    direction: str = Field(default="INBOUND", max_length=24)
    base_url: str | None = Field(default=None, max_length=500)
    auth_type: str = Field(default="API_KEY", max_length=32)
    config: dict | None = None
    is_active: bool = True


class IntegrationEndpointUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    system_type: str | None = Field(default=None, min_length=2, max_length=32)
    direction: str | None = Field(default=None, max_length=24)
    base_url: str | None = Field(default=None, max_length=500)
    auth_type: str | None = Field(default=None, max_length=32)
    config: dict | None = None
    is_active: bool | None = None


class IntegrationEndpointRead(IntegrationEndpointCreate):
    id: str
    last_success_at: datetime | None
    last_failure_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationEventCreate(BaseModel):
    endpoint_id: str
    source_event_id: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=2, max_length=64)
    direction: str = Field(default="INBOUND", max_length=24)
    payload: dict
    max_attempts: int = Field(default=3, ge=1, le=20)
    process_immediately: bool = True


class IntegrationEventRead(BaseModel):
    id: str
    event_no: str
    endpoint_id: str
    source_event_id: str
    event_type: str
    direction: str
    status: str
    payload: dict
    mapped_payload: dict | None
    attempt_count: int
    max_attempts: int
    next_retry_at: datetime | None
    last_error: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
