"""Authentication Application Service
Verifies credentials using Argon2id and generates RS256 JWT tokens.
"""

from typing import Dict, Any, Optional
from services.api.app.domain.security.passwords import verify_password
from services.api.app.domain.security.jwt import jwt_manager
from services.api.app.infra.repos.user_repo import user_repo
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.api.dto.problem import UnauthorizedException
from services.api.app.api.dto.auth import LoginResponse, UserDto


class AuthService:
    async def login(self, email: str, password: str, client_ip: Optional[str] = None) -> LoginResponse:
        user = await user_repo.get_by_email(email)
        if not user or not verify_password(password, user["pw_hash"]):
            await audit_repo.log_event(
                actor=email,
                actor_type="user",
                action="login_failed",
                resource="auth",
                detail={"ip": client_ip, "reason": "invalid_credentials"},
            )
            raise UnauthorizedException(detail="Invalid email or password")

        # Generate RS256 JWT token
        token = jwt_manager.create_access_token(
            user_id=user["user_id"],
            email=user["email"],
            tenant_id=user["tenant_id"],
            role=user["role"],
        )

        await audit_repo.log_event(
            actor=user["email"],
            actor_type="user",
            action="login_success",
            resource=f"user:{user['user_id']}",
            detail={"role": user["role"], "tenant_id": user["tenant_id"], "ip": client_ip},
        )

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=900,
            user=UserDto(
                user_id=user["user_id"],
                tenant_id=user["tenant_id"],
                email=user["email"],
                role=user["role"],
            ),
        )


auth_service = AuthService()
