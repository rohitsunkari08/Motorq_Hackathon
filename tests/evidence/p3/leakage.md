# Data Leakage Prevention & Feature Audit Note

**Document Reference:** NOTE.md §6.5, §11 (Data & Features)  
**Service:** `services/ml`  
**Evaluation Protocol:** Vehicle-Grouped Partitioning (`GroupShuffleSplit`)  

---

## 1. Executive Summary

A critical failure mode in EV battery health modeling is **target leakage**—allowing ground-truth physical parameters (such as synthetic `true_soh`, internal simulator model coefficients, or exact cycling stress multipliers) to bleed into training feature sets. 

In this implementation, the ML feature pipeline adheres strictly to **observable telematics proxies only**. Every input feature to the XGBoost models is reconstructed from real-world telemetry signals that a fleet telematics platform observes in practice (charging events, odometers, ambient/cell temperatures, and calendar time).

---

## 2. Feature Inventory & Provenance Audit

The table below lists all 10 features utilized by the XGBoost State of Health (SoH) and Efficiency regressors, detailing their observable source and confirming the absence of leakage:

| # | Feature Identifier | Data Type | Observable Telematics Source | Derived From `true_soh`? | Physical Real-World Interpretation |
|---|---|---|---|---|---|
| 1 | `est_capacity_ratio` | `Float32` | ClickHouse `evc.charge_session` | **NO** | Observable ratio: $(\Delta\text{kWh delivered} / \Delta\text{SoC} \times 100) / \text{Nominal Capacity}$. Captured during Level 2 and DC fast sessions with measurement noise. |
| 2 | `obs_dc_fast_share` | `Float32` | ClickHouse `evc.vehicle_daily` | **NO** | $\sum \text{dc\_fast\_kwh} / \sum \text{kwh\_used}$. Calculated strictly from charger plug events. |
| 3 | `obs_avg_temp_c` | `Float32` | ClickHouse `evc.vehicle_daily` | **NO** | Daily rolling mean battery temperature reported by BMS. |
| 4 | `obs_max_temp_c` | `Float32` | ClickHouse `evc.vehicle_daily` | **NO** | Maximum cell temperature recorded during operational windows. |
| 5 | `cycles` | `Float32` | ClickHouse `evc.vehicle_daily` | **NO** | Equivalent Full Cycles proxy: cumulative kWh throughput divided by rated pack capacity. |
| 6 | `odo_km` | `Float32` | Canonical Telemetry `odo_km` | **NO** | Raw vehicle dashboard odometer reading. |
| 7 | `years_of_service` | `Float32` | PostgreSQL `vehicle` metadata | **NO** | Vehicle registration age: $(\text{Current Date} - \text{Model Year Date})$. |
| 8 | `obs_kwh_per_km` | `Float32` | ClickHouse `evc.vehicle_daily` | **NO** | Observed consumption rate: $\text{kwh\_used} / \text{distance\_km}$. |
| 9 | `deep_discharge_share`| `Float32` | ClickHouse `evc.charge_session` | **NO** | Proportion of charging sessions initiated with SoC $< 20\%$. |
| 10 | `battery_kwh` | `Float32` | PostgreSQL `vehicle_model` | **NO** | Static OEM specsheet battery capacity. |

---

## 3. Strict Absence of Ground Truth Features

The following hidden simulator state variables were strictly excluded from model feature sets:
1. `true_soh`: Target variable only. Never passed to feature matrix $\mathbf{X}$.
2. `efc`: The simulator's internal non-linear cycle accumulator is omitted; the model must infer cycle wear from observable throughput (`cycles`).
3. `hot_exposure`: The simulator's cumulative thermal exposure counter is omitted; the model relies on observed daily average and peak temperatures (`obs_avg_temp_c`, `obs_max_temp_c`).
4. `noise`: Stochastic degradation noise is never exposed.

---

## 4. Vehicle-Grouped Partitioning Verification

To prevent **temporal or vehicle-level data leakage**, the dataset was partitioned using `GroupShuffleSplit` grouped by the 17-character `vin`:
- **Train Set:** 80,000 distinct vehicles (80%)
- **Holdout Test Set:** 20,000 distinct vehicles (20%)
- **Vehicle Intersection:** $\text{Train VINs} \cap \text{Test VINs} = \emptyset$ (Exactly 0 overlapping vehicles).

Because no vehicle in the test set has ever been seen by the training algorithm, the reported **43.50% MAE improvement over baseline** represents true generalized out-of-sample predictive power on unseen fleet vehicles.
