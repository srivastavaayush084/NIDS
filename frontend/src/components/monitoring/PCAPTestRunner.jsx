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

  const inputClasses = "w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-3 py-2.5 text-[#0F172A] text-xs font-medium font-mono focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]/30 transition";

  return (
    <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white shadow-sm flex flex-col gap-4 hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#EDE9FE] border border-[#4F46E5]/20 text-[#4F46E5]">
            <FileCode className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-[#0F172A]">Synchronous PCAP Benchmark Inspector</h3>
        </div>
        <span className="text-[11px] text-[#64748B] font-medium">Isolated Test Mode</span>
      </div>

      <form onSubmit={handleTest} className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="sm:col-span-2">
          <label className="block text-[#64748B] text-[10px] font-bold uppercase tracking-wider mb-1.5">PCAP File Path</label>
          <input
            type="text"
            required
            value={file}
            onChange={(e) => setFile(e.target.value)}
            placeholder="data/raw/sample.pcap"
            className={inputClasses}
          />
        </div>

        <div>
          <label className="block text-[#64748B] text-[10px] font-bold uppercase tracking-wider mb-1.5">Sample Limit</label>
          <input
            type="number"
            min={1}
            max={5000}
            value={maxPackets}
            onChange={(e) => setMaxPackets(Number(e.target.value))}
            className={inputClasses}
          />
        </div>

        <div className="sm:col-span-3 flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 text-[#0F172A] cursor-pointer">
            <input
              type="checkbox"
              checked={generateXai}
              onChange={(e) => setGenerateXai(e.target.checked)}
              className="accent-[#2563EB] rounded"
            />
            <span className="font-medium text-xs">Compute XAI Explanations for Anomaly Detections</span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold shadow-md shadow-[#2563EB]/25 transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            <span>Run Benchmark</span>
          </button>
        </div>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-[#EF4444]/30 text-[#991B1B] text-xs">
          {error}
        </div>
      )}

      {report && (
        <div className="p-4 rounded-xl border border-[#10B981]/30 bg-[#F0FDF4] flex flex-col gap-4 text-xs">
          <div className="flex items-center gap-2 text-[#065F46] font-bold">
            <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
            <span>PCAP Benchmark Analysis Complete</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] shadow-sm">
              <span className="text-[10px] text-[#64748B] uppercase font-semibold">Packets Parsed</span>
              <div className="text-base font-bold font-mono text-[#0F172A] mt-0.5">
                {formatNumber(report.packets_parsed)} / {formatNumber(report.packets_read)}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] shadow-sm">
              <span className="text-[10px] text-[#64748B] uppercase font-semibold">Flows Extracted</span>
              <div className="text-base font-bold font-mono text-[#4F46E5] mt-0.5">
                {formatNumber(report.flows_extracted)}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] shadow-sm">
              <span className="text-[10px] text-[#64748B] uppercase font-semibold">Anomalies / Alerts</span>
              <div className="text-base font-bold font-mono text-[#EF4444] mt-0.5">
                {report.anomalies_flagged} / {report.alerts_triggered}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white border border-[#E2E8F0] shadow-sm">
              <span className="text-[10px] text-[#64748B] uppercase font-semibold">Processing Speed</span>
              <div className="text-base font-bold font-mono text-[#10B981] mt-0.5">
                {report.throughput_pkts_per_sec} p/s
              </div>
            </div>
          </div>

          {/* Sample Flows Preview */}
          {report.sample_flows && report.sample_flows.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider mb-2">
                Sample Extracted Flows ({report.sample_flows.length})
              </h4>
              <div className="divide-y divide-[#E2E8F0] border border-[#E2E8F0] rounded-lg overflow-hidden bg-white">
                {report.sample_flows.map((sf, idx) => (
                  <div key={idx} className="p-3 flex items-center justify-between text-xs hover:bg-[#F8FAFC] transition">
                    <div className="font-mono text-[#0F172A]">
                      <span>{sf.src_ip}</span>
                      <span className="text-[#64748B] mx-1.5">&rarr;</span>
                      <span>{sf.dst_ip}</span>
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[10px] text-[#64748B] border border-[#E2E8F0]">
                        {sf.protocol}/{sf.service}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-[#EF4444]">
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
