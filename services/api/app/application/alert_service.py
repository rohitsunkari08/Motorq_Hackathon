"""Alert Application Service
Handles alert querying with keyset pagination, resolution, and Server-Sent Events (SSE).
"""

from typing import Optional, List, Dict, Any, AsyncGenerator
import asyncio
import json
from datetime import datetime
from services.api.app.infra.repos.alert_repo import alert_repo
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.infra.redis import redis_client
from services.api.app.api.dto.problem import NotFoundException
from services.api.app.api.dto.alert import AlertDto, AckAlertResponse
from services.api.app.api.dto.pagination import PaginatedResponse


class AlertService:
    async def get_alerts(
        self,
        tenant_id: int,
        status: str,
        user_role: str,
        actor: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse[AlertDto]:
        bypass_rls = (user_role == "admin")
        raw_items, next_cursor, has_more = await alert_repo.get_alerts_keyset(
            tenant_id=tenant_id,
            status=status,
            cursor=cursor,
            limit=limit,
            bypass_rls=bypass_rls,
        )

        dtos = [
            AlertDto(
                alert_id=it["alert_id"],
                vin=it["vin"],
                type=it["type"],
                severity=it["severity"],
                raised_at=it["raised_at"],
                resolved_at=it["resolved_at"],
                detail=it["detail"],
            )
            for it in raw_items
        ]

        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="list_alerts",
            resource="alerts",
            detail={"status": status, "count": len(dtos)},
        )

        return PaginatedResponse[AlertDto](
            items=dtos,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def acknowledge_alert(
        self,
        alert_id: int,
        tenant_id: int,
        user_role: str,
        actor: str,
    ) -> AckAlertResponse:
        bypass_rls = (user_role == "admin")
        res = await alert_repo.acknowledge_alert(alert_id, tenant_id, bypass_rls=bypass_rls)
        if not res:
            raise NotFoundException(detail=f"Alert {alert_id} not found or already resolved")

        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="ack_alert",
            resource=f"alert:{alert_id}",
            detail={"resolved_at": res["resolved_at"].isoformat()},
        )

        return AckAlertResponse(
            alert_id=res["alert_id"],
            status="resolved",
            resolved_at=res["resolved_at"],
        )

    async def stream_alerts(self, tenant_id: int) -> AsyncGenerator[str, None]:
        """Server-Sent Events generator streaming live alerts."""
        yield f": connected to alerts stream for tenant {tenant_id}\n\n"

        pubsub = None
        if redis_client.redis:
            try:
                pubsub = redis_client.redis.pubsub()
                await pubsub.subscribe("alerts.stream")
            except Exception:
                pubsub = None

        try:
            while True:
                message_sent = False
                if pubsub:
                    try:
                        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if msg and msg.get("type") == "message":
                            data = msg.get("data")
                            yield f"event: alert\ndata: {data}\n\n"
                            message_sent = True
                    except Exception:
                        pass

                if not message_sent:
                    # Heartbeat comment to keep connection alive
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(5.0)
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe("alerts.stream")
                    await pubsub.close()
                except Exception:
                    pass


alert_service = AlertService()
