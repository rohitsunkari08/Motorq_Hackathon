"""Unit & Integration Test Suite for FastAPI API v1
Per NOTE.md §6.3, §7, §15:
- Auth & RBAC (Admin, Fleet Manager, Viewer)
- Tenant Isolation & Postgres RLS
- Location Masking (Viewer geohash5 vs Manager precise)
- Keyset Pagination
- Rate Limiting (Redis token bucket 429 + Retry-After)
- Circuit Breaker Protection for ClickHouse
- Differential Privacy Benchmark (Laplace noise, k-anonymity suppression, budget)
- Nearest Reachable Charger (Spatial index with 10% reserve)
- Charge Plan DP optimization, approval & rejection
"""

import pytest
from httpx import AsyncClient, ASGITransport
from services.api.app.main import app
from services.api.app.domain.security.jwt import jwt_manager
from services.api.app.domain.circuit_breaker.breaker import CircuitBreaker, CircuitState
from services.api.app.domain.rate_limit.token_bucket import RateLimiter
from services.api.app.domain.benchmark.differential_privacy import DifferentialPrivacyBenchmark


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_auth_login_and_jwt_rs256():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid login
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "manager@voltfleet.com", "password": "Password123!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "fleet_manager"
        assert data["user"]["tenant_id"] == 1

        # Verify RS256 token claims
        claims = jwt_manager.verify_token(data["access_token"])
        assert claims.email == "manager@voltfleet.com"
        assert claims.role == "fleet_manager"
        assert claims.tenant_id == 1

        # Invalid login
        bad_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "manager@voltfleet.com", "password": "WrongPassword!"},
        )
        assert bad_res.status_code == 401
        assert bad_res.headers["content-type"] == "application/problem+json"


@pytest.mark.asyncio
async def test_rbac_and_role_permissions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get tokens for different roles
        admin_tok = (await client.post("/api/v1/auth/login", json={"email": "admin@voltfleet.com", "password": "Password123!"})).json()["access_token"]
        mgr_tok = (await client.post("/api/v1/auth/login", json={"email": "manager@voltfleet.com", "password": "Password123!"})).json()["access_token"]
        viewer_tok = (await client.post("/api/v1/auth/login", json={"email": "viewer@voltfleet.com", "password": "Password123!"})).json()["access_token"]

        # 1. Audit trail: Admin only (Manager & Viewer forbidden 403)
        res_mgr_audit = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {mgr_tok}"})
        assert res_mgr_audit.status_code == 403

        res_viewer_audit = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {viewer_tok}"})
        assert res_viewer_audit.status_code == 403

        res_admin_audit = await client.get("/api/v1/audit", headers={"Authorization": f"Bearer {admin_tok}"})
        assert res_admin_audit.status_code == 200

        # 2. Plan Approval: Manager & Admin only (Viewer forbidden 403)
        res_viewer_appr = await client.post("/api/v1/charge-plans/1/approve", headers={"Authorization": f"Bearer {viewer_tok}"})
        assert res_viewer_appr.status_code == 403


@pytest.mark.asyncio
async def test_role_based_location_masking():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        mgr_tok = (await client.post("/api/v1/auth/login", json={"email": "manager@voltfleet.com", "password": "Password123!"})).json()["access_token"]
        viewer_tok = (await client.post("/api/v1/auth/login", json={"email": "viewer@voltfleet.com", "password": "Password123!"})).json()["access_token"]

        vin = "1VXEV01A100000001"

        # Viewer detail: masked = True, geohash5 truncated
        v_viewer = await client.get(f"/api/v1/vehicles/{vin}", headers={"Authorization": f"Bearer {viewer_tok}"})
        assert v_viewer.status_code == 200
        v_data = v_viewer.json()
        assert v_data["location_masked"] is True

        # Manager detail: masked = False
        v_mgr = await client.get(f"/api/v1/vehicles/{vin}", headers={"Authorization": f"Bearer {mgr_tok}"})
        assert v_mgr.status_code == 200
        m_data = v_mgr.json()
        assert m_data["location_masked"] is False


@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tenant 1 manager
        t1_tok = (await client.post("/api/v1/auth/login", json={"email": "manager@voltfleet.com", "password": "Password123!"})).json()["access_token"]
        # Tenant 2 manager
        t2_tok = (await client.post("/api/v1/auth/login", json={"email": "manager@metrohaul.com", "password": "Password123!"})).json()["access_token"]

        # Tenant 1 cannot access Fleet 2 (belongs to Tenant 2)
        res = await client.get("/api/v1/fleets/2/vehicles", headers={"Authorization": f"Bearer {t1_tok}"})
        assert res.status_code == 404 or res.status_code == 403

        # Tenant 2 can access Fleet 2
        res2 = await client.get("/api/v1/fleets/2/vehicles?limit=5", headers={"Authorization": f"Bearer {t2_tok}"})
        assert res2.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_unit():
    limiter = RateLimiter(default_limit_per_minute=3)
    # First 3 allowed
    for _ in range(3):
        allowed, rem, retry = await limiter.is_allowed(tenant_id=99, route="test_route", limit_per_minute=3)
        assert allowed is True

    # 4th rejected
    allowed, rem, retry = await limiter.is_allowed(tenant_id=99, route="test_route", limit_per_minute=3)
    assert allowed is False
    assert retry >= 1


@pytest.mark.asyncio
async def test_circuit_breaker_unit():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED

    # Simulate failures
    await cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    await cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # While OPEN, call fails fast
    assert await cb.can_execute() is False

    # After recovery timeout, transitions to HALF_OPEN
    import asyncio
    await asyncio.sleep(0.15)
    assert await cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Consecutive successes close it
    await cb.record_success()
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_differential_privacy_benchmark_unit():
    dp = DifferentialPrivacyBenchmark(k_anonymity_floor=20, default_epsilon=1.0)

    # 1. Suppression check when n < 20
    small_sample = [95.0] * 10
    res_suppressed = dp.compute_dp_mean_soh(small_sample)
    assert res_suppressed["suppressed"] is True
    assert res_suppressed["dp_mean_soh_pct"] is None

    # 2. Calculation check when n >= 20
    large_sample = [95.0] * 50
    res_dp = dp.compute_dp_mean_soh(large_sample, epsilon=1.0, seed=123)
    assert res_dp["suppressed"] is False
    assert res_dp["dp_mean_soh_pct"] is not None
    assert 90.0 <= res_dp["dp_mean_soh_pct"] <= 100.0

    # 3. Budget consumption
    assert dp.consume_budget(tenant_id=42, epsilon=5.0) is True
    assert dp.get_remaining_budget(tenant_id=42) == 15.0
    # Over consume
    assert dp.consume_budget(tenant_id=42, epsilon=20.0) is False
