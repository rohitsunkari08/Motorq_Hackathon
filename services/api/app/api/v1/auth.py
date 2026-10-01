"""Auth Router."""

from fastapi import APIRouter, Request
from services.api.app.api.dto.auth import LoginRequest, LoginResponse
from services.api.app.application.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    """Authenticate with email and password to receive an RS256 JWT access token."""
    client_ip = request.client.host if request.client else None
    return await auth_service.login(req.email, req.password, client_ip=client_ip)
