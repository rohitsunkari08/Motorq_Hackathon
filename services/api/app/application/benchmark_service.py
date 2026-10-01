"""Differential Privacy Benchmark Application Service
Provides privacy-safe peer SoH averages using Laplace perturbation and k-anonymity.
"""

from typing import Dict, Any, Optional
from services.api.app.infra.repos.vehicle_repo import vehicle_repo
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.domain.benchmark.differential_privacy import dp_benchmark
from services.api.app.api.dto.problem import RateLimitExceededException, BadRequestException
from services.api.app.api.dto.benchmark import SohBenchmarkResponse


class BenchmarkService:
    def _parse_age_bucket(self, age_bucket: str) -> tuple[int, int]:
        current_year = 2026
        bucket = age_bucket.lower().strip()
        if bucket in ("0-1", "0-1yr", "0-1y", "<1"):
            return current_year - 1, current_year
        elif bucket in ("1-2", "1-2yr", "1-2y"):
            return current_year - 2, current_year - 1
        elif bucket in ("2-3", "2-3yr", "2-3y"):
            return current_year - 3, current_year - 2
        elif bucket in ("3+", "3-5", ">3"):
            return current_year - 10, current_year - 3
        else:
            return 2018, 2026

    async def get_soh_benchmark(
        self,
        model: str,
        age_bucket: str,
        tenant_id: int,
        actor: str,
        epsilon: float = 1.0,
    ) -> SohBenchmarkResponse:
        # Check and consume tenant DP budget
        allowed = dp_benchmark.consume_budget(tenant_id, epsilon)
        if not allowed:
            remaining = dp_benchmark.get_remaining_budget(tenant_id)
            raise RateLimitExceededException(
                detail=f"Differential privacy budget exhausted for tenant {tenant_id} (remaining={remaining} epsilon)",
                retry_after=86400,
            )

        min_year, max_year = self._parse_age_bucket(age_bucket)
        soh_values = await vehicle_repo.get_soh_by_model_and_age(model, min_year, max_year)

        dp_result = dp_benchmark.compute_dp_mean_soh(soh_values, epsilon=epsilon)
        remaining_budget = dp_benchmark.get_remaining_budget(tenant_id)

        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="query_dp_benchmark",
            resource=f"benchmark:{model}:{age_bucket}",
            detail={
                "epsilon": epsilon,
                "sample_size": dp_result["sample_size"],
                "suppressed": dp_result["suppressed"],
            },
        )

        return SohBenchmarkResponse(
            model=model,
            age_bucket=age_bucket,
            sample_size=dp_result["sample_size"],
            suppressed=dp_result["suppressed"],
            suppression_reason=dp_result["suppression_reason"],
            dp_mean_soh_pct=dp_result["dp_mean_soh_pct"],
            epsilon=dp_result["epsilon"],
            sensitivity=dp_result["sensitivity"],
            k_anonymity_floor=dp_benchmark.k_anonymity_floor,
            budget_remaining=round(remaining_budget, 2),
        )


benchmark_service = BenchmarkService()
