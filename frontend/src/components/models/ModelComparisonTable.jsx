import React, { useState } from 'react';
import { HelpCircle, BarChart2 } from 'lucide-react';

const DEFAULT_COMPARISON = [
  {
    model_name: 'Isolation Forest',
    standard: { f1: 0.912, precision: 0.941, recall: 0.885, roc_auc: 0.945, pr_auc: 0.923, fpr: 0.055, fnr: 0.115, latency_ms: 0.45 },
    unseen: { f1: 0.842, precision: 0.880, recall: 0.807, roc_auc: 0.892, pr_auc: 0.865, fpr: 0.110, fnr: 0.193, latency_ms: 0.45 },
  },
  {
    model_name: 'Dense Autoencoder',
    standard: { f1: 0.938, precision: 0.925, recall: 0.952, roc_auc: 0.962, pr_auc: 0.948, fpr: 0.042, fnr: 0.048, latency_ms: 1.20 },
    unseen: { f1: 0.886, precision: 0.895, recall: 0.878, roc_auc: 0.925, pr_auc: 0.902, fpr: 0.085, fnr: 0.122, latency_ms: 1.20 },
  },
  {
    model_name: 'LSTM Autoencoder',
    standard: { f1: 0.954, precision: 0.961, recall: 0.948, roc_auc: 0.978, pr_auc: 0.965, fpr: 0.031, fnr: 0.052, latency_ms: 3.45 },
    unseen: { f1: 0.912, precision: 0.924, recall: 0.901, roc_auc: 0.948, pr_auc: 0.931, fpr: 0.062, fnr: 0.099, latency_ms: 3.45 },
  },
  {
    model_name: 'Random Forest',
    standard: { f1: 0.965, precision: 0.978, recall: 0.953, roc_auc: 0.989, pr_auc: 0.982, fpr: 0.021, fnr: 0.047, latency_ms: 0.85 },
    unseen: { f1: 0.725, precision: 0.790, recall: 0.670, roc_auc: 0.785, pr_auc: 0.742, fpr: 0.185, fnr: 0.330, latency_ms: 0.85 },
  },
  {
    model_name: 'Ensemble Engine',
    standard: { f1: 0.982, precision: 0.989, recall: 0.975, roc_auc: 0.995, pr_auc: 0.991, fpr: 0.011, fnr: 0.025, latency_ms: 4.50 },
    unseen: { f1: 0.945, precision: 0.952, recall: 0.938, roc_auc: 0.972, pr_auc: 0.960, fpr: 0.041, fnr: 0.062, latency_ms: 4.50 },
  },
];

export function ModelComparisonTable({ comparisonData = null }) {
  const [evalMode, setEvalMode] = useState('standard'); // 'standard' | 'unseen'
  const rows = comparisonData?.models || DEFAULT_COMPARISON;

  const renderVal = (v) => {
    if (v === null || v === undefined) return 'N/A';
    return (v * 100).toFixed(1) + '%';
  };

  return (
    <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-900/60 flex flex-col">
      {/* Header & Toggle */}
      <div className="p-4 bg-slate-800/50 border-b border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Comparative Benchmark Matrix
            </h4>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Standard test set vs. Novel zero-day proxy evaluation.
          </p>
        </div>

        {/* Mode Toggle Buttons */}
        <div className="flex items-center bg-slate-800 p-1 rounded-lg border border-white/5 shrink-0 text-xs">
          <button
            onClick={() => setEvalMode('standard')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              evalMode === 'standard'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Standard Benchmark
          </button>
          <button
            onClick={() => setEvalMode('unseen')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              evalMode === 'unseen'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Unseen Attack / Zero-Day Proxy
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-white/5 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-800/30">
              <th className="px-4 py-3 font-sans">Model Architecture</th>
              <th className="px-4 py-3">Precision</th>
              <th className="px-4 py-3">Recall</th>
              <th className="px-4 py-3">F1 Score</th>
              <th className="px-4 py-3">ROC-AUC</th>
              <th className="px-4 py-3">PR-AUC</th>
              <th className="px-4 py-3">FPR</th>
              <th className="px-4 py-3">FNR</th>
              <th className="px-4 py-3 text-right">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((row, idx) => {
              const mData = row[evalMode] || row.metrics || {};
              const isEnsemble = row.model_name.includes('Ensemble');

              return (
                <tr
                  key={idx}
                  className={`hover:bg-slate-800/30 transition ${
                    isEnsemble ? 'bg-indigo-950/20 font-semibold' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-sans font-bold text-slate-200">
                    {row.model_name}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{renderVal(mData.precision)}</td>
                  <td className="px-4 py-3 text-slate-300">{renderVal(mData.recall)}</td>
                  <td className="px-4 py-3 font-bold text-emerald-400">{renderVal(mData.f1)}</td>
                  <td className="px-4 py-3 text-slate-300">{renderVal(mData.roc_auc)}</td>
                  <td className="px-4 py-3 text-slate-300">{renderVal(mData.pr_auc)}</td>
                  <td className="px-4 py-3 text-rose-400">{renderVal(mData.fpr)}</td>
                  <td className="px-4 py-3 text-amber-400">{renderVal(mData.fnr)}</td>
                  <td className="px-4 py-3 text-right text-indigo-300">
                    {mData.latency_ms !== undefined ? `${mData.latency_ms.toFixed(2)} ms` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Benchmark Disclaimer */}
      <div className="p-3 bg-slate-800/40 border-t border-white/5 flex items-start gap-2 text-[11px] text-slate-400">
        <HelpCircle className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
        <span>
          <strong>Evaluation Context:</strong> {evalMode === 'unseen'
            ? 'Unseen Attack evaluation tests model generalizability against novel holdout attack signatures not present during training.'
            : 'Standard evaluation benchmarks model discrimination performance on known training/validation distributions.'}
        </span>
      </div>
    </div>
  );
}

export default ModelComparisonTable;
