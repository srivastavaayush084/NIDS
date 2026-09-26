import React from 'react';
import { Radio, ArrowUpRight, HardDrive, AlertOctagon, Clock, Activity, Zap, AlertTriangle } from 'lucide-react';
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
    <div className="p-6 sm:p-7 rounded-2xl border border-[#E2E8F0] bg-white shadow-xs flex flex-col justify-between relative overflow-hidden transition-all duration-200 hover:border-[#CBD5E1] hover:shadow-md h-full">
      {/* Top subtle highlight line */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${
        isRunning
          ? 'bg-gradient-to-r from-transparent via-[#10B981]/50 to-transparent'
          : 'bg-gradient-to-r from-transparent via-[#2563EB]/20 to-transparent'
      }`} />

      <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl shrink-0 ${isRunning ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#F8FAFC] text-[#64748B] border border-[#E2E8F0]'}`}>
            <Radio className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#0F172A]">Live Traffic Ingestion</h3>
            <p className="text-xs text-[#64748B] mt-0.5">
              {isRunning ? (
                <>
                  Source: <span className="font-mono text-[#0F172A] font-semibold">{source.toUpperCase()}</span> ({target})
                </>
              ) : (
                <>
                  Status: <span className="font-mono text-[#0F172A] font-semibold">IDLE</span> — Configured: <span className="text-[#2563EB] font-mono font-medium">{target}</span>
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
              className="p-2 rounded-xl text-[#64748B] hover:text-[#0F172A] hover:bg-[#F8FAFC] border border-transparent hover:border-[#E2E8F0] transition"
              title="Open Live Monitoring"
            >
              <ArrowUpRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 2x2 metric panels with distinct, visible light-shade colors */}
      <div className="grid grid-cols-2 gap-3.5 py-5 border-b border-[#E2E8F0]">
        {/* Box 1: Session Uptime (Soft Indigo / Purple Shade) */}
        <div
          className="p-3.5 rounded-xl border transition-all duration-150 hover:shadow-xs"
          style={{
            background: 'linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%)',
            borderColor: '#A5B4FC',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase font-bold tracking-wider text-[#3730A3]">
              Session Uptime
            </span>
            <Clock className="w-3.5 h-3.5 text-[#4F46E5]" />
          </div>
          <div className="font-mono text-base font-bold text-[#1E1B4B] mt-1.5">
            {formatDuration(uptime)}
          </div>
        </div>

        {/* Box 2: Packets Captured (Soft Emerald / Mint Shade) */}
        <div
          className="p-3.5 rounded-xl border transition-all duration-150 hover:shadow-xs"
          style={{
            background: 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)',
            borderColor: '#6EE7B7',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase font-bold tracking-wider text-[#065F46]">
              Packets Captured
            </span>
            <Activity className="w-3.5 h-3.5 text-[#059669]" />
          </div>
          <div className="font-mono text-base font-bold text-[#064E3B] mt-1.5">
            {formatNumber(packets)}{' '}
            <span className="text-xs text-[#047857] font-semibold">({pktsPerSec} p/s)</span>
          </div>
        </div>

        {/* Box 3: Flows Ingested (Soft Sky / Blue Shade) */}
        <div
          className="p-3.5 rounded-xl border transition-all duration-150 hover:shadow-xs"
          style={{
            background: 'linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%)',
            borderColor: '#7DD3FC',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase font-bold tracking-wider text-[#075985]">
              Flows Ingested
            </span>
            <Zap className="w-3.5 h-3.5 text-[#0284C7]" />
          </div>
          <div className="font-mono text-base font-bold text-[#0C4A6E] mt-1.5">
            {formatNumber(flows)}{' '}
            <span className="text-xs text-[#0369A1] font-semibold">({flowsPerSec} f/s)</span>
          </div>
        </div>

        {/* Box 4: Anomalies / Alerts (Soft Rose / Coral Shade) */}
        <div
          className="p-3.5 rounded-xl border transition-all duration-150 hover:shadow-xs"
          style={{
            background: 'linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%)',
            borderColor: '#FDA4AF',
          }}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase font-bold tracking-wider text-[#9F1239]">
              Anomalies / Alerts
            </span>
            <AlertTriangle className="w-3.5 h-3.5 text-[#E11D48]" />
          </div>
          <div className="font-mono text-base font-bold text-[#881337] mt-1.5">
            {formatNumber(anomalies)}{' '}
            <span className="text-xs text-[#BE123C] font-semibold">/ {formatNumber(alerts)}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-[#64748B] pt-3.5">
        <span className="flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-[#64748B]" />
          Dropped Events: <span className="font-mono text-[#0F172A] font-semibold">{dropped}</span>
        </span>
        <span className="flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-[#64748B]" />
          Processing Errors: <span className="font-mono text-[#0F172A] font-semibold">{errors}</span>
        </span>
      </div>
    </div>
  );
}

export default MonitoringCard;
