import React from 'react';

export function ModelComparisonChart({
  models = [
    { name: 'Isolation Forest', f1: 0.912, precision: 0.941, recall: 0.885, latency: 0.45 },
    { name: 'Dense Autoencoder', f1: 0.938, precision: 0.925, recall: 0.952, latency: 1.20 },
    { name: 'LSTM Autoencoder', f1: 0.954, precision: 0.961, recall: 0.948, latency: 3.45 },
    { name: 'Random Forest', f1: 0.965, precision: 0.978, recall: 0.953, latency: 0.85 },
    { name: 'Ensemble Engine', f1: 0.982, precision: 0.989, recall: 0.975, latency: 4.50 },
  ],
  metric = 'f1',
}) {
  const isLatency = metric === 'latency';

  return (
    <div className="flex flex-col gap-3">
      {models.map((m, idx) => {
        const val = Number(m[metric] !== undefined ? m[metric] : m.metrics?.[metric] || 0);
        const barWidth = isLatency ? Math.min(100, (val / 10.0) * 100) : Math.min(100, val * 100);
        const displayVal = isLatency ? `${val.toFixed(2)} ms` : `${(val * 100).toFixed(1)}%`;

        return (
          <div key={idx} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300">{m.name || m.model_name}</span>
              <span className="font-mono font-bold text-indigo-300">{displayVal}</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-indigo-400 transition-all duration-500"
                style={{ width: `${barWidth}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default ModelComparisonChart;
