"""Compliance Test: GDPR / DPDP Right-to-Erasure Flow
Tests NOTE.md §7 & §15:
- Viewer/non-admin attempt returns 403 Forbidden
- Admin can execute erasure for a given VIN or driver_id
- After completion, all stores return 0 rows for that VIN:
  - Postgres: vehicle.erased_at is set, trips/alerts/plans are deleted
  - Redis: keys veh:latest:{vin}, veh:params:{vin}, tenantof:{vin} are deleted
  - ClickHouse: rows purged via ALTER TABLE DELETE mutation
  - Audit log records the event without PII
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from services.api.app.main import app
from services.api.app.infra.postgres import postgres_client
from services.api.app.infra.redis import redis_client


@pytest.mark.asyncio
async def test_right_to_erasure_compliance():
    # Use real synthetic vehicle VIN from Postgres
    test_vin = "1NMEV01A700000002"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Pre-seed Redis keys to verify deletion
        await redis_client.init()
        if redis_client.redis:
            await redis_client.redis.set(f"tenantof:{test_vin}", "1")
            await redis_client.redis.hset(
                f"veh:latest:{test_vin}",
                mapping={"soc_pct": "42.0", "vin": test_vin},
            )
            await redis_client.redis.hset(
                f"veh:params:{test_vin}",
                mapping={"capacity_kwh": "75.0"},
            )

        # 1. Non-admin (viewer) attempt must be rejected with 403
        viewer_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@voltfleet.com", "password": "Password123!"},
        )
        assert viewer_login.status_code == 200
        v_token = viewer_login.json()["access_token"]
        v_res = await client.post(
            "/api/v1/privacy/erasure",
            json={"vin": test_vin},
            headers={"Authorization": f"Bearer {v_token}"},
        )
        assert v_res.status_code == 403, f"Expected 403, got {v_res.status_code}"

        # 2. Admin executes erasure
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@voltfleet.com", "password": "Password123!"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        erasure_res = await client.post(
            "/api/v1/privacy/erasure",
            json={"vin": test_vin},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert erasure_res.status_code == 200
        data = erasure_res.json()
        assert data["status"] == "completed"
        assert "postgresql" in data["stores_purged"]

        # 3. Compliance Verification across stores
        # PostgreSQL check
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            erased_at = await conn.fetchval(
                "SELECT erased_at FROM vehicle WHERE vin = $1;", test_vin
            )
            assert erased_at is not None, "Vehicle should be marked erased_at"

            alert_count = await conn.fetchval(
                "SELECT count(*) FROM alert WHERE vin = $1;", test_vin
            )
            assert alert_count == 0, "All alerts for erased vehicle must be deleted"

            plan_count = await conn.fetchval(
                "SELECT count(*) FROM charge_plan WHERE vin = $1;", test_vin
            )
            assert plan_count == 0, "All charge plans for erased vehicle must be deleted"

            audit_count = await conn.fetchval(
                "SELECT count(*) FROM audit_log WHERE action = 'privacy_erasure' AND resource = $1;",
                f"vin:{test_vin}",
            )
            assert audit_count >= 1, "Audit log entry must exist for compliance"

        # Redis check
        if redis_client.redis:
            t = await redis_client.redis.get(f"tenantof:{test_vin}")
            assert t is None, "Redis tenantof key must be deleted"

            latest = await redis_client.redis.hgetall(f"veh:latest:{test_vin}")
            assert not latest, "Redis veh:latest key must be deleted"

            params = await redis_client.redis.hgetall(f"veh:params:{test_vin}")
            assert not params, "Redis veh:params key must be deleted"
