import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  VehicleDetail,
  TelemetryPoint,
  VehicleSohResponse,
  NearestChargersResponse,
  ChargePlan,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Car,
  Battery,
  Zap,
  Thermometer,
  Gauge,
  Navigation,
  CheckCircle,
  XCircle,
  TrendingDown,
  Clock,
  Sparkles,
  MapPin,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
  CartesianGrid,
} from 'recharts';

interface VehicleDetailPageProps {
  vin: string;
  onBack?: () => void;
}

export const VehicleDetailPage: React.FC<VehicleDetailPageProps> = ({ vin, onBack }) => {
  const { user } = useAuth();
  const [detail, setDetail] = useState<VehicleDetail | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPoint[]>([]);
  const [sohData, setSohData] = useState<VehicleSohResponse | null>(null);
  const [chargers, setChargers] = useState<NearestChargersResponse | null>(null);

  // Optimiser state
  const [targetSoc, setTargetSoc] = useState<number>(85);
  const [departureHours, setDepartureHours] = useState<number>(8);
  const [plan, setPlan] = useState<ChargePlan | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  const [planStatus, setPlanStatus] = useState<'proposed' | 'approved' | 'rejected' | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadVehicleData() {
      try {
        const [det, tel, soh, chg] = await Promise.all([
          api.getVehicleDetail(vin),
          api.getVehicleTelemetry(vin, 50),
          api.getVehicleSoh(vin),
          api.getNearestChargers(vin, 5),
        ]);
        if (isMounted) {
          setDetail(det);
          setTelemetry(tel);
          setSohData(soh);
          setChargers(chg);
        }
      } catch (err) {
        console.error('Failed to load vehicle data', err);
      }
    }
    loadVehicleData();
    return () => {
      isMounted = false;
    };
  }, [vin, user?.role]);

  const handleProposePlan = async () => {
    setOptimizing(true);
    setActionMessage(null);
    try {
      const chargerId = chargers?.chargers[0]?.charger_id || 1;
      const res = await api.proposePlan(vin, chargerId, targetSoc, departureHours, detail?.state.soc);
      setPlan(res);
      setPlanStatus('proposed');
      setActionMessage('Optimal charging plan computed via Dynamic Programming.');
    } catch (err: any) {
      setActionMessage(`Optimization failed: ${err.message}`);
    } finally {
      setOptimizing(false);
    }
  };

  const handleApprovePlan = async () => {
    if (!plan) return;
    try {
      await api.approvePlan(plan.plan_id);
      setPlanStatus('approved');
      setActionMessage(`Plan #${plan.plan_id} approved and dispatched to charger.`);
    } catch (err: any) {
      setActionMessage(`Approval failed: ${err.message}`);
    }
  };

  const handleRejectPlan = async () => {
    if (!plan) return;
    try {
      await api.rejectPlan(plan.plan_id);
      setPlanStatus('rejected');
      setActionMessage(`Plan #${plan.plan_id} rejected.`);
    } catch (err: any) {
      setActionMessage(`Rejection failed: ${err.message}`);
    }
  };

  // Format telemetry for Recharts
  const formattedTelemetry = telemetry.map((t) => ({
    time: new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    soc: t.soc_pct,
    temp: t.batt_temp_c,
    power: t.charge_kw,
    speed: t.speed_kmh,
  }));

  const isViewer = user?.role === 'viewer';
  const canApprove = user?.role === 'fleet_manager' || user?.role === 'admin';

  return (
    <div className="page-wrapper" id="page-vehicle-detail">
      {/* Navigation Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {onBack && (
            <button className="btn btn-secondary btn-sm" onClick={onBack}>
              ← Back to Fleet
            </button>
          )}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.75rem', fontFamily: 'var(--font-mono)' }}>{vin}</h1>
              <span className="badge badge-info">{detail?.oem}</span>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {detail?.model} · Assigned to: <strong>{detail?.driver_name || 'Fleet Driver'}</strong>
            </div>
          </div>
        </div>

        {/* Location Masking Alert */}
        <div
          id="detail-masking-status"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: isViewer ? 'var(--accent-amber-dim)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${isViewer ? 'rgba(245, 158, 11, 0.3)' : 'var(--border-color)'}`,
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.8rem',
            color: isViewer ? 'var(--accent-amber)' : 'var(--text-muted)',
          }}
        >
          <Navigation size={14} />
          <span>
            {isViewer
              ? `Masked Geohash: ${detail?.state.geohash?.substring(0, 5)}...`
              : `Exact: ${detail?.state.lat?.toFixed(4)}, ${detail?.state.lon?.toFixed(4)}`}
          </span>
        </div>
      </div>

      {/* Real-time State Quick Stats */}
      <div className="stat-grid" style={{ marginBottom: '24px' }}>
        <div className="card" style={{ borderBottom: '2px solid var(--accent-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              STATE OF CHARGE
            </span>
            <Battery size={20} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '8px', color: '#fff' }}>
            {detail?.state.soc}%
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Est. Usable Range: <strong>{detail?.estimated_range_km} km</strong>
          </div>
        </div>

        <div className="card" style={{ borderBottom: '2px solid var(--accent-emerald)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              BATTERY HEALTH (SOH)
            </span>
            <TrendingDown size={20} color="var(--accent-emerald)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '8px', color: 'var(--accent-emerald)' }}>
            {detail?.state.soh}%
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            XGBoost ML Pred: <strong>{sohData?.predicted_soh_xgb}%</strong> (-{sohData?.degradation_rate_pct_yr}%/yr)
          </div>
        </div>

        <div className="card" style={{ borderBottom: '2px solid var(--accent-amber)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              PACK TEMPERATURE
            </span>
            <Thermometer size={20} color="var(--accent-amber)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '8px', color: '#fff' }}>
            {detail?.state.temp_c}°C
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Optimal thermal window: 20°C - 35°C
          </div>
        </div>

        <div className="card" style={{ borderBottom: '2px solid var(--accent-purple)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              CHARGING POWER
            </span>
            <Zap size={20} color="var(--accent-purple)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '8px', color: '#fff' }}>
            {detail?.state.charging ? `${detail.state.charge_kw} kW` : 'Idle'}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            DC Max: {detail?.max_dc_kw} kW · Speed: {detail?.state.speed_kmh} km/h
          </div>
        </div>
      </div>

      {/* Row: Telemetry Time-Series Chart */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title">
            <Gauge size={18} color="var(--accent-cyan)" />
            <span>24-Hour Telemetry Time-Series (ClickHouse MergeTree)</span>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Resolution: 5-minute canonical snapshots
          </span>
        </div>

        <div style={{ height: '300px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedTelemetry} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={11} />
              <YAxis yAxisId="left" stroke="var(--accent-cyan)" fontSize={11} domain={[0, 100]} />
              <YAxis yAxisId="right" orientation="right" stroke="var(--accent-amber)" fontSize={11} domain={[15, 60]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border-color)',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="soc" stroke="#00F0FF" strokeWidth={2.5} name="SoC (%)" dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="temp" stroke="#F59E0B" strokeWidth={2} name="Temp (°C)" dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="power" stroke="#8B5CF6" strokeWidth={2} name="Charge (kW)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row: Nearest Chargers & DP Smart Charging Optimiser */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        {/* Nearest Reachable Chargers */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <MapPin size={18} color="var(--accent-emerald)" />
              <span>Nearest Reachable Chargers</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              10% Reserve Buffer Applied
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {chargers?.chargers.map((c) => (
              <div
                key={c.charger_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {c.operator} · {c.plug_type} · {c.distance_km} km away
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: 'var(--accent-cyan)', fontSize: '0.9rem' }}>
                    {c.power_kw} kW
                  </div>
                  <span className={`badge ${c.reachable ? 'badge-success' : 'badge-critical'}`} style={{ fontSize: '0.65rem' }}>
                    {c.reachable ? 'Reachable' : 'Out of Range'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* DP Charge Schedule Optimiser */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <div className="card-title">
              <Sparkles size={18} color="var(--accent-cyan)" />
              <span>Battery-Aware DP Charge Optimiser</span>
            </div>
            <span className="badge badge-purple">Time-of-Use + Health</span>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Dynamic Programming scheduling over 15-min slots. Minimizes energy tariff while penalizing battery degradation stress.
          </p>

          {/* Configuration Form */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label className="form-label" htmlFor="input-target-soc">
                Target SoC ({targetSoc}%)
              </label>
              <input
                id="input-target-soc"
                type="range"
                min="50"
                max="100"
                step="5"
                value={targetSoc}
                onChange={(e) => setTargetSoc(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" htmlFor="input-departure-hours">
                Departure Window ({departureHours} hrs)
              </label>
              <input
                id="input-departure-hours"
                type="range"
                min="2"
                max="18"
                step="1"
                value={departureHours}
                onChange={(e) => setDepartureHours(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          <button
            id="btn-propose-plan"
            className="btn btn-primary"
            onClick={handleProposePlan}
            disabled={optimizing}
            style={{ width: '100%', marginBottom: '16px' }}
          >
            <Sparkles size={16} />
            {optimizing ? 'Computing Bellman DP Backtrack...' : 'Compute Optimal Charging Schedule'}
          </button>

          {/* Action Result / Message */}
          {actionMessage && (
            <div
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(0, 240, 255, 0.08)',
                border: '1px solid rgba(0, 240, 255, 0.2)',
                fontSize: '0.8rem',
                color: 'var(--accent-cyan)',
                marginBottom: '14px',
              }}
            >
              {actionMessage}
            </div>
          )}

          {/* Plan Comparison Summary */}
          {plan && (
            <div
              id="plan-result-container"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                marginTop: 'auto',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Plan #{plan.plan_id}</span>
                <StatusBadge status={planStatus || plan.status} type="plan" />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px', textAlign: 'center' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Baseline Cost</div>
                  <div style={{ fontWeight: 700, textDecoration: 'line-through', color: 'var(--accent-rose)' }}>
                    ${plan.baseline_cost.toFixed(2)}
                  </div>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>DP Opt Cost</div>
                  <div style={{ fontWeight: 800, color: 'var(--accent-emerald)', fontSize: '1rem' }}>
                    ${plan.optimized_cost.toFixed(2)}
                  </div>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Net Savings</div>
                  <div style={{ fontWeight: 800, color: 'var(--accent-cyan)' }}>
                    {plan.savings_pct.toFixed(1)}%
                  </div>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Stress Relief</div>
                  <div style={{ fontWeight: 800, color: 'var(--accent-purple)' }}>
                    {plan.stress_reduction_pct.toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Action Buttons with RBAC enforcement */}
              {canApprove ? (
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    id="btn-approve-plan"
                    className="btn btn-success btn-sm"
                    style={{ flex: 1 }}
                    onClick={handleApprovePlan}
                    disabled={planStatus === 'approved'}
                  >
                    <CheckCircle size={15} />
                    Approve Plan (Manager)
                  </button>
                  <button
                    id="btn-reject-plan"
                    className="btn btn-danger btn-sm"
                    style={{ flex: 1 }}
                    onClick={handleRejectPlan}
                    disabled={planStatus === 'rejected'}
                  >
                    <XCircle size={15} />
                    Reject Plan
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--text-muted)', justifyContent: 'center' }}>
                  <ShieldAlert size={14} color="var(--accent-amber)" />
                  <span>Viewer Role: Read-only access (Approval restricted to Fleet Manager & Admin)</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
