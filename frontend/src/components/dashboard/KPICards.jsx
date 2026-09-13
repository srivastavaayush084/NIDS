import React from 'react';
import { Activity, AlertTriangle, ShieldAlert, Zap, TrendingUp } from 'lucide-react';
import { formatNumber } from '../../utils/formatters';

export function KPICards({ summary = null }) {
  const totalDetections = summary?.total_detections ?? summary?.detections_count ?? 0;
  const totalAnomalies = summary?.total_anomalies ?? summary?.anomalies_count ?? 0;
  const openAlerts = summary?.open_alerts ?? summary?.active_alerts ?? summary?.alerts_by_status?.OPEN ?? 0;
  const criticalAlerts = summary?.critical_alerts ?? summary?.severity_distribution?.CRITICAL ?? summary?.alerts_by_severity?.CRITICAL ?? 0;
  const avgRiskScore = summary?.average_risk_score ?? summary?.avg_risk_score ?? 0;

  const cards = [
    {
      label: 'Total Detections',
      value: formatNumber(totalDetections),
      subtext: `${summary?.detection_rate_per_sec || 0} events/sec`,
      icon: Activity,
      color: '#6366f1',
      bg: 'rgba(99, 102, 241, 0.12)',
    },
    {
      label: 'Anomalies Detected',
      value: formatNumber(totalAnomalies),
      subtext: `${totalDetections > 0 ? ((totalAnomalies / totalDetections) * 100).toFixed(1) : 0}% anomaly rate`,
      icon: Zap,
      color: '#ec4899',
      bg: 'rgba(236, 72, 153, 0.12)',
    },
    {
      label: 'Active Security Alerts',
      value: formatNumber(openAlerts),
      subtext: `${criticalAlerts} critical incidents`,
      icon: ShieldAlert,
      color: '#f97316',
      bg: 'rgba(249, 115, 22, 0.12)',
    },
    {
      label: 'Critical Incidents',
      value: formatNumber(criticalAlerts),
      subtext: 'Requires immediate triage',
      icon: AlertTriangle,
      color: '#ef4444',
      bg: 'rgba(239, 68, 68, 0.12)',
    },
    {
      label: 'Average Risk Score',
      value: `${Number(avgRiskScore).toFixed(1)}/100`,
      subtext: avgRiskScore >= 50 ? 'Elevated threat level' : 'Normal risk profile',
      icon: TrendingUp,
      color: avgRiskScore >= 50 ? '#ef4444' : '#10b981',
      bg: avgRiskScore >= 50 ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="p-4 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md shadow-md flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                {card.label}
              </span>
              <div
                className="p-1.5 rounded-lg shrink-0"
                style={{ backgroundColor: card.bg, color: card.color }}
              >
                <Icon className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-extrabold font-mono text-slate-100">{card.value}</div>
              <p className="text-[11px] text-slate-400 mt-1">{card.subtext}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default KPICards;
