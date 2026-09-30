"""Generate ground_truth_soh.parquet for ML training & evaluation
Matches NOTE.md §5.3 & §6.5:
- 100,000 synthetic vehicles with true_soh, true_eff_kwh_km
- observable features from vehicle_daily + charge_session:
  (est_capacity_kwh, dc_fast_share, avg/max temp, cycles, odo, age, kWh/km, deep_discharge_share)
"""

import os
import math
import random
import time
import pyarrow as pa
import pyarrow.parquet as pq

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

def main():
    random.seed(42)
    num_vehicles = 100000
    print(f"Generating ML ground truth parquet for {num_vehicles} vehicles...")
    t0 = time.time()

    vins = []
    oems = []
    model_ids = []
    model_names = []
    battery_kwhs = []
    rated_range_kms = []
    base_eff_kwh_kms = []
    years_of_services = []
    odo_kms = []
    efcs = []
    dc_fast_shares = []
    hot_exposures = []
    true_sohs = []
    true_eff_kwh_kms = []

    # Observable features
    est_capacity_kwhs = []
    est_capacity_ratios = []
    obs_dc_fast_shares = []
    obs_avg_temp_cs = []
    obs_max_temp_cs = []
    obs_kwh_per_kms = []
    deep_discharge_shares = []
    cycles_list = []

    for i in range(num_vehicles):
        oem = OEMS[i % len(OEMS)]
        model = MODELS[i % len(MODELS)]
        vin = generate_vin(oem, i + 1)

        years = round(0.5 + random.random() * 3.0, 2)
        odo = round(years * (12000.0 + random.random() * 8000.0), 1)
        efc = round(years * 45.0 * (0.8 + random.random() * 0.4), 1)
        dc_fast = round(0.15 + random.random() * 0.40, 3)
        hot_exp = round(years * (10.0 + random.random() * 20.0), 1)
        noise = (random.random() - 0.5) * 0.01

        true_soh = compute_soh(efc, dc_fast, hot_exp, noise)
        true_eff = round(model["base_eff"] * (0.95 + random.random() * 0.10), 4)

        # Observable features from sessions & daily telemetry
        est_cap = round(model["capacity_kwh"] * true_soh * (0.985 + random.random() * 0.03), 2)
        est_cap_ratio = round(est_cap / model["capacity_kwh"], 4)
        obs_dc_fast = round(max(0.0, min(1.0, dc_fast + (random.random() - 0.5) * 0.04)), 3)
        obs_avg_temp = round(20.0 + random.random() * 12.0, 1)
        obs_max_temp = round(obs_avg_temp + 10.0 + random.random() * 8.0, 1)
        obs_kwh_km = round(true_eff * (0.98 + random.random() * 0.04), 4)
        deep_disc = round(0.05 + random.random() * 0.20, 3)
        cycles = round(efc * (0.97 + random.random() * 0.06), 1)

        vins.append(vin)
        oems.append(oem)
        model_ids.append(model["model_id"])
        model_names.append(model["name"])
        battery_kwhs.append(model["capacity_kwh"])
        rated_range_kms.append(model["rated_range_km"])
        base_eff_kwh_kms.append(model["base_eff"])
        years_of_services.append(years)
        odo_kms.append(odo)
        efcs.append(efc)
        dc_fast_shares.append(dc_fast)
        hot_exposures.append(hot_exp)
        true_sohs.append(true_soh)
        true_eff_kwh_kms.append(true_eff)

        est_capacity_kwhs.append(est_cap)
        est_capacity_ratios.append(est_cap_ratio)
        obs_dc_fast_shares.append(obs_dc_fast)
        obs_avg_temp_cs.append(obs_avg_temp)
        obs_max_temp_cs.append(obs_max_temp)
        obs_kwh_per_kms.append(obs_kwh_km)
        deep_discharge_shares.append(deep_disc)
        cycles_list.append(cycles)

    table = pa.Table.from_pydict({
        "vin": vins,
        "oem": oems,
        "model_id": model_ids,
        "model_name": model_names,
        "battery_kwh": battery_kwhs,
        "rated_range_km": rated_range_kms,
        "base_eff_kwh_km": base_eff_kwh_kms,
        "years_of_service": years_of_services,
        "odo_km": odo_kms,
        "efc": efcs,
        "dc_fast_share": dc_fast_shares,
        "hot_exposure": hot_exposures,
        "true_soh": true_sohs,
        "true_eff_kwh_km": true_eff_kwh_kms,
        # Observables for training
        "est_capacity_kwh": est_capacity_kwhs,
        "est_capacity_ratio": est_capacity_ratios,
        "obs_dc_fast_share": obs_dc_fast_shares,
        "obs_avg_temp_c": obs_avg_temp_cs,
        "obs_max_temp_c": obs_max_temp_cs,
        "obs_kwh_per_km": obs_kwh_per_kms,
        "deep_discharge_share": deep_discharge_shares,
        "cycles": cycles_list,
    })

    os.makedirs("data", exist_ok=True)
    os.makedirs("services/ml/data", exist_ok=True)
    pq.write_table(table, "data/ground_truth_soh.parquet")
    pq.write_table(table, "services/ml/data/ground_truth_soh.parquet")
    print(f"ground_truth_soh.parquet generated in {time.time() - t0:.2f}s ({len(vins)} records)")

if __name__ == "__main__":
    main()
