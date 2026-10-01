import {
  FleetSummary,
  VehicleListItem,
  VehicleDetail,
  TelemetryPoint,
  VehicleSohResponse,
  Alert,
  ChargePlan,
  NearestChargersResponse,
  SohBenchmark,
  AuditLogEntry,
  FleetMap,
} from '../types';

export const MOCK_FLEET_SUMMARY: FleetSummary = {
  fleet_id: 1,
  name: 'VoltFleet Alpha (San Francisco Hub)',
  tenant_id: 1,
  total_vehicles: 12480,
  active_vehicles: 9840,
  charging_vehicles: 1940,
  avg_soc: 68.4,
  avg_soh: 94.6,
  open_alerts: 4,
  total_energy_kwh_today: 184500,
  cost_saved_usd_today: 14280.50,
  co2_saved_kg_today: 78540,
  soh_distribution: {
    '95-100': 6420,
    '90-95': 4120,
    '85-90': 1480,
    '80-85': 380,
    '<80': 80,
  },
};

export const MOCK_VEHICLES: VehicleListItem[] = [
  {
    vin: '1VXEV01A100000001',
    oem: 'VoltX',
    model: 'VoltX Hyper-e',
    battery_kwh: 75.0,
    rated_range_km: 420.0,
    max_dc_kw: 150.0,
    driver_name: 'Marcus Chen',
    latest_soc: 18.2,
    latest_soh: 96.2,
    status: 'warning',
  },
  {
    vin: '2NMEV02B200000002',
    oem: 'NordMotors',
    model: 'NordMotors Polar-4',
    battery_kwh: 82.0,
    rated_range_km: 450.0,
    max_dc_kw: 135.0,
    driver_name: 'Elena Rostova',
    latest_soc: 84.5,
    latest_soh: 93.8,
    status: 'charging',
  },
  {
    vin: '3ADEV03C300000003',
    oem: 'AsiaDrive',
    model: 'AsiaDrive Express-V',
    battery_kwh: 60.0,
    rated_range_km: 350.0,
    max_dc_kw: 100.0,
    driver_name: 'Kenji Takahashi',
    latest_soc: 11.4,
    latest_soh: 88.5,
    status: 'critical',
  },
  {
    vin: '4EEEV04D400000004',
    oem: 'EuroEV',
    model: 'EuroEV Continental',
    battery_kwh: 90.0,
    rated_range_km: 500.0,
    max_dc_kw: 175.0,
    driver_name: 'Sophie Dubois',
    latest_soc: 72.0,
    latest_soh: 95.1,
    status: 'active',
  },
  {
    vin: '5ZEEV05E500000005',
    oem: 'ZephyrEV',
    model: 'ZephyrEV Aero-6',
    battery_kwh: 50.0,
    rated_range_km: 300.0,
    max_dc_kw: 80.0,
    driver_name: 'David O’Connor',
    latest_soc: 61.8,
    latest_soh: 97.4,
    status: 'active',
  },
  {
    vin: '1VXEV01A100000006',
    oem: 'VoltX',
    model: 'VoltX Hyper-e',
    battery_kwh: 75.0,
    rated_range_km: 420.0,
    max_dc_kw: 150.0,
    driver_name: 'Ananya Sharma',
    latest_soc: 94.0,
    latest_soh: 98.1,
    status: 'active',
  },
];

export const MOCK_VEHICLE_DETAIL: VehicleDetail = {
  vin: '1VXEV01A100000001',
  oem: 'VoltX',
  model: 'VoltX Hyper-e',
  battery_kwh: 75.0,
  rated_range_km: 420.0,
  max_dc_kw: 150.0,
  driver_name: 'Marcus Chen',
  estimated_range_km: 76.4,
  state: {
    ts: new Date().toISOString(),
    soc: 18.2,
    soh: 96.2,
    speed_kmh: 42.5,
    temp_c: 32.8,
    charging: false,
    charge_kw: 0.0,
    lat: 37.7749,
    lon: -122.4194,
    geohash: '9q8yyk8',
    is_masked: false,
  },
};

export const generateMockTelemetry = (): TelemetryPoint[] => {
  const points: TelemetryPoint[] = [];
  const now = Date.now();
  for (let i = 24; i >= 0; i--) {
    const time = new Date(now - i * 3600 * 1000).toISOString();
    // Simulate realistic charge cycle: starts high, drops with driving, plugs in at hour 6
    let soc = 85 - (24 - i) * 2.8;
    if (soc < 15) soc = 15 + ((24 - i) % 4) * 3;
    const temp = 26 + Math.sin(i / 3) * 6;
    const speed = i % 4 === 0 ? 0 : 35 + (i * 7) % 45;
    const charging = speed === 0 && soc < 40 ? 1 : 0;
    const kw = charging ? 45.0 : 0.0;

    points.push({
      ts: time,
      soc_pct: Math.round(soc * 10) / 10,
      speed_kmh: speed,
      batt_temp_c: Math.round(temp * 10) / 10,
      charging: charging,
      charge_kw: kw,
    });
  }
  return points;
};

