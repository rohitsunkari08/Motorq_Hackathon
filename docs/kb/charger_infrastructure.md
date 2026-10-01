# EV Charger Infrastructure and Spatial Routing Guide

## Charger Classification

### AC Level 2 Charging
- **Power Rating**: 7.2 kW – 11.5 kW (208/240V, 30-48A single-phase).
- **Efficiency**: 88% - 92%.
- **Use Case**: Overnight depot dwell (6-10 hours), workplace charging, driver home chargers.
- **Battery Stress**: Minimal; negligible cyclic degradation penalty.

### DC Fast Charging (DCFC)
- **Power Rating**: 50 kW (500V, 100A), 100 kW, 150 kW, up to 350 kW.
- **Efficiency**: 90% - 94% (higher grid-to-vehicle losses at high currents).
- **Use Case**: Urgent en-route opportunity charging, quick shift turnaround (15-45 minutes).
- **Battery Stress**: High thermal and electrochemical stress. Accelerated C-rate degradation.

## Spatial Indexing and Charger Discovery
- Fleet systems index public and private chargers using **Geohash Level 7** (approx. 153m x 153m precision cells) and coarse **Geohash Level 5** bounding boxes (~4.9km x 4.9km).
- Reachability calculation:
  1. Expand vehicle location to geohash prefix and 8 neighbor bounding boxes.
  2. Filter candidate chargers by distance using the Haversine formula adjusted by a 1.3 road curvature factor:
     `road_distance_km = haversine(vehicle_coord, charger_coord) * 1.3`
  3. Energy needed:
     `energy_kwh = road_distance_km * vehicle_eff_kwh_per_km`
  4. Feasibility rule:
     `energy_kwh <= usable_battery_kwh * (1.0 - reserve_margin)` where standard reserve margin = 10%.
  5. Rank reachable candidates by distance and power rating.

## Depot Power Allocation and Load Balancing
- Depots have transformer capacity limits (e.g. 500 kW aggregate).
- Fleet scheduling prevents unmanaged coincident charging where all returning vehicles draw max power simultaneously, which triggers peak demand penalties.
