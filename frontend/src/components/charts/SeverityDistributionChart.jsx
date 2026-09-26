import React, { useState } from 'react';
import { SEVERITY_TIERS } from '../../utils/constants';

const TIERS_CONFIG = [
  { key: 'CRITICAL', label: 'Critical', color: '#EF4444', bg: 'rgba(239, 68, 68, 0.08)', border: 'rgba(239, 68, 68, 0.25)' },
  { key: 'HIGH', label: 'High', color: '#F97316', bg: 'rgba(249, 115, 22, 0.08)', border: 'rgba(249, 115, 22, 0.25)' },
  { key: 'MEDIUM', label: 'Medium', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.08)', border: 'rgba(245, 158, 11, 0.25)' },
  { key: 'LOW', label: 'Low', color: '#2563EB', bg: 'rgba(37, 99, 235, 0.08)', border: 'rgba(37, 99, 235, 0.25)' },
];

export function SeverityDistributionChart({ data = {} }) {
  const [hoveredKey, setHoveredKey] = useState(null);

  const counts = {
    CRITICAL: Number(data?.CRITICAL || data?.critical || 0),
    HIGH: Number(data?.HIGH || data?.high || 0),
    MEDIUM: Number(data?.MEDIUM || data?.medium || 0),
    LOW: Number(data?.LOW || data?.low || 0),
  };

  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  // SVG Geometry constants
  const size = 180;
  const center = size / 2;
  const radius = 62;
  const defaultStroke = 24;
  const activeStroke = 28;
  const circumference = 2 * Math.PI * radius;

  // Compute proportional arc segments
  let accumulatedRatio = 0;
  const segments = TIERS_CONFIG.map((tier) => {
    const count = counts[tier.key] || 0;
    const ratio = total > 0 ? count / total : 0;
    const strokeDasharray = `${ratio * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedRatio * circumference;
    accumulatedRatio += ratio;
    const pct = total > 0 ? (ratio * 100).toFixed(1) : '0.0';

    return {
      ...tier,
      count,
      pct,
      ratio,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const activeSegment = hoveredKey ? segments.find((s) => s.key === hoveredKey) : null;

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Interactive Pie / Donut Visual */}
      <div className="relative flex items-center justify-center">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90 drop-shadow-xs"
        >
          {/* Base Neutral Background Track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#F1F5F9"
            strokeWidth={defaultStroke}
          />

          {total > 0 ? (
            segments.map((seg) => {
              if (seg.count === 0) return null;
              const isHovered = hoveredKey === seg.key;
              const hasHover = hoveredKey !== null;

              return (
                <circle
                  key={seg.key}
                  cx={center}
                  cy={center}
                  r={radius}
                  fill="none"
                  stroke={seg.color}
                  strokeWidth={isHovered ? activeStroke : defaultStroke}
                  strokeDasharray={seg.strokeDasharray}
                  strokeDashoffset={seg.strokeDashoffset}
                  className="transition-all duration-300 cursor-pointer"
                  style={{
                    opacity: hasHover ? (isHovered ? 1.0 : 0.45) : 1.0,
                    filter: isHovered ? 'drop-shadow(0 2px 6px rgba(0, 0, 0, 0.18))' : 'none',
                  }}
                  onMouseEnter={() => setHoveredKey(seg.key)}
                  onMouseLeave={() => setHoveredKey(null)}
                >
                  <title>{`${seg.key}: ${seg.count.toLocaleString()} (${seg.pct}%)`}</title>
                </circle>
              );
            })
          ) : (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke="#E2E8F0"
              strokeWidth={defaultStroke}
              strokeDasharray="4, 4"
            />
          )}
        </svg>

        {/* Center Readout HUD */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center select-none"
          style={{ width: `${size}px`, height: `${size}px` }}
        >
          {activeSegment ? (
            <>
              <span
                className="text-2xl font-black font-mono tracking-tight animate-fade-in"
                style={{ color: activeSegment.color }}
              >
                {activeSegment.count.toLocaleString()}
              </span>
              <span
                className="text-[10px] font-bold uppercase tracking-wider mt-0.5"
                style={{ color: activeSegment.color }}
              >
                {activeSegment.label} ({activeSegment.pct}%)
              </span>
            </>
          ) : (
            <>
              <span className="text-2xl font-black font-mono tracking-tight text-[#0F172A]">
                {total.toLocaleString()}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] mt-0.5">
                {total === 0 ? 'No Threats' : 'Total Alerts'}
              </span>
            </>
          )}
        </div>
      </div>

      {/* 2x2 Interactive Legend Grid */}
      <div className="grid grid-cols-2 gap-2.5 w-full">
        {segments.map((seg) => {
          const isHovered = hoveredKey === seg.key;
          const hasHover = hoveredKey !== null;
          const isDominant = total > 0 && seg.count / total >= 0.5;

          return (
            <div
              key={seg.key}
              onMouseEnter={() => setHoveredKey(seg.key)}
              onMouseLeave={() => setHoveredKey(null)}
              className="p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col justify-between"
              style={{
                backgroundColor: isHovered ? seg.bg : '#F8FAFC',
                borderColor: isHovered ? seg.color : isDominant ? seg.border : '#E2E8F0',
                opacity: hasHover && !isHovered ? 0.6 : 1.0,
                transform: isHovered ? 'translateY(-1px)' : 'none',
                boxShadow: isHovered ? '0 2px 8px rgba(0, 0, 0, 0.06)' : 'none',
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0 transition-transform duration-200"
                    style={{
                      backgroundColor: seg.color,
                      transform: isHovered ? 'scale(1.25)' : 'scale(1)',
                      boxShadow: isHovered ? `0 0 6px ${seg.color}` : 'none',
                    }}
                  />
                  <span className="text-xs font-bold tracking-wide text-[#0F172A]">
                    {seg.key}
                  </span>
                </div>
                <span className="text-[11px] font-mono font-semibold text-[#64748B]">
                  {seg.pct}%
                </span>
              </div>

              <div className="flex items-baseline justify-between mt-2">
                <span className="text-lg font-black font-mono text-[#0F172A]">
                  {seg.count.toLocaleString()}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default SeverityDistributionChart;
