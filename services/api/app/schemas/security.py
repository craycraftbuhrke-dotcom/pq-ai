from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActorRead(BaseModel):
    user_id: str | None
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    auth_enabled: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    actor: ActorRead


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    is_active: bool = True


class UserRead(BaseModel):
    id: str
    username: str
    display_name: str
    email: str | None
    department: str | None
    is_active: bool
    last_login_at: datetime | None = None
    locked_until: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    permission_codes: list[str] = Field(default_factory=list)


class RoleRead(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    permission_codes: list[str]


class UserRoleAssignment(BaseModel):
    role_code: str = Field(min_length=2, max_length=64)


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    expires_at: datetime | None = None


class ApiKeyIssued(BaseModel):
    id: str
    name: str
    key_prefix: str
    raw_key: str
    expires_at: datetime | None
    warning: str = "密钥仅在本次响应中显示，请安全保存。"


class AuditLogRead(BaseModel):
    id: str
    request_id: str
    actor_username: str
    action: str
    http_method: str
    path: str
    resource_type: str | None
    resource_id: str | None
    status_code: int
    client_ip: str | None
    detail: dict | None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditSummary(BaseModel):
    total_events: int
    successful_writes: int
    failed_writes: int
    active_users: int
    active_api_keys: int
    events_by_action: dict[str, int]
