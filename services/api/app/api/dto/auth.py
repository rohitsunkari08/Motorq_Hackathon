"""Auth DTOs."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@voltfleet.com")
    password: str = Field(..., min_length=1, example="Password123!")


class UserDto(BaseModel):
    user_id: int
    tenant_id: int
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes
    user: UserDto
