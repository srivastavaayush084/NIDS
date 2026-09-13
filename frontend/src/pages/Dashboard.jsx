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
import { ShieldAlert, BarChart3, Radio, Cpu, ArrowRight } from 'lucide-react';

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

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide">
            Security Operations Center
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-model zero-day threat detection, traffic ingestion, and alert triage.
          </p>
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
