"""Machine Learning Training & Evaluation Pipeline for EV Battery Health & Efficiency
Implements NOTE.md §6.5:
- Data: per-vehicle features from vehicle_daily + charge_session
  (estimated capacity, dc_fast_share, avg/max temp, cycles, odo, age, kWh/km, deep_discharge_share)
- Targets:
  1. SoH % vs ground truth
  2. Energy efficiency kWh/km
- Models: XGBoost regressors
- Baselines:
  - SoH: linear(age, odo)
  - Efficiency: rated model efficiency
- Split: Grouped by vehicle (no vehicle in both train and test)
- Leakage check: no true_soh-derived features; capacity estimate only from observable sessions
- Metrics: MAE, RMSE, R2, per-OEM breakdown, feature importance
- Acceptance: SoH MAE beats baseline >= 30%
- Fleet outlier/anomaly: vehicles with SoH decline > 2 sigma vs peers -> FAST_DEGRADATION alert
- Vector use: 12-dim degradation profile for pgvector similar-vehicle retrieval
- Model artifacts: saved to models/*.json
"""

import json
import os
import time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
import xgboost as xgb


def load_dataset(parquet_path: str = "data/ground_truth_soh.parquet") -> pd.DataFrame:
    if not os.path.exists(parquet_path):
        parquet_path = "services/ml/data/ground_truth_soh.parquet"
    print(f"Loading fleet dataset from {parquet_path}...")
    table = pq.read_table(parquet_path)
    df = table.to_pandas()
    if "est_capacity_ratio" not in df.columns:
        df["est_capacity_ratio"] = df["est_capacity_kwh"] / df["battery_kwh"]
    if "cycles" not in df.columns:
        df["cycles"] = df["efc"]
    print(f"Loaded {len(df)} vehicle records.")
    return df


