FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN python -m pip install --no-cache-dir --prefer-binary --default-timeout=120 --retries=5 .

RUN addgroup --system pqai && adduser --system --ingroup pqai pqai
USER pqai
EXPOSE 8000
CMD : "${APP_NAME:?APP_NAME is required}"; : "${API_PREFIX:?API_PREFIX is required}"; : "${DATABASE_URL:?DATABASE_URL is required}"; : "${API_CORS_ORIGINS:?API_CORS_ORIGINS is required}"; : "${API_AUTH_ENABLED:?API_AUTH_ENABLED must be true}"; [ "$API_AUTH_ENABLED" = "true" ] || exit 1; : "${API_HOST:?API_HOST is required}"; : "${API_PORT:?API_PORT is required}"; : "${SEED_ON_STARTUP:=false}"; export API_AUTH_ENABLED SEED_ON_STARTUP; uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
