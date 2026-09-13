import React from 'react';

export function AlertTrendChart({
  points = [
    { label: '00:00', detections: 120, alerts: 4 },
    { label: '04:00', detections: 85, alerts: 1 },
    { label: '08:00', detections: 340, alerts: 12 },
    { label: '12:00', detections: 510, alerts: 18 },
    { label: '16:00', detections: 420, alerts: 9 },
    { label: '20:00', detections: 290, alerts: 6 },
  ],
  height = 160,
}) {
  if (!points || points.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-xs text-slate-500">
        No time-series telemetry available
      </div>
    );
  }

  const maxVal = Math.max(...points.map((p) => Math.max(p.detections || 0, p.alerts || 0)), 10);

  return (
    <div className="flex flex-col gap-2">
      {/* Legend */}
      <div className="flex items-center justify-end gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500" />
          <span className="text-slate-400">Total Detections</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-rose-500" />
          <span className="text-slate-400">Security Alerts</span>
        </div>
      </div>

      {/* SVG Responsive Area & Bars */}
      <div className="relative w-full overflow-hidden" style={{ height: `${height}px` }}>
        <svg className="w-full h-full" viewBox="0 0 500 120" preserveAspectRatio="none">
          <defs>
            <linearGradient id="detectionAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="alertBarGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fb7185" />
              <stop offset="100%" stopColor="#e11d48" />
            </linearGradient>
            <filter id="lineGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#6366f1" floodOpacity="0.5" />
            </filter>
          </defs>

          {/* Grid lines */}
          <line x1="0" y1="30" x2="500" y2="30" stroke="rgba(255,255,255,0.05)" strokeDasharray="3,3" />
          <line x1="0" y1="60" x2="500" y2="60" stroke="rgba(255,255,255,0.05)" strokeDasharray="3,3" />
          <line x1="0" y1="90" x2="500" y2="90" stroke="rgba(255,255,255,0.05)" strokeDasharray="3,3" />

          {/* Detections Area Fill */}
          {points.length > 1 && (
            <polygon
              fill="url(#detectionAreaGradient)"
              points={`10,110 ${points
                .map((p, idx) => {
                  const x = (idx / (points.length - 1)) * 480 + 10;
                  const y = 110 - ((p.detections || 0) / maxVal) * 95;
                  return `${x},${y}`;
                })
                .join(' ')} 490,110`}
            />
          )}

          {/* Detections Line Path */}
          {points.length > 1 && (
            <polyline
              fill="none"
              stroke="#818cf8"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#lineGlow)"
              points={points
                .map((p, idx) => {
                  const x = (idx / (points.length - 1)) * 480 + 10;
                  const y = 110 - ((p.detections || 0) / maxVal) * 95;
                  return `${x},${y}`;
                })
                .join(' ')}
            />
          )}

          {/* Alerts Bars */}
          {points.map((p, idx) => {
            const x = (idx / (points.length - 1)) * 480 + 6;
            const barHeight = Math.max(3, ((p.alerts || 0) / maxVal) * 95);
            const y = 110 - barHeight;
            return (
              <rect
                key={`bar-${idx}`}
                x={x}
                y={y}
                width="8"
                height={barHeight}
                rx="3"
                fill="url(#alertBarGradient)"
                opacity="0.9"
              >
                <title>{`${p.label}: ${p.alerts} alerts, ${p.detections} detections`}</title>
              </rect>
            );
          })}

          {/* Node circles on detection points */}
          {points.map((p, idx) => {
            const cx = (idx / (points.length - 1)) * 480 + 10;
            const cy = 110 - ((p.detections || 0) / maxVal) * 95;
            return (
              <circle
                key={`node-${idx}`}
                cx={cx}
                cy={cy}
                r="3"
                fill="#060913"
                stroke="#a5b4fc"
                strokeWidth="2"
              >
                <title>{`${p.label}: ${p.detections} total detections`}</title>
              </circle>
            );
          })}
        </svg>
      </div>

      {/* X-Axis Labels */}
      <div className="flex justify-between text-[10px] text-slate-500 font-mono px-2">
        {points.map((p, idx) => (
          <span key={idx}>{p.label}</span>
        ))}
      </div>
    </div>
  );
}

export default AlertTrendChart;
