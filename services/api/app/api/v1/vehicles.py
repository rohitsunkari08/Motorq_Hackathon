"""Vehicle Router."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from services.api.app.api.deps import get_current_user, TokenClaims, check_rate_limit
from services.api.app.api.dto.vehicle import (
    VehicleDetailDto,
    TelemetryPointDto,
    VehicleSohResponseDto,
)
from services.api.app.application.vehicle_service import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/{vin}", response_model=VehicleDetailDto)
async def get_vehicle(
    vin: str,
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("vehicle_detail", limit_per_minute=200)),
):
    """Retrieve detailed vehicle specs, current real-time state, and role-masked location."""
    return await vehicle_service.get_vehicle_detail(
        vin=vin,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )


@router.get("/{vin}/telemetry", response_model=List[TelemetryPointDto])
async def get_vehicle_telemetry(
    vin: str,
    from_ts: Optional[datetime] = Query(None, alias="from", description="ISO UTC start timestamp"),
    to_ts: Optional[datetime] = Query(None, alias="to", description="ISO UTC end timestamp"),
    limit: int = Query(100, ge=1, le=500, description="Max telemetry records"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("vehicle_telemetry", limit_per_minute=200)),
):
    """Query time-series telemetry from ClickHouse (protected by Circuit Breaker)."""
    return await vehicle_service.get_vehicle_telemetry(
        vin=vin,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
    )


@router.get("/{vin}/soh", response_model=VehicleSohResponseDto)
async def get_vehicle_soh(
    vin: str,
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("vehicle_soh", limit_per_minute=200)),
):
    """Retrieve historical SoH estimates and ML XGBoost degradation predictions."""
    return await vehicle_service.get_vehicle_soh(
        vin=vin,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )
