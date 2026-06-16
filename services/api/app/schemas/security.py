from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    api_key: str
    api_key_name: str
    expires_at: datetime | None
    warning: str = "API Key 仅在本次响应中显示，请安全保存。浏览器会话已通过 Cookie 保存认证状态。"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=120)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=120)


class ActorRead(BaseModel):
    user_id: str | None
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    auth_enabled: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=120)
    is_active: bool = True


class UserRead(UserCreate):
    id: str
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
