import React from 'react';
import { SeverityBadge } from '../common/SeverityBadge';
import { formatRelativeTime } from '../../utils/formatters';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

export function MonitoringLiveFeed({ events = [] }) {
  if (!events || events.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-[#64748B] border border-dashed border-[#E2E8F0] rounded-xl bg-[#F8FAFC]">
        No active flow events streamed yet. Start a capture session or PCAP replay above to begin live analysis.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-[#E2E8F0] text-[10px] font-bold uppercase tracking-wider text-[#64748B] bg-[#F8FAFC]">
            <th className="px-4 py-2.5">Severity</th>
            <th className="px-4 py-2.5">Flow Endpoints</th>
            <th className="px-4 py-2.5">Proto / Svc</th>
            <th className="px-4 py-2.5">Risk Score</th>
            <th className="px-4 py-2.5">Classification</th>
            <th className="px-4 py-2.5">Alert Triggered</th>
            <th className="px-4 py-2.5 text-right">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E2E8F0]">
          {events.slice(0, 50).map((evt, idx) => {
            const src = evt.src_ip || evt.flow_context?.src_ip || '—';
            const dst = evt.dst_ip || evt.flow_context?.dst_ip || '—';
            const srcPort = evt.src_port || evt.flow_context?.src_port;
            const dstPort = evt.dst_port || evt.flow_context?.dst_port;
            const proto = (evt.protocol || evt.flow_context?.protocol || 'TCP').toUpperCase();
            const service = (evt.service || evt.flow_context?.service || 'other').toLowerCase();
            const risk = Number(evt.risk_score || evt.prediction?.composite_risk_score || 0).toFixed(1);
            const isAnomaly = Boolean(evt.is_anomaly || evt.prediction?.is_anomaly);
            const severity = evt.severity || evt.prediction?.severity || 'LOW';
            const alertCreated = Boolean(evt.alert?.created || evt.alert_outcome?.created);

            return (
              <tr key={evt.flow_id || evt.detection_id || idx} className="hover:bg-[#F8FAFC] transition">
                <td className="px-4 py-2.5">
                  <SeverityBadge severity={severity} size="sm" />
                </td>

                <td className="px-4 py-2.5 font-mono text-[#0F172A]">
                  <span>{src}{srcPort ? `:${srcPort}` : ''}</span>
                  <span className="text-[#64748B] mx-1.5">&rarr;</span>
                  <span>{dst}{dstPort ? `:${dstPort}` : ''}</span>
                </td>

                <td className="px-4 py-2.5">
                  <span className="px-2 py-0.5 rounded-md bg-[#F1F5F9] border border-[#E2E8F0] font-mono text-[11px] text-[#0F172A]">
                    {proto}/{service}
                  </span>
                </td>

                <td className="px-4 py-2.5 font-mono font-bold text-[#EF4444]">
                  {risk}
                </td>

                <td className="px-4 py-2.5">
                  {isAnomaly ? (
                    <span className="inline-flex items-center gap-1 font-semibold text-[#EF4444]">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>ATTACK</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 font-semibold text-[#10B981]">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>NORMAL</span>
                    </span>
                  )}
                </td>

                <td className="px-4 py-2.5">
                  {alertCreated ? (
                    <span className="px-2 py-0.5 rounded-full bg-[#FEE2E2] text-[#991B1B] border border-[#EF4444]/30 font-bold text-[10px]">
                      ALERT CREATED
                    </span>
                  ) : (
                    <span className="text-[#CBD5E1] text-[11px]">—</span>
                  )}
                </td>

                <td className="px-4 py-2.5 text-right text-[#64748B] font-mono">
                  {formatRelativeTime(evt.timestamp || evt.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default MonitoringLiveFeed;
