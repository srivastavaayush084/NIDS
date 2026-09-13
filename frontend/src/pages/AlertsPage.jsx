import React from 'react';
import { ShieldAlert, CheckCircle } from 'lucide-react';
import { Card } from '../components/common/Card';

export function AlertsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">Security Incidents & Alerts</h2>
          <p className="text-xs text-slate-400">Zero-day anomaly detection alarms and forensic explanations</p>
        </div>
      </div>

      <Card
        title="Incident Alert Feed"
        subtitle="Historical and real-time security alerts"
        icon={ShieldAlert}
      >
        <div className="py-12 text-center text-slate-400">
          <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3 opacity-80" />
          <p className="text-sm font-medium text-slate-200">Zero-Day Detection System Active</p>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            No active threat alerts triggered yet. As network flows are ingested and evaluated by the 4 ML models, suspect zero-day anomalies with high risk scores will appear here with explainability insights.
          </p>
        </div>
      </Card>
    </div>
  );
}
