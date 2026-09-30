"""High-Performance Fleet Dataset Seeder for Phase P3
Seeds:
- Postgres: 100,000 vehicles, chargers across 5 metro clusters, drivers, initial alerts
- Redis: tenantof:{vin} and veh:params:{vin}
- ClickHouse: vehicle_daily (9M rows), charge_session (3.6M rows), telemetry history (86.4M rows)
- ML Data: ground_truth_soh.parquet
"""

import asyncio
import os
import math
import random
import time
import asyncpg
import clickhouse_connect
import pygeohash as pgh
import pyarrow as pa
import pyarrow.parquet as pq
import redis

# Model specifications per §5.3 / fleet.go
MODELS = [
    {"model_id": 1, "name": "VoltX Hyper-e", "capacity_kwh": 75.0, "rated_range_km": 420.0, "max_dc_kw": 150.0, "base_eff": 0.178},
    {"model_id": 2, "name": "NordMotors Polar-4", "capacity_kwh": 82.0, "rated_range_km": 450.0, "max_dc_kw": 135.0, "base_eff": 0.182},
    {"model_id": 3, "name": "AsiaDrive Express-V", "capacity_kwh": 60.0, "rated_range_km": 350.0, "max_dc_kw": 100.0, "base_eff": 0.171},
    {"model_id": 4, "name": "EuroEV Continental", "capacity_kwh": 90.0, "rated_range_km": 500.0, "max_dc_kw": 175.0, "base_eff": 0.180},
    {"model_id": 5, "name": "ZephyrEV Aero-6", "capacity_kwh": 50.0, "rated_range_km": 300.0, "max_dc_kw": 80.0, "base_eff": 0.166},
]

OEMS = ["VoltX", "NordMotors", "AsiaDrive", "EuroEV", "ZephyrEV"]
OEM_PREFIXES = {
    "VoltX": "1VXEV",
    "NordMotors": "1NMEV",
    "AsiaDrive": "1ADEV",
    "EuroEV": "1EEEV",
    "ZephyrEV": "1ZZEV",
}

VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
VIN_LETTER_VALUES = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5,
    'P': 7, 'R': 9,
    'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
}

def generate_vin(oem: str, vehicle_idx: int) -> str:
    prefix = OEM_PREFIXES.get(oem, "1VXEV")
    body = list(f"{prefix}01A0{vehicle_idx % 100000000:08d}")
    total = sum(VIN_LETTER_VALUES[body[i]] * VIN_WEIGHTS[i] for i in range(17) if i != 8)
    rem = total % 11
    body[8] = 'X' if rem == 10 else str(rem)
    return "".join(body)

def compute_soh(efc: float, dc_fast_share: float, hot_exposure: float, noise: float) -> float:
    coeff_cycle = 0.00160
    coeff_dc_fast = 0.00040
    coeff_thermal = 0.00025
    deg = coeff_cycle * math.sqrt(max(0.0, efc)) + coeff_dc_fast * dc_fast_share * efc + coeff_thermal * hot_exposure - noise
    soh = 1.0 - deg
    return round(max(0.65, min(1.0, soh)), 4)

