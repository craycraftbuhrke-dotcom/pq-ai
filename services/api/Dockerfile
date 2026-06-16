ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD : "${APP_NAME:?APP_NAME is required}"; : "${API_PREFIX:?API_PREFIX is required}"; : "${DATABASE_URL:?DATABASE_URL is required}"; : "${API_CORS_ORIGINS:?API_CORS_ORIGINS is required}"; : "${API_AUTH_ENABLED:?API_AUTH_ENABLED is required}"; : "${BOOTSTRAP_API_KEY:?BOOTSTRAP_API_KEY is required}"; : "${API_HOST:?API_HOST is required}"; : "${API_PORT:?API_PORT is required}"; alembic upgrade head && if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then python -m app.db.seed_demo; fi && uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
