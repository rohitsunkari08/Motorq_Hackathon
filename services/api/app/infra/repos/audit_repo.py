"""Audit Log Repository
Records and retrieves immutable audit trail entries per NOTE.md §6.3 / §7.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json
from services.api.app.infra.postgres import postgres_client


class AuditRepo:
    async def log_event(
        self,
        actor: str,
        actor_type: str,
        action: str,
        resource: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        """Append-only audit logging."""
        query = """
            INSERT INTO audit_log (actor, actor_type, action, resource, detail)
            VALUES ($1, $2, $3, $4, $5);
        """
        async with postgres_client.tenant_session(bypass_rls=True) as conn:
            await conn.execute(query, actor, actor_type, action, resource, json.dumps(detail or {}))

    async def get_audit_logs(
        self,
        cursor: Optional[int] = None,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[int], bool]:
        """Fetch audit log entries with keyset pagination by audit_id."""
        limit = min(max(1, limit), 200)
        fetch_limit = limit + 1

        if cursor:
            query = """
                SELECT audit_id, ts, actor, actor_type, action, resource, detail
                FROM audit_log
                WHERE audit_id < $1
                ORDER BY audit_id DESC
                LIMIT $2;
            """
            params = [cursor, fetch_limit]
        else:
            query = """
                SELECT audit_id, ts, actor, actor_type, action, resource, detail
                FROM audit_log
                ORDER BY audit_id DESC
                LIMIT $1;
            """
            params = [fetch_limit]

        async with postgres_client.tenant_session(bypass_rls=True) as conn:
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
                next_cursor = items[-1]["audit_id"]
            else:
                next_cursor = None

            return items, next_cursor, has_more


audit_repo = AuditRepo()
