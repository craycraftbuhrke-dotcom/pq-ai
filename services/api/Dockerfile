ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "if [ \"$SEED_DEMO_DATA\" = \"true\" ]; then python -m app.db.seed_demo; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
