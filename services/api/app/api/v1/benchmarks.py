"""Differential Privacy Benchmarks Router."""

from fastapi import APIRouter, Depends, Query
from services.api.app.api.deps import get_current_user, TokenClaims, check_rate_limit
from services.api.app.api.dto.benchmark import SohBenchmarkResponse
from services.api.app.application.benchmark_service import benchmark_service

router = APIRouter(prefix="/benchmarks", tags=["Differential Privacy Benchmarks"])


@router.get("/soh", response_model=SohBenchmarkResponse)
async def get_soh_benchmark(
    model: str = Query("Hyper-e", description="Vehicle model name for peer benchmark"),
    age_bucket: str = Query("1-2yr", description="Age bracket (e.g. 0-1yr, 1-2yr, 2-3yr, 3+)"),
    epsilon: float = Query(1.0, ge=0.1, le=5.0, description="Privacy loss parameter epsilon"),
    user: TokenClaims = Depends(get_current_user),
    _rl: bool = Depends(check_rate_limit("dp_benchmark", limit_per_minute=30)),
):
    """Retrieve peer fleet average SoH with Differential Privacy (Laplace noise & k-anonymity suppression)."""
    return await benchmark_service.get_soh_benchmark(
        model=model,
        age_bucket=age_bucket,
        tenant_id=user.tenant_id,
        actor=user.email,
        epsilon=epsilon,
    )
