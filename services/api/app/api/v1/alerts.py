"""Alerts Router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse
from services.api.app.api.deps import get_current_user, TokenClaims, check_rate_limit
from services.api.app.api.dto.alert import AlertDto, AckAlertResponse
from services.api.app.api.dto.pagination import PaginatedResponse
from services.api.app.application.alert_service import alert_service

router = APIRouter(tags=["Alerts"])


@router.get("/alerts", response_model=PaginatedResponse[AlertDto])
async def list_alerts(
    status: str = Query("open", pattern="^(open|resolved|all)$", description="Filter by alert status"),
    cursor: Optional[str] = Query(None, description="Keyset pagination cursor"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("list_alerts", limit_per_minute=200)),
):
    """List fleet alerts with keyset pagination using partial index (NOTE.md §14 Q2)."""
    return await alert_service.get_alerts(
        tenant_id=user.tenant_id,
        status=status,
        user_role=user.role,
        actor=user.email,
        cursor=cursor,
        limit=limit,
    )


@router.post("/alerts/{alert_id}/ack", response_model=AckAlertResponse)
async def acknowledge_alert(
    alert_id: int = Path(..., ge=1, le=9223372036854775807, description="Alert ID"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("ack_alert", limit_per_minute=100)),
):
    """Acknowledge / resolve an active alert."""
    return await alert_service.acknowledge_alert(
        alert_id=alert_id,
        tenant_id=user.tenant_id,
        user_role=user.role,
        actor=user.email,
    )


@router.get("/stream/alerts")
async def stream_alerts(
    user: TokenClaims = Depends(get_current_user),
):
    """Stream live alerts via Server-Sent Events (SSE)."""
    return StreamingResponse(
        alert_service.stream_alerts(user.tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
