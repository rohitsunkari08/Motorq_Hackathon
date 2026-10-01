"""Privacy and Erasure DTOs."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ErasureRequest(BaseModel):
    vin: Optional[str] = Field(default=None, pattern=r"^[A-HJ-NPR-Z0-9]{17}$", description="17-char VIN to erase")
    driver_id: Optional[int] = Field(default=None, description="Driver ID to scrub")


class ErasureResponse(BaseModel):
    req_id: int
    vin: Optional[str] = None
    driver_id: Optional[int] = None
    status: str = "completed"
    stores_purged: List[str]
    completed_at: datetime
