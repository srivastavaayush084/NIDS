import React from 'react';
import { SEVERITY_TIERS } from '../../utils/constants';

export function RiskScore({
  score = 0,
  threshold = 50.0,
  showLabel = true,
  showBar = true,
  size = 'md',
}) {
  const numericScore = Math.max(0, Math.min(100, Number(score) || 0));

  const getTier = (val) => {
    if (val >= 75) return SEVERITY_TIERS.CRITICAL;
    if (val >= 50) return SEVERITY_TIERS.HIGH;
    if (val >= 25) return SEVERITY_TIERS.MEDIUM;
    return SEVERITY_TIERS.LOW;
  };

  const tier = getTier(numericScore);

  const barHeight = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-2.5',
  }[size] || 'h-2';

  const textSize = {
    sm: 'text-xs',
    md: 'text-sm font-semibold',
    lg: 'text-base font-bold',
  }[size] || 'text-sm font-semibold';

  return (
    <div className="flex flex-col gap-1 w-full max-w-xs">
      <div className="flex items-center justify-between">
        {showLabel && (
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
            Risk Score
          </span>
        )}
        <span
          className={`${textSize} font-mono tracking-tight`}
          style={{ color: tier.color }}
        >
          {numericScore.toFixed(1)}
          <span className="text-[11px] text-slate-500 font-normal">/100</span>
        </span>
      </div>

      {showBar && (
        <div className={`relative w-full bg-slate-800 rounded-full overflow-hidden ${barHeight}`}>
          {/* Progress fill */}
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${numericScore}%`,
              backgroundColor: tier.color,
            }}
          />
          {/* Threshold marker */}
          {threshold > 0 && threshold < 100 && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white/70"
              style={{ left: `${threshold}%` }}
              title={`Decision Threshold: ${threshold}`}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default RiskScore;
