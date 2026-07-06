from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard_snapshot import dashboard_snapshot

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)) -> dict:
    return dashboard_snapshot(db if isinstance(db, Session) else None)
