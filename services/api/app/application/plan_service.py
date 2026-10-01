"""Charge Plan Application Service
Orchestrates Dynamic Programming charge schedule optimization and approval workflow.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from services.api.app.infra.repos.plan_repo import plan_repo
from services.api.app.infra.repos.vehicle_repo import vehicle_repo
from services.api.app.infra.repos.charger_repo import charger_repo
from services.api.app.infra.repos.audit_repo import audit_repo
from services.api.app.infra.redis import redis_client
from services.api.app.domain.optimiser.dp_scheduler import optimize_charge_schedule
from services.api.app.api.dto.problem import NotFoundException, ForbiddenException, BadRequestException
from services.api.app.api.dto.plan import ChargePlanDto, ApproveRejectResponse, SlotActionDto


class PlanService:
    async def propose_plan(
        self,
        vin: str,
        charger_id: int,
        target_soc: float,
        departure_hours_ahead: float,
        current_soc_override: Optional[float],
        tenant_id: int,
        user_role: str,
        actor: str,
    ) -> ChargePlanDto:
        bypass_rls = (user_role == "admin")
        v = await vehicle_repo.get_vehicle_by_vin(vin, tenant_id, bypass_rls=bypass_rls)
        if not v:
            raise NotFoundException(detail=f"Vehicle {vin} not found")

        ch = await charger_repo.get_charger_by_id(charger_id)
        if not ch:
            raise NotFoundException(detail=f"Charger {charger_id} not found")

        # Determine start SoC
        if current_soc_override is not None:
            soc_start = current_soc_override
        else:
            latest = await redis_client.get_vehicle_latest_state(vin)
            soc_start = float(latest["soc_pct"]) if "soc_pct" in latest else 25.0

        if target_soc <= soc_start:
            raise BadRequestException(
                detail=f"Target SoC ({target_soc}%) must be greater than starting SoC ({soc_start}%)"
            )

        now = datetime.now(timezone.utc)
        arrival_slot = (now.hour * 4) + (now.minute // 15)
        slot_span = max(4, int(departure_hours_ahead * 4))
        departure_slot = min(96, arrival_slot + slot_span)
        if departure_slot <= arrival_slot:
            departure_slot = min(96, arrival_slot + 12)

        max_kw = min(float(ch["power_kw"]), float(v["max_dc_kw"]))
        soh_val = float(v["latest_soh_pct"]) / 100.0 if v.get("latest_soh_pct") else 0.96

        # Run DP Optimization
        dp_result = optimize_charge_schedule(
            vin=vin,
            initial_soc=soc_start,
            target_soc=target_soc,
            battery_capacity_kwh=float(v["battery_kwh"]),
            soh=soh_val,
            max_charge_kw=max_kw,
            arrival_slot=arrival_slot,
            departure_slot=departure_slot,
        )

        start_ts = now
        end_ts = now + timedelta(hours=departure_hours_ahead)

        db_plan = await plan_repo.create_plan(
            vin=vin,
            charger_id=charger_id,
            start_ts=start_ts,
            end_ts=end_ts,
            target_soc=target_soc,
            est_cost=dp_result.optimal_cost,
            baseline_cost=dp_result.baseline_cost,
            proposed_by=actor,
            tenant_id=tenant_id,
            bypass_rls=bypass_rls,
        )

        schedule_dtos = [
            SlotActionDto(
                slot_index=s.slot_idx,
                slot_start=now + timedelta(minutes=15 * (s.slot_idx - arrival_slot)),
                tariff_price_per_kwh=s.tariff_price,
                action_power_kw=s.power_kw,
                soc_start=s.soc_start,
                soc_end=s.soc_end,
                cost_usd=s.slot_cost,
                degradation_penalty_usd=s.slot_stress,
            )
            for s in dp_result.schedule
        ]

        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="propose_charge_plan",
            resource=f"plan:{db_plan['plan_id']}",
            detail={
                "vin": vin,
                "charger_id": charger_id,
                "savings_pct": dp_result.cost_savings_pct,
                "stress_reduction_pct": dp_result.stress_reduction_pct,
            },
        )

        return ChargePlanDto(
            plan_id=db_plan["plan_id"],
            vin=vin,
            charger_id=charger_id,
            start_ts=start_ts,
            end_ts=end_ts,
            target_soc=target_soc,
            est_cost=round(dp_result.optimal_cost, 2),
            baseline_cost=round(dp_result.baseline_cost, 2),
            savings_pct=round(dp_result.cost_savings_pct, 2),
            stress_reduction_pct=round(dp_result.stress_reduction_pct, 2),
            status=db_plan["status"],
            proposed_by=actor,
            schedule=schedule_dtos,
        )

    async def approve_plan(
        self,
        plan_id: int,
        tenant_id: int,
        user_role: str,
        user_id: int,
        actor: str,
    ) -> ApproveRejectResponse:
        if user_role not in ("fleet_manager", "admin"):
            raise ForbiddenException(detail="Only fleet managers and admins can approve charge plans")

        bypass_rls = (user_role == "admin")
        plan = await plan_repo.get_plan_by_id(plan_id, tenant_id, bypass_rls=bypass_rls)
        if not plan:
            raise NotFoundException(detail=f"Charge plan {plan_id} not found")

        updated = await plan_repo.update_plan_status(
            plan_id=plan_id,
            status="approved",
            approved_by=user_id,
            tenant_id=tenant_id,
            bypass_rls=bypass_rls,
        )

        now = datetime.now(timezone.utc)
        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="approve_charge_plan",
            resource=f"plan:{plan_id}",
            detail={"approved_by": user_id, "previous_status": plan["status"]},
        )

        return ApproveRejectResponse(
            plan_id=plan_id,
            status="approved",
            action="approved",
            actor_id=user_id,
            timestamp=now,
        )

    async def reject_plan(
        self,
        plan_id: int,
        tenant_id: int,
        user_role: str,
        user_id: int,
        actor: str,
    ) -> ApproveRejectResponse:
        if user_role not in ("fleet_manager", "admin"):
            raise ForbiddenException(detail="Only fleet managers and admins can reject charge plans")

        bypass_rls = (user_role == "admin")
        plan = await plan_repo.get_plan_by_id(plan_id, tenant_id, bypass_rls=bypass_rls)
        if not plan:
            raise NotFoundException(detail=f"Charge plan {plan_id} not found")

        updated = await plan_repo.update_plan_status(
            plan_id=plan_id,
            status="rejected",
            approved_by=None,
            tenant_id=tenant_id,
            bypass_rls=bypass_rls,
        )

        now = datetime.now(timezone.utc)
        await audit_repo.log_event(
            actor=actor,
            actor_type="user",
            action="reject_charge_plan",
            resource=f"plan:{plan_id}",
            detail={"rejected_by": user_id, "previous_status": plan["status"]},
        )

        return ApproveRejectResponse(
            plan_id=plan_id,
            status="rejected",
            action="rejected",
            actor_id=user_id,
            timestamp=now,
        )


plan_service = PlanService()
