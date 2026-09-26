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

      {/* 2x2 metric panels with distinct light-shade colors */}
      <div className="grid grid-cols-2 gap-3.5 py-5 border-b border-[#E2E8F0]">
        {/* Box 1: Session Uptime (Soft Indigo / Blue) */}
        <div className="p-3.5 rounded-xl bg-[#EEF2FF] border border-[#C7D2FE] transition-all duration-150 hover:shadow-xs hover:border-[#818CF8]">
          <span className="text-[11px] uppercase font-bold tracking-wider text-[#4338CA]">Session Uptime</span>
          <div className="font-mono text-base font-bold text-[#1E1B4B] mt-1">{formatDuration(uptime)}</div>
        </div>

        {/* Box 2: Packets Captured (Soft Emerald / Mint) */}
        <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] transition-all duration-150 hover:shadow-xs hover:border-[#34D399]">
          <span className="text-[11px] uppercase font-bold tracking-wider text-[#047857]">Packets Captured</span>
          <div className="font-mono text-base font-bold text-[#064E3B] mt-1">
            {formatNumber(packets)} <span className="text-xs text-[#059669] font-normal">({pktsPerSec} p/s)</span>
          </div>
        </div>

        {/* Box 3: Flows Ingested (Soft Sky / Blue) */}
        <div className="p-3.5 rounded-xl bg-[#F0F9FF] border border-[#BAE6FD] transition-all duration-150 hover:shadow-xs hover:border-[#38BDF8]">
          <span className="text-[11px] uppercase font-bold tracking-wider text-[#0369A1]">Flows Ingested</span>
          <div className="font-mono text-base font-bold text-[#0C4A6E] mt-1">
            {formatNumber(flows)} <span className="text-xs text-[#0284C7] font-normal">({flowsPerSec} f/s)</span>
          </div>
        </div>

        {/* Box 4: Anomalies / Alerts (Soft Rose / Coral) */}
        <div className="p-3.5 rounded-xl bg-[#FFF1F2] border border-[#FECDD3] transition-all duration-150 hover:shadow-xs hover:border-[#FB7185]">
          <span className="text-[11px] uppercase font-bold tracking-wider text-[#BE123C]">Anomalies / Alerts</span>
          <div className="font-mono text-base font-bold text-[#881337] mt-1">
            {formatNumber(anomalies)} <span className="text-xs text-[#E11D48] font-normal">/ {formatNumber(alerts)}</span>
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