export const MOCK_SOH_PREDICTION: VehicleSohResponse = {
  vin: '1VXEV01A100000001',
  current_soh: 96.2,
  true_soh_proxy: 95.8,
  predicted_soh_xgb: 96.1,
  degradation_rate_pct_yr: 1.84,
  dc_fast_share_pct: 18.5,
  history: [
    { day: '2026-09-01', distance_km: 142.5, kwh_used: 24.2, avg_temp_c: 24.1, est_capacity_kwh: 74.2, soh: 98.9 },
    { day: '2026-09-08', distance_km: 165.0, kwh_used: 28.1, avg_temp_c: 25.3, est_capacity_kwh: 73.8, soh: 98.4 },
    { day: '2026-09-15', distance_km: 154.2, kwh_used: 26.0, avg_temp_c: 27.0, est_capacity_kwh: 73.1, soh: 97.5 },
    { day: '2026-09-22', distance_km: 180.1, kwh_used: 31.4, avg_temp_c: 26.2, est_capacity_kwh: 72.8, soh: 96.9 },
    { day: '2026-09-29', distance_km: 172.8, kwh_used: 29.5, avg_temp_c: 24.8, est_capacity_kwh: 72.1, soh: 96.2 },
  ],
};

export const MOCK_ALERTS: Alert[] = [
  {
    alert_id: 101,
    vin: '3ADEV03C300000003',
    alert_type: 'RANGE_RISK',
    severity: 'CRITICAL',
    message: 'Predicted range (28.4 km) < 1.2x distance to nearest charger (24.1 km). Immediate charging detour recommended.',
    data: { predicted_range_km: 28.4, charger_distance_km: 24.1, buffer_ratio: 1.18 },
    created_at: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
    resolved_at: null,
    latency_ms: 820,
  },
  {
    alert_id: 102,
    vin: '1VXEV01A100000001',
    alert_type: 'LOW_SOC',
    severity: 'WARN',
    message: 'State of charge dropped to 18.2% (<15% buffer margin approaching).',
    data: { current_soc: 18.2, threshold: 20.0 },
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    resolved_at: null,
    latency_ms: 615,
  },
  {
    alert_id: 103,
    vin: '2NMEV02B200000002',
    alert_type: 'THERMAL',
    severity: 'HIGH',
    message: 'Pack cell temperature sustained at 51.4°C during high-power DC fast-charge.',
    data: { temp_c: 51.4, limit_c: 50.0, duration_s: 75 },
    created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    resolved_at: null,
    latency_ms: 1140,
  },
  {
    alert_id: 104,
    vin: '4EEEV04D400000004',
    alert_type: 'HARSH_BRAKE',
    severity: 'INFO',
    message: 'Telemetry event HARSH_BRAKE detected: -4.8 m/s² deceleration.',
    data: { decel_mps2: -4.8, initial_speed_kmh: 68.0 },
    created_at: new Date(Date.now() - 110 * 60 * 1000).toISOString(),
    resolved_at: new Date(Date.now() - 100 * 60 * 1000).toISOString(),
    latency_ms: 450,
  },
];

export const MOCK_NEAREST_CHARGERS: NearestChargersResponse = {
  vin: '1VXEV01A100000001',
  current_soc: 18.2,
  usable_range_km: 76.4,
  chargers: [
    {
      charger_id: 1,
      name: 'ChargePoint Plaza — Market St',
      operator: 'ChargePoint Network',
      power_kw: 150.0,
      plug_type: 'CCS Combo 1',
      lat: 37.7833,
      lon: -122.4167,
      distance_km: 1.8,
      est_travel_energy_kwh: 0.38,
      reachable: true,
    },
    {
      charger_id: 2,
      name: 'Electrify America — 4th & Mission',
      operator: 'Electrify America',
      power_kw: 350.0,
      plug_type: 'CCS / CHAdeMO',
      lat: 37.7850,
      lon: -122.4040,
      distance_km: 2.6,
      est_travel_energy_kwh: 0.55,
      reachable: true,
    },
    {
      charger_id: 3,
      name: 'EVgo Fast Charger — Civic Center',
      operator: 'EVgo',
      power_kw: 100.0,
      plug_type: 'CCS Combo 1',
      lat: 37.7780,
      lon: -122.4170,
      distance_km: 0.9,
      est_travel_energy_kwh: 0.19,
      reachable: true,
    },
  ],
};

