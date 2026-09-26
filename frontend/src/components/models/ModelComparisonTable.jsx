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
    <div className="border border-[#E2E8F0] rounded-2xl overflow-hidden bg-white shadow-sm flex flex-col hover:shadow-md transition-all duration-200">
      {/* Header & Toggle */}
      <div className="p-4 bg-[#F8FAFC] border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-[#2563EB]">
              <BarChart2 className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#0F172A]">
              Comparative Benchmark Matrix
            </h4>
          </div>
          <p className="text-[11px] text-[#64748B] mt-0.5 ml-9">
            Standard test set vs. Novel zero-day proxy evaluation.
          </p>
        </div>

        {/* Mode Toggle Buttons */}
        <div className="flex items-center bg-[#F1F5F9] p-1 rounded-lg border border-[#E2E8F0] shrink-0 text-xs">
          <button
            onClick={() => setEvalMode('standard')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              evalMode === 'standard'
                ? 'bg-[#2563EB] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            Standard Benchmark
          </button>
          <button
            onClick={() => setEvalMode('unseen')}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              evalMode === 'unseen'
                ? 'bg-[#2563EB] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#0F172A]'
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
            <tr className="border-b border-[#E2E8F0] text-[10px] font-bold uppercase tracking-wider text-[#64748B] bg-[#F8FAFC]">
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
          <tbody className="divide-y divide-[#E2E8F0]">
            {rows.map((row, idx) => {
              const mData = row[evalMode] || row.metrics || {};
              const isEnsemble = row.model_name.includes('Ensemble');

              return (
                <tr
                  key={idx}
                  className={`hover:bg-[#F8FAFC] transition ${
                    isEnsemble ? 'bg-[#EAF2FF]/50 font-semibold' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-sans font-bold text-[#0F172A]">
                    {row.model_name}
                  </td>
                  <td className="px-4 py-3 text-[#0F172A]">{renderVal(mData.precision)}</td>
                  <td className="px-4 py-3 text-[#0F172A]">{renderVal(mData.recall)}</td>
                  <td className="px-4 py-3 font-bold text-[#10B981]">{renderVal(mData.f1)}</td>
                  <td className="px-4 py-3 text-[#0F172A]">{renderVal(mData.roc_auc)}</td>
                  <td className="px-4 py-3 text-[#0F172A]">{renderVal(mData.pr_auc)}</td>
                  <td className="px-4 py-3 text-[#EF4444]">{renderVal(mData.fpr)}</td>
                  <td className="px-4 py-3 text-[#F59E0B]">{renderVal(mData.fnr)}</td>
                  <td className="px-4 py-3 text-right text-[#4F46E5]">
                    {mData.latency_ms !== undefined ? `${mData.latency_ms.toFixed(2)} ms` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Benchmark Disclaimer */}
      <div className="p-3 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-start gap-2 text-[11px] text-[#64748B]">
        <HelpCircle className="w-3.5 h-3.5 text-[#94A3B8] shrink-0 mt-0.5" />
        <span>
          <strong className="text-[#0F172A]">Evaluation Context:</strong> {evalMode === 'unseen'
            ? 'Unseen Attack evaluation tests model generalizability against novel holdout attack signatures not present during training.'
            : 'Standard evaluation benchmarks model discrimination performance on known training/validation distributions.'}
        </span>
      </div>
    </div>
  );
}

export default ModelComparisonTable;
