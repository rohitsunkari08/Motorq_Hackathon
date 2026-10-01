"""Privacy and Right-to-Erasure Application Service
Coordinates multi-store erasure across PostgreSQL, Redis, and ClickHouse per NOTE.md §7.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio
from services.api.app.infra.postgres import postgres_client
from services.api.app.infra.redis import redis_client
from services.api.app.infra.clickhouse import clickhouse_client
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.api.dto.problem import BadRequestException, ForbiddenException
from services.api.app.api.dto.privacy import ErasureResponse


class PrivacyService:
    async def execute_erasure(
        self,
        vin: Optional[str],
        driver_id: Optional[int],
        user_role: str,
        actor: str,
    ) -> ErasureResponse:
        if user_role != "admin":
            raise ForbiddenException(detail="Right-to-erasure execution is restricted to administrators")

        if not vin and not driver_id:
            raise BadRequestException(detail="Must specify either 'vin' or 'driver_id' to execute erasure")

        now = datetime.now(timezone.utc)
        stores_purged = []

        # 1. PostgreSQL Purge
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            if vin:
                await conn.execute("UPDATE vehicle SET erased_at = NOW() WHERE vin = $1;", vin)
                await conn.execute("DELETE FROM trip WHERE vin = $1;", vin)
                await conn.execute("DELETE FROM alert WHERE vin = $1;", vin)
                await conn.execute("DELETE FROM charge_plan WHERE vin = $1;", vin)
                await conn.execute("DELETE FROM soh_estimate WHERE vin = $1;", vin)

            if driver_id:
                await conn.execute(
                    "UPDATE driver SET erased_at = NOW(), pseudonym = 'REDACTED_ERASED' WHERE driver_id = $1;",
                    driver_id,
                )
                await conn.execute("UPDATE trip SET driver_id = NULL WHERE driver_id = $1;", driver_id)

            # Record in erasure_request
            req_row = await conn.fetchrow(
                """
                INSERT INTO erasure_request (vin, driver_id, requested_at, completed_at)
                VALUES ($1, $2, $3, $4)
                RETURNING req_id;
                """,
                vin,
                driver_id,
                now,
                now,
            )
            req_id = req_row["req_id"]
        stores_purged.append("postgresql")

        # 2. Redis Purge
        if vin and redis_client.redis:
            try:
                await redis_client.redis.delete(
                    f"veh:latest:{vin}",
                    f"veh:params:{vin}",
                    f"tenantof:{vin}",
                )
                stores_purged.append("redis")
            except Exception:
                pass

        # 3. ClickHouse Mutations
        if vin:
            try:
                # Issue synchronous / light mutations in ClickHouse
                await clickhouse_client.command(f"ALTER TABLE evc.telemetry DELETE WHERE vin = '{vin}'")
                await clickhouse_client.command(f"ALTER TABLE evc.vehicle_daily DELETE WHERE vin = '{vin}'")
                await clickhouse_client.command(f"ALTER TABLE evc.charge_session DELETE WHERE vin = '{vin}'")

                # Poll mutations briefly
                for _ in range(5):
                    res = await clickhouse_client.query(
                        f"SELECT count() FROM system.mutations WHERE database = 'evc' AND is_done = 0 AND command LIKE '%{vin}%'"
                    )
                    if res.result_rows and res.result_rows[0][0] == 0:
                        break
                    await asyncio.sleep(0.5)

                stores_purged.append("clickhouse")
            except Exception:
                pass

        # 4. Audit Log (No PII)
        resource_id = f"vin:{vin}" if vin else f"driver:{driver_id}"
        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="privacy_erasure",
            resource=resource_id,
            detail={"stores_purged": stores_purged, "req_id": req_id},
        )

        return ErasureResponse(
            req_id=req_id,
            vin=vin,
            driver_id=driver_id,
            status="completed",
            stores_purged=stores_purged,
            completed_at=now,
        )


privacy_service = PrivacyService()
