import React from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import { Card } from '../common/Card';

export function AlertSummary({ alerts = [] }) {
  return (
    <Card
      title="Recent Security Alerts"
      subtitle="Zero-day detection incident feed"
      icon={ShieldAlert}
    >
      {alerts.length === 0 ? (
        <div className="py-8 text-center text-slate-400">
          <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
          <p className="text-xs">No active zero-day security incidents reported</p>
          <span className="text-[10px] text-slate-500 mt-1 block">Traffic monitoring active (Phase 1 Baseline)</span>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div key={a.id} className="p-3 rounded bg-slate-800/40 border border-white/5 flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-200">{a.title}</div>
                <div className="text-[10px] text-slate-400">{a.description}</div>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300">
                Risk: {(a.risk_score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
