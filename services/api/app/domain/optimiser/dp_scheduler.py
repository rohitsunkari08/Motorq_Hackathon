"""Battery-Health-Aware Dynamic Programming Charge Scheduler
Implements NOTE.md §6.4:
- 15-min slots over horizon <=24h (T<=96)
- SoC states 0..100% in 1% steps
- actions = power level in {0, 1/3, 2/3, 1} x min(charger_kw, vehicle max_dc, AC limit)
- transition adds kWh
- cost = tariff(slot) x kWh + lambda x degradation_penalty(kW/maxkW)^2 x kWh
- constraint: soc(departure) >= target, plugged window [arrive, depart]
- backtrack to schedule
- baseline = full power from arrival (charge-on-arrival)
- Output: plan, cost, baseline cost, savings %, stress reduction %
- Complexity: O(T x S x A) = 96 x 101 x 4 ~ 39K ops; < 5ms per vehicle
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import math


@dataclass
class ChargeSlot:
    slot_idx: int
    time_str: str
    power_kw: float
    power_fraction: float
    kwh_added: float
    soc_start: float
    soc_end: float
    tariff_price: float
    slot_cost: float
    slot_stress: float


@dataclass
class OptimizationResult:
    vin: str
    initial_soc: float
    target_soc: float
    achieved_soc: float
    arrival_time_str: str
    departure_time_str: str
    schedule: List[ChargeSlot]
    total_kwh_added: float
    optimal_cost: float
    baseline_cost: float
    cost_savings_pct: float
    optimal_stress: float
    baseline_stress: float
    stress_reduction_pct: float
    feasible: bool
    runtime_ms: float
    meta: Dict[str, Any] = field(default_factory=dict)


def format_slot_time(slot_idx: int) -> str:
    total_minutes = (slot_idx * 15) % 1440
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def get_default_tariffs() -> List[float]:
    """Default 24-hour commercial TOU tariff in 96 15-minute slots:
    - 00:00 - 06:00: Ultra Off-Peak ($0.080/kWh)
    - 06:00 - 14:00: Normal ($0.150/kWh)
    - 14:00 - 20:00: Peak ($0.280/kWh)
    - 20:00 - 24:00: Normal ($0.140/kWh)
    """
    tariffs = []
    for slot in range(96):
        hour = slot // 4
        if 0 <= hour < 6:
            tariffs.append(0.080)
        elif 6 <= hour < 14:
            tariffs.append(0.150)
        elif 14 <= hour < 20:
            tariffs.append(0.280)
        else:
            tariffs.append(0.140)
    return tariffs


def optimize_charge_schedule(
    vin: str = "SYNTHETIC_EV",
    initial_soc: float = 20.0,
    target_soc: float = 85.0,
    battery_capacity_kwh: float = 75.0,
    soh: float = 0.95,
    max_charge_kw: float = 100.0,
    arrival_slot: int = 56,     # e.g. 14:00 (peak start)
    departure_slot: int = 88,   # e.g. 22:00 (departure after peak)
    tariffs: Optional[List[float]] = None,
    lambda_degradation: float = 0.05,
    charger_efficiency: float = 0.92,
) -> OptimizationResult:
    """Solves the battery-health-aware charge scheduling DP."""
    t_start = time.perf_counter()

    if tariffs is None or len(tariffs) < 96:
        tariffs = get_default_tariffs()

    # Boundaries validation
    initial_soc = max(0.0, min(100.0, float(initial_soc)))
    target_soc = max(initial_soc, min(100.0, float(target_soc)))
    arrival_slot = max(0, min(95, arrival_slot))
    departure_slot = max(arrival_slot + 1, min(96, departure_slot))

    effective_capacity = max(1.0, battery_capacity_kwh * soh)
    slot_hours = 0.25  # 15 minutes = 0.25 hour

    # Discrete power action fractions per §6.4: {0, 1/3, 2/3, 1}
    action_fractions = [0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0]

    # Precalculate step impact for each action
    # power_kw, kwh_delivered, delta_soc_float, stress_penalty
    action_info = []
    for frac in action_fractions:
        p_kw = frac * max_charge_kw
        kwh = p_kw * slot_hours * charger_efficiency
        delta_soc = (kwh / effective_capacity) * 100.0
        # Battery degradation proxy: (kW / max_kw)^2 * kWh
        stress_proxy = (frac ** 2) * kwh
        action_info.append((p_kw, frac, kwh, delta_soc, stress_proxy))

    num_slots = departure_slot - arrival_slot
    # State space: integer SoC 0..100 (101 states)
    # Forward DP: dp[t_idx][soc] = min cost to reach this state
    inf = float('inf')
    dp = [[inf] * 101 for _ in range(num_slots + 1)]
    # parent[t_idx][soc] = (prev_soc, action_idx)
    parent = [[None] * 101 for _ in range(num_slots + 1)]

    init_state = int(round(initial_soc))
    dp[0][init_state] = 0.0

    for step in range(num_slots):
        cur_slot = arrival_slot + step
        tariff_price = tariffs[cur_slot]

        for s in range(101):
            cur_cost = dp[step][s]
            if cur_cost == inf:
                continue

            for a_idx, (p_kw, frac, kwh, delta_soc, stress_proxy) in enumerate(action_info):
                next_s = min(100, int(round(s + delta_soc)))

                # If battery is already at 100%, cannot charge further
                if s == 100 and frac > 0.0:
                    continue

                # Step cost: tariff * kWh + lambda * stress
                step_cost = (tariff_price * kwh) + (lambda_degradation * stress_proxy)
                new_cost = cur_cost + step_cost

                if new_cost < dp[step + 1][next_s]:
                    dp[step + 1][next_s] = new_cost
                    parent[step + 1][next_s] = (s, a_idx)

    # Find the best terminal state at departure that meets target_soc
    target_int = int(round(target_soc))
    best_final_s = -1
    best_cost = inf

    # First attempt: meets target_soc
    for s in range(target_int, 101):
        if dp[num_slots][s] < best_cost:
            best_cost = dp[num_slots][s]
            best_final_s = s

    feasible = True
    # If target is unreachable within plugged window, take max reachable SoC
    if best_final_s == -1:
        feasible = False
        for s in range(100, -1, -1):
            if dp[num_slots][s] < inf:
                best_cost = dp[num_slots][s]
                best_final_s = s
                break

    if best_final_s == -1:
        best_final_s = init_state
        best_cost = 0.0

    # Backtrack schedule
    schedule: List[ChargeSlot] = []
    curr_s = best_final_s

    total_kwh_optimal = 0.0
    total_tariff_cost_optimal = 0.0
    total_stress_optimal = 0.0

    reversed_slots = []
    for step in range(num_slots, 0, -1):
        p_info = parent[step][curr_s]
        if p_info is None:
            # Fallback if no parent recorded
            prev_s = curr_s
            a_idx = 0
        else:
            prev_s, a_idx = p_info

        p_kw, frac, kwh, delta_soc, stress_proxy = action_info[a_idx]
        cur_slot_idx = arrival_slot + (step - 1)
        tariff_price = tariffs[cur_slot_idx]
        slot_tariff_cost = tariff_price * kwh

        total_kwh_optimal += kwh
        total_tariff_cost_optimal += slot_tariff_cost
        total_stress_optimal += stress_proxy

        slot_item = ChargeSlot(
            slot_idx=cur_slot_idx,
            time_str=format_slot_time(cur_slot_idx),
            power_kw=round(p_kw, 2),
            power_fraction=round(frac, 3),
            kwh_added=round(kwh, 3),
            soc_start=float(prev_s),
            soc_end=float(curr_s),
            tariff_price=tariff_price,
            slot_cost=round(slot_tariff_cost, 4),
            slot_stress=round(stress_proxy, 4),
        )
        reversed_slots.append(slot_item)
        curr_s = prev_s

    schedule = list(reversed(reversed_slots))

    # Compute Baseline: "Charge-on-Arrival" at full power (fraction = 1.0)
    baseline_cur_soc = initial_soc
    baseline_tariff_cost = 0.0
    baseline_stress = 0.0
    baseline_kwh = 0.0

    for step in range(num_slots):
        cur_slot_idx = arrival_slot + step
        tariff_price = tariffs[cur_slot_idx]

        if baseline_cur_soc < target_soc:
            # Charge at max power
            p_kw = max_charge_kw
            kwh = p_kw * slot_hours * charger_efficiency
            delta_soc = (kwh / effective_capacity) * 100.0

            # Trim to target_soc if overshooting
            if baseline_cur_soc + delta_soc > target_soc:
                needed_soc = target_soc - baseline_cur_soc
                needed_kwh = (needed_soc / 100.0) * effective_capacity
                kwh = max(0.0, needed_kwh)
                delta_soc = needed_soc

            baseline_cur_soc += delta_soc
            baseline_kwh += kwh
            baseline_tariff_cost += tariff_price * kwh
            baseline_stress += (1.0 ** 2) * kwh
        else:
            # Idle
            pass

    # Ensure baseline is non-zero to avoid division by zero
    if baseline_tariff_cost <= 0.001:
        cost_savings_pct = 0.0
    else:
        cost_savings_pct = round(max(0.0, (baseline_tariff_cost - total_tariff_cost_optimal) / baseline_tariff_cost * 100.0), 2)

    if baseline_stress <= 0.001:
        stress_reduction_pct = 0.0
    else:
        stress_reduction_pct = round(max(0.0, (baseline_stress - total_stress_optimal) / baseline_stress * 100.0), 2)

    runtime_ms = (time.perf_counter() - t_start) * 1000.0

    return OptimizationResult(
        vin=vin,
        initial_soc=round(initial_soc, 2),
        target_soc=round(target_soc, 2),
        achieved_soc=float(best_final_s),
        arrival_time_str=format_slot_time(arrival_slot),
        departure_time_str=format_slot_time(departure_slot),
        schedule=schedule,
        total_kwh_added=round(total_kwh_optimal, 2),
        optimal_cost=round(total_tariff_cost_optimal, 2),
        baseline_cost=round(baseline_tariff_cost, 2),
        cost_savings_pct=cost_savings_pct,
        optimal_stress=round(total_stress_optimal, 2),
        baseline_stress=round(baseline_stress, 2),
        stress_reduction_pct=stress_reduction_pct,
        feasible=feasible,
        runtime_ms=round(runtime_ms, 3),
        meta={
            "battery_capacity_kwh": battery_capacity_kwh,
            "soh": soh,
            "effective_capacity_kwh": round(effective_capacity, 2),
            "max_charge_kw": max_charge_kw,
            "arrival_slot": arrival_slot,
            "departure_slot": departure_slot,
            "plugged_duration_hours": round(num_slots * 0.25, 2),
            "lambda_degradation": lambda_degradation,
        }
    )
