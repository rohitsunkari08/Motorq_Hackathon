"""Vehicle Repository
Handles vehicle details, specifications, and SoH records.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from services.api.app.infra.postgres import postgres_client


class VehicleRepo:
    async def get_vehicle_by_vin(
        self,
        vin: str,
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT 
                v.vin,
                v.fleet_id,
                f.name AS fleet_name,
                f.tenant_id,
                v.model_year,
                vm.name AS model_name,
                vm.battery_kwh,
                vm.rated_range_km,
                vm.max_dc_kw,
                o.name AS oem_name,
                se.soh_pct AS latest_soh_pct,
                v.erased_at
            FROM vehicle v
            JOIN fleet f ON v.fleet_id = f.fleet_id
            JOIN vehicle_model vm ON v.model_id = vm.model_id
            JOIN oem o ON vm.oem_id = o.oem_id
            LEFT JOIN LATERAL (
                SELECT soh_pct 
                FROM soh_estimate 
                WHERE vin = v.vin 
                ORDER BY est_at DESC 
                LIMIT 1
            ) se ON true
            WHERE v.vin = $1 AND v.erased_at IS NULL;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, vin)
            return dict(row) if row else None

    async def get_soh_history(
        self,
        vin: str,
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT est_at, soh_pct, model_version
            FROM soh_estimate
            WHERE vin = $1
            ORDER BY est_at ASC;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            rows = await conn.fetch(query, vin)
            return [
                {
                    "est_at": str(r["est_at"]),
                    "soh_pct": float(r["soh_pct"]),
                    "model_version": r["model_version"],
                }
                for r in rows
            ]

    async def get_soh_by_model_and_age(
        self,
        model_name: str,
        min_year: int,
        max_year: int,
    ) -> List[float]:
        """Fetch SoH distribution for Differential Privacy benchmarking."""
        query = """
            SELECT se.soh_pct
            FROM vehicle v
            JOIN vehicle_model vm ON v.model_id = vm.model_id
            JOIN LATERAL (
                SELECT soh_pct FROM soh_estimate WHERE vin = v.vin ORDER BY est_at DESC LIMIT 1
            ) se ON true
            WHERE vm.name ILIKE $1
              AND v.model_year >= $2
              AND v.model_year <= $3
              AND v.erased_at IS NULL;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            rows = await conn.fetch(query, f"%{model_name}%", min_year, max_year)
            return [float(r["soh_pct"]) for r in rows]


vehicle_repo = VehicleRepo()
