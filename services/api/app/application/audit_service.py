"""Audit Application Service
Enables compliance auditing per NOTE.md §6.3 / §7.
"""

from typing import Optional, List, Dict, Any
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.api.dto.problem import ForbiddenException
from services.api.app.api.dto.audit import AuditLogEntryDto
from services.api.app.api.dto.pagination import PaginatedResponse


class AuditService:
    async def get_audit_trail(
        self,
        user_role: str,
        cursor: Optional[int] = None,
        limit: int = 50,
    ) -> PaginatedResponse[AuditLogEntryDto]:
        if user_role != "admin":
            raise ForbiddenException(detail="Audit trail access is restricted to administrators")

        raw_items, next_cursor, has_more = await audit_repo.get_audit_logs(cursor=cursor, limit=limit)

        dtos = [
            AuditLogEntryDto(
                audit_id=it["audit_id"],
                ts=it["ts"],
                actor=it["actor"],
                actor_type=it["actor_type"],
                action=it["action"],
                resource=it["resource"],
                detail=it["detail"],
            )
            for it in raw_items
        ]

        return PaginatedResponse[AuditLogEntryDto](
            items=dtos,
            next_cursor=str(next_cursor) if next_cursor else None,
            has_more=has_more,
        )


audit_service = AuditService()
