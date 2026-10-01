"""Fleet DTOs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FleetDto(BaseModel):
    fleet_id: int
    tenant_id: int
    name: str


class VehicleListItemDto(BaseModel):
    vin: str
    fleet_id: int
    model_name: str
    model_year: int
    battery_kwh: float
    rated_range_km: float
    max_dc_kw: float
    latest_soh_pct: Optional[float] = None
    latest_soc_pct: Optional[float] = None
    is_charging: Optional[bool] = None


class FleetSummaryDto(BaseModel):
    fleet_id: int
    fleet_name: str
    total_vehicles: int
    active_vehicles_24h: int
    avg_soc_pct: float
    fleet_avg_soh_pct: float
    total_energy_kwh_30d: float
    cost_saved_usd_est: float
    open_alerts_count: int


class GeohashCellDto(BaseModel):
    geohash: str
    vehicle_count: int
    avg_soc: float
    center_lat: float
    center_lon: float


class VehicleMarkerDto(BaseModel):
    vin: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    geohash5: str
    soc_pct: float
    charging: bool
    location_masked: bool


class FleetMapDto(BaseModel):
    fleet_id: int
    role: str
    cells: List[GeohashCellDto]
    vehicles: List[VehicleMarkerDto] = Field(default_factory=list, description="Individual vehicles (masked if viewer)")
