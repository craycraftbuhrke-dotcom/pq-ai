from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PQ-AI API"
    api_prefix: str = "/api/v1"
    database_url: str = (
        "mysql+pymysql://pq_ai:pq_ai_dev_password@localhost:3306/pq_ai?charset=utf8mb4"
    )
    api_cors_origins: str = "http://localhost:3000"
    api_auth_enabled: bool = False
    bootstrap_api_key: str = "pq-ai-demo-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
