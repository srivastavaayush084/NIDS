import React, { useState, useEffect } from 'react';
import { useMonitoring } from '../hooks/useMonitoring';
import { useDetection } from '../hooks/useDetection';
import { MonitoringControls } from '../components/monitoring/MonitoringControls';
import { MonitoringLiveFeed } from '../components/monitoring/MonitoringLiveFeed';
import { PCAPTestRunner } from '../components/monitoring/PCAPTestRunner';
import { ModelCompatibilityMatrix } from '../components/monitoring/ModelCompatibilityMatrix';
import { ThroughputChart } from '../components/charts/ThroughputChart';
import { Card } from '../components/common/Card';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { StatusPill } from '../components/common/StatusPill';
import { Radio, Activity, CheckCircle2, ShieldAlert, FileText } from 'lucide-react';
import { formatDuration, formatNumber } from '../utils/formatters';

export function Monitoring() {
  const {
    status,
    interfaces,
    driverInfo,
    compatibility,
    loading,
    error: statusError,
    actionLoading,
    refetch,
    startMonitoring,
    stopMonitoring,
    testPcap,
  } = useMonitoring(3000);

  const { detections } = useDetection({ page_size: 30 }, true);

  const isRunning = Boolean(status?.running);
  const uptime = status?.uptime_seconds || 0;
  const packets = status?.packets_captured || 0;
  const flows = status?.flows_created || 0;
  const anomalies = status?.anomalies_detected || 0;
  const alerts = status?.alerts_generated || 0;
  const pktsPerSec = status?.throughput_pkts_sec || 0;
  const flowsPerSec = status?.throughput_flows_sec || 0;
  const bufferUtil = status?.buffer_utilization_pct || 0;
  const statusMsg = status?.status_message || status?.message || (isRunning ? 'Monitoring active' : 'No active session');

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide flex items-center gap-2.5">
            <span>Real-Time Traffic Ingestion</span>
            <StatusPill status={status?.status || (isRunning ? 'RUNNING' : 'STOPPED')} />
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {statusMsg}
          </p>
        </div>
      </div>

      {status?.error && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="font-semibold">Pipeline Error:</span>
          <span>{status.error}</span>
        </div>
      )}

      {statusError && <ErrorAlert message={statusError} onRetry={refetch} />}

      {/* Top Telemetry Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Capture Status</span>
          <div className="text-sm font-bold font-mono text-slate-100 mt-1">
            {isRunning ? status?.source?.toUpperCase() || 'LIVE' : 'IDLE'}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Session Uptime</span>
          <div className="text-sm font-bold font-mono text-emerald-400 mt-1">
            {formatDuration(uptime)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Packets Captured</span>
          <div className="text-sm font-bold font-mono text-slate-100 mt-1">
            {formatNumber(packets)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Flows Aggregated</span>
          <div className="text-sm font-bold font-mono text-indigo-300 mt-1">
            {formatNumber(flows)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Anomalies Detected</span>
          <div className="text-sm font-bold font-mono text-rose-400 mt-1">
            {formatNumber(anomalies)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md">
          <span className="text-[10px] uppercase font-bold text-slate-400">Alerts Triggered</span>
          <div className="text-sm font-bold font-mono text-rose-300 mt-1">
            {formatNumber(alerts)}
          </div>
        </div>
      </div>

      {/* Real-time Throughput Meter */}
      <ThroughputChart
        pktsPerSec={pktsPerSec}
        flowsPerSec={flowsPerSec}
        bufferUtilPct={bufferUtil}
      />

      {/* Main Controls + PCAP Test Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MonitoringControls
          status={status}
          interfaces={interfaces}
          driverInfo={driverInfo}
          onStart={startMonitoring}
          onStop={stopMonitoring}
          loading={actionLoading}
        />

        <PCAPTestRunner
          onRunTest={testPcap}
          loading={actionLoading}
        />
      </div>

      {/* Model Feature Compatibility Matrix */}
      <ModelCompatibilityMatrix compatibility={compatibility} />

      {/* Real-Time Detection Feed */}
      <Card
        title="Live Traffic & Detection Event Stream"
        subtitle="Real-time flow records processed through the ML Ensemble Engine"
        icon={Activity}
      >
        <MonitoringLiveFeed events={detections} />
      </Card>
    </div>
  );
}

export default Monitoring;
