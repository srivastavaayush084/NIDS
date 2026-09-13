import React from 'react';
import { SeverityBadge } from '../common/SeverityBadge';
import { StatusPill } from '../common/StatusPill';
import { formatDate, formatRelativeTime } from '../../utils/formatters';
import { ShieldAlert, ArrowRight } from 'lucide-react';

export function RecentAlertsTable({ alerts = [], onSelectAlert }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="p-8 text-center border border-dashed border-white/10 rounded-xl bg-slate-900/30 text-xs text-slate-400">
        <ShieldAlert className="w-6 h-6 mx-auto text-slate-500 mb-2" />
        No recent high-priority alerts recorded. System operating normally.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-white/5 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-800/30">
            <th className="px-4 py-2.5">Severity</th>
            <th className="px-4 py-2.5">Alert Title</th>
            <th className="px-4 py-2.5">Source &rarr; Destination</th>
            <th className="px-4 py-2.5">Risk</th>
            <th className="px-4 py-2.5">Status</th>
            <th className="px-4 py-2.5">Time</th>
            <th className="px-4 py-2.5 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {alerts.map((alt) => {
            const alertId = alt.alert_id || alt._id || alt.id;
            const src = alt.source_ip || alt.flow_context?.src_ip || '—';
            const dst = alt.destination_ip || alt.flow_context?.dst_ip || '—';
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
                onClick={() => onSelectAlert && onSelectAlert(alertId)}
                className={`hover:bg-slate-800/50 cursor-pointer transition-all duration-150 group ${borderClass}`}
              >
                <td className="px-4 py-3">
                  <SeverityBadge severity={alt.severity} size="sm" />
                </td>
                <td className="px-4 py-3 font-medium text-slate-200">
                  <div className="truncate max-w-xs font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                    {alt.title || 'Multi-Model Consensus Anomaly'}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{alertId}</div>
                </td>
                <td className="px-4 py-3 font-mono text-xs">
                  <span className="px-2 py-1 rounded-md bg-slate-900/80 border border-white/5 inline-flex items-center gap-1.5 text-slate-300">
                    <span className="text-slate-200 font-semibold">{src}</span>
                    <span className="text-indigo-400">&rarr;</span>
                    <span className="text-slate-200 font-semibold">{dst}</span>
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`font-mono font-bold text-xs ${
                      riskNum >= 70 ? 'text-rose-400' : riskNum >= 40 ? 'text-amber-400' : 'text-emerald-400'
                    }`}>
                      {risk}
                    </span>
                    <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden shrink-0 hidden sm:block">
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
                <td className="px-4 py-3">
                  <StatusPill status={alt.status} size="sm" />
                </td>
                <td className="px-4 py-3 text-slate-400 font-mono text-xs" title={formatDate(alt.created_at)}>
                  {formatRelativeTime(alt.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onSelectAlert) onSelectAlert(alertId);
                    }}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-indigo-600 hover:text-white text-indigo-400 transition-all duration-150 group-hover:translate-x-0.5"
                    title="Investigate incident"
                  >
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default RecentAlertsTable;
