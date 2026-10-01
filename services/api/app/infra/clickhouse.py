"""ClickHouse Client with Circuit Breaker Protection
Per NOTE.md §6.3:
Circuit breaker around ClickHouse queries to prevent cascading failures.
"""

from typing import Optional, List, Dict, Any
import asyncio
import clickhouse_connect
from services.api.app.config import settings
from services.api.app.domain.circuit_breaker.breaker import ch_circuit_breaker


class ClickHouseClient:
    def __init__(self):
        self._client = None

    def get_client(self):
        if not self._client:
            self._client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DB,
                connect_timeout=10,
                send_receive_timeout=30,
            )
        return self._client

    async def query(self, query_str: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Run query guarded by circuit breaker."""
        def _exec():
            client = self.get_client()
            return client.query(query_str, parameters=parameters)

        loop = asyncio.get_running_loop()
        return await ch_circuit_breaker.call(loop.run_in_executor, None, _exec)

    async def command(self, cmd_str: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Run command/mutation guarded by circuit breaker."""
        def _exec():
            client = self.get_client()
            return client.command(cmd_str, parameters=parameters)

        loop = asyncio.get_running_loop()
        return await ch_circuit_breaker.call(loop.run_in_executor, None, _exec)


clickhouse_client = ClickHouseClient()
