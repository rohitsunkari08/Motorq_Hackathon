import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'severity' | 'vehicle' | 'role' | 'plan';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'severity' }) => {
  const norm = status.toLowerCase();

  let className = 'badge badge-info';
  let label = status;

  if (type === 'severity') {
    if (norm === 'critical') className = 'badge badge-critical';
    else if (norm === 'high') className = 'badge badge-high';
    else if (norm === 'warn' || norm === 'warning') className = 'badge badge-warn';
    else if (norm === 'info') className = 'badge badge-info';
  } else if (type === 'vehicle') {
    if (norm === 'active') className = 'badge badge-success';
    else if (norm === 'charging') className = 'badge badge-purple';
    else if (norm === 'warning') className = 'badge badge-warn';
    else if (norm === 'critical') className = 'badge badge-critical';
    else className = 'badge badge-secondary';
  } else if (type === 'role') {
    if (norm === 'admin') className = 'badge badge-purple';
    else if (norm === 'fleet_manager') className = 'badge badge-info';
    else className = 'badge badge-secondary';
    label = norm === 'fleet_manager' ? 'Fleet Manager' : norm === 'admin' ? 'Admin' : 'Viewer (Masked)';
  } else if (type === 'plan') {
    if (norm === 'approved') className = 'badge badge-success';
    else if (norm === 'proposed') className = 'badge badge-warn';
    else if (norm === 'rejected') className = 'badge badge-critical';
    else className = 'badge badge-info';
  }

  return (
    <span className={className} id={`badge-${norm}`}>
      {label}
    </span>
  );
};
