from fastapi import APIRouter

from app.api.routes import (
    ai,
    body_map,
    bulk,
    dashboard,
    engineering,
    factories,
    features,
    health,
    integration,
    master_data,
    material_governance,
    measurement_governance,
    modeling,
    process,
    quality,
    recipe_wide,
    remote_station,
    robot_governance,
    security,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(engineering.router)
api_router.include_router(factories.router)
api_router.include_router(master_data.router)
api_router.include_router(process.router)
api_router.include_router(recipe_wide.router)
api_router.include_router(remote_station.router)
api_router.include_router(material_governance.router)
api_router.include_router(robot_governance.router)
api_router.include_router(quality.router)
api_router.include_router(body_map.router)
api_router.include_router(measurement_governance.router)
api_router.include_router(features.router)
api_router.include_router(modeling.router)
api_router.include_router(integration.router)
api_router.include_router(security.router)
api_router.include_router(ai.router)
api_router.include_router(bulk.router)
