"""Unit Tests for Nearest Reachable Charger Index & A* Route Planning
Verifies NOTE.md §6.4:
- Geohash prefix index
- Haversine distance with 1.3 road factor
- Reachability filter with 10% reserve
- Ranking by distance and power
- A* multi-stop route planner
- Test coverage >= 80%
"""

import pytest
import pygeohash as pgh
from services.api.app.domain.charger.index import (
    ChargerSpatialIndex,
    ChargerCandidate,
    haversine_km,
    get_geohash5_neighbors,
)
from services.api.app.domain.charger.route import (
    plan_charging_route,
    RoutePlan,
    RouteStop,
)


@pytest.fixture
def sample_chargers():
    # Metro cluster in New York area (lat ~ 40.71, lon ~ -74.00)
    chargers = []
    chargers.append({
        "charger_id": 1,
        "network": "Electrify America",
        "lat": 40.7150,
        "lon": -74.0020,
        "power_kw": 150.0,
        "geohash7": pgh.encode(40.7150, -74.0020, precision=7)
    })
    chargers.append({
        "charger_id": 2,
        "network": "EVgo",
        "lat": 40.7200,
        "lon": -73.9950,
        "power_kw": 100.0,
        "geohash7": pgh.encode(40.7200, -73.9950, precision=7)
    })
    chargers.append({
        "charger_id": 3,
        "network": "ChargePoint L2",
        "lat": 40.7110,
        "lon": -74.0080,
        "power_kw": 11.0,
        "geohash7": pgh.encode(40.7110, -74.0080, precision=7)
    })
    chargers.append({
        "charger_id": 4,
        "network": "Distant Supercharger",
        "lat": 41.5000,
        "lon": -74.0000,  # ~88 km away
        "power_kw": 250.0,
        "geohash7": pgh.encode(41.5000, -74.0000, precision=7)
    })
    return chargers


def test_haversine_km():
    # NYC (40.7128, -74.0060) to Philadelphia (39.9526, -75.1652) is ~130 km
    d = haversine_km(40.7128, -74.0060, 39.9526, -75.1652)
    assert 120.0 < d < 140.0


def test_get_geohash5_neighbors():
    gh5 = "dr5re"
    neighbors = get_geohash5_neighbors(gh5)
    assert len(neighbors) == 9
    assert gh5 in neighbors


def test_find_nearest_reachable_normal_range(sample_chargers):
    index = ChargerSpatialIndex(sample_chargers)

    # Vehicle at 40.7128, -74.0060 with 50% SoC (usable range ~ 200 km)
    results = index.find_nearest_reachable(
        lat=40.7128,
        lon=-74.0060,
        soc_pct=50.0,
        battery_capacity_kwh=75.0,
        soh=0.95,
        eff_kwh_per_km=0.18,
        max_results=5,
    )

    assert len(results) >= 3
    # Check that nearby chargers are marked reachable
    nearby = [r for r in results if r.charger_id in (1, 2, 3)]
    for ch in nearby:
        assert ch.reachable is True
        assert ch.road_distance_km < 5.0
        assert ch.road_distance_km >= ch.air_distance_km  # Road factor 1.3


def test_find_nearest_reachable_critically_low_soc(sample_chargers):
    index = ChargerSpatialIndex(sample_chargers)

    # Vehicle with only 1.5% SoC: usable range ~ 5 km, reserve budget ~ 4.5 km
    results = index.find_nearest_reachable(
        lat=40.7128,
        lon=-74.0060,
        soc_pct=1.5,
        battery_capacity_kwh=75.0,
        soh=0.95,
        eff_kwh_per_km=0.18,
        max_results=5,
    )

    # Distant charger (~88 km away) must NOT be reachable
    distant = [r for r in results if r.charger_id == 4]
    if distant:
        assert distant[0].reachable is False


def test_ranking_prefers_closer_and_higher_power(sample_chargers):
    index = ChargerSpatialIndex(sample_chargers)
    results = index.find_nearest_reachable(
        lat=40.7128,
        lon=-74.0060,
        soc_pct=60.0,
        battery_capacity_kwh=75.0,
        max_results=5,
    )

    # Top result should be reachable and sorted by road distance
    assert results[0].reachable is True
    for i in range(len(results) - 1):
        if results[i].reachable == results[i+1].reachable:
            assert results[i].road_distance_km <= results[i+1].road_distance_km + 0.1


def test_route_planner_direct_trip():
    # Short trip: 30 km with 80% SoC -> no stops needed
    plan = plan_charging_route(
        start_lat=40.7128,
        start_lon=-74.0060,
        dest_lat=40.8500,
        dest_lon=-73.9500,
        chargers=[],
        initial_soc_pct=80.0,
        battery_capacity_kwh=75.0,
    )

    assert isinstance(plan, RoutePlan)
    assert plan.feasible is True
    assert plan.total_charge_time_min == 0.0
    assert len(plan.stops) == 2
    assert plan.stops[0].stop_type == "ORIGIN"
    assert plan.stops[1].stop_type == "DESTINATION"


def test_route_planner_requires_stop():
    # Long trip: ~250 km with only 30% battery (range ~120 km) -> requires charging stop
    # Waypoint charger halfway
    mid_charger = {
        "charger_id": 99,
        "network": "Turnpike Fast DC",
        "lat": 40.3000,
        "lon": -74.3000,
        "power_kw": 150.0,
    }

    plan = plan_charging_route(
        start_lat=40.7128,
        start_lon=-74.0060,
        dest_lat=39.5000,
        dest_lon=-75.0000,
        chargers=[mid_charger],
        initial_soc_pct=45.0,
        battery_capacity_kwh=75.0,
        target_arrival_soc_pct=15.0,
        charge_to_soc_pct=80.0,
    )

    assert isinstance(plan, RoutePlan)
    assert plan.feasible is True
    assert plan.total_charge_time_min > 0.0
    assert any(s.stop_type == "CHARGER" for s in plan.stops)


def test_route_planner_unreachable_no_chargers():
    # Trip of 500 km with only 15% SoC and empty charger list
    plan = plan_charging_route(
        start_lat=40.7128,
        start_lon=-74.0060,
        dest_lat=45.0000,
        dest_lon=-74.0060,
        chargers=[],
        initial_soc_pct=15.0,
    )
    assert plan.feasible is False
    assert "unreachable" in plan.reason.lower()
