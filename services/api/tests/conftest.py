import os

os.environ.setdefault("APP_NAME", "PQ-AI API Test")
os.environ.setdefault("API_PREFIX", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("API_CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("API_AUTH_ENABLED", "false")
os.environ.setdefault("BOOTSTRAP_API_KEY", "test-bootstrap-api-key")
