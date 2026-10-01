from fastapi import APIRouter
from services.api.app.api.v1.auth import router as auth_router
from services.api.app.api.v1.fleets import router as fleets_router
from services.api.app.api.v1.vehicles import router as vehicles_router
from services.api.app.api.v1.alerts import router as alerts_router
from services.api.app.api.v1.chargers import router as chargers_router
from services.api.app.api.v1.plans import router as plans_router
from services.api.app.api.v1.benchmarks import router as benchmarks_router
from services.api.app.api.v1.privacy import router as privacy_router
from services.api.app.api.v1.audit import router as audit_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(fleets_router)
api_v1_router.include_router(vehicles_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(chargers_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(benchmarks_router)
api_v1_router.include_router(privacy_router)
api_v1_router.include_router(audit_router)

__all__ = ["api_v1_router"]
