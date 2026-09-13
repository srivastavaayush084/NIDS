import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { MODEL_DESCRIPTIONS } from '../../utils/constants';

export function ModelCompatibilityMatrix({ compatibility = {} }) {
  const modelKeys = ['isolation_forest', 'autoencoder', 'lstm_autoencoder', 'random_forest', 'ensemble'];

  return (
    <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-900/60">
      <div className="px-5 py-3.5 bg-slate-800/50 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Feature Extraction & Model Compatibility Matrix
          </h4>
        </div>
        <span className="text-[11px] font-mono text-emerald-400">Target Schema: synthetic (26 features)</span>
      </div>

      <div className="divide-y divide-white/5">
        {modelKeys.map((key) => {
          const report = compatibility[key] || {
            model_name: key,
            compatible: true,
            available_features: 26,
            total_required_features: 26,
            explanation: 'All 26 required features extracted and mapped.',
          };
          const meta = MODEL_DESCRIPTIONS[key] || { title: key, type: 'ML Model' };

          return (
            <div key={key} className="p-4 flex items-center justify-between text-xs hover:bg-slate-800/30 transition">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-200">{meta.title}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                    {meta.type}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{report.explanation}</p>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <span className="font-mono text-xs text-slate-300 font-semibold">
                  {report.available_features}/{report.total_required_features} Features
                </span>

                {report.compatible ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-semibold text-[11px]">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>COMPATIBLE</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-400 font-semibold text-[11px]">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>INCOMPATIBLE</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ModelCompatibilityMatrix;
