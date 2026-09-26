import React from 'react';

const STATUS_CONFIGS = {
  // Operational & Monitoring States
  RUNNING: { label: 'RUNNING', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: true },
  ACTIVE: { label: 'ACTIVE', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: true },
  ONLINE: { label: 'ONLINE', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: true },
  CONNECTED: { label: 'CONNECTED', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: false },
  STOPPED: { label: 'STOPPED', color: '#64748B', bg: 'rgba(100, 116, 139, 0.1)', pulse: false },
  OFFLINE: { label: 'OFFLINE', color: '#64748B', bg: 'rgba(100, 116, 139, 0.1)', pulse: false },
  DISCONNECTED: { label: 'DISCONNECTED', color: '#EF4444', bg: 'rgba(239, 68, 68, 0.1)', pulse: false },
  STARTING: { label: 'STARTING', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.1)', pulse: true },
  STOPPING: { label: 'STOPPING', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.1)', pulse: true },
  ERROR: { label: 'ERROR', color: '#EF4444', bg: 'rgba(239, 68, 68, 0.1)', pulse: false },

  // System Health States
  HEALTHY: { label: 'HEALTHY', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: false },
  DEGRADED: { label: 'DEGRADED', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.1)', pulse: false },
  UNAVAILABLE: { label: 'UNAVAILABLE', color: '#EF4444', bg: 'rgba(239, 68, 68, 0.1)', pulse: false },

  // Alert Lifecycle States
  OPEN: { label: 'OPEN', color: '#EF4444', bg: 'rgba(239, 68, 68, 0.1)', pulse: true },
  ACKNOWLEDGED: { label: 'ACKNOWLEDGED', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.1)', pulse: false },
  RESOLVED: { label: 'RESOLVED', color: '#10B981', bg: 'rgba(16, 185, 129, 0.1)', pulse: false },
  DISMISSED: { label: 'DISMISSED', color: '#64748B', bg: 'rgba(100, 116, 139, 0.1)', pulse: false },
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
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-[#E2E8F0] ${sizeClasses}`}
      style={{
        backgroundColor: config.bg,
        color: config.color,
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.pulse ? 'animate-pulse' : ''}`}
        style={{
          backgroundColor: config.color,
          boxShadow: config.pulse ? `0 0 8px ${config.color}` : undefined,
        }}
      />
      <span className="tracking-wide font-semibold">{displayText}</span>
    </span>
  );
}

export default StatusPill;