export const MOCK_CHARGE_PLAN: ChargePlan = {
  plan_id: 8421,
  vin: '1VXEV01A100000001',
  charger_id: 1,
  status: 'proposed',
  target_soc: 85.0,
  initial_soc: 18.2,
  departure_time: new Date(Date.now() + 8 * 3600 * 1000).toISOString(),
  baseline_cost: 14.85,
  optimized_cost: 9.65,
  savings_pct: 35.02,
  stress_reduction_pct: 64.8,
  schedule: [
    { slot: 0, time: '22:00', power_kw: 0.0, soc_start: 18.2, soc_end: 18.2, cost_usd: 0.00 },
    { slot: 1, time: '23:00', power_kw: 0.0, soc_start: 18.2, soc_end: 18.2, cost_usd: 0.00 },
    { slot: 2, time: '00:00', power_kw: 22.0, soc_start: 18.2, soc_end: 32.8, cost_usd: 1.10 },
    { slot: 3, time: '01:00', power_kw: 22.0, soc_start: 32.8, soc_end: 47.4, cost_usd: 1.10 },
    { slot: 4, time: '02:00', power_kw: 22.0, soc_start: 47.4, soc_end: 62.0, cost_usd: 1.10 },
    { slot: 5, time: '03:00', power_kw: 22.0, soc_start: 62.0, soc_end: 76.6, cost_usd: 1.10 },
    { slot: 6, time: '04:00', power_kw: 12.6, soc_start: 76.6, soc_end: 85.0, cost_usd: 0.63 },
    { slot: 7, time: '05:00', power_kw: 0.0, soc_start: 85.0, soc_end: 85.0, cost_usd: 0.00 },
  ],
};

export const MOCK_DP_BENCHMARK: SohBenchmark = {
  model: 'VoltX Hyper-e',
  age_bucket: '1-2yr',
  fleet_avg_soh: 96.2,
  peer_avg_soh_noisy: 95.8,
  epsilon: 1.0,
  sample_size: 4210,
  k_suppressed: false,
  confidence_interval: [95.4, 96.2],
  remaining_budget: 18.0,
};

export const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    audit_id: 901,
    ts: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    actor: 'manager@voltfleet.com',
    actor_type: 'user',
    action: 'propose_charge_plan',
    resource: 'vehicle:1VXEV01A100000001',
    tenant_id: 1,
    detail: { plan_id: 8421, target_soc: 85, savings_pct: 35.02 },
  },
  {
    audit_id: 902,
    ts: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
    actor: 'agent_copilot',
    actor_type: 'agent',
    action: 'rag_search_kb',
    resource: 'kb:battery_care',
    tenant_id: 1,
    detail: { query: 'optimal charging temperature limits', chunks_retrieved: 3 },
  },
  {
    audit_id: 903,
    ts: new Date(Date.now() - 32 * 60 * 1000).toISOString(),
    actor: 'admin@voltfleet.com',
    actor_type: 'user',
    action: 'query_dp_benchmark',
    resource: 'benchmark:Hyper-e',
    tenant_id: 1,
    detail: { epsilon: 1.0, age_bucket: '1-2yr' },
  },
  {
    audit_id: 904,
    ts: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
    actor: 'admin@voltfleet.com',
    actor_type: 'user',
    action: 'privacy_erasure_completed',
    resource: 'vin:5ZEEV05E599999999',
    tenant_id: 1,
    detail: { stores_purged: ['postgres', 'redis', 'clickhouse'] },
  },
];

export const MOCK_FLEET_MAP: FleetMap = {
  fleet_id: 1,
  clusters: [
    { geohash: '9q8yy', lat: 37.7749, lon: -122.4194, count: 48, avg_soc: 68.2, critical_count: 1 },
    { geohash: '9q8yj', lat: 37.7312, lon: -122.3850, count: 32, avg_soc: 74.5, critical_count: 0 },
    { geohash: '9q9p1', lat: 37.8044, lon: -122.2712, count: 24, avg_soc: 62.1, critical_count: 2 },
    { geohash: '9q8zn', lat: 37.8715, lon: -122.2730, count: 18, avg_soc: 81.0, critical_count: 0 },
  ],
  vehicles: [
    { vin: '1VXEV01A100000001', lat: 37.7749, lon: -122.4194, geohash: '9q8yyk8', soc: 18.2, speed_kmh: 42.5, status: 'warning', is_masked: false },
    { vin: '2NMEV02B200000002', lat: 37.7833, lon: -122.4167, geohash: '9q8yyv2', soc: 84.5, speed_kmh: 0.0, status: 'charging', is_masked: false },
    { vin: '3ADEV03C300000003', lat: 37.8044, lon: -122.2712, geohash: '9q9p1ab', soc: 11.4, speed_kmh: 55.0, status: 'critical', is_masked: false },
    { vin: '4EEEV04D400000004', lat: 37.7312, lon: -122.3850, geohash: '9q8yj01', soc: 72.0, speed_kmh: 62.1, status: 'active', is_masked: false },
    { vin: '5ZEEV05E500000005', lat: 37.8715, lon: -122.2730, geohash: '9q8zn44', soc: 61.8, speed_kmh: 48.0, status: 'active', is_masked: false },
  ],
};
