"""Audit Trail Router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from services.api.app.api.deps import require_role, TokenClaims, check_rate_limit
from services.api.app.api.dto.audit import AuditLogEntryDto
from services.api.app.api.dto.pagination import PaginatedResponse
from services.api.app.application.audit_service import audit_service

router = APIRouter(tags=["Compliance & Audit"])


@router.get("/audit", response_model=PaginatedResponse[AuditLogEntryDto])
async def get_audit_trail(
    cursor: Optional[int] = Query(None, description="Keyset pagination cursor (audit_id)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    user: TokenClaims = Depends(require_role(["admin"])),
    _rl: bool = Depends(check_rate_limit("audit_trail", limit_per_minute=60)),
):
    """Query immutable audit trail entries (Admin only)."""
    return await audit_service.get_audit_trail(
        user_role=user.role,
        cursor=cursor,
        limit=limit,
    )
