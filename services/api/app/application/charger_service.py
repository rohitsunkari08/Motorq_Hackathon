"""Charger Application Service
Integrates with domain spatial index to rank nearest reachable chargers.
"""

from typing import List, Dict, Any, Optional
from services.api.app.infra.repos.charger_repo import charger_repo
from services.api.app.infra.repos.vehicle_repo import vehicle_repo
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.infra.redis import redis_client
from services.api.app.domain.charger.index import ChargerSpatialIndex
from services.api.app.api.dto.problem import NotFoundException
from services.api.app.api.dto.charger import NearestChargerResponse, RankedChargerDto


class ChargerService:
    def __init__(self):
        self._spatial_index: Optional[ChargerSpatialIndex] = None

    async def get_spatial_index(self) -> ChargerSpatialIndex:
        if not self._spatial_index:
            chargers = await charger_repo.get_all_chargers()
            self._spatial_index = ChargerSpatialIndex(chargers)
        return self._spatial_index

    async def find_nearest_chargers(
        self,
        vin: str,
        tenant_id: int,
        user_role: str,
        actor: str,
        override_lat: Optional[float] = None,
        override_lon: Optional[float] = None,
        limit: int = 5,
    ) -> NearestChargerResponse:
        bypass_rls = (user_role == "admin")
        v = await vehicle_repo.get_vehicle_by_vin(vin, tenant_id, bypass_rls=bypass_rls)
        if not v:
            raise NotFoundException(detail=f"Vehicle {vin} not found")

        # Fetch latest position and SoC from Redis
        latest = await redis_client.get_vehicle_latest_state(vin)
        lat = override_lat or (float(latest["lat"]) if "lat" in latest else 52.520)
        lon = override_lon or (float(latest["lon"]) if "lon" in latest else 13.405)
        current_soc = float(latest["soc_pct"]) if "soc_pct" in latest else 25.0

        battery_kwh = float(v["battery_kwh"])
        rated_range = float(v["rated_range_km"])

        spatial_idx = await self.get_spatial_index()
        candidates = spatial_idx.find_nearest_reachable(
            lat=lat,
            lon=lon,
            soc_pct=current_soc,
            battery_capacity_kwh=battery_kwh,
            soh=0.95,
            max_results=limit,
        )

        dtos = [
            RankedChargerDto(
                charger_id=c.charger_id,
                network=c.network,
                geohash7=c.geohash7,
                lat=c.lat,
                lon=c.lon,
                power_kw=c.power_kw,
                air_distance_km=round(c.air_distance_km, 2),
                road_distance_km=round(c.road_distance_km, 2),
                energy_needed_kwh=round(c.energy_needed_kwh, 2),
                usable_range_km=round(c.usable_range_km, 2),
                reachable=c.reachable,
            )
            for c in candidates
        ]

        usable_range_km = (current_soc / 100.0) * rated_range * 0.90

        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="find_nearest_chargers",
            resource=f"vin:{vin}",
            detail={"candidates_count": len(dtos), "reachable_count": sum(1 for c in dtos if c.reachable)},
        )

        return NearestChargerResponse(
            vin=vin,
            current_soc_pct=current_soc,
            battery_kwh=battery_kwh,
            usable_range_km=round(usable_range_km, 2),
            candidates=dtos,
        )


charger_service = ChargerService()
