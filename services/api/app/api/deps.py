"""FastAPI Dependencies for Auth, RBAC, and Rate Limiting."""

from typing import List, Optional, Callable
from fastapi import Request, Depends, Header
from services.api.app.domain.security.jwt import jwt_manager, TokenClaims
from services.api.app.domain.rate_limit.token_bucket import rate_limiter
from services.api.app.api.dto.problem import (
    UnauthorizedException,
    ForbiddenException,
    RateLimitExceededException,
)


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> TokenClaims:
    """Extract and verify Bearer RS256 JWT token."""
    if not authorization:
        raise UnauthorizedException(
            detail="Authorization header missing",
            instance=request.url.path,
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(
            detail="Authorization header must follow Bearer <token> format",
            instance=request.url.path,
        )

    token = parts[1]
    try:
        claims = jwt_manager.verify_token(token)
        return claims
    except Exception as exc:
        raise UnauthorizedException(
            detail=f"Invalid or expired access token: {str(exc)}",
            instance=request.url.path,
        )


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory checking user role membership."""
    async def _role_checker(user: TokenClaims = Depends(get_current_user)) -> TokenClaims:
        if user.role not in allowed_roles:
            raise ForbiddenException(
                detail=f"Operation requires one of roles {allowed_roles}, but user has role '{user.role}'"
            )
        return user
    return _role_checker


def check_rate_limit(route_name: str, limit_per_minute: int = 120) -> Callable:
    """Dependency checking tenant-specific token bucket rate limit."""
    async def _limiter(user: TokenClaims = Depends(get_current_user)):
        from services.api.app.config import settings
        from services.api.app.monitoring import RATE_LIMIT_EXCEEDED_TOTAL

        if not settings.RATE_LIMIT_ENABLED or user.role == "admin":
            return True

        limit = max(limit_per_minute, settings.RATE_LIMIT_TOKENS_PER_MINUTE)
        allowed, remaining, retry_after = await rate_limiter.is_allowed(
            tenant_id=user.tenant_id,
            route=route_name,
            limit_per_minute=limit,
        )
        if not allowed:
            RATE_LIMIT_EXCEEDED_TOTAL.labels(route=route_name).inc()
            raise RateLimitExceededException(
                retry_after=retry_after,
                detail=f"Rate limit of {limit} req/min exceeded for tenant {user.tenant_id}",
            )
        return True
    return _limiter
