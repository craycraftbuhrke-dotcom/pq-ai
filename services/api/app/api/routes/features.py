from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.features import PointFeatureBuildRequest, PointFeatureResult
from app.services.feature_aggregation import build_point_feature_snapshot

router = APIRouter(prefix="/features", tags=["feature-engineering"])


@router.post("/point-snapshots/build", response_model=PointFeatureResult)
def build_point_snapshot(
    payload: PointFeatureBuildRequest, db: Session = Depends(get_db)
) -> dict:
    return build_point_feature_snapshot(
        db,
        production_run_id=payload.production_run_id,
        measurement_point_id=payload.measurement_point_id,
        target_family=payload.target_family,
        feature_set_version=payload.feature_set_version,
    )
