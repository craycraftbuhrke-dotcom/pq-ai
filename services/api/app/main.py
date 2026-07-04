from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.database_errors import database_error_response
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


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", None)
    return database_error_response(exc, request_id)


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "api": settings.api_prefix}
