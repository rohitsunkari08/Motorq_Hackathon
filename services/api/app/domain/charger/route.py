"""A* Multi-Stop EV Charging Route Planner
Implements NOTE.md §6.4:
- A* multi-stop route planner over charger graph
- Heuristic: haversine distance to destination
- Edge feasibility: energy required <= current battery range (with safety buffer)
- Objective: Minimize total trip time = drive time + charging time
"""

import heapq
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from .index import haversine_km, ROAD_FACTOR, SAFETY_RESERVE


@dataclass
class RouteStop:
    stop_type: str  # "ORIGIN", "CHARGER", "DESTINATION"
    name: str
    lat: float
    lon: float
    arrival_soc_pct: float
    departure_soc_pct: float
    charge_kw: float
    charge_duration_min: float
    leg_distance_km: float
    leg_drive_time_min: float


@dataclass
class RoutePlan:
    feasible: bool
    total_distance_km: float
    total_drive_time_min: float
    total_charge_time_min: float
    total_trip_time_min: float
    stops: List[RouteStop]
    reason: Optional[str] = None


def plan_charging_route(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    chargers: List[Dict],
    initial_soc_pct: float = 80.0,
    battery_capacity_kwh: float = 75.0,
    soh: float = 0.95,
    eff_kwh_per_km: float = 0.18,
    target_arrival_soc_pct: float = 20.0,
    charge_to_soc_pct: float = 80.0,
    avg_speed_kmh: float = 85.0,
) -> RoutePlan:
    """Plans an energy-feasible multi-stop route using A* search."""
    eff_cap = max(1.0, battery_capacity_kwh * soh)
    eff = max(0.05, eff_kwh_per_km)

    def soc_from_kwh(kwh: float) -> float:
        return (kwh / eff_cap) * 100.0

    def kwh_from_soc(soc: float) -> float:
        return (soc / 100.0) * eff_cap

    # Direct trip check
    direct_air = haversine_km(start_lat, start_lon, dest_lat, dest_lon)
    direct_road = direct_air * ROAD_FACTOR
    energy_needed = direct_road * eff
    current_energy = kwh_from_soc(initial_soc_pct)
    min_dest_energy = kwh_from_soc(target_arrival_soc_pct)

    if current_energy - energy_needed >= min_dest_energy:
        # Feasible directly with no charging stops
        drive_time = (direct_road / avg_speed_kmh) * 60.0
        final_soc = soc_from_kwh(current_energy - energy_needed)
        return RoutePlan(
            feasible=True,
            total_distance_km=round(direct_road, 1),
            total_drive_time_min=round(drive_time, 1),
            total_charge_time_min=0.0,
            total_trip_time_min=round(drive_time, 1),
            stops=[
                RouteStop("ORIGIN", "Origin", start_lat, start_lon, initial_soc_pct, initial_soc_pct, 0.0, 0.0, 0.0, 0.0),
                RouteStop("DESTINATION", "Destination", dest_lat, dest_lon, round(final_soc, 1), round(final_soc, 1), 0.0, 0.0, round(direct_road, 1), round(drive_time, 1))
            ]
        )

    # Graph nodes: 0 = origin, 1..N = chargers, N+1 = destination
    nodes = [{"id": 0, "name": "Origin", "lat": start_lat, "lon": start_lon, "power_kw": 0.0}]
    for idx, c in enumerate(chargers):
        nodes.append({
            "id": idx + 1,
            "name": c.get("network", f"Charger {c.get('charger_id', idx+1)}"),
            "lat": c["lat"],
            "lon": c["lon"],
            "power_kw": float(c.get("power_kw", 100.0))
        })
    dest_id = len(nodes)
    nodes.append({"id": dest_id, "name": "Destination", "lat": dest_lat, "lon": dest_lon, "power_kw": 0.0})

    # A* Priority Queue: (estimated_total_time, elapsed_time, current_node_id, current_soc, path)
    # Heuristic: direct road time to destination
    h_init = ((direct_road) / avg_speed_kmh) * 60.0
    pq = [(h_init, 0.0, 0, initial_soc_pct, [0])]
    visited = {}

    best_plan = None

    while pq:
        est_total, elapsed, curr_id, curr_soc, path = heapq.heappop(pq)
        curr_node = nodes[curr_id]

        if curr_id == dest_id:
            # Found destination!
            best_plan = (elapsed, path)
            break

        # Prune if visited with higher SoC and less time
        state_key = (curr_id, round(curr_soc / 10.0))
        if state_key in visited and visited[state_key] <= elapsed:
            continue
        visited[state_key] = elapsed

        # Explore neighbors
        for next_node in nodes:
            next_id = next_node["id"]
            if next_id in path:
                continue

            leg_dist = haversine_km(curr_node["lat"], curr_node["lon"], next_node["lat"], next_node["lon"]) * ROAD_FACTOR
            leg_energy = leg_dist * eff
            rem_energy = kwh_from_soc(curr_soc) - leg_energy
            reserve_energy = kwh_from_soc(10.0)  # 10% hard reserve

            if rem_energy < reserve_energy:
                continue  # Unreachable

            arrival_soc = soc_from_kwh(rem_energy)

            # If destination reached
            if next_id == dest_id:
                if arrival_soc >= target_arrival_soc_pct:
                    drive_time = (leg_dist / avg_speed_kmh) * 60.0
                    new_elapsed = elapsed + drive_time
                    heapq.heappush(pq, (new_elapsed, new_elapsed, dest_id, arrival_soc, path + [dest_id]))
                continue

            # If stopping at charger, charge from arrival_soc to charge_to_soc_pct
            charge_kw = next_node["power_kw"]
            needed_charge_kwh = max(0.0, kwh_from_soc(charge_to_soc_pct) - rem_energy)
            charge_duration_hr = needed_charge_kwh / max(10.0, charge_kw * 0.92)
            charge_duration_min = charge_duration_hr * 60.0

            drive_time = (leg_dist / avg_speed_kmh) * 60.0
            new_elapsed = elapsed + drive_time + charge_duration_min
            departure_soc = max(arrival_soc, charge_to_soc_pct)

            # Heuristic: road time from next_node to destination
            h_cost = (haversine_km(next_node["lat"], next_node["lon"], dest_lat, dest_lon) * ROAD_FACTOR / avg_speed_kmh) * 60.0
            heapq.heappush(pq, (new_elapsed + h_cost, new_elapsed, next_id, departure_soc, path + [next_id]))

    if not best_plan:
        return RoutePlan(
            feasible=False,
            total_distance_km=round(direct_road, 1),
            total_drive_time_min=0.0,
            total_charge_time_min=0.0,
            total_trip_time_min=0.0,
            stops=[],
            reason="Destination unreachable with available charger density."
        )

    # Reconstruct stops
    total_time, path_node_ids = best_plan
    stops = []
    tot_dist = 0.0
    tot_drive = 0.0
    tot_charge = 0.0

    cur_soc = initial_soc_pct
    for i in range(len(path_node_ids)):
        n = nodes[path_node_ids[i]]
        if i == 0:
            stops.append(RouteStop("ORIGIN", n["name"], n["lat"], n["lon"], cur_soc, cur_soc, 0.0, 0.0, 0.0, 0.0))
        else:
            prev = nodes[path_node_ids[i-1]]
            dist = haversine_km(prev["lat"], prev["lon"], n["lat"], n["lon"]) * ROAD_FACTOR
            drive = (dist / avg_speed_kmh) * 60.0
            rem_kwh = kwh_from_soc(cur_soc) - (dist * eff)
            arr_soc = soc_from_kwh(rem_kwh)

            if n["id"] == dest_id:
                stops.append(RouteStop("DESTINATION", n["name"], n["lat"], n["lon"], round(arr_soc, 1), round(arr_soc, 1), 0.0, 0.0, round(dist, 1), round(drive, 1)))
                tot_dist += dist
                tot_drive += drive
            else:
                dep_soc = charge_to_soc_pct
                charge_kwh = max(0.0, kwh_from_soc(dep_soc) - rem_kwh)
                chg_time = (charge_kwh / max(10.0, n["power_kw"] * 0.92)) * 60.0
                stops.append(RouteStop("CHARGER", n["name"], n["lat"], n["lon"], round(arr_soc, 1), round(dep_soc, 1), n["power_kw"], round(chg_time, 1), round(dist, 1), round(drive, 1)))
                tot_dist += dist
                tot_drive += drive
                tot_charge += chg_time
                cur_soc = dep_soc

    return RoutePlan(
        feasible=True,
        total_distance_km=round(tot_dist, 1),
        total_drive_time_min=round(tot_drive, 1),
        total_charge_time_min=round(tot_charge, 1),
        total_trip_time_min=round(tot_drive + tot_charge, 1),
        stops=stops
    )
