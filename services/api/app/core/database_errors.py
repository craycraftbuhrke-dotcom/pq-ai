from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError


MAX_DATABASE_ERROR_LENGTH = 2000


def describe_database_error(exc: BaseException) -> str:
    raw_message = str(exc.orig) if isinstance(exc, DBAPIError) and exc.orig else str(exc)
    message = " ".join(raw_message.split())
    if len(message) > MAX_DATABASE_ERROR_LENGTH:
        return f"{message[:MAX_DATABASE_ERROR_LENGTH]}..."
    return message


def classify_database_error(exc: BaseException) -> tuple[int, str]:
    if isinstance(exc, IntegrityError):
        message = describe_database_error(exc).lower()
        if "foreign key" in message or "fk_" in message or "references" in message:
            return 409, "数据引用冲突：关联的目标记录不存在或已被删除，请检查输入数据"
        if "duplicate" in message or "unique" in message:
            return 409, "数据重复冲突：相同的数据记录已存在，请勿重复提交"
        if "not null" in message or "null" in message:
            return 422, "数据完整性错误：必填字段缺失，请检查输入数据"
        return 409, f"数据完整性冲突：{describe_database_error(exc)}"
    if isinstance(exc, OperationalError):
        message = describe_database_error(exc).lower()
        if "lock" in message or "deadlock" in message:
            return 503, "数据库繁忙：存在并发操作冲突，请稍后重试"
        if "timeout" in message or "timed out" in message:
            return 504, "数据库操作超时：请确认数据量是否正常，稍后重试"
        if "connection" in message or "refused" in message or "gone away" in message:
            return 502, "数据库连接失败：请确认数据库服务是否正常运行"
        return 503, f"数据库操作异常：{describe_database_error(exc)}"
    return 503, f"数据库操作失败：{describe_database_error(exc)}"


def database_error_payload(exc: BaseException, request_id: str | None = None) -> dict[str, str]:
    status, message = classify_database_error(exc)
    payload: dict[str, str] = {
        "detail": message,
        "error": message,
        "error_type": exc.__class__.__name__,
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def database_error_status(exc: BaseException) -> int:
    status, _ = classify_database_error(exc)
    return status


def database_error_response(exc: BaseException, request_id: str | None = None) -> JSONResponse:
    status, message = classify_database_error(exc)
    payload: dict[str, str] = {
        "detail": message,
        "error": message,
        "error_type": exc.__class__.__name__,
    }
    if request_id:
        payload["request_id"] = request_id
    return JSONResponse(status_code=status, content=payload)
