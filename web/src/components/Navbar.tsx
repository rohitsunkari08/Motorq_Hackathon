import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { StatusBadge } from './StatusBadge';
import { Zap, ShieldCheck, Activity, LogOut, ChevronDown } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout, switchRole, activeFleetId, setActiveFleetId } = useAuth();

  const fleets = [
    { id: 1, name: 'VoltFleet Logistics' },
    { id: 2, name: 'MetroDelivery Corp' },
    { id: 3, name: 'GreenHaul Transit' },
  ];

  return (
    <header
      id="main-navbar"
      style={{
        height: '70px',
        borderBottom: '1px solid var(--border-color)',
        background: 'rgba(10, 13, 20, 0.85)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      {/* Brand & Live System Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #00F0FF 0%, #8B5CF6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-glow-cyan)',
            }}
          >
            <Zap size={20} color="#05101a" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em', color: '#fff' }}>
              EVC <span style={{ color: 'var(--accent-cyan)' }}>COPILOT</span>
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              EV Fleet Intelligence & DP
            </div>
          </div>
        </div>

        {/* Live Ingest Badge */}
        <div
          id="system-status-indicator"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            padding: '4px 12px',
            borderRadius: 'var(--radius-full)',
            fontSize: '0.75rem',
            color: 'var(--accent-emerald)',
          }}
        >
          <span className="status-dot active"></span>
          <span>Redpanda: <strong>114k ev/s</strong></span>
          <span style={{ color: 'var(--border-color)' }}>|</span>
          <span>ClickHouse: <strong>Active</strong></span>
        </div>
      </div>

      {/* Fleet Selector, Role Quick Switcher & User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Fleet Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Tenant:</span>
          <select
            id="tenant-select"
            className="form-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
            value={activeFleetId}
            onChange={(e) => setActiveFleetId(Number(e.target.value))}
          >
            {fleets.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>

        {/* Role Switcher (For Demo & Location Masking Proof) */}
        {user && (
          <div
            id="role-switch-container"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '4px 8px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
            }}
          >
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Role:</span>
            {(['fleet_manager', 'viewer', 'admin'] as UserRole[]).map((r) => (
              <button
                key={r}
                id={`btn-role-${r}`}
                onClick={() => switchRole(r)}
                style={{
                  background: user.role === r ? 'var(--accent-cyan-dim)' : 'transparent',
                  color: user.role === r ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  border: user.role === r ? '1px solid rgba(0, 240, 255, 0.3)' : '1px solid transparent',
                  borderRadius: 'var(--radius-sm)',
                  padding: '3px 8px',
                  fontSize: '0.75rem',
                  fontWeight: user.role === r ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
              >
                {r === 'fleet_manager' ? 'Manager' : r === 'viewer' ? 'Viewer (Masked)' : 'Admin'}
              </button>
            ))}
          </div>
        )}

        {/* User Profile */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>{user.email}</div>
              <StatusBadge status={user.role} type="role" />
            </div>

            <button
              id="btn-logout"
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
              style={{ padding: '8px' }}
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
