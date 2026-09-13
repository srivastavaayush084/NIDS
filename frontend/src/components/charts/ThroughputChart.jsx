import React from 'react';

export function ThroughputChart({
  pktsPerSec = 0,
  flowsPerSec = 0,
  bufferUtilPct = 0,
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {/* Packets per second */}
      <div className="p-3.5 rounded-xl border border-white/5 bg-slate-800/40 flex flex-col justify-between">
        <span className="text-[11px] font-medium text-slate-400">Packet Throughput</span>
        <div className="flex items-baseline gap-1.5 mt-2">
          <span className="text-xl font-bold font-mono text-emerald-400">{pktsPerSec.toFixed(1)}</span>
          <span className="text-xs text-slate-400">pkts/sec</span>
        </div>
      </div>

      {/* Flows per second */}
      <div className="p-3.5 rounded-xl border border-white/5 bg-slate-800/40 flex flex-col justify-between">
        <span className="text-[11px] font-medium text-slate-400">Flow Ingestion</span>
        <div className="flex items-baseline gap-1.5 mt-2">
          <span className="text-xl font-bold font-mono text-indigo-400">{flowsPerSec.toFixed(1)}</span>
          <span className="text-xs text-slate-400">flows/sec</span>
        </div>
      </div>

      {/* Buffer utilization */}
      <div className="p-3.5 rounded-xl border border-white/5 bg-slate-800/40 flex flex-col justify-between">
        <span className="text-[11px] font-medium text-slate-400">Buffer Utilization</span>
        <div className="mt-2">
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-sm font-bold font-mono text-slate-200">{bufferUtilPct.toFixed(1)}%</span>
            <span className="text-[10px] text-slate-400">10k capacity</span>
          </div>
          <div className="h-1.5 w-full bg-slate-700/60 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                bufferUtilPct > 80 ? 'bg-rose-500' : bufferUtilPct > 50 ? 'bg-amber-500' : 'bg-indigo-500'
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
