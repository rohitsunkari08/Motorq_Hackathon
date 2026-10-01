"""PostgreSQL Database Client with Row-Level Security (RLS) support
Uses asyncpg connection pooling.
Enforces tenant isolation by setting `app.tenant_id` locally per transaction.
"""

import json
from typing import AsyncGenerator, Optional
import asyncpg
from contextlib import asynccontextmanager

from services.api.app.config import settings


class PostgresClient:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def init_pool(self):
        import asyncio
        current_loop = asyncio.get_running_loop()
        if self.pool and getattr(self.pool, "_loop", None) == current_loop:
            return
        if self.pool:
            try:
                await self.pool.close()
            except Exception:
                pass
            self.pool = None

        self.pool = await asyncpg.create_pool(
            dsn=settings.POSTGRES_URL,
            min_size=2,
            max_size=15,
            command_timeout=30.0,
            max_inactive_connection_lifetime=30.0,
        )

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def tenant_session(
        self,
        tenant_id: Optional[int] = None,
        bypass_rls: bool = False,
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """Context manager providing a connection with transaction-scoped tenant RLS."""
        import asyncio
        current_loop = asyncio.get_running_loop()
        if not self.pool or getattr(self.pool, "_loop", None) != current_loop:
            await self.init_pool()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if bypass_rls:
                    await conn.execute("SET LOCAL app.bypass_rls = 'on';")
                elif tenant_id is not None:
                    await conn.execute(f"SET LOCAL app.tenant_id = '{int(tenant_id)}';")
                yield conn


postgres_client = PostgresClient()
