import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { SeverityBadge } from '../common/SeverityBadge';
import { StatusPill } from '../common/StatusPill';
import { formatDate, formatRelativeTime } from '../../utils/formatters';
import { Eye, CheckCircle2, ShieldCheck, XCircle } from 'lucide-react';

export function AlertsTable({
  alerts = [],
  onViewDetails,
  onAcknowledge,
  onResolve,
  onDismiss,
  actionLoading = false,
}) {
  const { isAnalyst } = useAuth();
  if (!alerts || alerts.length === 0) {
    return (
      <div className="p-12 text-center text-slate-400 text-xs">
        No security incident alerts found matching current filter criteria.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-white/10 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-800/40">
            <th className="px-4 py-3">Severity</th>
            <th className="px-4 py-3">Alert Title & ID</th>
            <th className="px-4 py-3">Source &rarr; Target</th>
            <th className="px-4 py-3">Risk Score</th>
            <th className="px-4 py-3">Occurrences</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Detected</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {alerts.map((alt) => {
            const alertId = alt.alert_id || alt._id || alt.id;
            const src = alt.source_ip || alt.flow_context?.src_ip || '—';
            const dst = alt.destination_ip || alt.flow_context?.dst_ip || '—';
            const srcPort = alt.source_port || alt.flow_context?.src_port;
            const dstPort = alt.destination_port || alt.flow_context?.dst_port;
            const risk = Number(alt.risk_score || 0).toFixed(1);
            const occ = alt.occurrence_count || alt.count || 1;
            const status = alt.status || 'OPEN';

            return (
              <tr
                key={alertId}
                className="hover:bg-slate-800/30 transition group cursor-pointer"
                onClick={() => onViewDetails && onViewDetails(alertId)}
              >
                <td className="px-4 py-3">
                  <SeverityBadge severity={alt.severity} size="sm" />
                </td>

                <td className="px-4 py-3 font-medium text-slate-200">
                  <div className="font-semibold text-slate-100 truncate max-w-xs">{alt.title || 'Multi-Model Consensus Anomaly'}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{alertId}</div>
                </td>

                <td className="px-4 py-3 font-mono text-slate-300">
                  <div>
                    <span className="text-slate-200">{src}</span>
                    {srcPort && <span className="text-slate-500">:{srcPort}</span>}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    &rarr; <span className="text-slate-200">{dst}</span>
                    {dstPort && <span className="text-slate-500">:{dstPort}</span>}
                  </div>
                </td>

                <td className="px-4 py-3 font-mono font-bold text-rose-400">
                  {risk}
                </td>

                <td className="px-4 py-3 font-mono text-slate-300">
                  {occ}x
                </td>

                <td className="px-4 py-3">
                  <StatusPill status={status} size="sm" />
                </td>

                <td className="px-4 py-3 text-slate-400" title={formatDate(alt.created_at)}>
                  {formatRelativeTime(alt.created_at)}
                </td>

                <td className="px-4 py-3 text-right">
                  <div
                    className="inline-flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => onViewDetails(alertId)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                      title="Investigate Alert Details"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>

                    {isAnalyst && status === 'OPEN' && (
                      <button
                        onClick={() => onAcknowledge(alertId)}
                        disabled={actionLoading}
                        className="p-1.5 rounded-lg bg-amber-950/40 hover:bg-amber-900/60 border border-amber-500/30 text-amber-300 transition"
                        title="Acknowledge Alert"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {isAnalyst && (status === 'OPEN' || status === 'ACKNOWLEDGED') && (
                      <>
                        <button
                          onClick={() => onResolve(alertId)}
                          disabled={actionLoading}
                          className="p-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-500/30 text-emerald-300 transition"
                          title="Resolve Alert"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => onDismiss(alertId)}
                          disabled={actionLoading}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/5 text-slate-400 hover:text-slate-200 transition"
                          title="Dismiss Alert"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default AlertsTable;
