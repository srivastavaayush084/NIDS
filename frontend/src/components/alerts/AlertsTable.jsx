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
            const occ = alt.occurrence_count || alt.count || 1;
            const status = alt.status || 'OPEN';

            const riskNum = Number(alt.risk_score || 0);
            const risk = riskNum.toFixed(1);
            const sevNorm = (alt.severity || 'LOW').toUpperCase();
            const borderClass = sevNorm === 'CRITICAL'
              ? 'border-l-critical'
              : sevNorm === 'HIGH'
              ? 'border-l-high'
              : sevNorm === 'MEDIUM'
              ? 'border-l-medium'
              : 'border-l-low';

            return (
              <tr
                key={alertId}
                className={`hover:bg-slate-800/40 transition-all duration-150 group cursor-pointer ${borderClass}`}
                onClick={() => onViewDetails && onViewDetails(alertId)}
              >
                <td className="px-4 py-3">
                  <SeverityBadge severity={alt.severity} size="sm" />
                </td>

                <td className="px-4 py-3 font-medium text-slate-200">
                  <div className="font-semibold text-slate-100 truncate max-w-xs group-hover:text-indigo-300 transition-colors">
                    {alt.title || 'Multi-Model Consensus Anomaly'}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{alertId}</div>
                </td>

                <td className="px-4 py-3 font-mono text-xs">
                  <div className="px-2 py-1 rounded bg-slate-900/80 border border-white/5 inline-block text-slate-300">
                    <div>
                      <span className="text-slate-200 font-semibold">{src}</span>
                      {srcPort && <span className="text-slate-500">:{srcPort}</span>}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      <span className="text-indigo-400">&rarr;</span> <span className="text-slate-200 font-semibold">{dst}</span>
                      {dstPort && <span className="text-slate-500">:{dstPort}</span>}
                    </div>
                  </div>
                </td>

                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`font-mono font-bold text-xs ${
                      riskNum >= 70 ? 'text-rose-400' : riskNum >= 40 ? 'text-amber-400' : 'text-emerald-400'
                    }`}>
                      {risk}
                    </span>
                    <div className="w-10 h-1.5 rounded-full bg-slate-800 overflow-hidden shrink-0 hidden sm:block">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(100, Math.max(0, riskNum))}%`,
                          backgroundColor: riskNum >= 70 ? '#f43f5e' : riskNum >= 40 ? '#f59e0b' : '#10b981',
                          boxShadow: riskNum >= 70 ? '0 0 6px #f43f5e' : undefined,
                        }}
                      />
                    </div>
                  </div>
                </td>

                <td className="px-4 py-3 font-mono text-slate-300">
                  <span className="px-2 py-0.5 rounded bg-slate-800/80 text-xs font-semibold">
                    {occ}x
                  </span>
                </td>

                <td className="px-4 py-3">
                  <StatusPill status={status} size="sm" />
                </td>

                <td className="px-4 py-3 text-slate-400 font-mono text-xs" title={formatDate(alt.created_at)}>
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
