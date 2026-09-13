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
import { ShieldAlert, BarChart3, Radio, Cpu, ArrowRight, ShieldCheck, Flame, Zap } from 'lucide-react';

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
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* SOC Operational Threat Posture Banner */}
      <div className={`p-4 sm:p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden backdrop-blur-xl ${
        isElevated
          ? 'bg-gradient-to-r from-rose-950/40 via-slate-900/80 to-slate-900/80 border-rose-500/30 shadow-lg shadow-rose-950/20'
          : openCount > 0
          ? 'bg-gradient-to-r from-amber-950/30 via-slate-900/80 to-slate-900/80 border-amber-500/30'
          : 'bg-gradient-to-r from-indigo-950/30 via-slate-900/80 to-slate-900/80 border-white/10'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start sm:items-center gap-3.5">
            <div className={`p-3 rounded-xl border shrink-0 ${
              isElevated
                ? 'bg-rose-500/20 border-rose-500/40 text-rose-400 glow-critical'
                : 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400 glow-indigo'
            }`}>
              {isElevated ? <Flame className="w-6 h-6 animate-pulse" /> : <ShieldCheck className="w-6 h-6" />}
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <span className={`text-[11px] font-mono font-bold tracking-widest px-2.5 py-0.5 rounded-full border ${
                  isElevated
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                    : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                }`}>
                  {isElevated ? 'POSTURE: ELEVATED THREAT' : 'POSTURE: ALL CLEAR'}
                </span>
                <span className="text-slate-400 text-xs font-medium">
                  Ensemble: <span className="text-slate-200 font-mono font-semibold">4/4 Online</span> (IsoForest, Autoencoder, LSTM, RF)
                </span>
              </div>

              <h2 className="text-lg sm:text-xl font-black text-slate-100 uppercase tracking-wide mt-1">
                Zero-Day AI Security Operations Center
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {isElevated
                  ? `${criticalCount} high-severity zero-day anomaly consensus incident(s) require immediate triage.`
                  : 'Real-time multi-model network traffic inspection active. Continuous consensus scoring operational.'}
              </p>
            </div>
          </div>

          {/* Quick SOC Actions */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {isElevated && (
              <button
                onClick={() => navigate('/alerts?severity=CRITICAL')}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-lg shadow-rose-600/30 border border-rose-400/30 transition"
              >
                <Flame className="w-3.5 h-3.5" />
                <span>Triage {criticalCount} Critical</span>
              </button>
            )}

            <button
              onClick={() => navigate('/monitoring')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-white/10 transition"
            >
              <Radio className="w-3.5 h-3.5 text-emerald-400" />
              <span>Live Ingestion</span>
            </button>

            <button
              onClick={() => navigate('/models')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-white/10 transition"
            >
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>Model Registry</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={onRefresh} />}

      {/* Top KPI Cards */}
      <KPICards summary={summary} monitoringStatus={monitoringStatus} />

      {/* Primary Grid: Live Monitoring + Severity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <MonitoringCard
            status={monitoringStatus}
            onNavigateToMonitoring={() => navigate('/monitoring')}
          />
        </div>

        <Card
          title="Threat Severity Distribution"
          subtitle="Incident severity breakdown"
          icon={BarChart3}
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Detection & Alert Frequency"
          subtitle="Time-series attack telemetry"
          icon={ShieldAlert}
        >
          <AlertTrendChart points={summary?.trend_points} />
        </Card>

        <Card
          title="AI Model Ensemble Health"
          subtitle="Active registered detection engines"
          icon={Cpu}
          action={
            <button
              onClick={() => navigate('/models')}
              className="flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
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
            className="flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition"
          >
            <span>All Alerts</span>
            <ArrowRight className="w-3.5 h-3.5" />
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
