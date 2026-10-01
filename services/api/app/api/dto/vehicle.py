"""Vehicle and Telemetry DTOs."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class VehicleDetailDto(BaseModel):
    vin: str
    fleet_id: int
    fleet_name: str
    tenant_id: int
    model_name: str
    oem_name: str
    model_year: int
    battery_kwh: float
    rated_range_km: float
    max_dc_kw: float
    latest_soc_pct: Optional[float] = None
    latest_soh_pct: Optional[float] = None
    latest_speed_kmh: Optional[float] = None
    latest_temp_c: Optional[float] = None
    is_charging: Optional[bool] = None
    charge_kw: Optional[float] = None
    latest_odo_km: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    geohash: Optional[str] = None
    location_masked: bool = False
    last_seen_ts: Optional[datetime] = None


class TelemetryPointDto(BaseModel):
    ts: datetime
    seq: int
    soc_pct: float
    speed_kmh: float
    batt_temp_c: float
    charging: int
    charge_kw: float
    odo_km: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    geohash7: str
    dtc: List[str] = Field(default_factory=list)
    evt: str = "NONE"
    location_masked: bool = False


class SohEstimateDto(BaseModel):
    est_at: str
    soh_pct: float
    model_version: str


class VehicleSohResponseDto(BaseModel):
    vin: str
    current_soh_pct: float
    baseline_linear_soh_pct: float
    ml_predicted_soh_pct: float
    model_version: str
    history: List[SohEstimateDto]
    similar_vehicles: List[Dict[str, Any]] = Field(default_factory=list)
