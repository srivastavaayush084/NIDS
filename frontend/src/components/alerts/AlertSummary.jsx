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
        <div className="py-8 text-center text-[#64748B]">
          <CheckCircle2 className="w-8 h-8 text-[#10B981] mx-auto mb-2 opacity-80" />
          <p className="text-xs font-medium text-[#0F172A]">No active zero-day security incidents reported</p>
          <span className="text-[10px] text-[#64748B] mt-1 block">Traffic monitoring active (Phase 1 Baseline)</span>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div key={a.id} className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between hover:border-[#CBD5E1] transition">
              <div>
                <div className="text-xs font-semibold text-[#0F172A]">{a.title}</div>
                <div className="text-[10px] text-[#64748B]">{a.description}</div>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[#FEE2E2] text-[#991B1B] border border-[#EF4444]/30 font-bold">
                Risk: {(a.risk_score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
