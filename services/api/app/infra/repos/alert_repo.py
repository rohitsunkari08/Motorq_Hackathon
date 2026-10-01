"""Alert Repository
Handles alert retrieval with keyset pagination and partial index utilization (NOTE.md §14 Q2).
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json
from services.api.app.infra.postgres import postgres_client


class AlertRepo:
    async def get_alerts_keyset(
        self,
        tenant_id: int,
        status: str = "open",
        cursor: Optional[str] = None,
        limit: int = 50,
        bypass_rls: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
        """Q2 Optimised: Keyset pagination on alerts table using partial index.
        Cursor format: '<epoch_ms>_<alert_id>'
        """
        limit = min(max(1, limit), 200)
        fetch_limit = limit + 1

        cursor_ts: Optional[datetime] = None
        cursor_id: Optional[int] = None
        if cursor and "_" in cursor:
            try:
                ts_part, id_part = cursor.split("_", 1)
                cursor_ts = datetime.fromtimestamp(float(ts_part) / 1000.0)
                cursor_id = int(id_part)
            except Exception:
                pass

        where_clauses = []
        params = []
        idx = 1

        if status == "open":
            where_clauses.append("a.resolved_at IS NULL")
        elif status == "resolved":
            where_clauses.append("a.resolved_at IS NOT NULL")

        if cursor_ts and cursor_id:
            where_clauses.append(f"(a.raised_at, a.alert_id) < (${idx}, ${idx+1})")
            params.extend([cursor_ts, cursor_id])
            idx += 2

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        query = f"""
            SELECT 
                a.alert_id,
                a.vin,
                a.type,
                a.severity,
                a.raised_at,
                a.resolved_at,
                a.detail
            FROM alert a
            {where_sql}
            ORDER BY a.raised_at DESC, a.alert_id DESC
            LIMIT ${idx};
        """
        params.append(fetch_limit)

        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            rows = await conn.fetch(query, *params)
            items = []
            for r in rows:
                item = dict(r)
                if isinstance(item["detail"], str):
                    try:
                        item["detail"] = json.loads(item["detail"])
                    except Exception:
                        pass
                items.append(item)

            has_more = len(items) > limit
            if has_more:
                items = items[:limit]
                last = items[-1]
                ms = int(last["raised_at"].timestamp() * 1000)
                next_cursor = f"{ms}_{last['alert_id']}"
            else:
                next_cursor = None

            return items, next_cursor, has_more

    async def acknowledge_alert(
        self,
        alert_id: int,
        tenant_id: int,
        bypass_rls: bool = False,
    ) -> Optional[Dict[str, Any]]:
        query = """
            UPDATE alert
            SET resolved_at = NOW()
            WHERE alert_id = $1 AND resolved_at IS NULL
            RETURNING alert_id, vin, type, severity, raised_at, resolved_at;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            row = await conn.fetchrow(query, alert_id)
            return dict(row) if row else None

    async def count_open_alerts(self, tenant_id: int, bypass_rls: bool = False) -> int:
        query = """
            SELECT count(*)
            FROM alert
            WHERE resolved_at IS NULL;
        """
        async with postgres_client.tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as conn:
            val = await conn.fetchval(query)
            return int(val) if val else 0


alert_repo = AlertRepo()
