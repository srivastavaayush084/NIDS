import React from 'react';
import { Radio, ArrowUpRight, HardDrive, AlertOctagon } from 'lucide-react';
import { StatusPill } from '../common/StatusPill';
import { formatNumber, formatDuration } from '../../utils/formatters';

export function MonitoringCard({ status = null, onNavigateToMonitoring }) {
  const isRunning = Boolean(status?.running);
  const source = status?.source || 'idle';
  const target = status?.target || (status?.available_interfaces?.find((i) => i.is_default)?.name || 'Ready');
  const uptime = status?.uptime_seconds || 0;
  const packets = status?.packets_captured || 0;
  const flows = status?.flows_created || 0;
  const anomalies = status?.anomalies_detected || 0;
  const alerts = status?.alerts_generated || 0;
  const dropped = status?.dropped_events || 0;
  const errors = status?.error_count || 0;
  const pktsPerSec = status?.throughput_pkts_sec || 0;
  const flowsPerSec = status?.throughput_flows_sec || 0;

  return (
    <div className="p-5 rounded-2xl border border-white/10 bg-slate-900/70 backdrop-blur-md shadow-xl flex flex-col justify-between relative overflow-hidden transition-all duration-200 hover:border-white/15">
      {/* Top subtle highlight line */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${
        isRunning
          ? 'bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent'
          : 'bg-gradient-to-r from-transparent via-white/10 to-transparent'
      }`} />

      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-lg ${isRunning ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Live Traffic Ingestion</h3>
            <p className="text-xs text-slate-400">
              {isRunning ? (
                <>
                  Source: <span className="font-mono text-slate-300 font-semibold">{source.toUpperCase()}</span> ({target})
                </>
              ) : (
                <>
                  Status: <span className="font-mono text-slate-300 font-semibold">IDLE</span> — Configured: <span className="text-indigo-300 font-mono">{target}</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <StatusPill status={isRunning ? 'RUNNING' : 'STOPPED'} />
          {onNavigateToMonitoring && (
            <button
              onClick={onNavigateToMonitoring}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              title="Open Live Monitoring"
            >
              <ArrowUpRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3 border-b border-white/5 text-xs">
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400">Session Uptime</span>
          <div className="font-mono font-bold text-slate-200 mt-0.5">{formatDuration(uptime)}</div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400">Packets Captured</span>
          <div className="font-mono font-bold text-slate-200 mt-0.5">{formatNumber(packets)} ({pktsPerSec} p/s)</div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400">Flows Ingested</span>
          <div className="font-mono font-bold text-indigo-300 mt-0.5">{formatNumber(flows)} ({flowsPerSec} f/s)</div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400">Anomalies / Alerts</span>
          <div className="font-mono font-bold text-rose-400 mt-0.5">{formatNumber(anomalies)} / {formatNumber(alerts)}</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2">
        <span className="flex items-center gap-1.5">
          <HardDrive className="w-3.5 h-3.5 text-slate-500" />
          Dropped Events: <span className="font-mono text-slate-300">{dropped}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <AlertOctagon className="w-3.5 h-3.5 text-slate-500" />
          Processing Errors: <span className="font-mono text-slate-300">{errors}</span>
        </span>
      </div>
    </div>
  );
}

export default MonitoringCard;
