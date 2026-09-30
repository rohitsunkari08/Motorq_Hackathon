"""Phase 0 Acceptance Verification Test
Tests that all services, tables, RLS policies, and seed data match NOTE.md §5.4.
"""
import subprocess
import json
import pytest

def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert res.returncode == 0, f"Command failed: {cmd}\nStderr: {res.stderr}\nStdout: {res.stdout}"
    return res.stdout.strip()

def test_containers_running():
    out = run_cmd("docker compose ps --format json")
    # docker compose ps JSON output might be line-delimited or array
    lines = [line for line in out.splitlines() if line.strip()]
    containers = []
    for line in lines:
        try:
            containers.append(json.loads(line))
        except Exception:
            pass
    services = {c.get("Service"): c.get("State") for c in containers}
    assert services.get("clickhouse") == "running"
    assert services.get("postgres") == "running"
    assert services.get("redpanda") == "running"
    assert services.get("redis") == "running"
    assert services.get("prometheus") == "running"
    assert services.get("grafana") == "running"

def test_clickhouse_tables():
    out = run_cmd('docker compose exec -T clickhouse clickhouse-client --query "SHOW TABLES IN evc"')
    tables = set(out.splitlines())
    expected = {"telemetry", "telemetry_1m", "telemetry_1m_mv", "vehicle_daily", "charge_session"}
    assert expected.issubset(tables), f"Missing ClickHouse tables: {expected - tables}"

def test_clickhouse_column_ttl():
    out = run_cmd('docker compose exec -T clickhouse clickhouse-client --query "SHOW CREATE TABLE evc.telemetry"')
    assert "`lat` Float32 TTL toDateTime(ts) + toIntervalDay(30)" in out
    assert "`lon` Float32 TTL toDateTime(ts) + toIntervalDay(30)" in out
    assert "toIntervalDay(365)" in out

def test_postgres_tables():
    out = run_cmd('docker compose exec -T postgres psql -U evc -d evc -t -A -c "SELECT tablename FROM pg_tables WHERE schemaname=\'public\';"')
    tables = set(out.splitlines())
    expected = {
        "tenant", "subscription", "fleet", "oem", "vehicle_model", "vehicle",
        "driver", "trip", "charger", "tariff", "tariff_slot", "app_user",
        "alert", "charge_plan", "soh_estimate", "audit_log", "erasure_request",
        "doc_chunk"
    }
    assert expected.issubset(tables), f"Missing Postgres tables: {expected - tables}"

def test_postgres_rls_policies():
    out = run_cmd('docker compose exec -T postgres psql -U evc -d evc -t -A -c "SELECT tablename FROM pg_policies;"')
    policies = set(out.splitlines())
    expected = {"vehicle", "alert", "charge_plan", "trip"}
    assert expected.issubset(policies), f"Missing RLS policies for: {expected - policies}"

def test_postgres_seed_tenants_and_users():
    tenants_count = run_cmd('docker compose exec -T postgres psql -U evc -d evc -t -A -c "SELECT count(*) FROM tenant;"')
    assert int(tenants_count) == 3, f"Expected 3 tenants, got {tenants_count}"

    users_count = run_cmd('docker compose exec -T postgres psql -U evc -d evc -t -A -c "SELECT count(*) FROM app_user;"')
    assert int(users_count) == 9, f"Expected 9 users, got {users_count}"

    roles_per_tenant = run_cmd('''docker compose exec -T postgres psql -U evc -d evc -t -A -c "SELECT tenant_id, string_agg(role, ',' ORDER BY role) FROM app_user GROUP BY tenant_id ORDER BY tenant_id;"''')
    for line in roles_per_tenant.splitlines():
        tid, roles = line.split("|")
        assert roles == "admin,fleet_manager,viewer", f"Tenant {tid} missing roles: {roles}"

def test_redpanda_topics():
    out = run_cmd('docker compose exec -T redpanda rpk topic list')
    assert "telemetry.raw" in out
    assert "telemetry.canonical" in out
    assert "alerts" in out
    assert "telemetry.dlq" in out

if __name__ == "__main__":
    pytest.main(["-v", __file__])
