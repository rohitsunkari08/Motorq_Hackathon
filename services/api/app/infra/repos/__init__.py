from services.api.app.infra.repos.user_repo import user_repo, UserRepo
from services.api.app.infra.repos.fleet_repo import fleet_repo, FleetRepo
from services.api.app.infra.repos.vehicle_repo import vehicle_repo, VehicleRepo
from services.api.app.infra.repos.alert_repo import alert_repo, AlertRepo
from services.api.app.infra.repos.charger_repo import charger_repo, ChargerRepo
from services.api.app.infra.repos.plan_repo import plan_repo, PlanRepo
from services.api.app.infra.repos.audit_repo import audit_repo, AuditRepo
from services.api.app.infra.repos.telemetry_repo import telemetry_repo, TelemetryRepo

__all__ = [
    "user_repo", "UserRepo",
    "fleet_repo", "FleetRepo",
    "vehicle_repo", "VehicleRepo",
    "alert_repo", "AlertRepo",
    "charger_repo", "ChargerRepo",
    "plan_repo", "PlanRepo",
    "audit_repo", "AuditRepo",
    "telemetry_repo", "TelemetryRepo",
]
