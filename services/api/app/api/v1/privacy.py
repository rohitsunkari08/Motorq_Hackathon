"""Privacy and Right-to-Erasure Router."""

from fastapi import APIRouter, Depends
from services.api.app.api.deps import require_role, TokenClaims, check_rate_limit
from services.api.app.api.dto.privacy import ErasureRequest, ErasureResponse
from services.api.app.application.privacy_service import privacy_service

router = APIRouter(prefix="/privacy", tags=["Privacy & Compliance"])


@router.post("/erasure", response_model=ErasureResponse)
async def execute_erasure(
    req: ErasureRequest,
    user: TokenClaims = Depends(require_role(["admin"])),
    _rl: bool = Depends(check_rate_limit("privacy_erasure", limit_per_minute=20)),
):
    """Execute GDPR/DPDP Right-to-Erasure across PostgreSQL, Redis, and ClickHouse (Admin only)."""
    return await privacy_service.execute_erasure(
        vin=req.vin,
        driver_id=req.driver_id,
        user_role=user.role,
        actor=user.email,
    )
