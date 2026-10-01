"""Charge Plan DTOs."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProposePlanRequest(BaseModel):
    charger_id: int
    target_soc: float = Field(..., ge=10.0, le=100.0, example=80.0)
    departure_hours_ahead: float = Field(default=8.0, ge=1.0, le=24.0, example=8.0)
    current_soc: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Optional override; reads latest if omitted")


class SlotActionDto(BaseModel):
    slot_index: int
    slot_start: datetime
    tariff_price_per_kwh: float
    action_power_kw: float
    soc_start: float
    soc_end: float
    cost_usd: float
    degradation_penalty_usd: float


class ChargePlanDto(BaseModel):
    plan_id: int
    vin: str
    charger_id: int
    start_ts: datetime
    end_ts: datetime
    target_soc: float
    est_cost: float
    baseline_cost: float
    savings_pct: float
    stress_reduction_pct: float
    status: str  # proposed, approved, rejected
    proposed_by: str
    approved_by: Optional[int] = None
    schedule: Optional[List[SlotActionDto]] = None


class ApproveRejectResponse(BaseModel):
    plan_id: int
    status: str
    action: str
    actor_id: int
    timestamp: datetime
