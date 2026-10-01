"""Redis Client
Provides async access to Redis for latest vehicle state, tenant-of-vin lookups,
rate limiting token bucket, and alert pub/sub.
"""

from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from services.api.app.config import settings


class RedisClient:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def init(self):
        import asyncio
        current_loop = asyncio.get_running_loop()
        if self.redis:
            pool = getattr(self.redis, "connection_pool", None)
            if pool and getattr(pool, "_loop", None) == current_loop:
                return
            try:
                await self.redis.aclose()
            except Exception:
                pass
            self.redis = None

        self.redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
        )

    async def close(self):
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def get_tenant_of_vin(self, vin: str) -> Optional[int]:
        """Look up tenant_id for a given VIN from Redis cache `tenantof:{vin}`."""
        if not self.redis:
            await self.init()
        try:
            val = await self.redis.get(f"tenantof:{vin}")
            if val:
                return int(val)
        except Exception:
            pass
        return None

    async def get_vehicle_latest_state(self, vin: str) -> Dict[str, Any]:
        """Fetch latest telemetry snapshot from Redis hash `veh:latest:{vin}`."""
        if not self.redis:
            await self.init()
        try:
            data = await self.redis.hgetall(f"veh:latest:{vin}")
            return data or {}
        except Exception:
            return {}

    async def get_vehicle_params(self, vin: str) -> Dict[str, Any]:
        """Fetch vehicle specs from Redis hash `veh:params:{vin}`."""
        if not self.redis:
            await self.init()
        try:
            data = await self.redis.hgetall(f"veh:params:{vin}")
            return data or {}
        except Exception:
            return {}

    async def publish_alert(self, alert_json: str):
        """Publish alert to Redis channel `alerts.stream`."""
        if not self.redis:
            await self.init()
        try:
            await self.redis.publish("alerts.stream", alert_json)
        except Exception:
            pass


redis_client = RedisClient()
