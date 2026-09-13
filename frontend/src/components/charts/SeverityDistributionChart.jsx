import React from 'react';
import { SEVERITY_TIERS } from '../../utils/constants';

export function SeverityDistributionChart({ data = {} }) {
  const counts = {
    CRITICAL: Number(data?.CRITICAL || data?.critical || 0),
    HIGH: Number(data?.HIGH || data?.high || 0),
    MEDIUM: Number(data?.MEDIUM || data?.medium || 0),
    LOW: Number(data?.LOW || data?.low || 0),
  };

  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-col gap-4">
      {/* Distribution Progress Bar */}
      <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden flex">
        {total > 0 ? (
          Object.entries(counts).map(([sev, count]) => {
            if (count === 0) return null;
            const pct = (count / total) * 100;
            const tier = SEVERITY_TIERS[sev] || SEVERITY_TIERS.LOW;
            return (
              <div
                key={sev}
                className="h-full transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  backgroundColor: tier.color,
                }}
                title={`${sev}: ${count} (${pct.toFixed(1)}%)`}
              />
            );
          })
        ) : (
          <div className="w-full h-full bg-slate-800 flex items-center justify-center text-[10px] text-slate-500">
            No incidents recorded
          </div>
        )}
      </div>

      {/* Legend & Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {Object.entries(counts).map(([sev, count]) => {
          const tier = SEVERITY_TIERS[sev] || SEVERITY_TIERS.LOW;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
          return (
            <div
              key={sev}
              className="p-3 rounded-lg border border-white/5 bg-slate-800/40 flex flex-col"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: tier.color }}
                />
                <span className="text-[11px] font-semibold text-slate-300">{sev}</span>
              </div>
              <div className="flex items-baseline justify-between mt-auto">
                <span className="text-lg font-bold font-mono text-slate-100">{count}</span>
                <span className="text-[11px] font-mono text-slate-400">{pct}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default SeverityDistributionChart;
