"""Nearest Reachable Charger Spatial Index
Implements NOTE.md §6.4:
- geohash prefix index (precision 5, expand to 8 neighbours)
- candidates -> haversine x road factor 1.3
- filter by energy <= usable range x (1 - 10% reserve)
- rank by distance & power
- Complexity: O(k log k), k = local candidates
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import pygeohash as pgh


ROAD_FACTOR = 1.3
SAFETY_RESERVE = 0.10  # 10% range reserve


@dataclass
class ChargerCandidate:
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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_geohash5_neighbors(gh5: str) -> List[str]:
    """Expands a 5-char geohash to include itself plus its 8 surrounding neighbors."""
    neighbors = [gh5]
    directions = ["top", "bottom", "right", "left"]
    try:
        # Cardinal
        top = pgh.get_adjacent(gh5, "top")
        bottom = pgh.get_adjacent(gh5, "bottom")
        right = pgh.get_adjacent(gh5, "right")
        left = pgh.get_adjacent(gh5, "left")
        neighbors.extend([top, bottom, right, left])
        # Diagonal
        neighbors.append(pgh.get_adjacent(top, "right"))
        neighbors.append(pgh.get_adjacent(top, "left"))
        neighbors.append(pgh.get_adjacent(bottom, "right"))
        neighbors.append(pgh.get_adjacent(bottom, "left"))
    except Exception:
        # Fallback if border exception
        pass
    return list(set(neighbors))


class ChargerSpatialIndex:
    def __init__(self, chargers: Optional[List[Dict]] = None):
        self.chargers_by_prefix5: Dict[str, List[Dict]] = {}
        self.chargers_by_prefix4: Dict[str, List[Dict]] = {}
        self.all_chargers: List[Dict] = []
        if chargers:
            self.load_chargers(chargers)

    def load_chargers(self, chargers: List[Dict]):
        self.all_chargers = chargers
        self.chargers_by_prefix5.clear()
        self.chargers_by_prefix4.clear()

        for c in chargers:
            gh = c.get("geohash7", "")
            if not gh and "lat" in c and "lon" in c:
                gh = pgh.encode(c["lat"], c["lon"], precision=7)
                c["geohash7"] = gh

            if len(gh) >= 5:
                p5 = gh[:5]
                self.chargers_by_prefix5.setdefault(p5, []).append(c)
            if len(gh) >= 4:
                p4 = gh[:4]
                self.chargers_by_prefix4.setdefault(p4, []).append(c)

    def find_nearest_reachable(
        self,
        lat: float,
        lon: float,
        soc_pct: float,
        battery_capacity_kwh: float,
        soh: float = 0.95,
        eff_kwh_per_km: float = 0.18,
        max_results: int = 10,
    ) -> List[ChargerCandidate]:
        """Finds and ranks reachable chargers within current range using geohash prefix index."""
        # Calculate remaining usable range
        effective_capacity = max(1.0, battery_capacity_kwh * soh)
        current_kwh = (max(0.0, soc_pct) / 100.0) * effective_capacity
        eff = max(0.05, eff_kwh_per_km)
        usable_range_km = current_kwh / eff
        # Apply 10% reserve budget
        max_safe_road_km = usable_range_km * (1.0 - SAFETY_RESERVE)

        # 1. Geohash prefix lookup
        v_gh5 = pgh.encode(lat, lon, precision=5)
        search_prefixes = get_geohash5_neighbors(v_gh5)

        candidates_pool = []
        seen_ids = set()
        for p in search_prefixes:
            for ch in self.chargers_by_prefix5.get(p, []):
                cid = ch["charger_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates_pool.append(ch)

        # Fallback to precision 4 if local density is sparse (< 5 chargers)
        if len(candidates_pool) < 5:
            v_gh4 = v_gh5[:4]
            for ch in self.chargers_by_prefix4.get(v_gh4, []):
                cid = ch["charger_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates_pool.append(ch)

        # If still sparse, consider all chargers
        if len(candidates_pool) < 3:
            for ch in self.all_chargers:
                cid = ch["charger_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates_pool.append(ch)

        # 2. Distance and Reachability calculation
        results: List[ChargerCandidate] = []
        for ch in candidates_pool:
            air_dist = haversine_km(lat, lon, ch["lat"], ch["lon"])
            road_dist = air_dist * ROAD_FACTOR
            energy_needed = road_dist * eff
            reachable = road_dist <= max_safe_road_km

            cand = ChargerCandidate(
                charger_id=ch["charger_id"],
                network=ch.get("network", "Unknown"),
                geohash7=ch.get("geohash7", ""),
                lat=ch["lat"],
                lon=ch["lon"],
                power_kw=float(ch.get("power_kw", 50.0)),
                air_distance_km=round(air_dist, 2),
                road_distance_km=round(road_dist, 2),
                energy_needed_kwh=round(energy_needed, 2),
                usable_range_km=round(usable_range_km, 2),
                reachable=reachable,
            )
            results.append(cand)

        # 3. Rank: Reachable first, then lowest road distance, then highest power_kw
        results.sort(key=lambda c: (
            0 if c.reachable else 1,
            c.road_distance_km,
            -c.power_kw
        ))

        return results[:max_results]
