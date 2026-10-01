"""Fleet Router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
from services.api.app.api.deps import get_current_user, TokenClaims, check_rate_limit
from services.api.app.api.dto.fleet import (
    VehicleListItemDto,
    FleetSummaryDto,
    FleetMapDto,
)
from services.api.app.api.dto.pagination import PaginatedResponse
from services.api.app.application.fleet_service import fleet_service

router = APIRouter(prefix="/fleets", tags=["Fleets"])


@router.get("/{fleet_id}/vehicles", response_model=PaginatedResponse[VehicleListItemDto])
async def list_fleet_vehicles(
    fleet_id: int = Path(..., ge=1, le=2147483647, description="Fleet ID"),
    cursor: Optional[str] = Query(None, description="Keyset pagination cursor (VIN)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("fleet_vehicles", limit_per_minute=200)),
):
    """Retrieve fleet vehicles using high-performance keyset pagination (NOTE.md §14 Q1)."""
    return await fleet_service.get_fleet_vehicles(
        fleet_id=fleet_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
        cursor=cursor,
        limit=limit,
    )


@router.get("/{fleet_id}/summary", response_model=FleetSummaryDto)
async def get_fleet_summary(
    fleet_id: int = Path(..., ge=1, le=2147483647, description="Fleet ID"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("fleet_summary", limit_per_minute=200)),
):
    """Retrieve operational fleet KPIs and energy statistics."""
    return await fleet_service.get_fleet_summary(
        fleet_id=fleet_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )


@router.get("/{fleet_id}/map", response_model=FleetMapDto)
async def get_fleet_map(
    fleet_id: int = Path(..., ge=1, le=2147483647, description="Fleet ID"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("fleet_map", limit_per_minute=200)),
):
    """Server-side geohash cell clustered map. Role-aware: viewers receive geohash5 masked coords."""
    return await fleet_service.get_fleet_map(
        fleet_id=fleet_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )
