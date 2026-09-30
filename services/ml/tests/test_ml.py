"""Unit Tests for Machine Learning Service
Verifies:
- Model loading from JSON artifacts
- SoH prediction bounds and sensibility
- Efficiency prediction
- 12-dimensional degradation embeddings for pgvector
"""

import pytest
import numpy as np
from services.ml.inference import MLPredictor, get_ml_predictor


@pytest.fixture
def predictor():
    return get_ml_predictor()


def test_predict_soh_bounds(predictor):
    # Healthy vehicle
    healthy_features = {
        "est_capacity_ratio": 0.99,
        "obs_dc_fast_share": 0.15,
        "obs_avg_temp_c": 21.0,
        "obs_max_temp_c": 30.0,
        "cycles": 35.0,
        "odo_km": 12000.0,
        "years_of_service": 0.8,
        "obs_kwh_per_km": 0.175,
        "deep_discharge_share": 0.05,
        "battery_kwh": 75.0,
    }
    pred_healthy = predictor.predict_soh_pct(healthy_features)
    assert 92.0 <= pred_healthy <= 100.0

    # Heavily degraded vehicle
    degraded_features = {
        "est_capacity_ratio": 0.82,
        "obs_dc_fast_share": 0.60,
        "obs_avg_temp_c": 32.0,
        "obs_max_temp_c": 46.0,
        "cycles": 180.0,
        "odo_km": 75000.0,
        "years_of_service": 3.4,
        "obs_kwh_per_km": 0.22,
        "deep_discharge_share": 0.35,
        "battery_kwh": 75.0,
    }
    pred_degraded = predictor.predict_soh_pct(degraded_features)
    assert 70.0 <= pred_degraded <= 94.0
    assert pred_healthy > pred_degraded


def test_predict_efficiency(predictor):
    features = {
        "base_eff_kwh_km": 0.178,
        "obs_avg_temp_c": 22.0,
        "obs_kwh_per_km": 0.181,
        "battery_kwh": 75.0,
        "years_of_service": 1.2,
    }
    eff = predictor.predict_efficiency(features)
    assert 0.10 <= eff <= 0.30


def test_degradation_embedding_12d(predictor):
    features = {
        "est_capacity_ratio": 0.95,
        "obs_dc_fast_share": 0.25,
        "obs_avg_temp_c": 22.0,
        "obs_max_temp_c": 35.0,
        "cycles": 50.0,
        "odo_km": 20000.0,
        "years_of_service": 1.5,
        "obs_kwh_per_km": 0.18,
        "deep_discharge_share": 0.10,
        "soh_pct": 96.0,
    }
    vec = predictor.get_degradation_embedding_12d(features)
    assert len(vec) == 12
    # Verify unit norm
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 0.01
