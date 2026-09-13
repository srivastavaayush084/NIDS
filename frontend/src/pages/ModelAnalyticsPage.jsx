import React from 'react';
import { Cpu, BarChart3, Info } from 'lucide-react';
import { ModelStatusGrid } from '../components/analytics/ModelStatusGrid';
import { Card } from '../components/common/Card';

export function ModelAnalyticsPage({ models }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">AI/ML Model Registry & Analytics</h2>
          <p className="text-xs text-slate-400">Model ensemble metrics, architecture configurations, and comparison benchmarks</p>
        </div>
      </div>

      <ModelStatusGrid models={models} />

      <Card
        title="Detection Model Ensemble Strategy"
        subtitle="Comparing unsupervised zero-day detection vs baseline signatures"
        icon={BarChart3}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 space-y-2">
            <h4 className="font-semibold text-indigo-400 text-sm">1. Isolation Forest (Unsupervised)</h4>
            <p className="text-slate-300">
              Isolates anomalous data points through random tree partitioning. Ideal for identifying previously unobserved outlier packet metrics without prior training on attack labels.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 space-y-2">
            <h4 className="font-semibold text-purple-400 text-sm">2. Deep Autoencoder (Reconstruction)</h4>
            <p className="text-slate-300">
              Neural network trained to compress and reconstruct benign traffic patterns. High reconstruction error indicates novel zero-day payload or communication protocol anomalies.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 space-y-2">
            <h4 className="font-semibold text-cyan-400 text-sm">3. Temporal LSTM Network</h4>
            <p className="text-slate-300">
              Analyzes time-series flow windows to detect stealthy multi-phase zero-day attacks, slow port scanning, and command-and-control beaconing.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 space-y-2">
            <h4 className="font-semibold text-emerald-400 text-sm">4. Random Forest Baseline</h4>
            <p className="text-slate-300">
              Supervised machine learning benchmark used for comparative academic evaluation between traditional signature detection and novel zero-day identification.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