async def seed_postgres(vehicles_data, chargers_data):
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "evc"),
        password=os.getenv("PG_PASSWORD", os.getenv("POSTGRES_PASSWORD", "change_me")),
        database=os.getenv("POSTGRES_DB", "evc"),
    )
    try:
        await conn.execute("SET app.bypass_rls = 'on';")
        
        # 1. Seed Chargers
        print(f"Seeding {len(chargers_data)} chargers into Postgres...")
        charger_records = [
            (c["charger_id"], c["network"], c["geohash7"], c["lat"], c["lon"], c["power_kw"])
            for c in chargers_data
        ]
        await conn.execute("TRUNCATE TABLE charger RESTART IDENTITY CASCADE;")
        await conn.copy_records_to_table(
            "charger",
            records=charger_records,
            columns=["charger_id", "network", "geohash7", "lat", "lon", "power_kw"]
        )

        # 2. Seed Drivers
        print("Seeding 3,000 drivers into Postgres...")
        driver_records = [
            (i + 1, (i % 3) + 1, f"DRV-{i+1:05d}", None)
            for i in range(3000)
        ]
        await conn.execute("TRUNCATE TABLE driver RESTART IDENTITY CASCADE;")
        await conn.copy_records_to_table(
            "driver",
            records=driver_records,
            columns=["driver_id", "fleet_id", "pseudonym", "erased_at"]
        )

        # 3. Seed 100,000 Vehicles
        print(f"Seeding {len(vehicles_data)} vehicles into Postgres...")
        # Check current vehicle count
        cur_count = await conn.fetchval("SELECT count(*) FROM vehicle;")
        if cur_count < len(vehicles_data):
            await conn.execute("TRUNCATE TABLE vehicle CASCADE;")
            vehicle_records = [
                (v["vin"], v["fleet_id"], v["model_id"], v["model_year"], None)
                for v in vehicles_data
            ]
            t0 = time.time()
            await conn.copy_records_to_table(
                "vehicle",
                records=vehicle_records,
                columns=["vin", "fleet_id", "model_id", "model_year", "erased_at"]
            )
            print(f"Postgres vehicles seeded in {time.time() - t0:.2f}s")
        else:
            print(f"Postgres already has {cur_count} vehicles.")

        # 4. Seed initial alerts
        print("Seeding sample alerts into Postgres...")
        await conn.execute("TRUNCATE TABLE alert RESTART IDENTITY CASCADE;")
        from datetime import datetime, timezone, timedelta
        base_time = datetime(2026, 9, 30, 18, 0, 0, tzinfo=timezone.utc)
        alert_records = []
        for i in range(100):
            v = vehicles_data[i]
            raised_at = base_time + timedelta(minutes=i % 60)
            resolved_at = None if i < 30 else (raised_at + timedelta(minutes=30))
            alert_records.append((
                i + 1,
                v["vin"],
                "RANGE_RISK" if i % 2 == 0 else "LOW_SOC",
                1 if i % 2 == 0 else 3,
                raised_at,
                resolved_at,
                '{"source":"seed","initial_soc":12.5}'
            ))
        await conn.copy_records_to_table(
            "alert",
            records=alert_records,
            columns=["alert_id", "vin", "type", "severity", "raised_at", "resolved_at", "detail"]
        )
        print("Postgres seeding complete.")
    finally:
        await conn.close()

def seed_redis(vehicles_data):
    print("Connecting to Redis...")
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    t0 = time.time()
    pipe = r.pipeline(transaction=False)
    batch_size = 5000
    for idx, v in enumerate(vehicles_data):
        # tenantof:{vin} -> tenant_id (fleet_id == tenant_id in 1:1 seed mapping)
        pipe.set(f"tenantof:{v['vin']}", v["fleet_id"])
        # veh:params:{vin}
        pipe.hset(f"veh:params:{v['vin']}", mapping={
            "capacity_kwh": str(v["capacity_kwh"]),
            "soh": str(v["true_soh"]),
            "base_eff_kwh_km": str(v["base_eff"]),
            "max_dc_kw": str(v["max_dc_kw"]),
            "model_name": v["model_name"],
            "oem": v["oem"]
        })
        if (idx + 1) % batch_size == 0 or idx == len(vehicles_data) - 1:
            pipe.execute()
            pipe = r.pipeline(transaction=False)
    print(f"Redis seeded {len(vehicles_data)} vehicles in {time.time() - t0:.2f}s")

