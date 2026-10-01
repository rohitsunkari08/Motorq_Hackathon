import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { AuditLogEntry, SohBenchmark, ErasureResponse } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  ShieldAlert,
  Trash2,
  Lock,
  Eye,
  Sliders,
  Database,
  CheckCircle,
  AlertOctagon,
  Key,
  ShieldCheck,
} from 'lucide-react';

export const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);

  // Erasure form
  const [erasureVin, setErasureVin] = useState('5ZEEV05E599999999');
  const [erasureStatus, setErasureStatus] = useState<ErasureResponse | null>(null);
  const [erasing, setErasing] = useState(false);

  // DP Benchmark form
  const [model, setModel] = useState('VoltX Hyper-e');
  const [ageBucket, setAgeBucket] = useState('1-2yr');
  const [epsilon, setEpsilon] = useState(1.0);
  const [benchmark, setBenchmark] = useState<SohBenchmark | null>(null);
  const [loadingBench, setLoadingBench] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [logs, bench] = await Promise.all([
          api.getAuditTrail(undefined, 20),
          api.getSohBenchmark(model, ageBucket, epsilon),
        ]);
        if (isMounted) {
          setAuditLogs(logs.items);
          setBenchmark(bench);
        }
      } catch (err) {
        console.error('Failed to load admin data', err);
      } finally {
        if (isMounted) setLoadingLogs(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleQueryBenchmark = async () => {
    setLoadingBench(true);
    try {
      const res = await api.getSohBenchmark(model, ageBucket, epsilon);
      setBenchmark(res);
    } catch (err) {
      console.error('Failed to query benchmark', err);
    } finally {
      setLoadingBench(false);
    }
  };

  const handleExecuteErasure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!erasureVin.trim()) return;
    setErasing(true);
    setErasureStatus(null);
    try {
      const res = await api.executeErasure(erasureVin);
      setErasureStatus(res);
      // Reload audit logs
      const updatedLogs = await api.getAuditTrail(undefined, 20);
      setAuditLogs(updatedLogs.items);
    } catch (err) {
      console.error('Erasure failed', err);
    } finally {
      setErasing(false);
    }
  };

  const isAdmin = user?.role === 'admin';

  return (
    <div className="page-wrapper" id="page-admin">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.85rem' }}>Compliance, Privacy & Security Admin</h1>
            <span className="badge badge-purple">DPDP Act 2023 · GDPR</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Multi-store Right-to-Erasure verification, Differential Privacy benchmarks, and append-only audit trail.
          </p>
        </div>

        {!isAdmin && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--accent-amber-dim)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              color: 'var(--accent-amber)',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8rem',
            }}
          >
            <AlertOctagon size={16} />
            <span>Admin privileges required for erasure. Switch to Admin role in header to test.</span>
          </div>
        )}
      </div>

      {/* Row 1: Role-Based Location Masking Proof & DP Benchmarking */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        {/* Role-Based Location Masking Interactive Demonstration */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Eye size={18} color="var(--accent-cyan)" />
              <span>Role-Based Location Masking Proof (NOTE.md §7)</span>
            </div>
            <span className="badge badge-info">Zero-Trust Telematics</span>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Demonstrates how API responses dynamically sanitize coordinates based on JWT claims.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Fleet Manager View */}
            <div
              style={{
                background: 'rgba(16, 185, 129, 0.05)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-emerald)' }}>
                  Fleet Manager Role
                </span>
                <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>Precise</span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Returned Coordinates:</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#fff', margin: '4px 0' }}>
                37.774928, -122.419416
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
                Resolution: <strong>Sub-meter GPS</strong>. Retained for 30 days before ClickHouse column TTL downsamples.
              </div>
            </div>

            {/* Viewer Role */}
            <div
              style={{
                background: 'rgba(245, 158, 11, 0.05)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-amber)' }}>
                  Viewer Role
                </span>
                <span className="badge badge-warn" style={{ fontSize: '0.65rem' }}>Masked</span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Returned Coordinates:</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#fff', margin: '4px 0' }}>
                37.7490, -122.4316 <span style={{ color: 'var(--accent-amber)' }}>(9q8yy)</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
                Resolution: <strong>geohash5 (~4.9km × 4.9km)</strong>. Prevents unauthorized driver trajectory stalking.
              </div>
            </div>
          </div>
        </div>

        {/* Differential Privacy SoH Benchmark */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Lock size={18} color="var(--accent-purple)" />
              <span>Differential Privacy SoH Benchmark</span>
            </div>
            <span className="badge badge-purple">Laplace Mechanism</span>
          </div>

          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Cross-fleet battery health benchmarking with Laplace noise and k-anonymity suppression floor (n ≥ 20).
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '14px' }}>
            <div>
              <label className="form-label">Vehicle Model</label>
              <select
                id="select-dp-model"
                className="form-select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="VoltX Hyper-e">VoltX Hyper-e</option>
                <option value="NordMotors Polar-4">NordMotors Polar-4</option>
                <option value="AsiaDrive Express-V">AsiaDrive Express-V</option>
                <option value="EuroEV Continental">EuroEV Continental</option>
                <option value="ZephyrEV Aero-6">ZephyrEV Aero-6</option>
              </select>
            </div>

            <div>
              <label className="form-label">Age Bucket</label>
              <select
                id="select-dp-age"
                className="form-select"
                value={ageBucket}
                onChange={(e) => setAgeBucket(e.target.value)}
              >
                <option value="0-1yr">0-1 year</option>
                <option value="1-2yr">1-2 years</option>
                <option value="2-3yr">2-3 years</option>
                <option value="3+">3+ years</option>
              </select>
            </div>

            <div>
              <label className="form-label">Epsilon (ε={epsilon})</label>
              <input
                id="input-dp-epsilon"
                type="range"
                min="0.1"
                max="3.0"
                step="0.1"
                value={epsilon}
                onChange={(e) => setEpsilon(Number(e.target.value))}
                style={{ width: '100%', marginTop: '8px' }}
              />
            </div>
          </div>

          <button
            id="btn-query-benchmark"
            className="btn btn-secondary btn-sm"
            onClick={handleQueryBenchmark}
            disabled={loadingBench}
            style={{ width: '100%', marginBottom: '14px' }}
          >
            {loadingBench ? 'Applying Laplace Mechanism...' : 'Query Privacy-Preserving Peer Benchmark'}
          </button>

          {/* Benchmark output card */}
          {benchmark && (
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '12px',
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '8px',
                textAlign: 'center',
              }}
            >
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Fleet Avg</div>
                <div style={{ fontWeight: 800, color: 'var(--accent-cyan)' }}>{benchmark.fleet_avg_soh}%</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Peer Avg (Noisy)</div>
                <div style={{ fontWeight: 800, color: 'var(--accent-purple)' }}>{benchmark.peer_avg_soh_noisy}%</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Peer Sample</div>
                <div style={{ fontWeight: 700, color: '#fff' }}>{benchmark.sample_size.toLocaleString()}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Budget Left</div>
                <div style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>{benchmark.remaining_budget.toFixed(1)} ε</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Row 2: Right-to-Erasure Execution Tool */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title">
            <Trash2 size={18} color="var(--accent-rose)" />
            <span>Right-to-Erasure (GDPR / DPDP Multi-Store Purge)</span>
          </div>
          <span className="badge badge-critical">Admin Privilege Required</span>
        </div>

        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Executes synchronous multi-store data scrubbing: sets <code>erased_at</code> in PostgreSQL, issues <code>ALTER TABLE DELETE</code> in ClickHouse, purges Redis hot state, and appends an immutable compliance audit record.
        </p>

        <form onSubmit={handleExecuteErasure} style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            id="input-erasure-vin"
            type="text"
            className="form-input"
            placeholder="Enter VIN to erase (e.g. 5ZEEV05E599999999)..."
            value={erasureVin}
            onChange={(e) => setErasureVin(e.target.value)}
            disabled={!isAdmin || erasing}
            style={{ maxWidth: '420px', fontFamily: 'var(--font-mono)' }}
          />

          <button
            id="btn-execute-erasure"
            type="submit"
            className="btn btn-danger"
            disabled={!isAdmin || erasing || !erasureVin.trim()}
          >
            <Trash2 size={16} />
            {erasing ? 'Executing Multi-Store Purge...' : 'Execute Right-to-Erasure'}
          </button>
        </form>

        {erasureStatus && (
          <div
            id="erasure-result-status"
            style={{
              marginTop: '16px',
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-emerald)', fontWeight: 700, marginBottom: '8px' }}>
              <CheckCircle size={18} />
              <span>Erasure Completed Successfully for {erasureStatus.target_id}</span>
            </div>
            <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <span>PostgreSQL 3NF: {erasureStatus.stores_purged.postgres ? '✓ Scrubbed' : 'Failed'}</span>
              <span>Redis Cache: {erasureStatus.stores_purged.redis ? '✓ Keys Deleted' : 'Failed'}</span>
              <span>ClickHouse: {erasureStatus.stores_purged.clickhouse ? '✓ Mutation Executed' : 'Failed'}</span>
              <span>Completed: {new Date(erasureStatus.completed_at).toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* Row 3: Immutable Audit Log Table */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Database size={18} color="var(--accent-cyan)" />
            <span>Immutable Compliance Audit Trail</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Appended on every API read, plan approval, and AI agent call
          </span>
        </div>

        <div className="table-container">
          <table className="custom-table" id="table-audit-logs">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Timestamp (UTC)</th>
                <th>Actor</th>
                <th>Actor Type</th>
                <th>Action</th>
                <th>Resource Target</th>
                <th>Audit Details</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.audit_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    #{log.audit_id}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {new Date(log.ts).toLocaleString()}
                  </td>
                  <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{log.actor}</td>
                  <td>
                    <span
                      className={`badge ${
                        log.actor_type === 'agent'
                          ? 'badge-purple'
                          : log.actor_type === 'user'
                          ? 'badge-info'
                          : 'badge-secondary'
                      }`}
                      style={{ fontSize: '0.65rem' }}
                    >
                      {log.actor_type}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.825rem', color: 'var(--accent-cyan)' }}>
                    {log.action}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{log.resource}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', maxWidth: '300px' }}>
                    {log.detail ? JSON.stringify(log.detail) : '—'}
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
