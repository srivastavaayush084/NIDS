import React, { useState } from 'react';
import { Loader2, CheckCircle2, FileCode, Zap } from 'lucide-react';
import { SeverityBadge } from '../common/SeverityBadge';
import { formatNumber } from '../../utils/formatters';

export function PCAPTestRunner({ onRunTest, loading = false }) {
  const [file, setFile] = useState('data/sample/sample_network_traffic.pcap');
  const [maxPackets, setMaxPackets] = useState(200);
  const [generateXai, setGenerateXai] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const handleTest = async (e) => {
    e.preventDefault();
    if (!file.trim()) {
      setError('Please provide a PCAP file path.');
      return;
    }
    setError(null);
    setReport(null);
    try {
      const res = await onRunTest({
        file: file.trim(),
        max_packets: Number(maxPackets) || 200,
        generate_xai: generateXai,
        dataset_name: 'synthetic',
      });
      setReport(res);
    } catch (err) {
      setError(err.message || 'PCAP benchmark test failed.');
    }
  };

  return (
    <div className="p-5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md flex flex-col gap-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-bold text-slate-100">Synchronous PCAP Benchmark Inspector</h3>
        </div>
        <span className="text-[11px] text-slate-400">Isolated Test Mode</span>
      </div>

      <form onSubmit={handleTest} className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="sm:col-span-2">
          <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">PCAP File Path</label>
          <input
            type="text"
            required
            value={file}
            onChange={(e) => setFile(e.target.value)}
            placeholder="data/raw/sample.pcap"
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">Sample Limit</label>
          <input
            type="number"
            min={1}
            max={5000}
            value={maxPackets}
            onChange={(e) => setMaxPackets(Number(e.target.value))}
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="sm:col-span-3 flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={generateXai}
              onChange={(e) => setGenerateXai(e.target.checked)}
              className="accent-indigo-500 rounded"
            />
            <span>Compute XAI Explanations for Anomaly Detections</span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/25 transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            <span>Run Benchmark</span>
          </button>
        </div>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
          {error}
        </div>
      )}

      {report && (
        <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex flex-col gap-4 text-xs">
          <div className="flex items-center gap-2 text-emerald-400 font-bold">
            <CheckCircle2 className="w-4 h-4" />
            <span>PCAP Benchmark Analysis Complete</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Packets Parsed</span>
              <div className="text-base font-bold font-mono text-slate-100 mt-0.5">
                {formatNumber(report.packets_parsed)} / {formatNumber(report.packets_read)}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Flows Extracted</span>
              <div className="text-base font-bold font-mono text-indigo-300 mt-0.5">
                {formatNumber(report.flows_extracted)}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Anomalies / Alerts</span>
              <div className="text-base font-bold font-mono text-rose-400 mt-0.5">
                {report.anomalies_flagged} / {report.alerts_triggered}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Processing Speed</span>
              <div className="text-base font-bold font-mono text-emerald-400 mt-0.5">
                {report.throughput_pkts_per_sec} p/s
              </div>
            </div>
          </div>

          {/* Sample Flows Preview */}
          {report.sample_flows && report.sample_flows.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Sample Extracted Flows ({report.sample_flows.length})
              </h4>
              <div className="divide-y divide-white/5 border border-white/10 rounded-lg overflow-hidden bg-slate-900/60">
                {report.sample_flows.map((sf, idx) => (
                  <div key={idx} className="p-3 flex items-center justify-between text-xs">
                    <div className="font-mono text-slate-300">
                      <span>{sf.src_ip}</span>
                      <span className="text-slate-500 mx-1.5">&rarr;</span>
                      <span>{sf.dst_ip}</span>
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                        {sf.protocol}/{sf.service}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-rose-400">
                        Risk: {Number(sf.risk_score || 0).toFixed(1)}
                      </span>
                      <SeverityBadge severity={sf.severity} size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PCAPTestRunner;
