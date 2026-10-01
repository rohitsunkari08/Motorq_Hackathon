"""Differential Privacy Benchmark DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class SohBenchmarkResponse(BaseModel):
    model: str
    age_bucket: str
    sample_size: int
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    dp_mean_soh_pct: Optional[float] = None
    epsilon: float
    sensitivity: float
    k_anonymity_floor: int = 20
    budget_remaining: float
