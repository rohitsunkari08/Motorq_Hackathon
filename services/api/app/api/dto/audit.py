"""Audit Log DTOs."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AuditLogEntryDto(BaseModel):
    audit_id: int
    ts: datetime
    actor: str
    actor_type: str
    action: str
    resource: str
    detail: Optional[Dict[str, Any]] = None
