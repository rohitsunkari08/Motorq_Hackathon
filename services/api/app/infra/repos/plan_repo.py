"""Charge Plan Repository."""

from typing import Optional, Dict, Any
from datetime import datetime
from services.api.app.infra.postgres import postgres_client


class PlanRepo:
    async def create_plan(
        self,
        vin: str,
        charger_id: int,
        start_ts: datetime,
        end_ts: datetime,
        target_soc: float,
        est_cost: float,
        baseline_cost: float,
        proposed_by: str,
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> Dict[str, Any]:
        query = """
            INSERT INTO charge_plan (
                vin, charger_id, start_ts, end_ts, target_soc, 
                est_cost, baseline_cost, status, proposed_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'proposed', $8)
            RETURNING plan_id, vin, charger_id, start_ts, end_ts, target_soc, est_cost, baseline_cost, status, proposed_by;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(
                query,
                vin,
                charger_id,
                start_ts,
                end_ts,
                target_soc,
                est_cost,
                baseline_cost,
                proposed_by,
            )
            return dict(row)

    async def get_plan_by_id(
        self,
        plan_id: int,
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT plan_id, vin, charger_id, start_ts, end_ts, target_soc, 
                   est_cost, baseline_cost, status, proposed_by, approved_by
            FROM charge_plan
            WHERE plan_id = $1;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, plan_id)
            return dict(row) if row else None

    async def update_plan_status(
        self,
        plan_id: int,
        status: str,
        approved_by: Optional[int],
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> Optional[Dict[str, Any]]:
        query = """
            UPDATE charge_plan
            SET status = $1, approved_by = $2
            WHERE plan_id = $3
            RETURNING plan_id, vin, charger_id, status, approved_by;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, status, approved_by, plan_id)
            return dict(row) if row else None


plan_repo = PlanRepo()
