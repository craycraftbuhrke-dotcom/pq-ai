import os
from secrets import token_urlsafe

os.environ.setdefault("APP_NAME", "PQ-AI API Test")
os.environ.setdefault("API_PREFIX", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("API_CORS_ORIGINS", "http://localhost,http://localhost:80,http://localhost:8080")
os.environ.setdefault("API_AUTH_ENABLED", "false")
os.environ.setdefault("TEST_RUNTIME_API_KEY", token_urlsafe(32))
os.environ.setdefault("TEST_RUNTIME_PASSWORD", token_urlsafe(32))
