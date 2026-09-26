import React from 'react';
import { Activity, AlertTriangle, ShieldAlert, Zap, TrendingUp } from 'lucide-react';
import { formatNumber } from '../../utils/formatters';

export function KPICards({ summary = null, monitoringStatus = null }) {
  const totalDetections = summary?.total_detections ?? summary?.detections_count ?? 0;
  const totalAnomalies = summary?.total_anomalies ?? summary?.anomalies_count ?? 0;
  const openAlerts = summary?.open_alerts ?? summary?.active_alerts ?? summary?.alerts_by_status?.OPEN ?? 0;
  const criticalAlerts = summary?.critical_alerts ?? summary?.severity_distribution?.CRITICAL ?? summary?.alerts_by_severity?.CRITICAL ?? 0;
  const avgRiskScore = summary?.average_risk_score ?? summary?.avg_risk_score ?? 0;

  const isLive = Boolean(monitoringStatus?.running);
  const liveRate = isLive
    ? (monitoringStatus?.throughput_flows_sec || monitoringStatus?.flows_per_second || summary?.detection_rate_per_sec || 0)
    : (summary?.detection_rate_per_sec || 0);

  const cards = [
    {
      label: 'Total Detections',
      value: formatNumber(totalDetections),
      subtext: isLive
        ? `${Number(liveRate).toFixed(1)} events/sec (Live)`
        : '0 events/sec (Idle)',
      icon: Activity,
      color: '#2563EB',
      bg: 'rgba(37, 99, 235, 0.08)',
    },
    {
      label: 'Anomalies Detected',
      value: formatNumber(totalAnomalies),
      subtext: `${totalDetections > 0 ? ((totalAnomalies / totalDetections) * 100).toFixed(1) : 0}% anomaly rate`,
      icon: Zap,
      color: '#4F46E5',
      bg: 'rgba(79, 70, 229, 0.08)',
    },
    {
      label: 'Active Security Alerts',
      value: formatNumber(openAlerts),
      subtext: `${criticalAlerts} critical incidents`,
      icon: ShieldAlert,
      color: '#F59E0B',
      bg: 'rgba(245, 158, 11, 0.08)',
    },
    {
      label: 'Critical Incidents',
      value: formatNumber(criticalAlerts),
      subtext: 'Requires immediate triage',
      icon: AlertTriangle,
      color: '#EF4444',
      bg: 'rgba(239, 68, 68, 0.08)',
    },
    {
      label: 'Average Risk Score',
      value: `${Number(avgRiskScore).toFixed(1)}/100`,
      subtext: avgRiskScore >= 50 ? 'Elevated threat level' : 'Normal risk profile',
      icon: TrendingUp,
      color: avgRiskScore >= 50 ? '#EF4444' : '#10B981',
      bg: avgRiskScore >= 50 ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-5 sm:gap-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="p-5 sm:p-6 rounded-2xl border border-[#E2E8F0] bg-white shadow-xs flex flex-col justify-between relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-[#CBD5E1] hover:shadow-md group"
          >
            {/* Top Color Accent Line */}
            <div
              className="absolute top-0 left-0 right-0 h-[3px] transition-opacity duration-200"
              style={{
                background: `linear-gradient(to right, transparent, ${card.color}, transparent)`,
              }}
            />

            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748B] group-hover:text-[#0F172A] transition-colors">
                {card.label}
              </span>
              <div
                className="p-2.5 rounded-xl shrink-0 transition-transform duration-200 group-hover:scale-105"
                style={{
                  backgroundColor: card.bg,
                  color: card.color,
                }}
              >
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div>
              <div className="text-3xl font-extrabold font-mono text-[#0F172A] tracking-tight">
                {card.value}
              </div>
              <p className="text-xs text-[#64748B] mt-1.5 flex items-center justify-between">
                <span>{card.subtext}</span>
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default KPICards;
