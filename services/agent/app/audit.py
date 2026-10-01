"""Audit Logging for Agent Service.

Per NOTE.md §6.6:
- Every tool call by the agent writes to audit_log with actor_type='agent'
- Detail captures prompt hash, execution latency, and token count.
"""

import json
from typing import Dict, Any, Optional
import asyncpg

from services.agent.app.config import settings


async def log_agent_audit(
    actor: str,
    action: str,
    resource: str,
    prompt_hash: str,
    latency_ms: float,
    token_count: int,
    tool_args: Optional[Dict[str, Any]] = None,
    status: str = "success",
    extra: Optional[Dict[str, Any]] = None,
):
    """Write an immutable audit log entry into PostgreSQL with actor_type='agent'."""
    detail = {
        "prompt_hash": prompt_hash,
        "latency_ms": round(latency_ms, 2),
        "token_count": token_count,
        "status": status,
        "tool_args": tool_args or {},
    }
    if extra:
        detail.update(extra)

    try:
        conn = await asyncpg.connect(settings.POSTGRES_URL, timeout=1.5)
        try:
            # Bypass RLS to append to the system audit_log
            await conn.execute("SET LOCAL app.bypass_rls = 'on';")
            await conn.execute(
                """
                INSERT INTO audit_log (actor, actor_type, action, resource, detail)
                VALUES ($1, 'agent', $2, $3, $4::jsonb);
                """,
                actor,
                action,
                resource,
                json.dumps(detail),
            )
        finally:
            await conn.close()
    except Exception as e:
        # Non-fatal to keep agent responsive if DB is temporarily disconnected
        print(f"Warning: Failed to write agent audit log: {e}")
