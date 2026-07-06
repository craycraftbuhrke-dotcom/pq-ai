from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PQ-AI API"
    api_prefix: str = "/api/v1"
    database_url: str
    # 默认允许 nginx 惯例端口（80）与常见备用端口（8080），部署时通过 API_CORS_ORIGINS 覆盖
    api_cors_origins: str = "http://localhost,http://localhost:80,http://localhost:8080"
    # 认证总开关：默认关闭，测试期直接放行所有请求；正式投用时通过环境变量 API_AUTH_ENABLED=true 开启。
    api_auth_enabled: bool = False
    session_ttl_minutes: int = 12 * 60
    login_lockout_threshold: int = 5
    login_lockout_minutes: int = 15
    # 启动时自动预置固定字典（质量指标定义 + 工艺参数定义）。默认开启；
    # 若某次部署想跳过（例如 DB 只读、只做灰度），可通过环境变量 SEED_ON_STARTUP=false 关闭。
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
