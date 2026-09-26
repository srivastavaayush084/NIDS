import React from 'react';
import { useNavigate } from 'react-router-dom';
import { KPICards } from '../components/dashboard/KPICards';
import { MonitoringCard } from '../components/dashboard/MonitoringCard';
import { RecentAlertsTable } from '../components/dashboard/RecentAlertsTable';
import { SeverityDistributionChart } from '../components/charts/SeverityDistributionChart';
import { AlertTrendChart } from '../components/charts/AlertTrendChart';
import { ModelOverviewGrid } from '../components/dashboard/ModelOverviewGrid';
import { Card } from '../components/common/Card';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ShieldAlert, PieChart, Radio, Cpu, ArrowRight, ShieldCheck, Flame, Zap } from 'lucide-react';

export function Dashboard({
  summary = null,
  alertStats = null,
  monitoringStatus = null,
  recentAlerts = [],
  models = [],
  loading = false,
  error = null,
  onRefresh,
}) {
  const navigate = useNavigate();

  if (loading && !summary && !monitoringStatus) {
    return <LoadingSpinner message="Loading SOC Dashboard Telemetry..." size="lg" className="py-20" />;
  }

  const criticalCount = summary?.critical_alerts ?? summary?.severity_distribution?.CRITICAL ?? alertStats?.severity_distribution?.CRITICAL ?? 0;
  const openCount = summary?.open_alerts ?? summary?.active_alerts ?? alertStats?.status_distribution?.OPEN ?? 0;
  const isElevated = criticalCount > 0;

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      {/* SOC Operational Threat Posture Banner */}
      <div className={`p-6 sm:p-7 rounded-2xl border transition-all duration-300 relative overflow-hidden shadow-sm ${
        isElevated
          ? 'bg-gradient-to-r from-red-50 via-white to-white border-red-200'
          : openCount > 0
          ? 'bg-gradient-to-r from-amber-50 via-white to-white border-amber-200'
          : 'bg-gradient-to-r from-[#EAF2FF] via-white to-white border-[#E2E8F0]'
      }`}>
        {/* Subtle accent line on top */}
        <div
          className={`absolute top-0 left-0 right-0 h-[3px] ${
            isElevated
              ? 'bg-gradient-to-r from-transparent via-[#EF4444] to-transparent'
              : 'bg-gradient-to-r from-transparent via-[#2563EB] to-transparent'
          }`}
        />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-4">
            <div className={`p-3.5 rounded-2xl border shrink-0 ${
              isElevated
                ? 'bg-red-50 border-red-200 text-[#EF4444]'
                : 'bg-[#EAF2FF] border-[#2563EB]/25 text-[#2563EB]'
            }`}>
              {isElevated ? <Flame className="w-7 h-7 animate-pulse text-[#EF4444]" /> : <ShieldCheck className="w-7 h-7 text-[#10B981]" />}
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-3">
                <span className={`text-[11px] font-mono font-bold tracking-widest px-3 py-1 rounded-full border ${
                  isElevated
                    ? 'bg-red-50 text-[#EF4444] border-red-200 animate-pulse'
                    : 'bg-emerald-50 text-[#10B981] border-emerald-200'
                }`}>
                  {isElevated ? 'POSTURE: ELEVATED THREAT' : 'POSTURE: ALL CLEAR'}
                </span>
                <span className="text-[#64748B] text-xs font-medium">
                  Ensemble: <span className="text-[#10B981] font-mono font-semibold">4/4 Online</span> (IsoForest, Autoencoder, LSTM, RF)
                </span>
              </div>

              <h2 className="text-xl sm:text-2xl font-black text-[#0F172A] uppercase tracking-wide mt-1.5">
                Zero-Day AI Security Operations Center
              </h2>
              <p className="text-xs sm:text-sm text-[#64748B] mt-1">
                {isElevated
                  ? `${criticalCount} high-severity zero-day anomaly consensus incident(s) require immediate triage.`
                  : 'Real-time multi-model network traffic inspection active. Continuous consensus scoring operational.'}
              </p>
            </div>
          </div>

          {/* Quick SOC Actions */}
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            {isElevated && (
              <button
                onClick={() => navigate('/alerts?severity=CRITICAL')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#EF4444] hover:bg-red-600 text-white text-xs font-bold shadow-md shadow-red-500/20 transition"
              >
                <Flame className="w-4 h-4" />
                <span>Triage {criticalCount} Critical</span>
              </button>
            )}

            <button
              onClick={() => navigate('/monitoring')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white hover:bg-[#F8FAFC] text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition shadow-2xs"
            >
              <Radio className="w-4 h-4 text-[#10B981]" />
              <span>Live Ingestion</span>
            </button>

            <button
              onClick={() => navigate('/models')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white hover:bg-[#F8FAFC] text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition shadow-2xs"
            >
              <Cpu className="w-4 h-4 text-[#2563EB]" />
              <span>Model Registry</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={onRefresh} />}

      {/* Top KPI Cards */}
      <KPICards summary={summary} monitoringStatus={monitoringStatus} />

      {/* Primary Grid: Live Monitoring + Severity Distribution (Equal Width) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
        <MonitoringCard
          status={monitoringStatus}
          onNavigateToMonitoring={() => navigate('/monitoring')}
        />

        <Card
          title="Threat Severity Distribution"
          subtitle="Incident severity breakdown"
          icon={PieChart}
          className="h-full"
        >
          <SeverityDistributionChart
            data={
              summary?.severity_distribution ||
              summary?.alerts_by_severity ||
              alertStats?.severity_distribution ||
              alertStats?.severity_breakdown ||
              {}
            }
          />
        </Card>
      </div>

      {/* Middle Grid: Alert Trend Chart + Model Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card
          title="Detection & Alert Frequency"
          subtitle="Time-series attack telemetry"
          icon={ShieldAlert}
        >
          <AlertTrendChart points={summary?.trend_points} height={180} />
        </Card>

        <Card
          title="AI Model Ensemble Health"
          subtitle="Active registered detection engines"
          icon={Cpu}
          action={
            <button
              onClick={() => navigate('/models')}
              className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition"
            >
              <span>View All</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          }
        >
          <ModelOverviewGrid models={models} onSelectModel={() => navigate('/models')} />
        </Card>
      </div>

      {/* Recent High Priority Alerts Table */}
      <Card
        title="Recent High-Priority Security Incidents"
        subtitle="Latest anomalous flows requiring analyst review"
        icon={ShieldAlert}
        action={
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition"
          >
            <span>All Alerts</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        }
      >
        <RecentAlertsTable
          alerts={recentAlerts}
          onSelectAlert={(alertId) => navigate(`/alerts/${alertId}`)}
        />
      </Card>
    </div>
  );
}

export default Dashboard;
