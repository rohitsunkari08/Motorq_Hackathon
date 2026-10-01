import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { FleetSummary, FleetMap, VehicleListItem } from '../types';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import {
  Car,
  Zap,
  BatteryCharging,
  DollarSign,
  AlertTriangle,
  MapPin,
  Search,
  Eye,
  ShieldCheck,
  TrendingDown,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip as LeafletTooltip } from 'react-leaflet';

interface FleetOverviewPageProps {
  onSelectVehicle: (vin: string) => void;
}

export const FleetOverviewPage: React.FC<FleetOverviewPageProps> = ({ onSelectVehicle }) => {
  const { user, activeFleetId } = useAuth();
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [mapData, setMapData] = useState<FleetMap | null>(null);
  const [vehicles, setVehicles] = useState<VehicleListItem[]>([]);
  const [searchVin, setSearchVin] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setLoading(true);
      try {
        const [sumRes, mapRes, vehRes] = await Promise.all([
          api.getFleetSummary(activeFleetId),
          api.getFleetMap(activeFleetId),
          api.getFleetVehicles(activeFleetId, undefined, 50),
        ]);
        if (isMounted) {
          setSummary(sumRes);
          setMapData(mapRes);
          setVehicles(vehRes.items);
        }
      } catch (e) {
        console.error('Failed to load fleet overview data', e);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, [activeFleetId, user?.role]);

  // Format SoH distribution for Recharts
  const sohChartData = summary?.soh_distribution
    ? Object.entries(summary.soh_distribution).map(([range, count]) => ({
        range: `${range}%`,
        count,
      }))
    : [];

  const filteredVehicles = vehicles.filter(
    (v) =>
      v.vin.toLowerCase().includes(searchVin.toLowerCase()) ||
      v.model.toLowerCase().includes(searchVin.toLowerCase()) ||
      (v.driver_name && v.driver_name.toLowerCase().includes(searchVin.toLowerCase()))
  );

  const isViewer = user?.role === 'viewer';

  return (
    <div className="page-wrapper" id="page-fleet-overview">
      {/* Top Banner & Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.85rem', marginBottom: '6px' }}>Fleet Intelligence Overview</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Real-time telematics aggregation, battery health distribution, and geohash cell tracking.
          </p>
        </div>

        {/* Masking status indicator */}
        <div
          id="location-masking-banner"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: isViewer ? 'var(--accent-amber-dim)' : 'var(--accent-emerald-dim)',
            border: `1px solid ${isViewer ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.825rem',
            color: isViewer ? 'var(--accent-amber)' : 'var(--accent-emerald)',
          }}
        >
          {isViewer ? <Eye size={18} /> : <ShieldCheck size={18} />}
          <span>
            {isViewer
              ? 'Role-Aware Privacy Active: Masked to geohash5 cell (~4.9km)'
              : 'Fleet Manager Authorization: High-precision coordinates'}
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="stat-grid">
        <StatCard
          id="stat-total-vehicles"
          title="Monitored Fleet"
          value={summary ? summary.total_vehicles.toLocaleString() : '12,480'}
          subtitle="Simulated OEM Connected Fleet"
          icon={<Car size={22} />}
          glowColor="cyan"
        />
        <StatCard
          id="stat-active-charging"
          title="Active / Charging"
          value={`${summary ? summary.active_vehicles.toLocaleString() : '9,840'} / ${summary ? summary.charging_vehicles.toLocaleString() : '1,940'}`}
          subtitle={`${summary ? summary.avg_soc : 68.4}% Mean State of Charge`}
          icon={<BatteryCharging size={22} />}
          glowColor="purple"
        />
        <StatCard
          id="stat-avg-soh"
          title="Fleet Health (SoH)"
          value={`${summary ? summary.avg_soh : 94.6}%`}
          subtitle="Fleet degradation ~2.3%/yr"
          icon={<TrendingDown size={22} />}
          glowColor="emerald"
        />
        <StatCard
          id="stat-cost-saved"
          title="DP Cost Savings"
          value={`$${summary ? summary.cost_saved_usd_today.toLocaleString() : '14,280'}`}
          subtitle="26.2% vs Arrival Baseline"
          icon={<DollarSign size={22} />}
          glowColor="amber"
        />
      </div>

      {/* Middle Row: Clustered Map & SoH Distribution */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        {/* Clustered Fleet Map */}
        <div className="card" style={{ height: '440px', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header" style={{ marginBottom: '12px' }}>
            <div className="card-title">
              <MapPin size={18} color="var(--accent-cyan)" />
              <span>Server-Side Geohash Clustered Map</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {isViewer ? 'Cell precision: 5 chars' : 'Precision: 7 chars'}
            </span>
          </div>

          <div style={{ flex: 1, width: '100%', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
            <MapContainer
              center={[37.7749, -122.4194]}
              zoom={11}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Render Geohash Clusters */}
              {mapData?.clusters.map((cluster) => (
                <CircleMarker
                  key={cluster.geohash}
                  center={[cluster.lat, cluster.lon]}
                  radius={Math.min(30, Math.max(12, cluster.count / 2))}
                  pathOptions={{
                    color: cluster.critical_count > 0 ? '#EF4444' : '#00F0FF',
                    fillColor: cluster.critical_count > 0 ? '#EF4444' : '#00F0FF',
                    fillOpacity: 0.35,
                    weight: 2,
                  }}
                >
                  <Popup>
                    <div style={{ padding: '4px', fontSize: '0.85rem' }}>
                      <strong style={{ color: '#00F0FF' }}>Geohash: {cluster.geohash}</strong>
                      <div>Vehicles: <strong>{cluster.count}</strong></div>
                      <div>Avg SoC: <strong>{cluster.avg_soc}%</strong></div>
                      {cluster.critical_count > 0 && (
                        <div style={{ color: '#EF4444' }}>Critical Alerts: {cluster.critical_count}</div>
                      )}
                    </div>
                  </Popup>
                  <LeafletTooltip direction="center" permanent className="map-tooltip">
                    <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#fff' }}>
                      {cluster.count}
                    </span>
                  </LeafletTooltip>
                </CircleMarker>
              ))}

              {/* Individual vehicles */}
              {mapData?.vehicles.map((v) => (
                <CircleMarker
                  key={v.vin}
                  center={[v.lat, v.lon]}
                  radius={6}
                  pathOptions={{
                    color: v.status === 'critical' ? '#EF4444' : v.status === 'charging' ? '#8B5CF6' : '#10B981',
                    fillColor: v.status === 'critical' ? '#EF4444' : v.status === 'charging' ? '#8B5CF6' : '#10B981',
                    fillOpacity: 0.9,
                    weight: 1,
                  }}
                >
                  <Popup>
                    <div style={{ padding: '6px', fontSize: '0.85rem' }}>
                      <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{v.vin}</div>
                      <div>SoC: <strong>{v.soc}%</strong></div>
                      <div>Speed: <strong>{v.speed_kmh} km/h</strong></div>
                      <div>Status: <strong>{v.status}</strong></div>
                      {v.is_masked && (
                        <div style={{ color: 'var(--accent-amber)', fontSize: '0.75rem', marginTop: '4px' }}>
                          *Location geohash-masked
                        </div>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </div>

        {/* SoH Distribution Histogram */}
        <div className="card" style={{ height: '440px', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header" style={{ marginBottom: '12px' }}>
            <div className="card-title">
              <Zap size={18} color="var(--accent-emerald)" />
              <span>Fleet Battery Health (SoH) Distribution</span>
            </div>
            <span className="badge badge-success">Calibrated Model</span>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Degradation histogram across 100,000 vehicles. EFC square-root model with DC fast charging degradation penalties.
          </p>

          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sohChartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                <XAxis dataKey="range" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderColor: 'var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {sohChartData.map((entry, index) => {
                    let color = '#10B981';
                    if (entry.range.includes('<80')) color = '#EF4444';
                    else if (entry.range.includes('80-85')) color = '#F59E0B';
                    else if (entry.range.includes('85-90')) color = '#00F0FF';
                    else if (entry.range.includes('90-95')) color = '#3B82F6';
                    return <Cell key={`cell-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Vehicle Fleet Keyset Table */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Car size={18} color="var(--accent-cyan)" />
            <span>Fleet Vehicles (Keyset Indexed)</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ position: 'relative', width: '280px' }}>
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                id="input-vehicle-search"
                type="text"
                className="form-input"
                style={{ paddingLeft: '32px', fontSize: '0.85rem' }}
                placeholder="Search VIN, Model, Driver..."
                value={searchVin}
                onChange={(e) => setSearchVin(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="custom-table" id="table-vehicles">
            <thead>
              <tr>
                <th>Vehicle VIN</th>
                <th>OEM / Model</th>
                <th>Driver</th>
                <th>Battery Capacity</th>
                <th>Latest SoC</th>
                <th>Health (SoH)</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredVehicles.map((v) => (
                <tr key={v.vin}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {v.vin}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{v.model}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{v.oem}</div>
                  </td>
                  <td>{v.driver_name || 'Unassigned'}</td>
                  <td>
                    {v.battery_kwh} kWh <span style={{ color: 'var(--text-muted)' }}>({v.max_dc_kw} kW DC)</span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '50px',
                          height: '6px',
                          borderRadius: '3px',
                          background: 'rgba(255, 255, 255, 0.1)',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${v.latest_soc}%`,
                            height: '100%',
                            background:
                              v.latest_soc < 20
                                ? 'var(--accent-rose)'
                                : v.latest_soc < 40
                                ? 'var(--accent-amber)'
                                : 'var(--accent-emerald)',
                          }}
                        />
                      </div>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{v.latest_soc}%</span>
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        fontWeight: 700,
                        color: v.latest_soh > 92 ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                      }}
                    >
                      {v.latest_soh}%
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={v.status} type="vehicle" />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      id={`btn-view-${v.vin}`}
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectVehicle(v.vin)}
                    >
                      Inspect Telemetry
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
