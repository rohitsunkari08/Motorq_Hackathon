"""Differential Privacy (DP) Benchmark Domain Module
Implements NOTE.md §7 / §12:
- Peer average SoH by (model, age bucket)
- Laplace mechanism with scale b = sensitivity / epsilon = (100 / n) / epsilon
- Bounded values [0, 100] => sensitivity = 100 / n
- k-anonymity floor: suppress groups where n < 20
- Tenant privacy budget tracking (cumulative epsilon budget)
"""

import math
from typing import Dict, Any, Optional, Tuple, List
import numpy as np


class DifferentialPrivacyBenchmark:
    def __init__(
        self,
        default_epsilon: float = 1.0,
        k_anonymity_floor: int = 20,
        tenant_budget: float = 20.0,
    ):
        self.default_epsilon = default_epsilon
        self.k_anonymity_floor = k_anonymity_floor
        self.tenant_budget = tenant_budget
        # In-memory tenant budget tracker: tenant_id -> consumed_epsilon
        self._tenant_consumed_budget: Dict[int, float] = {}

    def get_remaining_budget(self, tenant_id: int) -> float:
        consumed = self._tenant_consumed_budget.get(tenant_id, 0.0)
        return max(0.0, self.tenant_budget - consumed)

    def consume_budget(self, tenant_id: int, epsilon: float) -> bool:
        """Attempts to consume epsilon from tenant's privacy budget.
        Returns True if successful, False if budget exceeded.
        """
        remaining = self.get_remaining_budget(tenant_id)
        if remaining < epsilon:
            return False
        self._tenant_consumed_budget[tenant_id] = self._tenant_consumed_budget.get(tenant_id, 0.0) + epsilon
        return True

    def calculate_sensitivity(self, n: int, val_min: float = 0.0, val_max: float = 100.0) -> float:
        """Computes L1 sensitivity of sample mean for bounded values."""
        if n <= 0:
            return float("inf")
        return (val_max - val_min) / float(n)

    def calculate_laplace_scale(self, n: int, epsilon: float, val_min: float = 0.0, val_max: float = 100.0) -> float:
        """Scale parameter b = sensitivity / epsilon = (val_max - val_min) / (n * epsilon)."""
        sensitivity = self.calculate_sensitivity(n, val_min, val_max)
        if epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        return sensitivity / epsilon

    def sample_laplace_noise(self, scale: float, seed: Optional[int] = None) -> float:
        """Draws a sample from Laplace(0, scale)."""
        rng = np.random.default_rng(seed)
        return float(rng.laplace(0.0, scale))

    def compute_dp_mean_soh(
        self,
        soh_values: List[float],
        epsilon: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Computes differentially private mean SoH with k-anonymity suppression.
        Returns:
            Dictionary containing:
            - suppressed (bool)
            - sample_size (int)
            - dp_mean_soh_pct (float or None)
            - true_mean (float or None for auditing)
            - epsilon (float)
            - sensitivity (float)
            - noise_added (float)
        """
        eps = epsilon or self.default_epsilon
        n = len(soh_values)

        if n < self.k_anonymity_floor:
            return {
                "suppressed": True,
                "suppression_reason": f"Sample size n={n} is below k-anonymity floor (k={self.k_anonymity_floor})",
                "sample_size": n,
                "dp_mean_soh_pct": None,
                "epsilon": eps,
                "sensitivity": self.calculate_sensitivity(max(1, n)),
                "noise_added": 0.0,
            }

        true_mean = float(np.mean(soh_values))
        sensitivity = self.calculate_sensitivity(n)
        scale = self.calculate_laplace_scale(n, eps)
        noise = self.sample_laplace_noise(scale, seed=seed)

        # Perturbed and bounded mean
        noisy_mean = float(np.clip(true_mean + noise, 0.0, 100.0))

        return {
            "suppressed": False,
            "suppression_reason": None,
            "sample_size": n,
            "dp_mean_soh_pct": round(noisy_mean, 2),
            "true_mean": round(true_mean, 2),
            "epsilon": eps,
            "sensitivity": round(sensitivity, 5),
            "noise_added": round(noise, 5),
        }


dp_benchmark = DifferentialPrivacyBenchmark()
