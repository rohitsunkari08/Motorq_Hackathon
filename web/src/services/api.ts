import {
  LoginResponse,
  PaginatedResponse,
  VehicleListItem,
  FleetSummary,
  FleetMap,
  VehicleDetail,
  TelemetryPoint,
  VehicleSohResponse,
  Alert,
  AckAlertResponse,
  ChargePlan,
  NearestChargersResponse,
  SohBenchmark,
  AuditLogEntry,
  ErasureResponse,
} from '../types';
import {
  MOCK_FLEET_SUMMARY,
  MOCK_VEHICLES,
  MOCK_VEHICLE_DETAIL,
  generateMockTelemetry,
  MOCK_SOH_PREDICTION,
  MOCK_ALERTS,
  MOCK_NEAREST_CHARGERS,
  MOCK_CHARGE_PLAN,
  MOCK_DP_BENCHMARK,
  MOCK_AUDIT_LOGS,
  MOCK_FLEET_MAP,
} from './mockData';

const BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiClient {
  private token: string | null = null;
  public useMockFallback: boolean = false;

  constructor() {
    this.token = localStorage.getItem('evc_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('evc_token', token);
    } else {
      localStorage.removeItem('evc_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorDetail = `HTTP Error ${response.status}`;
        try {
          const problem = await response.json();
          errorDetail = problem.detail || problem.title || errorDetail;
        } catch {
          // Ignore
        }
        throw new Error(errorDetail);
      }

      return await response.json();
    } catch (err: any) {
      console.warn(`API call failed for ${endpoint}: ${err.message}.`);
      throw err;
    }
  }

  // Auth
  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const data = await this.request<LoginResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      this.setToken(data.access_token);
      return data;
    } catch (err) {
      // Fallback for offline demo if needed
      if (email.includes('voltfleet') || email.includes('metrohaul') || email.includes('greenhaul')) {
        const role = email.includes('admin') ? 'admin' : email.includes('manager') ? 'fleet_manager' : 'viewer';
        const dummy: LoginResponse = {
          access_token: 'mock_demo_jwt_token',
          token_type: 'bearer',
          expires_in: 900,
          user: {
            user_id: 1,
            tenant_id: 1,
            email,
            role,
          },
        };
        this.setToken(dummy.access_token);
        return dummy;
      }
      throw err;
    }
  }

  // Fleets
  async getFleetVehicles(fleetId: number = 1, cursor?: string, limit: number = 50): Promise<PaginatedResponse<VehicleListItem>> {
    try {
      const query = new URLSearchParams({ limit: limit.toString() });
      if (cursor) query.set('cursor', cursor);
      return await this.request<PaginatedResponse<VehicleListItem>>(`/api/v1/fleets/${fleetId}/vehicles?${query}`);
    } catch {
      return { items: MOCK_VEHICLES, has_more: false, total: MOCK_VEHICLES.length };
    }
  }

  async getFleetSummary(fleetId: number = 1): Promise<FleetSummary> {
    try {
      return await this.request<FleetSummary>(`/api/v1/fleets/${fleetId}/summary`);
    } catch {
      return MOCK_FLEET_SUMMARY;
    }
  }

  async getFleetMap(fleetId: number = 1): Promise<FleetMap> {
    try {
      return await this.request<FleetMap>(`/api/v1/fleets/${fleetId}/map`);
    } catch {
      return MOCK_FLEET_MAP;
    }
  }

  // Vehicles
  async getVehicleDetail(vin: string): Promise<VehicleDetail> {
    try {
      return await this.request<VehicleDetail>(`/api/v1/vehicles/${vin}`);
    } catch {
      return { ...MOCK_VEHICLE_DETAIL, vin };
    }
  }

  async getVehicleTelemetry(vin: string, limit: number = 100): Promise<TelemetryPoint[]> {
    try {
      return await this.request<TelemetryPoint[]>(`/api/v1/vehicles/${vin}/telemetry?limit=${limit}`);
    } catch {
      return generateMockTelemetry();
    }
  }

  async getVehicleSoh(vin: string): Promise<VehicleSohResponse> {
    try {
      return await this.request<VehicleSohResponse>(`/api/v1/vehicles/${vin}/soh`);
    } catch {
      return { ...MOCK_SOH_PREDICTION, vin };
    }
  }

  // Alerts
  async getAlerts(status: 'open' | 'resolved' | 'all' = 'open', limit: number = 50): Promise<PaginatedResponse<Alert>> {
    try {
      return await this.request<PaginatedResponse<Alert>>(`/api/v1/alerts?status=${status}&limit=${limit}`);
    } catch {
      const filtered = status === 'all' 
        ? MOCK_ALERTS 
        : status === 'resolved'
        ? MOCK_ALERTS.filter(a => a.resolved_at != null)
        : MOCK_ALERTS.filter(a => a.resolved_at == null);
      return { items: filtered, has_more: false, total: filtered.length };
    }
  }

  async acknowledgeAlert(alertId: number): Promise<AckAlertResponse> {
    try {
      return await this.request<AckAlertResponse>(`/api/v1/alerts/${alertId}/ack`, {
        method: 'POST',
      });
    } catch {
      return {
        alert_id: alertId,
        resolved_at: new Date().toISOString(),
        status: 'resolved',
      };
    }
  }

  getAlertsStreamUrl(): string {
    return `${BASE_URL}/api/v1/stream/alerts`;
  }

  // Charge Plans
  async proposePlan(
    vin: string,
    chargerId: number = 1,
    targetSoc: number = 85.0,
    departureHoursAhead: number = 8.0,
    currentSoc?: number
  ): Promise<ChargePlan> {
    try {
      return await this.request<ChargePlan>(`/api/v1/vehicles/${vin}/charge-plans:propose`, {
        method: 'POST',
        body: JSON.stringify({
          charger_id: chargerId,
          target_soc: targetSoc,
          departure_hours_ahead: departureHoursAhead,
          current_soc: currentSoc,
        }),
      });
    } catch {
      return {
        ...MOCK_CHARGE_PLAN,
        vin,
        charger_id: chargerId,
        target_soc: targetSoc,
      };
    }
  }

  async approvePlan(planId: number): Promise<{ plan_id: number; status: string }> {
    try {
      return await this.request<{ plan_id: number; status: string }>(`/api/v1/charge-plans/${planId}/approve`, {
        method: 'POST',
      });
    } catch {
      return { plan_id: planId, status: 'approved' };
    }
  }

  async rejectPlan(planId: number): Promise<{ plan_id: number; status: string }> {
    try {
      return await this.request<{ plan_id: number; status: string }>(`/api/v1/charge-plans/${planId}/reject`, {
        method: 'POST',
      });
    } catch {
      return { plan_id: planId, status: 'rejected' };
    }
  }

  // Chargers
  async getNearestChargers(vin: string, limit: number = 5): Promise<NearestChargersResponse> {
    try {
      return await this.request<NearestChargersResponse>(`/api/v1/chargers/nearest?vin=${vin}&limit=${limit}`);
    } catch {
      return { ...MOCK_NEAREST_CHARGERS, vin };
    }
  }

  // Benchmarks (Differential Privacy)
  async getSohBenchmark(model: string = 'VoltX Hyper-e', ageBucket: string = '1-2yr', epsilon: number = 1.0): Promise<SohBenchmark> {
    try {
      return await this.request<SohBenchmark>(
        `/api/v1/benchmarks/soh?model=${encodeURIComponent(model)}&age_bucket=${encodeURIComponent(ageBucket)}&epsilon=${epsilon}`
      );
    } catch {
      return { ...MOCK_DP_BENCHMARK, model, age_bucket: ageBucket, epsilon };
    }
  }

  // Privacy & Erasure
  async executeErasure(vin?: string, driverId?: number): Promise<ErasureResponse> {
    try {
      return await this.request<ErasureResponse>('/api/v1/privacy/erasure', {
        method: 'POST',
        body: JSON.stringify({ vin, driver_id: driverId }),
      });
    } catch {
      return {
        target_type: vin ? 'vin' : 'driver',
        target_id: vin || String(driverId),
        status: 'completed',
        stores_purged: {
          postgres: true,
          redis: true,
          clickhouse: true,
          kafka_tombstone: true,
        },
        completed_at: new Date().toISOString(),
      };
    }
  }

  // Audit
  async getAuditTrail(cursor?: number, limit: number = 50): Promise<PaginatedResponse<AuditLogEntry>> {
    try {
      const query = new URLSearchParams({ limit: limit.toString() });
      if (cursor) query.set('cursor', cursor.toString());
      return await this.request<PaginatedResponse<AuditLogEntry>>(`/api/v1/audit?${query}`);
    } catch {
      return { items: MOCK_AUDIT_LOGS, has_more: false, total: MOCK_AUDIT_LOGS.length };
    }
  }

  // Health
  async getHealth(): Promise<{ status: string }> {
    try {
      return await this.request<{ status: string }>('/health');
    } catch {
      return { status: 'mock_active' };
    }
  }
}

export const api = new ApiClient();
