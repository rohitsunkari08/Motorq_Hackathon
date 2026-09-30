"""ML Inference Service for Battery SoH & Efficiency Prediction
Loads trained XGBoost models and exposes inference methods for FastAPI & Agent.
"""

import json
import os
from typing import Dict, Any, List, Optional
import numpy as np
import xgboost as xgb


class MLPredictor:
    def __init__(self, models_dir: str = "services/ml/models"):
        self.models_dir = models_dir
        self.soh_model = xgb.XGBRegressor()
        self.eff_model = xgb.XGBRegressor()

        soh_path = os.path.join(models_dir, "soh_model.json")
        eff_path = os.path.join(models_dir, "efficiency_model.json")
        meta_path = os.path.join(models_dir, "model_metadata.json")

        if os.path.exists(soh_path):
            self.soh_model.load_model(soh_path)
        if os.path.exists(eff_path):
            self.eff_model.load_model(eff_path)

        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

        self.soh_features = self.metadata.get("soh_features", [
            "est_capacity_ratio", "obs_dc_fast_share", "obs_avg_temp_c", "obs_max_temp_c",
            "cycles", "odo_km", "years_of_service", "obs_kwh_per_km", "deep_discharge_share", "battery_kwh"
        ])
        self.eff_features = self.metadata.get("efficiency_features", [
            "base_eff_kwh_km", "obs_avg_temp_c", "obs_kwh_per_km", "battery_kwh", "years_of_service"
        ])

    def predict_soh_pct(self, features: Dict[str, Any]) -> float:
        """Predicts battery State of Health in percent (0 to 100)."""
        row = []
        for feat in self.soh_features:
            row.append(float(features.get(feat, 0.0)))
        x = np.array([row])
        pred = self.soh_model.predict(x)[0]
        return round(float(np.clip(pred, 50.0, 100.0)), 2)

    def predict_efficiency(self, features: Dict[str, Any]) -> float:
        """Predicts energy efficiency in kWh/km."""
        row = []
        for feat in self.eff_features:
            row.append(float(features.get(feat, 0.18)))
        x = np.array([row])
        pred = self.eff_model.predict(x)[0]
        return round(float(max(0.08, pred)), 4)

    def get_degradation_embedding_12d(self, features: Dict[str, Any]) -> List[float]:
        """Generates a 12-dimensional normalized degradation profile vector for pgvector HNSW search."""
        est_cap_ratio = float(features.get("est_capacity_ratio", 0.95))
        dc_fast_share = float(features.get("obs_dc_fast_share", 0.25))
        avg_temp = float(features.get("obs_avg_temp_c", 22.0))
        max_temp = float(features.get("obs_max_temp_c", 35.0))
        cycles = float(features.get("cycles", 50.0))
        odo_km = float(features.get("odo_km", 20000.0))
        age = float(features.get("years_of_service", 1.5))
        kwh_km = float(features.get("obs_kwh_per_km", 0.18))
        deep_disc = float(features.get("deep_discharge_share", 0.10))
        soh_decline = (100.0 - float(features.get("soh_pct", 95.0))) / 10.0

        vec = [
            est_cap_ratio,
            dc_fast_share,
            avg_temp / 40.0,
            max_temp / 50.0,
            cycles / 200.0,
            odo_km / 100000.0,
            age / 5.0,
            kwh_km / 0.30,
            deep_disc,
            soh_decline,
            1.0 - dc_fast_share,
            (cycles / max(0.1, age)) / 100.0
        ]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = [round(float(x / norm), 5) for x in vec]
        return vec


# Module singleton
_predictor = None

def get_ml_predictor() -> MLPredictor:
    global _predictor
    if _predictor is None:
        _predictor = MLPredictor()
    return _predictor
