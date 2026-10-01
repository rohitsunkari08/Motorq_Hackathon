"""Charge Plans Router."""

from fastapi import APIRouter, Depends, Path
from services.api.app.api.deps import get_current_user, require_role, TokenClaims, check_rate_limit
from services.api.app.api.dto.plan import (
    ProposePlanRequest,
    ChargePlanDto,
    ApproveRejectResponse,
)
from services.api.app.application.plan_service import plan_service

router = APIRouter(tags=["Charge Plans"])


@router.post("/vehicles/{vin}/charge-plans:propose", response_model=ChargePlanDto)
async def propose_charge_plan(
    vin: str,
    req: ProposePlanRequest,
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("propose_plan", limit_per_minute=60)),
):
    """Propose an optimal battery-aware charging schedule using Dynamic Programming."""
    return await plan_service.propose_plan(
        vin=vin,
        charger_id=req.charger_id,
        target_soc=req.target_soc,
        departure_hours_ahead=req.departure_hours_ahead,
        current_soc_override=req.current_soc,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )


@router.post("/charge-plans/{plan_id}/approve", response_model=ApproveRejectResponse)
async def approve_charge_plan(
    plan_id: int = Path(..., ge=1, le=9223372036854775807, description="Plan ID"),
    user: TokenClaims = Depends(require_role(["admin", "fleet_manager"])),
    _rl: bool = Depends(check_rate_limit("approve_plan", limit_per_minute=60)),
):
    """Approve a proposed charge plan (fleet managers and admins only)."""
    return await plan_service.approve_plan(
        plan_id=plan_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        user_id=int(user.sub),
        actor=user.email,
    )


@router.post("/charge-plans/{plan_id}/reject", response_model=ApproveRejectResponse)
async def reject_charge_plan(
    plan_id: int = Path(..., ge=1, le=9223372036854775807, description="Plan ID"),
    user: TokenClaims = Depends(require_role(["admin", "fleet_manager"])),
    _rl: bool = Depends(check_rate_limit("reject_plan", limit_per_minute=60)),
):
    """Reject a proposed charge plan (fleet managers and admins only)."""
    return await plan_service.reject_plan(
        plan_id=plan_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        user_id=int(user.sub),
        actor=user.email,
    )
