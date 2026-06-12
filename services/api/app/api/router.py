from fastapi import APIRouter

from app.api.routes import (
    ai,
    dashboard,
    factories,
    features,
    health,
    integration,
    master_data,
    modeling,
    process,
    quality,
    security,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(factories.router)
api_router.include_router(master_data.router)
api_router.include_router(process.router)
api_router.include_router(quality.router)
api_router.include_router(features.router)
api_router.include_router(modeling.router)
api_router.include_router(integration.router)
api_router.include_router(security.router)
api_router.include_router(ai.router)
