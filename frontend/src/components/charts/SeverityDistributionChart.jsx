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
      <div className="h-5 w-full bg-[#F8FAFC] rounded-full p-0.5 border border-[#E2E8F0] overflow-hidden flex shadow-inner">
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
                }}
                title={`${sev}: ${count} (${pct.toFixed(1)}%)`}
              />
            );
          })
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-[#64748B] font-mono">
            Zero anomalous flows recorded
          </div>
        )}
      </div>

      {/* Legend & Breakdown Cards: Clean 2x2 Grid with generous space */}
      <div className="grid grid-cols-2 gap-3.5">
        {Object.entries(counts).map(([sev, count]) => {
          const tier = SEVERITY_TIERS[sev] || SEVERITY_TIERS.LOW;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
          const hasIncidents = count > 0;

          return (
            <div
              key={sev}
              className={`p-3.5 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
                hasIncidents && sev === 'CRITICAL'
                  ? 'bg-red-50/60 border-red-200'
                  : hasIncidents && sev === 'HIGH'
                  ? 'bg-orange-50/60 border-orange-200'
                  : 'bg-[#F8FAFC] border-[#E2E8F0]'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{
                      backgroundColor: tier.color,
                    }}
                  />
                  <span className="text-xs font-bold tracking-wide text-[#0F172A]">{sev}</span>
                </div>
                <span className="text-[11px] font-mono font-semibold text-[#64748B]">{pct}%</span>
              </div>

              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-black font-mono text-[#0F172A]">{count}</span>
              </div>

              {/* Micro proportion bar */}
              <div className="w-full h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden mt-2.5">
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
