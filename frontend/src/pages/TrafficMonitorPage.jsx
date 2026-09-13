import React from 'react';
import { Radio, Database, Info } from 'lucide-react';
import { Card } from '../components/common/Card';

export function TrafficMonitorPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">Network Traffic Telemetry</h2>
          <p className="text-xs text-slate-400">Real-time and simulated flow ingestion monitoring</p>
        </div>
      </div>

      <div className="cyber-card p-6 border-indigo-500/20 bg-indigo-950/10">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-indigo-300">Phase 1 Architecture Ready</h4>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              The traffic ingestion ingestion layer is architecturally decoupled. REST endpoint <code>POST /api/v1/traffic/ingest</code> is prepared for PCAP dataset replay and simulated streaming in subsequent development phases.
            </p>
          </div>
        </div>
      </div>

      <Card
        title="Active Network Interfaces & Datasets"
        subtitle="Configured data sources"
        icon={Database}
      >
        <div className="space-y-3 text-xs">
          <div className="p-3.5 rounded bg-slate-800/40 border border-white/5 flex items-center justify-between">
            <div>
              <div className="font-semibold text-slate-200">Dataset Stream / Flow Replay</div>
              <div className="text-[11px] text-slate-400">Target: <code>data/raw/</code> and <code>data/sample/</code></div>
            </div>
            <span className="px-2.5 py-1 rounded bg-slate-700/50 text-slate-300 font-mono text-[11px]">Configured</span>
          </div>

          <div className="p-3.5 rounded bg-slate-800/40 border border-white/5 flex items-center justify-between">
            <div>
              <div className="font-semibold text-slate-200">Live Socket / Packet Sniffer</div>
              <div className="text-[11px] text-slate-400">Interface: Async Non-blocking Queue</div>
            </div>
            <span className="px-2.5 py-1 rounded bg-slate-700/50 text-slate-300 font-mono text-[11px]">Ready for Phase 2</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
