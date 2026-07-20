from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["system"])


@router.get("/health/live")
def liveness() -> dict:
    return {"status": "ok", "service": "pq-ai-api", "check": "liveness"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="数据库尚未就绪") from exc
    return {"status": "ok", "service": "pq-ai-api", "check": "readiness"}


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return readiness(db)
