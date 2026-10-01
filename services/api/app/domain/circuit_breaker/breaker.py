"""Circuit Breaker Pattern for Downstream Stores (ClickHouse)
Protects the API from cascading failures when ClickHouse or other external sinks are degraded.
States: CLOSED, OPEN, HALF_OPEN
"""

import time
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
from services.api.app.api.dto.problem import CircuitBreakerOpenException


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(
        self,
        name: str = "clickhouse",
        failure_threshold: int = 5,
        recovery_timeout: float = 10.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        self._trips_total = 0
        self._lock = asyncio.Lock()

    @property
    def trips_total(self) -> int:
        return self._trips_total

    async def can_execute(self) -> bool:
        async with self._lock:
            now = time.time()
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if now - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.last_state_change = now
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True
            return False

    async def record_success(self):
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = time.time()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    async def record_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.OPEN
                    self._trips_total += 1
                    self.last_state_change = time.time()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function guarded by circuit breaker."""
        if not await self.can_execute():
            raise CircuitBreakerOpenException(
                detail=f"Circuit breaker '{self.name}' is OPEN. Downstream store unavailable."
            )
        try:
            import inspect
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
            await self.record_success()
            return result
        except Exception as exc:
            await self.record_failure()
            raise exc


# Singleton instance for ClickHouse
ch_circuit_breaker = CircuitBreaker(name="clickhouse", failure_threshold=5, recovery_timeout=10.0)
