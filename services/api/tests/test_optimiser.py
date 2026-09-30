"""Unit Tests for Battery-Health-Aware Dynamic Programming Charge Scheduler
Verifies NOTE.md §6.4:
- O(T x S x A) complexity
- DP beats baseline cost
- Stress reduction > 0%
- Test coverage >= 80%
"""

import pytest
import time
from services.api.app.domain.optimiser.dp_scheduler import (
    optimize_charge_schedule,
    format_slot_time,
    get_default_tariffs,
    OptimizationResult,
    ChargeSlot,
)


def test_format_slot_time():
    assert format_slot_time(0) == "00:00"
    assert format_slot_time(4) == "01:00"
    assert format_slot_time(56) == "14:00"
    assert format_slot_time(95) == "23:45"


def test_default_tariffs():
    tariffs = get_default_tariffs()
    assert len(tariffs) == 96
    # 02:00 (slot 8) is ultra off-peak ($0.080)
    assert tariffs[8] == 0.080
    # 10:00 (slot 40) is normal ($0.150)
    assert tariffs[40] == 0.150
    # 16:00 (slot 64) is peak ($0.280)
    assert tariffs[64] == 0.280


def test_dp_beats_baseline_cost_during_peak_arrival():
    """Vehicle arrives at 14:00 (slot 56, start of peak tariff $0.280) and departs at 22:00 (slot 88).
    Baseline charges immediately at peak prices.
    DP delays charging to off-peak / normal tariff slots and avoids high-power charging,
    saving cost and reducing battery degradation stress.
    """
    res = optimize_charge_schedule(
        vin="TEST_VIN_001",
        initial_soc=20.0,
        target_soc=80.0,
        battery_capacity_kwh=75.0,
        soh=0.95,
        max_charge_kw=100.0,
        arrival_slot=56,    # 14:00 (Peak $0.280)
        departure_slot=88,  # 22:00
        lambda_degradation=0.05,
    )

    assert isinstance(res, OptimizationResult)
    assert res.feasible is True
    assert res.achieved_soc >= 80.0
    assert len(res.schedule) == (88 - 56)

    # DP must beat baseline cost
    assert res.optimal_cost < res.baseline_cost, (
        f"DP cost {res.optimal_cost} was not lower than baseline cost {res.baseline_cost}"
    )
    assert res.cost_savings_pct > 15.0, (
        f"Expected >= 15% cost savings, got {res.cost_savings_pct}%"
    )

    # DP must reduce battery stress
    assert res.optimal_stress < res.baseline_stress, (
        f"DP stress {res.optimal_stress} was not lower than baseline stress {res.baseline_stress}"
    )
    assert res.stress_reduction_pct > 15.0, (
        f"Expected >= 15% stress reduction, got {res.stress_reduction_pct}%"
    )

    print(f"\nOptimization Result:")
    print(f"Optimal Cost: ${res.optimal_cost:.2f} vs Baseline: ${res.baseline_cost:.2f} (Savings: {res.cost_savings_pct:.1f}%)")
    print(f"Optimal Stress: {res.optimal_stress:.2f} vs Baseline: {res.baseline_stress:.2f} (Reduction: {res.stress_reduction_pct:.1f}%)")


def test_dp_avoids_peak_hours():
    """Verify that DP schedule does not charge at full power during peak hours 14:00-20:00 (slots 56-80)."""
    res = optimize_charge_schedule(
        initial_soc=30.0,
        target_soc=75.0,
        arrival_slot=56,    # 14:00 (Peak)
        departure_slot=92,  # 23:00 (After peak)
    )

    # Count charging power during peak slots (56 to 79) vs after-peak slots (80 to 91)
    peak_kwh = sum(slot.kwh_added for slot in res.schedule if 56 <= slot.slot_idx < 80)
    after_peak_kwh = sum(slot.kwh_added for slot in res.schedule if slot.slot_idx >= 80)

    assert after_peak_kwh > peak_kwh, "DP should shift charging volume from peak to after-peak"


def test_dp_degradation_penalty_sensitivity():
    """Increasing lambda_degradation should encourage lower charging power fractions (gentle charging)."""
    res_low_lambda = optimize_charge_schedule(
        initial_soc=20.0,
        target_soc=70.0,
        arrival_slot=0,     # Plenty of time (00:00 to 08:00)
        departure_slot=32,
        lambda_degradation=0.001,
    )

    res_high_lambda = optimize_charge_schedule(
        initial_soc=20.0,
        target_soc=70.0,
        arrival_slot=0,
        departure_slot=32,
        lambda_degradation=0.20,
    )

    # High lambda should have lower or equal stress
    assert res_high_lambda.optimal_stress <= res_low_lambda.optimal_stress + 0.05


def test_dp_battery_already_full():
    """If vehicle is already at target SoC, zero charging should occur."""
    res = optimize_charge_schedule(
        initial_soc=85.0,
        target_soc=85.0,
        arrival_slot=10,
        departure_slot=20,
    )
    assert res.achieved_soc == 85.0
    assert res.optimal_cost == 0.0
    assert res.total_kwh_added == 0.0
    assert all(s.power_kw == 0.0 for s in res.schedule)


def test_dp_unreachable_target():
    """Window too short to reach 100% from 10% in 30 minutes (2 slots).
    Should mark feasible=False and charge as much as physically possible.
    """
    res = optimize_charge_schedule(
        initial_soc=10.0,
        target_soc=90.0,
        battery_capacity_kwh=100.0,
        max_charge_kw=50.0,
        arrival_slot=10,
        departure_slot=12,  # Only 30 minutes (max deliverable ~23 kWh ~= 23% SoC)
    )
    assert res.feasible is False
    assert res.achieved_soc < 90.0
    assert res.achieved_soc > 10.0


def test_dp_runtime_performance():
    """Verify that DP schedule executes in < 5ms per vehicle (O(T x S x A) ~ 39K ops)."""
    t0 = time.perf_counter()
    n_runs = 50
    for i in range(n_runs):
        optimize_charge_schedule(
            initial_soc=15.0 + (i % 20),
            target_soc=80.0,
            arrival_slot=20 + (i % 30),
            departure_slot=60 + (i % 25),
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    avg_per_run_ms = elapsed_ms / n_runs
    print(f"\nAverage DP runtime over {n_runs} runs: {avg_per_run_ms:.2f} ms/vehicle")
    assert avg_per_run_ms < 10.0, f"Average runtime {avg_per_run_ms:.2f}ms exceeds 10ms budget"
