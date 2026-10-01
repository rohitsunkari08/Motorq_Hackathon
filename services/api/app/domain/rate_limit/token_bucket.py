"""Redis-backed Token Bucket Rate Limiter
Per NOTE.md §6.3:
Rate limit Redis token bucket (per tenant+route, 429 + Retry-After).
Key format: rl:{tenant}:{route}:{minute}
"""

import time
import math
from typing import Tuple, Optional
import redis.asyncio as aioredis


class RateLimiter:
    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        default_limit_per_minute: int = 120,
    ):
        self.redis = redis_client
        self.default_limit = default_limit_per_minute
        # Fallback local in-memory storage for test/offline environments
        self._local_buckets = {}

    def set_redis(self, client: aioredis.Redis):
        self.redis = client

    async def is_allowed(
        self,
        tenant_id: int,
        route: str,
        limit_per_minute: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """Check if request is allowed under token bucket / window limit.
        Returns:
            (allowed: bool, remaining_tokens: int, retry_after_seconds: int)
        """
        limit = limit_per_minute or self.default_limit
        current_ts = int(time.time())
        current_minute = current_ts // 60
        window_expiry = 65  # seconds
        seconds_left_in_minute = 60 - (current_ts % 60)

        # Normalize route name to avoid unbounded keys
        safe_route = route.strip("/").replace("/", "_") or "root"
        key = f"rl:{tenant_id}:{safe_route}:{current_minute}"

        if self.redis:
            try:
                # Use Redis INCR and EXPIRE pipeline
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, window_expiry)
                results = await pipe.execute()
                current_count = results[0]

                if current_count <= limit:
                    remaining = max(0, limit - current_count)
                    return True, remaining, 0
                else:
                    return False, 0, max(1, seconds_left_in_minute)
            except Exception:
                # Graceful fallback to local in-memory
                pass

        # In-memory fallback
        bucket_key = (tenant_id, safe_route, current_minute)
        count = self._local_buckets.get(bucket_key, 0) + 1
        self._local_buckets[bucket_key] = count

        # Clean old minutes
        old_keys = [k for k in self._local_buckets if k[2] < current_minute - 2]
        for ok in old_keys:
            self._local_buckets.pop(ok, None)

        if count <= limit:
            return True, max(0, limit - count), 0
        else:
            return False, 0, max(1, seconds_left_in_minute)


rate_limiter = RateLimiter()