def train_and_evaluate():
    t_start = time.time()
    df = load_dataset()

    # Features for SoH regressor per §6.5 (Strict observable features, no leakage)
    soh_features = [
        "est_capacity_ratio",
        "obs_dc_fast_share",
        "obs_avg_temp_c",
        "obs_max_temp_c",
        "cycles",
        "odo_km",
        "years_of_service",
        "obs_kwh_per_km",
        "deep_discharge_share",
        "battery_kwh",
    ]

    # Target: SoH in percentage (e.g. 85.0 to 100.0)
    y_soh = df["true_soh"] * 100.0

    # Features for Efficiency regressor
    eff_features = [
        "base_eff_kwh_km",
        "obs_avg_temp_c",
        "obs_kwh_per_km",
        "battery_kwh",
        "years_of_service",
    ]
    y_eff = df["true_eff_kwh_km"]

    # 1. Grouped train/test split by vehicle VIN (80% train, 20% test)
    # Ensures zero vehicle overlap between train and test
    gss = GroupShuffleSplit(n_splits=1, train_size=0.8, random_state=42)
    train_idx, test_idx = next(gss.split(df, groups=df["vin"]))

    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()

    # Verify vehicle isolation
    train_vins = set(train_df["vin"])
    test_vins = set(test_df["vin"])
    overlap = train_vins.intersection(test_vins)
    assert len(overlap) == 0, f"Vehicle leakage detected! Overlap count: {len(overlap)}"
    print(f"Grouped split verified: {len(train_df)} train vehicles, {len(test_df)} holdout test vehicles (0 overlap).")

    # ========================================================
    # 2. Battery State of Health (SoH) Models
    # ========================================================
    print("\n--- Training Battery SoH Models ---")
    # Baseline SoH: linear(age, odo) per §6.5
    baseline_features = ["years_of_service", "odo_km"]
    lin_base = LinearRegression()
    lin_base.fit(train_df[baseline_features], train_df["true_soh"] * 100.0)
    soh_base_pred = lin_base.predict(test_df[baseline_features])

    base_mae = mean_absolute_error(test_df["true_soh"] * 100.0, soh_base_pred)
    base_rmse = np.sqrt(mean_squared_error(test_df["true_soh"] * 100.0, soh_base_pred))
    base_r2 = r2_score(test_df["true_soh"] * 100.0, soh_base_pred)

    # XGBoost SoH Regressor
    soh_model = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
    )
    soh_model.fit(
        train_df[soh_features],
        train_df["true_soh"] * 100.0,
        eval_set=[(test_df[soh_features], test_df["true_soh"] * 100.0)],
        verbose=False,
    )
    soh_model_pred = soh_model.predict(test_df[soh_features])

    model_mae = mean_absolute_error(test_df["true_soh"] * 100.0, soh_model_pred)
    model_rmse = np.sqrt(mean_squared_error(test_df["true_soh"] * 100.0, soh_model_pred))
    model_r2 = r2_score(test_df["true_soh"] * 100.0, soh_model_pred)

    # Improvement calculation
    improvement_pct = ((base_mae - model_mae) / base_mae) * 100.0

    print(f"Baseline SoH (Linear): MAE = {base_mae:.4f}%, RMSE = {base_rmse:.4f}%, R2 = {base_r2:.4f}")
    print(f"XGBoost SoH Model:     MAE = {model_mae:.4f}%, RMSE = {model_rmse:.4f}%, R2 = {model_r2:.4f}")
    print(f"SoH MAE Improvement Over Baseline: {improvement_pct:.2f}% (Acceptance requirement: >= 30%)")

    assert improvement_pct >= 30.0, f"SoH MAE improvement {improvement_pct:.2f}% < 30% standard!"

    # Per-OEM breakdown
    test_df["soh_pred"] = soh_model_pred
    per_oem_metrics = {}
    for oem_name, oem_group in test_df.groupby("oem"):
        oem_mae = mean_absolute_error(oem_group["true_soh"] * 100.0, oem_group["soh_pred"])
        oem_base_mae = mean_absolute_error(
            oem_group["true_soh"] * 100.0,
            lin_base.predict(oem_group[baseline_features])
        )
        per_oem_metrics[oem_name] = {
            "baseline_mae": round(oem_base_mae, 4),
            "model_mae": round(oem_mae, 4),
            "improvement_pct": round(((oem_base_mae - oem_mae) / oem_base_mae) * 100.0, 2),
            "sample_count": len(oem_group),
        }

    # Feature importances
    feature_importances = dict(zip(soh_features, [round(float(x), 4) for x in soh_model.feature_importances_]))

    # ========================================================
    # 3. Energy Efficiency (kWh/km) Models
    # ========================================================
    print("\n--- Training Energy Efficiency Models ---")
    eff_base_pred = test_df["base_eff_kwh_km"].values
    eff_base_mae = mean_absolute_error(test_df["true_eff_kwh_km"], eff_base_pred)

    eff_model = xgb.XGBRegressor(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.08,
        random_state=42,
        n_jobs=-1,
    )
    eff_model.fit(
        train_df[eff_features],
        train_df["true_eff_kwh_km"],
        eval_set=[(test_df[eff_features], test_df["true_eff_kwh_km"])],
        verbose=False,
    )
    eff_model_pred = eff_model.predict(test_df[eff_features])

    eff_model_mae = mean_absolute_error(test_df["true_eff_kwh_km"], eff_model_pred)
    eff_improvement_pct = ((eff_base_mae - eff_model_mae) / eff_base_mae) * 100.0

    print(f"Baseline Efficiency: MAE = {eff_base_mae:.5f} kWh/km")
    print(f"XGBoost Efficiency:  MAE = {eff_model_mae:.5f} kWh/km")
    print(f"Efficiency MAE Improvement: {eff_improvement_pct:.2f}%")

    # ========================================================
    # 4. Fleet Outlier / Anomaly Detection (> 2 sigma decline)
    # ========================================================
    print("\n--- Detecting Fleet Fast-Degradation Outliers (> 2 sigma) ---")
    df["annual_decline_rate"] = (1.0 - df["true_soh"]) / df["years_of_service"].clip(lower=0.5)
    df["age_bucket"] = pd.cut(df["years_of_service"], bins=[0, 1.5, 2.5, 5.0], labels=["0-1.5yr", "1.5-2.5yr", "2.5yr+"])

    anomalies = []
    for (model_name, age_b), group in df.groupby(["model_name", "age_bucket"], observed=False):
        mean_rate = group["annual_decline_rate"].mean()
        std_rate = group["annual_decline_rate"].std()
        threshold = mean_rate + 2.0 * std_rate

        outliers = group[group["annual_decline_rate"] > threshold]
        for _, row in outliers.head(5).iterrows():
            anomalies.append({
                "vin": row["vin"],
                "model_name": row["model_name"],
                "oem": row["oem"],
                "age_years": row["years_of_service"],
                "annual_decline_rate": round(row["annual_decline_rate"] * 100, 2),
                "peer_mean_rate": round(mean_rate * 100, 2),
                "peer_std_rate": round(std_rate * 100, 2),
                "sigma_deviation": round((row["annual_decline_rate"] - mean_rate) / std_rate, 2),
                "alert_type": "FAST_DEGRADATION"
            })

    print(f"Total flagged FAST_DEGRADATION anomaly candidates: {len(anomalies)}")

    # ========================================================
    # 5. 12-Dimensional Degradation Profile Vector
    # ========================================================
    print("\n--- Generating 12-Dimensional Degradation Profile Vectors ---")
    # Features:
    # 1. est_capacity_ratio
    # 2. obs_dc_fast_share
    # 3. obs_avg_temp_c / 40.0
    # 4. obs_max_temp_c / 50.0
    # 5. cycles / 200.0
    # 6. odo_km / 100000.0
    # 7. years_of_service / 5.0
    # 8. obs_kwh_per_km / 0.30
    # 9. deep_discharge_share
    # 10. (1.0 - true_soh) * 10.0
    # 11. 1.0 - obs_dc_fast_share
    # 12. (cycles / years_of_service) / 100.0
    sample_vins = df["vin"].head(10).tolist()
    sample_vectors = {}
    for _, row in df.head(10).iterrows():
        vec = [
            float(row["est_capacity_ratio"]),
            float(row["obs_dc_fast_share"]),
            float(row["obs_avg_temp_c"] / 40.0),
            float(row["obs_max_temp_c"] / 50.0),
            float(row["cycles"] / 200.0),
            float(row["odo_km"] / 100000.0),
            float(row["years_of_service"] / 5.0),
            float(row["obs_kwh_per_km"] / 0.30),
            float(row["deep_discharge_share"]),
            float((1.0 - row["true_soh"]) * 10.0),
            float(1.0 - row["obs_dc_fast_share"]),
            float((row["cycles"] / max(0.1, row["years_of_service"])) / 100.0),
        ]
        # Normalize vector for cosine distance
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = [round(x / norm, 5) for x in vec]
        sample_vectors[row["vin"]] = vec

    # ========================================================
    # 6. Save Artifacts & Evidence
    # ========================================================
    os.makedirs("services/ml/models", exist_ok=True)
    os.makedirs("tests/evidence/p3", exist_ok=True)

    # Save XGBoost models in JSON format
    soh_model_path = "services/ml/models/soh_model.json"
    eff_model_path = "services/ml/models/efficiency_model.json"
    soh_model.save_model(soh_model_path)
    eff_model.save_model(eff_model_path)
    print(f"Saved SoH model to {soh_model_path}")
    print(f"Saved Efficiency model to {eff_model_path}")

    # Save metadata
    metadata = {
        "soh_features": soh_features,
        "efficiency_features": eff_features,
        "soh_metrics": {
            "baseline_mae": round(base_mae, 4),
            "baseline_rmse": round(base_rmse, 4),
            "baseline_r2": round(base_r2, 4),
            "model_mae": round(model_mae, 4),
            "model_rmse": round(model_rmse, 4),
            "model_r2": round(model_r2, 4),
            "improvement_pct": round(improvement_pct, 2),
        },
        "efficiency_metrics": {
            "baseline_mae": round(eff_base_mae, 5),
            "model_mae": round(eff_model_mae, 5),
            "improvement_pct": round(eff_improvement_pct, 2),
        },
        "per_oem_metrics": per_oem_metrics,
        "feature_importances": feature_importances,
        "train_vehicles": len(train_df),
        "test_vehicles": len(test_df),
        "total_anomalies_flagged": len(anomalies),
        "training_time_seconds": round(time.time() - t_start, 2),
    }

    meta_path = "services/ml/models/model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Evidence reports
    evidence_json = "tests/evidence/p3/ml_eval_report.json"
    with open(evidence_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    evidence_txt = "tests/evidence/p3/ml_eval_report.txt"
    with open(evidence_txt, "w", encoding="utf-8") as f:
        f.write("Phase 3 ML Battery Health & Efficiency Evaluation Report\n")
        f.write("=======================================================\n")
        f.write(f"Total Fleet Vehicles: {len(df):,}\n")
        f.write(f"Grouped Split: {len(train_df):,} Train / {len(test_df):,} Holdout Test (Zero overlap)\n\n")
        f.write("1. State of Health (SoH %) Model Results:\n")
        f.write(f"   Baseline linear(age, odo) MAE : {base_mae:.4f}%\n")
        f.write(f"   XGBoost Regressor MAE         : {model_mae:.4f}%\n")
        f.write(f"   XGBoost Regressor RMSE        : {model_rmse:.4f}%\n")
        f.write(f"   XGBoost Regressor R2          : {model_r2:.4f}\n")
        f.write(f"   Relative MAE Improvement      : {improvement_pct:.2f}% (Acceptance: >= 30% - PASSED)\n\n")
        f.write("2. Per-OEM Breakdown:\n")
        for oem, m in per_oem_metrics.items():
            f.write(f"   - {oem:12s}: Model MAE = {m['model_mae']:.4f}% | Baseline MAE = {m['baseline_mae']:.4f}% | Improvement = {m['improvement_pct']}%\n")
        f.write("\n3. Feature Importances:\n")
        for feat, imp in sorted(feature_importances.items(), key=lambda x: x[1], reverse=True):
            f.write(f"   - {feat:22s}: {imp:.4f}\n")
        f.write(f"\n4. Energy Efficiency (kWh/km) Results:\n")
        f.write(f"   Baseline Rated MAE            : {eff_base_mae:.5f} kWh/km\n")
        f.write(f"   XGBoost Regressor MAE         : {eff_model_mae:.5f} kWh/km\n")
        f.write(f"   Relative MAE Improvement      : {eff_improvement_pct:.2f}%\n")
        f.write(f"\n5. Fast Degradation Anomalies Flagged: {len(anomalies):,} vehicles (> 2 sigma decline)\n")
        f.write(f"   Sample Anomaly: VIN {anomalies[0]['vin']} ({anomalies[0]['model_name']}, {anomalies[0]['oem']}) - {anomalies[0]['sigma_deviation']} sigma\n")

    print(f"\nEvaluation evidence written to {evidence_txt} and {evidence_json}")
    return metadata


if __name__ == "__main__":
    train_and_evaluate()
