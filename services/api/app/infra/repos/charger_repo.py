"""Charger and Tariff Repository."""

from typing import List, Dict, Any, Optional
from services.api.app.infra.postgres import postgres_client


class ChargerRepo:
    async def get_all_chargers(self) -> List[Dict[str, Any]]:
        query = """
            SELECT charger_id, network, geohash7, lat, lon, power_kw
            FROM charger
            ORDER BY charger_id ASC;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]

    async def get_charger_by_id(self, charger_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT charger_id, network, geohash7, lat, lon, power_kw
            FROM charger
            WHERE charger_id = $1;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            row = await conn.fetchrow(query, charger_id)
            return dict(row) if row else None

    async def get_tariff_slots(self, tariff_id: int = 1) -> List[Dict[str, Any]]:
        query = """
            SELECT hour_start, hour_end, price_per_kwh
            FROM tariff_slot
            WHERE tariff_id = $1
            ORDER BY hour_start ASC;
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            rows = await conn.fetch(query, tariff_id)
            return [dict(r) for r in rows]


charger_repo = ChargerRepo()
