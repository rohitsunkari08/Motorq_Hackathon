import React from 'react';

interface StatCardProps {
  id: string;
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    positive: boolean;
  };
  glowColor?: 'cyan' | 'emerald' | 'purple' | 'amber';
}

export const StatCard: React.FC<StatCardProps> = ({
  id,
  title,
  value,
  subtitle,
  icon,
  trend,
  glowColor,
}) => {
  let glowStyle = {};
  if (glowColor === 'cyan') glowStyle = { borderBottom: '2px solid var(--accent-cyan)' };
  else if (glowColor === 'emerald') glowStyle = { borderBottom: '2px solid var(--accent-emerald)' };
  else if (glowColor === 'purple') glowStyle = { borderBottom: '2px solid var(--accent-purple)' };
  else if (glowColor === 'amber') glowStyle = { borderBottom: '2px solid var(--accent-amber)' };

  return (
    <div className="card" id={id} style={glowStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {title}
          </span>
          <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#ffffff', marginTop: '6px', fontFamily: 'var(--font-heading)' }}>
            {value}
          </div>
        </div>
        {icon && (
          <div
            style={{
              padding: '10px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.04)',
              color: 'var(--text-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
          {trend && (
            <span
              style={{
                color: trend.positive ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                fontWeight: 600,
              }}
            >
              {trend.positive ? '↑' : '↓'} {trend.value}
            </span>
          )}
          {subtitle && <span style={{ color: 'var(--text-muted)' }}>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
