import React from 'react';

export function ThroughputChart({
  pktsPerSec = 0,
  flowsPerSec = 0,
  bufferUtilPct = 0,
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {/* Packets per second */}
      <div className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col justify-between">
        <span className="text-[11px] font-medium text-[#64748B]">Packet Throughput</span>
        <div className="flex items-baseline gap-1.5 mt-2">
          <span className="text-xl font-bold font-mono text-[#10B981]">{pktsPerSec.toFixed(1)}</span>
          <span className="text-xs text-[#64748B]">pkts/sec</span>
        </div>
      </div>

      {/* Flows per second */}
      <div className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col justify-between">
        <span className="text-[11px] font-medium text-[#64748B]">Flow Ingestion</span>
        <div className="flex items-baseline gap-1.5 mt-2">
          <span className="text-xl font-bold font-mono text-[#2563EB]">{flowsPerSec.toFixed(1)}</span>
          <span className="text-xs text-[#64748B]">flows/sec</span>
        </div>
      </div>

      {/* Buffer utilization */}
      <div className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col justify-between">
        <span className="text-[11px] font-medium text-[#64748B]">Buffer Utilization</span>
        <div className="mt-2">
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-sm font-bold font-mono text-[#0F172A]">{bufferUtilPct.toFixed(1)}%</span>
            <span className="text-[10px] text-[#64748B]">10k capacity</span>
          </div>
          <div className="h-1.5 w-full bg-[#E2E8F0] rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                bufferUtilPct > 80 ? 'bg-[#EF4444]' : bufferUtilPct > 50 ? 'bg-[#F59E0B]' : 'bg-[#2563EB]'
              }`}
              style={{ width: `${Math.min(100, bufferUtilPct)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default ThroughputChart;