def seed_clickhouse(vehicles_data):
    print("Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_HTTP_PORT", 8123)),
        username=os.getenv("CLICKHOUSE_USER", "evc"),
        password=os.getenv("CH_PASSWORD", os.getenv("CLICKHOUSE_PASSWORD", "change_me")),
        database=os.getenv("CLICKHOUSE_DB", "evc"),
    )

    # 1. Create and populate evc.vehicle_seed
    print("Creating and populating evc.vehicle_seed table in ClickHouse...")
    client.command("""
    CREATE TABLE IF NOT EXISTS evc.vehicle_seed (
        vin FixedString(17),
        fleet_id UInt8,
        model_id UInt8,
        oem LowCardinality(String),
        model_name LowCardinality(String),
        capacity_kwh Float32,
        base_eff Float32,
        true_soh Float32,
        dc_fast_share Float32,
        max_dc_kw Float32,
        odo_km Float32,
        efc Float32
    ) ENGINE = MergeTree ORDER BY vin;
    """)
    client.command("TRUNCATE TABLE evc.vehicle_seed;")

    # Batch insert 100K vehicle_seed rows using pyarrow for extreme speed
    arrow_table = pa.Table.from_pydict({
        "vin": [v["vin"] for v in vehicles_data],
        "fleet_id": [v["fleet_id"] for v in vehicles_data],
        "model_id": [v["model_id"] for v in vehicles_data],
        "oem": [v["oem"] for v in vehicles_data],
        "model_name": [v["model_name"] for v in vehicles_data],
        "capacity_kwh": [v["capacity_kwh"] for v in vehicles_data],
        "base_eff": [v["base_eff"] for v in vehicles_data],
        "true_soh": [v["true_soh"] for v in vehicles_data],
        "dc_fast_share": [v["dc_fast_share"] for v in vehicles_data],
        "max_dc_kw": [v["max_dc_kw"] for v in vehicles_data],
        "odo_km": [v["odo_km"] for v in vehicles_data],
        "efc": [v["efc"] for v in vehicles_data],
    })
    client.insert_arrow("evc.vehicle_seed", arrow_table)
    print("evc.vehicle_seed loaded.")

    # 2. Populate evc.vehicle_daily (90 days x 100K = 9,000,000 rows)
    cur_daily = client.command("SELECT count() FROM evc.vehicle_daily")
    if cur_daily < 9000000:
        print("Generating 9,000,000 rows for evc.vehicle_daily via ClickHouse native engine...")
        t0 = time.time()
        client.command("""
        INSERT INTO evc.vehicle_daily
        SELECT
            v.vin,
            toDate('2026-07-01') + toIntervalDay(d.number) AS day,
            toFloat32(40.0 + (cityHash64(v.vin, d.number) % 120)) AS distance_km,
            toFloat32((40.0 + (cityHash64(v.vin, d.number) % 120)) * v.base_eff * (0.95 + (cityHash64(v.vin, d.number, 1) % 15) / 100.0)) AS kwh_used,
            toFloat32(if(cityHash64(v.vin, d.number) % 3 == 0, v.capacity_kwh * 0.45 * v.dc_fast_share, 0.0)) AS dc_fast_kwh,
            toFloat32(if(cityHash64(v.vin, d.number) % 2 == 0, v.capacity_kwh * 0.55 * (1.0 - v.dc_fast_share), 0.0)) AS ac_kwh,
            toFloat32(18.0 + (cityHash64(v.vin, d.number, 2) % 200) / 10.0) AS avg_temp_c,
            toUInt16(1 + (cityHash64(v.vin, d.number, 3) % 3)) AS sessions,
            toFloat32(v.capacity_kwh * v.true_soh * (0.98 + (cityHash64(v.vin, d.number, 4) % 40) / 1000.0)) AS est_capacity_kwh
        FROM evc.vehicle_seed v
        CROSS JOIN numbers(90) d;
        """)
        print(f"evc.vehicle_daily (9M rows) generated in {time.time() - t0:.2f}s")
    else:
        print(f"evc.vehicle_daily already populated ({cur_daily} rows).")

    # 3. Populate evc.charge_session (36 sessions x 100K = 3,600,000 rows)
    cur_sessions = client.command("SELECT count() FROM evc.charge_session")
    if cur_sessions < 3600000:
        print("Generating 3,600,000 rows for evc.charge_session via ClickHouse native engine...")
        t0 = time.time()
        client.command("""
        INSERT INTO evc.charge_session
        SELECT
            v.vin,
            toDateTime64('2026-07-01 02:00:00', 3, 'UTC') + toIntervalDay(s.number * 2.5) + toIntervalMinute((cityHash64(v.vin, s.number) % 120)) AS start_ts,
            toDateTime64('2026-07-01 03:30:00', 3, 'UTC') + toIntervalDay(s.number * 2.5) + toIntervalMinute((cityHash64(v.vin, s.number) % 120) + 45 + (cityHash64(v.vin, s.number, 1) % 60)) AS end_ts,
            toFloat32(15.0 + (cityHash64(v.vin, s.number, 2) % 30)) AS soc_start,
            toFloat32(80.0 + (cityHash64(v.vin, s.number, 3) % 18)) AS soc_end,
            toFloat32(v.capacity_kwh * v.true_soh * ((80.0 + (cityHash64(v.vin, s.number, 3) % 18)) - (15.0 + (cityHash64(v.vin, s.number, 2) % 30))) / 100.0 * 1.05) AS kwh_added,
            toFloat32(if(cityHash64(v.vin, s.number) % 2 == 0, 100.0, 11.0)) AS max_kw,
            if(cityHash64(v.vin, s.number) % 2 == 0, 'DC_FAST', 'AC_LEVEL_2') AS charger_type
        FROM evc.vehicle_seed v
        CROSS JOIN numbers(36) s;
        """)
        print(f"evc.charge_session (3.6M rows) generated in {time.time() - t0:.2f}s")
    else:
        print(f"evc.charge_session already populated ({cur_sessions} rows).")

    # 4. Populate evc.telemetry history: 10K vehicles x 30 days @ 5-min intervals (~86.4M rows)
    cur_telem = client.command("SELECT count() FROM evc.telemetry")
    if cur_telem < 10000000:
        print("Generating telemetry history in evc.telemetry (10K vehicles x 30 days @ 5-min = 86,400,000 rows)...")
        t0 = time.time()
        # Insert in chunks of 5 days (14.4M rows per chunk) for stability and smooth execution
        for day_chunk in range(0, 30, 5):
            print(f"  Generating days {day_chunk} to {day_chunk + 4}...")
            client.command(f"""
            INSERT INTO evc.telemetry
            SELECT
                v.vin,
                toDateTime64('2026-09-01 00:00:00', 3, 'UTC') + toIntervalMinute(({day_chunk} + d.number) * 1440 + m.number * 5) AS ts,
                toUInt64(({day_chunk} + d.number) * 288 + m.number + 1) AS seq,
                v.oem,
                'dr5regw' AS geohash7,
                toFloat32(40.7128 + ((cityHash64(v.vin, m.number) % 100) - 50) / 1000.0) AS lat,
                toFloat32(-74.0060 + ((cityHash64(v.vin, m.number, 1) % 100) - 50) / 1000.0) AS lon,
                toFloat32(if((m.number % 288) BETWEEN 96 AND 216, 35.0 + (cityHash64(v.vin, m.number) % 50), 0.0)) AS speed_kmh,
                toFloat32(40.0 + (cityHash64(v.vin, d.number) % 55)) AS soc_pct,
                toFloat64(v.odo_km + ({day_chunk} + d.number) * 60.0 + m.number * 0.2) AS odo_km,
                toFloat32(24.0 + (cityHash64(v.vin, m.number, 2) % 140) / 10.0) AS batt_temp_c,
                toUInt8(if((m.number % 288) BETWEEN 12 AND 60, 1, 0)) AS charging,
                toFloat32(if((m.number % 288) BETWEEN 12 AND 60, 50.0, 0.0)) AS charge_kw,
                [] AS dtc,
                'NONE' AS evt
            FROM (SELECT * FROM evc.vehicle_seed LIMIT 10000) v
            CROSS JOIN numbers(5) d
            CROSS JOIN numbers(288) m
            SETTINGS max_partitions_per_insert_block = 1000;
            """)
        print(f"evc.telemetry history generated in {time.time() - t0:.2f}s")
    else:
        print(f"evc.telemetry already has {cur_telem} rows.")

