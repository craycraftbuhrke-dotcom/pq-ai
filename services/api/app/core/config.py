from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PQ-AI API"
    api_prefix: str = "/api/v1"
    database_url: str
    # 默认允许 nginx 惯例端口（80）与常见备用端口（8080），部署时通过 API_CORS_ORIGINS 覆盖
    api_cors_origins: str = "http://localhost,http://localhost:80,http://localhost:8080"
    # 默认失败关闭；只有隔离测试可显式设为 false。
    api_auth_enabled: bool = True
    allow_self_registration: bool = False
    session_ttl_minutes: int = 12 * 60
    login_lockout_threshold: int = 5
    login_lockout_minutes: int = 15
    bulk_import_max_bytes: int = 50 * 1024 * 1024
    file_import_max_bytes: int = 50 * 1024 * 1024
    # 生产启动不得隐式写库。仅在受控初始化任务中显式开启目录预置。
    seed_on_startup: bool = False
    # Optional Redis for multi-replica actor/summary cache. Empty = in-process TTL only.
    redis_url: str | None = None
    cache_default_ttl_seconds: int = 45
    actor_cache_ttl_seconds: int = 60
    summary_cache_ttl_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
