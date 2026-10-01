"""Chargers Router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from services.api.app.api.deps import get_current_user, TokenClaims, check_rate_limit
from services.api.app.api.dto.charger import NearestChargerResponse
from services.api.app.application.charger_service import charger_service

router = APIRouter(prefix="/chargers", tags=["Chargers"])


@router.get("/nearest", response_model=NearestChargerResponse)
async def get_nearest_chargers(
    vin: str = Query(..., description="Vehicle VIN to calculate reachable range"),
    lat: Optional[float] = Query(None, description="Optional override latitude"),
    lon: Optional[float] = Query(None, description="Optional override longitude"),
    limit: int = Query(5, ge=1, le=20, description="Max chargers to return"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("nearest_chargers", limit_per_minute=100)),
):
    """Find and rank reachable chargers using geohash spatial indexing and 10% safety reserve."""
    return await charger_service.find_nearest_chargers(
        vin=vin,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
        override_lat=lat,
        override_lon=lon,
        limit=limit,
    )
