export type UserRole = 'admin' | 'fleet_manager' | 'viewer';

export interface User {
  user_id: number;
  tenant_id: number;
  email: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface VehicleListItem {
  vin: string;
  oem: string;
  model: string;
  battery_kwh: number;
  rated_range_km: number;
  max_dc_kw: number;
  driver_name?: string;
  latest_soc: number;
  latest_soh: number;
  status: 'active' | 'charging' | 'idle' | 'warning' | 'critical';
}

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor?: string | number | null;
  has_more: boolean;
  total?: number;
}

export interface FleetSummary {
  fleet_id: number;
  name: string;
  tenant_id: number;
  total_vehicles: number;
  active_vehicles: number;
  charging_vehicles: number;
  avg_soc: number;
  avg_soh: number;
  open_alerts: number;
  total_energy_kwh_today: number;
  cost_saved_usd_today: number;
  co2_saved_kg_today: number;
  soh_distribution: Record<string, number>;
}

export interface MapCluster {
  geohash: string;
  lat: number;
  lon: number;
  count: number;
  avg_soc: number;
  critical_count: number;
}

export interface MapVehicle {
  vin: string;
  lat: number;
  lon: number;
  geohash: string;
  soc: number;
  speed_kmh: number;
  status: string;
  is_masked: boolean;
}

export interface FleetMap {
  fleet_id: number;
  clusters: MapCluster[];
  vehicles: MapVehicle[];
}

export interface VehicleState {
  ts: string;
  soc: number;
  soh: number;
  speed_kmh: number;
  temp_c: number;
  charging: boolean;
  charge_kw: number;
  lat: number;
  lon: number;
  geohash: string;
  is_masked: boolean;
}

export interface VehicleDetail {
  vin: string;
  oem: string;
  model: string;
  battery_kwh: number;
  rated_range_km: number;
  max_dc_kw: number;
  driver_name?: string;
  state: VehicleState;
  estimated_range_km: number;
}

export interface TelemetryPoint {
  ts: string;
  soc_pct: number;
  speed_kmh: number;
  batt_temp_c: number;
  charging: number;
  charge_kw: number;
}

export interface SohHistoryEntry {
  day: string;
  distance_km: number;
  kwh_used: number;
  avg_temp_c: number;
  est_capacity_kwh: number;
  soh: number;
}

export interface VehicleSohResponse {
  vin: string;
  current_soh: number;
  true_soh_proxy: number;
  predicted_soh_xgb: number;
  degradation_rate_pct_yr: number;
  dc_fast_share_pct: number;
  history: SohHistoryEntry[];
}

export interface Alert {
  alert_id: number;
  vin: string;
  alert_type: 'RANGE_RISK' | 'LOW_SOC' | 'THERMAL' | 'RAPID_DROP' | 'HARSH_BRAKE' | 'FAST_DEGRADATION';
  severity: 'CRITICAL' | 'HIGH' | 'WARN' | 'INFO';
  message: string;
  data?: Record<string, any>;
  created_at: string;
  resolved_at?: string | null;
  latency_ms?: number;
}

export interface AckAlertResponse {
  alert_id: number;
  resolved_at: string;
  status: string;
}

export interface ScheduleSlot {
  slot: number;
  time: string;
  power_kw: number;
  soc_start: number;
  soc_end: number;
  cost_usd: number;
}

export interface ChargePlan {
  plan_id: number;
  vin: string;
  charger_id: number;
  status: 'proposed' | 'approved' | 'rejected' | 'active' | 'completed';
  target_soc: number;
  initial_soc: number;
  departure_time: string;
  baseline_cost: number;
  optimized_cost: number;
  savings_pct: number;
  stress_reduction_pct: number;
  schedule: ScheduleSlot[];
}

export interface NearestCharger {
  charger_id: number;
  name: string;
  operator: string;
  power_kw: number;
  plug_type: string;
  lat: number;
  lon: number;
  distance_km: number;
  est_travel_energy_kwh: number;
  reachable: boolean;
}

export interface NearestChargersResponse {
  vin: string;
  current_soc: number;
  usable_range_km: number;
  chargers: NearestCharger[];
}

export interface SohBenchmark {
  model: string;
  age_bucket: string;
  fleet_avg_soh: number;
  peer_avg_soh_noisy: number;
  epsilon: number;
  sample_size: number;
  k_suppressed: boolean;
  confidence_interval: [number, number];
  remaining_budget: number;
}

export interface AuditLogEntry {
  audit_id: number;
  ts: string;
  actor: string;
  actor_type: 'user' | 'agent' | 'system';
  action: string;
  resource: string;
  tenant_id: number;
  detail?: Record<string, any>;
}

export interface ErasureResponse {
  target_type: 'vin' | 'driver';
  target_id: string;
  status: 'completed' | 'not_found' | 'error';
  stores_purged: {
    postgres: boolean;
    redis: boolean;
    clickhouse: boolean;
    kafka_tombstone: boolean;
  };
  completed_at: string;
}

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'copilot';
  timestamp: string;
  text: string;
  toolCalls?: Array<{
    name: string;
    args: Record<string, any>;
    status: 'success' | 'running' | 'rejected';
  }>;
  guardrails?: {
    delegatedJwt: boolean;
    roleChecked: boolean;
    readOnlyEnforced: boolean;
    maskingApplied: boolean;
  };
}
