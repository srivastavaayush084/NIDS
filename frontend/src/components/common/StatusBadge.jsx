import React from 'react';

export function StatusBadge({ status, label }) {
  const isHealthy = status === 'healthy' || status === 'initialized' || status === 'OPEN';
  const isWarning = status === 'standby' || status === 'ACKNOWLEDGED';
  const isDanger = status === 'disconnected' || status === 'error' || status === 'CRITICAL' || status === 'HIGH';

  let colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  let dotColor = 'bg-emerald-400';

  if (isDanger) {
    colorClasses = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    dotColor = 'bg-rose-400';
  } else if (isWarning) {
    colorClasses = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    dotColor = 'bg-amber-400';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${colorClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} animate-pulse`} />
      {label || status}
    </span>
  );
}