def generate_ground_truth_parquet(vehicles_data):
    print("Generating ground_truth_soh.parquet for ML...")
    os.makedirs("services/ml/data", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Observable features + ground truth
    table = pa.Table.from_pydict({
        "vin": [v["vin"] for v in vehicles_data],
        "oem": [v["oem"] for v in vehicles_data],
        "model_id": [v["model_id"] for v in vehicles_data],
        "model_name": [v["model_name"] for v in vehicles_data],
        "battery_kwh": [v["capacity_kwh"] for v in vehicles_data],
        "rated_range_km": [v["rated_range_km"] for v in vehicles_data],
        "base_eff_kwh_km": [v["base_eff"] for v in vehicles_data],
        "years_of_service": [v["years_of_service"] for v in vehicles_data],
        "odo_km": [v["odo_km"] for v in vehicles_data],
        "efc": [v["efc"] for v in vehicles_data],
        "dc_fast_share": [v["dc_fast_share"] for v in vehicles_data],
        "hot_exposure": [v["hot_exposure"] for v in vehicles_data],
        "true_soh": [v["true_soh"] for v in vehicles_data],
        "true_eff_kwh_km": [v["true_eff"] for v in vehicles_data],
        # Observable session features per §6.5
        "est_capacity_kwh": [v["est_capacity_kwh"] for v in vehicles_data],
        "obs_dc_fast_share": [v["obs_dc_fast_share"] for v in vehicles_data],
        "obs_avg_temp_c": [v["obs_avg_temp_c"] for v in vehicles_data],
        "obs_max_temp_c": [v["obs_max_temp_c"] for v in vehicles_data],
        "obs_kwh_per_km": [v["obs_kwh_per_km"] for v in vehicles_data],
        "deep_discharge_share": [v["deep_discharge_share"] for v in vehicles_data],
    })

    pq.write_table(table, "services/ml/data/ground_truth_soh.parquet")
    pq.write_table(table, "data/ground_truth_soh.parquet")
    print("ground_truth_soh.parquet written successfully.")

def main():
    random.seed(42)
    num_vehicles = 100000

    print(f"Generating synthetic fleet metadata for {num_vehicles} vehicles...")
    t0 = time.time()
    vehicles_data = []

    # 5 Metropolitan clusters (SF, LA, Chicago, NY, Seattle)
    metro_clusters = [
        {"name": "SF Bay", "lat": 37.77, "lon": -122.41},
        {"name": "Los Angeles", "lat": 34.05, "lon": -118.24},
        {"name": "Chicago", "lat": 41.87, "lon": -87.62},
        {"name": "New York", "lat": 40.71, "lon": -74.00},
        {"name": "Seattle", "lat": 47.60, "lon": -122.33},
    ]

    for i in range(num_vehicles):
        oem = OEMS[i % len(OEMS)]
        model = MODELS[i % len(MODELS)]
        vin = generate_vin(oem, i + 1)
        fleet_id = (i % 3) + 1  # 3 fleets mapped to 3 tenants

        years_of_service = round(0.5 + random.random() * 3.0, 2)
        odo_km = round(years_of_service * (12000.0 + random.random() * 8000.0), 1)
        efc = round(years_of_service * 45.0 * (0.8 + random.random() * 0.4), 1)
        dc_fast_share = round(0.15 + random.random() * 0.40, 3)
        hot_exposure = round(years_of_service * (10.0 + random.random() * 20.0), 1)
        noise = (random.random() - 0.5) * 0.01

        true_soh = compute_soh(efc, dc_fast_share, hot_exposure, noise)
        true_eff = round(model["base_eff"] * (0.95 + random.random() * 0.10), 4)

        # Observable features from sessions & daily telemetry per §6.5
        est_capacity_kwh = round(model["capacity_kwh"] * true_soh * (0.985 + random.random() * 0.03), 2)
        obs_dc_fast_share = round(max(0.0, min(1.0, dc_fast_share + (random.random() - 0.5) * 0.04)), 3)
        obs_avg_temp = round(20.0 + random.random() * 12.0, 1)
        obs_max_temp = round(obs_avg_temp + 10.0 + random.random() * 8.0, 1)
        obs_kwh_per_km = round(true_eff * (0.98 + random.random() * 0.04), 4)
        deep_discharge_share = round(0.05 + random.random() * 0.20, 3)

        cluster = metro_clusters[i % len(metro_clusters)]
        lat = cluster["lat"] + (random.random() - 0.5) * 0.3
        lon = cluster["lon"] + (random.random() - 0.5) * 0.3

        vehicles_data.append({
            "index": i,
            "vin": vin,
            "fleet_id": fleet_id,
            "model_id": model["model_id"],
            "model_name": model["name"],
            "oem": oem,
            "capacity_kwh": model["capacity_kwh"],
            "rated_range_km": model["rated_range_km"],
            "max_dc_kw": model["max_dc_kw"],
            "base_eff": model["base_eff"],
            "model_year": 2021 + (i % 4),
            "years_of_service": years_of_service,
            "odo_km": odo_km,
            "efc": efc,
            "dc_fast_share": dc_fast_share,
            "hot_exposure": hot_exposure,
            "true_soh": true_soh,
            "true_eff": true_eff,
            "est_capacity_kwh": est_capacity_kwh,
            "obs_dc_fast_share": obs_dc_fast_share,
            "obs_avg_temp_c": obs_avg_temp,
            "obs_max_temp_c": obs_max_temp,
            "obs_kwh_per_km": obs_kwh_per_km,
            "deep_discharge_share": deep_discharge_share,
            "lat": lat,
            "lon": lon,
        })
    print(f"Metadata generated in {time.time() - t0:.2f}s")

    # Generate ~600 chargers across the 5 metro clusters
    print("Generating charger network across metro areas...")
    networks = ["Electrify America", "EVgo", "ChargePoint", "Tesla Supercharger", "FleetDepot Fast"]
    powers = [50.0, 100.0, 150.0, 250.0, 350.0, 11.0, 22.0]
    chargers_data = []
    charger_id = 1
    for cluster in metro_clusters:
        for _ in range(120):
            clat = cluster["lat"] + (random.random() - 0.5) * 0.35
            clon = cluster["lon"] + (random.random() - 0.5) * 0.35
            gh7 = pgh.encode(clat, clon, precision=7)
            chargers_data.append({
                "charger_id": charger_id,
                "network": random.choice(networks),
                "geohash7": gh7,
                "lat": round(clat, 6),
                "lon": round(clon, 6),
                "power_kw": random.choice(powers)
            })
            charger_id += 1

    # Execute seed targets
    asyncio.run(seed_postgres(vehicles_data, chargers_data))
    seed_redis(vehicles_data)
    seed_clickhouse(vehicles_data)
    generate_ground_truth_parquet(vehicles_data)

    print("\n==============================================")
    print("All Seed Operations Finished Successfully!")
    print("==============================================")

if __name__ == "__main__":
    main()
