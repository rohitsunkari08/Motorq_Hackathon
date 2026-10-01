"""Alert DTOs."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AlertDto(BaseModel):
    alert_id: int
    vin: str
    type: str
    severity: int
    raised_at: datetime
    resolved_at: Optional[datetime] = None
    detail: Optional[Dict[str, Any]] = None


class AckAlertResponse(BaseModel):
    alert_id: int
    status: str = "resolved"
    resolved_at: datetime
