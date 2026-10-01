"""Fleet Repository
Handles fleet queries, keyset pagination per NOTE.md §14 Q1, and fleet KPIs.
"""

from typing import Optional, List, Dict, Any, Tuple
from services.api.app.infra.postgres import postgres_client


class FleetRepo:
    async def get_fleet_by_id(self, fleet_id: int, tenant_id: int, bypass_rls: bool = False) -> Optional[Dict[str, Any]]:
        if bypass_rls:
            query = """
                SELECT fleet_id, tenant_id, name
                FROM fleet
                WHERE fleet_id = $1;
            """
            params = [fleet_id]
        else:
            query = """
                SELECT fleet_id, tenant_id, name
                FROM fleet
                WHERE fleet_id = $1 AND tenant_id = $2;
            """
            params = [fleet_id, tenant_id]

        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None

    async def get_fleet_vehicles_keyset(
        self,
        fleet_id: int,
        tenant_id: int,
        cursor_vin: Optional[str] = None,
        limit: int = 50,
        bypass_rls: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
        """Q1 Optimised: Keyset pagination + single join without ORM N+1.
        Uses index vehicle(fleet_id, vin).
        """
        limit = min(max(1, limit), 200)
        fetch_limit = limit + 1

        query = """
            SELECT 
                v.vin,
                v.fleet_id,
                v.model_year,
                vm.name AS model_name,
                vm.battery_kwh,
                vm.rated_range_km,
                vm.max_dc_kw,
                se.soh_pct AS latest_soh_pct
            FROM vehicle v
            JOIN vehicle_model vm ON v.model_id = vm.model_id
            LEFT JOIN LATERAL (
                SELECT soh_pct 
                FROM soh_estimate 
                WHERE vin = v.vin 
                ORDER BY est_at DESC 
                LIMIT 1
            ) se ON true
            WHERE v.fleet_id = $1
              AND ($2::text IS NULL OR v.vin > $2)
              AND v.erased_at IS NULL
            ORDER BY v.vin ASC
            LIMIT $3;
        """

        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            rows = await conn.fetch(query, fleet_id, cursor_vin, fetch_limit)
            items = [dict(r) for r in rows]

            has_more = len(items) > limit
            if has_more:
                items = items[:limit]
                next_cursor = items[-1]["vin"]
            else:
                next_cursor = None

            return items, next_cursor, has_more

    async def get_fleet_stats(self, fleet_id: int, tenant_id: int, bypass_rls: bool = False) -> Dict[str, Any]:
        """Aggregate fleet metrics from Postgres."""
        query = """
            SELECT 
                count(v.vin) AS total_vehicles,
                COALESCE(avg(se.soh_pct), 96.5) AS avg_soh_pct
            FROM vehicle v
            LEFT JOIN LATERAL (
                SELECT soh_pct FROM soh_estimate WHERE vin = v.vin ORDER BY est_at DESC LIMIT 1
            ) se ON true
            WHERE v.fleet_id = $1 AND v.erased_at IS NULL;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, fleet_id)
            return dict(row) if row else {"total_vehicles": 0, "avg_soh_pct": 100.0}


fleet_repo = FleetRepo()
