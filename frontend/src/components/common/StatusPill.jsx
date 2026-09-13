import React from 'react';

const STATUS_CONFIGS = {
  // Operational & Monitoring States
  RUNNING: { label: 'RUNNING', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: true },
  ACTIVE: { label: 'ACTIVE', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: true },
  ONLINE: { label: 'ONLINE', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: true },
  CONNECTED: { label: 'CONNECTED', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: false },
  STOPPED: { label: 'STOPPED', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', pulse: false },
  OFFLINE: { label: 'OFFLINE', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', pulse: false },
  DISCONNECTED: { label: 'DISCONNECTED', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', pulse: false },
  STARTING: { label: 'STARTING', color: '#eab308', bg: 'rgba(234, 179, 8, 0.15)', pulse: true },
  STOPPING: { label: 'STOPPING', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)', pulse: true },
  ERROR: { label: 'ERROR', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', pulse: false },

  // System Health States
  HEALTHY: { label: 'HEALTHY', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: false },
  DEGRADED: { label: 'DEGRADED', color: '#eab308', bg: 'rgba(234, 179, 8, 0.15)', pulse: false },
  UNAVAILABLE: { label: 'UNAVAILABLE', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', pulse: false },

  // Alert Lifecycle States
  OPEN: { label: 'OPEN', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', pulse: true },
  ACKNOWLEDGED: { label: 'ACKNOWLEDGED', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)', pulse: false },
  RESOLVED: { label: 'RESOLVED', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulse: false },
  DISMISSED: { label: 'DISMISSED', color: '#64748b', bg: 'rgba(100, 116, 139, 0.15)', pulse: false },
};

export function StatusPill({ status = 'STOPPED', customLabel = null, size = 'md' }) {
  const normStatus = (status || 'STOPPED').toUpperCase();
  const config = STATUS_CONFIGS[normStatus] || {
    label: normStatus,
    color: '#94a3b8',
    bg: 'rgba(148, 163, 184, 0.15)',
    pulse: false,
  };

  const displayText = customLabel || config.label;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size] || 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-white/5 ${sizeClasses}`}
      style={{
        backgroundColor: config.bg,
        color: config.color,
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.pulse ? 'animate-pulse' : ''}`}
        style={{ backgroundColor: config.color }}
      />
      <span className="tracking-wide font-semibold">{displayText}</span>
    </span>
  );
}

export default StatusPill;
