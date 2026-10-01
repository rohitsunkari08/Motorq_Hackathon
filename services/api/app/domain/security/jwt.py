"""RS256 JWT Issuer and Validator
Generates RSA keypair if missing, signs and verifies tokens per NOTE.md §6.3 / §7.
Claims: sub, email, tenant_id, role, exp, iat
"""

import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pydantic import BaseModel

from services.api.app.config import settings, CERTS_DIR


class TokenClaims(BaseModel):
    sub: str
    email: str
    tenant_id: int
    role: str
    exp: int
    iat: int


class JWTManager:
    def __init__(self, certs_dir: Path = CERTS_DIR):
        self.certs_dir = certs_dir
        self.private_key_path = certs_dir / "jwt_rs256.key"
        self.public_key_path = certs_dir / "jwt_rs256.pub"
        self._private_key_pem: Optional[bytes] = None
        self._public_key_pem: Optional[bytes] = None
        self._ensure_keys()

    def _ensure_keys(self):
        """Ensure RSA keys exist on disk; generate if missing."""
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        if not self.private_key_path.exists() or not self.public_key_path.exists():
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            self._private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key = private_key.public_key()
            self._public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            with open(self.private_key_path, "wb") as f:
                f.write(self._private_key_pem)
            with open(self.public_key_path, "wb") as f:
                f.write(self._public_key_pem)
        else:
            with open(self.private_key_path, "rb") as f:
                self._private_key_pem = f.read()
            with open(self.public_key_path, "rb") as f:
                self._public_key_pem = f.read()

    @property
    def private_key(self) -> bytes:
        if not self._private_key_pem:
            self._ensure_keys()
        return self._private_key_pem

    @property
    def public_key(self) -> bytes:
        if not self._public_key_pem:
            self._ensure_keys()
        return self._public_key_pem

    def create_access_token(
        self,
        user_id: int,
        email: str,
        tenant_id: int,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create RS256 signed access token valid for 15 minutes by default."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user_id),
            "email": email,
            "tenant_id": tenant_id,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        token = jwt.encode(payload, self.private_key, algorithm=settings.JWT_ALGORITHM)
        return token

    # Alias for convenience
    issue_token = create_access_token

    def verify_token(self, token: str) -> TokenClaims:
        """Verify RS256 token and return parsed TokenClaims. Raises PyJWTError on failure."""
        payload = jwt.decode(
            token,
            self.public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "email", "tenant_id", "role", "exp", "iat"]},
        )
        return TokenClaims(**payload)


jwt_manager = JWTManager()
