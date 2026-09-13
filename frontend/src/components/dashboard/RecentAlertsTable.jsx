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
            const risk = Number(alt.risk_score || 0).toFixed(1);

            return (
              <tr
                key={alertId}
                onClick={() => onSelectAlert && onSelectAlert(alertId)}
                className="hover:bg-slate-800/40 cursor-pointer transition"
              >
                <td className="px-4 py-3">
                  <SeverityBadge severity={alt.severity} size="sm" />
                </td>
                <td className="px-4 py-3 font-medium text-slate-200">
                  <div className="truncate max-w-xs">{alt.title || 'Multi-Model Consensus Anomaly'}</div>
                  <div className="text-[10px] font-mono text-slate-500">{alertId}</div>
                </td>
                <td className="px-4 py-3 font-mono text-slate-300">
                  <span className="text-slate-200">{src}</span>
                  <span className="text-slate-500 mx-1.5">&rarr;</span>
                  <span className="text-slate-200">{dst}</span>
                </td>
                <td className="px-4 py-3 font-mono font-bold text-rose-400">
                  {risk}
                </td>
                <td className="px-4 py-3">
                  <StatusPill status={alt.status} size="sm" />
                </td>
                <td className="px-4 py-3 text-slate-400" title={formatDate(alt.created_at)}>
                  {formatRelativeTime(alt.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onSelectAlert) onSelectAlert(alertId);
                    }}
                    className="p-1 rounded hover:bg-slate-700 text-indigo-400 hover:text-indigo-200 transition"
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
