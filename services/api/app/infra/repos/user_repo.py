"""User Repository for Postgres authentication and lookup."""

from typing import Optional, Dict, Any
import asyncpg
from services.api.app.infra.postgres import postgres_client


class UserRepo:
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT user_id, tenant_id, email, role, pw_hash
            FROM app_user
            WHERE email = $1;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            row = await conn.fetchrow(query, email)
            return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT user_id, tenant_id, email, role
            FROM app_user
            WHERE user_id = $1;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            row = await conn.fetchrow(query, user_id)
            return dict(row) if row else None


user_repo = UserRepo()
