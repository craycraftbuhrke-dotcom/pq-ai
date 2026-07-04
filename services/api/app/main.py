from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.api.router import api_router
from app.core.config import settings
from app.db.schema_policy import missing_column_name, missing_table_name
from app.middleware.security import security_and_audit_middleware

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="汽车喷涂工艺与漆膜质量 AI 闭环 API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(security_and_audit_middleware)
app.include_router(api_router, prefix=settings.api_prefix)


def _schema_mismatch_response(
    request: Request,
    *,
    missing_table: str | None = None,
    missing_column: str | None = None,
) -> JSONResponse:
    missing_part = f"缺少表 {missing_table}" if missing_table else f"缺少字段 {missing_column}"
    content: dict[str, str | None] = {
        "code": "SCHEMA_MISMATCH",
        "detail": (
            f"当前 MySQL 数据库结构未与应用版本同步，{missing_part}。"
            "数据库结构变更必须走审批工单并由人工执行项目 DBA SQL 后再启动系统。"
        ),
        "request_id": getattr(request.state, "request_id", None),
    }
    if missing_table:
        content["missing_table"] = missing_table
    if missing_column:
        content["missing_column"] = missing_column
    return JSONResponse(status_code=503, content=content)


@app.exception_handler(ProgrammingError)
async def database_programming_error_handler(
    request: Request, exc: ProgrammingError
) -> JSONResponse:
    table_name = missing_table_name(exc)
    if table_name:
        return _schema_mismatch_response(request, missing_table=table_name)
    return JSONResponse(
        status_code=500,
        content={
            "code": "DATABASE_PROGRAMMING_ERROR",
            "detail": "数据库执行错误，请检查数据库结构、字段或 SQL 兼容性。",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(OperationalError)
async def database_operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    column_name = missing_column_name(exc)
    if column_name:
        return _schema_mismatch_response(request, missing_column=column_name)
    return JSONResponse(
        status_code=500,
        content={
            "code": "DATABASE_OPERATIONAL_ERROR",
            "detail": "数据库连接或执行错误，请检查 MySQL 服务、表结构和字段兼容性。",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "api": settings.api_prefix}
