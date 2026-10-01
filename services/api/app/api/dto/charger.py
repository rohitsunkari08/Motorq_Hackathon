"""Charger DTOs."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChargerDto(BaseModel):
    charger_id: int
    network: str
    geohash7: str
    lat: float
    lon: float
    power_kw: float


class RankedChargerDto(BaseModel):
    charger_id: int
    network: str
    geohash7: str
    lat: float
    lon: float
    power_kw: float
    air_distance_km: float
    road_distance_km: float
    energy_needed_kwh: float
    usable_range_km: float
    reachable: bool


class NearestChargerResponse(BaseModel):
    vin: str
    current_soc_pct: float
    battery_kwh: float
    usable_range_km: float
    candidates: List[RankedChargerDto]
