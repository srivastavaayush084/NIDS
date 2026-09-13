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
      <div className="h-5 w-full bg-slate-950/80 rounded-full p-0.5 border border-white/10 overflow-hidden flex shadow-inner">
        {total > 0 ? (
          Object.entries(counts).map(([sev, count]) => {
            if (count === 0) return null;
            const pct = (count / total) * 100;
            const tier = SEVERITY_TIERS[sev] || SEVERITY_TIERS.LOW;
            return (
              <div
                key={sev}
                className="h-full first:rounded-l-full last:rounded-r-full transition-all duration-500 hover:opacity-90"
                style={{
                  width: `${pct}%`,
                  backgroundColor: tier.color,
                  boxShadow: sev === 'CRITICAL' ? '0 0 8px rgba(244, 63, 94, 0.4)' : undefined,
                }}
                title={`${sev}: ${count} (${pct.toFixed(1)}%)`}
              />
            );
          })
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-500 font-mono">
            Zero anomalous flows recorded
          </div>
        )}
      </div>

      {/* Legend & Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {Object.entries(counts).map(([sev, count]) => {
          const tier = SEVERITY_TIERS[sev] || SEVERITY_TIERS.LOW;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
          const hasIncidents = count > 0;

          return (
            <div
              key={sev}
              className={`p-3 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
                hasIncidents && sev === 'CRITICAL'
                  ? 'bg-rose-950/20 border-rose-500/30'
                  : hasIncidents && sev === 'HIGH'
                  ? 'bg-orange-950/20 border-orange-500/30'
                  : 'bg-slate-800/40 border-white/5'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      backgroundColor: tier.color,
                      boxShadow: hasIncidents ? `0 0 8px ${tier.color}` : undefined,
                    }}
                  />
                  <span className="text-[11px] font-semibold text-slate-300">{sev}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">{pct}%</span>
              </div>

              <div className="flex items-baseline justify-between mt-1">
                <span className="text-xl font-black font-mono text-slate-100">{count}</span>
              </div>

              {/* Micro proportion bar */}
              <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden mt-2">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: tier.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default SeverityDistributionChart;
