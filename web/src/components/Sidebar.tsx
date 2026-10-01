import React from 'react';
import {
  LayoutDashboard,
  Bell,
  Car,
  Bot,
  ShieldAlert,
  Sliders,
  Cpu,
} from 'lucide-react';

export type NavTab = 'overview' | 'alerts' | 'vehicles' | 'copilot' | 'admin';

interface SidebarProps {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  openAlertsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  openAlertsCount,
}) => {
  const navItems = [
    { id: 'overview' as NavTab, label: 'Fleet Overview', icon: LayoutDashboard },
    {
      id: 'alerts' as NavTab,
      label: 'Live Alerts',
      icon: Bell,
      badge: openAlertsCount > 0 ? openAlertsCount : undefined,
    },
    { id: 'vehicles' as NavTab, label: 'Vehicle & Plans', icon: Car },
    { id: 'copilot' as NavTab, label: 'Copilot Chat', icon: Bot, highlight: true },
    { id: 'admin' as NavTab, label: 'Compliance & Admin', icon: ShieldAlert },
  ];

  return (
    <aside
      id="main-sidebar"
      style={{
        width: '260px',
        backgroundColor: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px 16px',
        height: 'calc(100vh - 70px)',
        position: 'sticky',
        top: '70px',
      }}
    >
      <div>
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 12px 12px' }}>
          Platform Navigation
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;

            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onTabChange(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isActive
                    ? 'linear-gradient(90deg, rgba(0, 240, 255, 0.15) 0%, rgba(0, 240, 255, 0.03) 100%)'
                    : 'transparent',
                  color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  border: isActive ? '1px solid rgba(0, 240, 255, 0.3)' : '1px solid transparent',
                  cursor: 'pointer',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.9rem',
                  transition: 'all var(--transition-fast)',
                  textAlign: 'left',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon size={18} strokeWidth={isActive ? 2.5 : 2} />
                  <span>{item.label}</span>
                </div>

                {item.badge !== undefined && (
                  <span
                    className="badge badge-critical"
                    style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                  >
                    {item.badge}
                  </span>
                )}

                {item.highlight && !item.badge && (
                  <span
                    className="badge badge-purple"
                    style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                  >
                    AI
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Footer info */}
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <Cpu size={14} color="var(--accent-cyan)" />
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Architecture v1.0
          </span>
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
          Go Ingest · ClickHouse MV · Redis AP · Postgres 3NF · DP Benchmark
        </div>
      </div>
    </aside>
  );
};
