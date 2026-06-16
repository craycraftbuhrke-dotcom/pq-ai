from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError


MAX_DATABASE_ERROR_LENGTH = 2000


def describe_database_error(exc: BaseException) -> str:
    raw_message = str(exc.orig) if isinstance(exc, DBAPIError) and exc.orig else str(exc)
    message = " ".join(raw_message.split())
    if len(message) > MAX_DATABASE_ERROR_LENGTH:
        return f"{message[:MAX_DATABASE_ERROR_LENGTH]}..."
    return message


def database_error_payload(exc: BaseException, request_id: str | None = None) -> dict[str, str]:
    message = f"数据库操作失败：{describe_database_error(exc)}"
    payload = {
        "detail": message,
        "error": message,
        "error_type": exc.__class__.__name__,
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def database_error_response(exc: BaseException, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=503, content=database_error_payload(exc, request_id))
