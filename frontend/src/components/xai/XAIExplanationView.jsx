import React from 'react';
import { HelpCircle, TrendingUp, TrendingDown, Layers, Activity } from 'lucide-react';

export function XAIExplanationView({ explanation = null }) {
  if (!explanation) {
    return (
      <div className="p-4 rounded-xl bg-slate-800/30 border border-white/5 text-xs text-slate-400">
        No Explainable AI attribution data attached to this detection record.
      </div>
    );
  }

  const isAvailable = explanation.is_available !== false;
  const summary = explanation.summary || 'Feature attribution analysis completed.';
  const topFeatures = explanation.top_features || explanation.fused_feature_contributions || [];
  const peakTimestep = explanation.peak_timestep;
  const method = explanation.method || 'ensemble_risk_attribution';

  return (
    <div className="flex flex-col gap-4">
      {/* Summary Banner */}
      <div className="p-4 rounded-xl bg-slate-800/50 border border-white/10 flex items-start gap-3">
        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
          <Activity className="w-4 h-4" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Risk Attribution Summary
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-700/60 text-slate-300">
              {method}
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed">{summary}</p>
          {peakTimestep && (
            <p className="text-[11px] text-amber-300/90 font-mono mt-1">
              Peak Temporal Anomaly Timestep: <span className="font-bold">{peakTimestep}</span>
            </p>
          )}
        </div>
      </div>

      {/* Top Contributing Features Table */}
      {topFeatures.length > 0 ? (
        <div className="border border-white/10 rounded-xl overflow-hidden bg-slate-900/60">
          <div className="px-4 py-2.5 bg-slate-800/60 border-b border-white/5 flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            <span>Feature Name</span>
            <div className="flex items-center gap-8">
              <span>Feature Value</span>
              <span className="w-24 text-right">Risk Effect</span>
            </div>
          </div>

          <div className="divide-y divide-white/5">
            {topFeatures.map((feat, idx) => {
              const name = feat.feature_name || feat.name || `Feature #${idx + 1}`;
              const val = feat.feature_value !== undefined ? feat.feature_value : feat.value;
              const weight = Number(feat.attribution_weight || feat.contribution || feat.shap_value || 0);
              const isPositive = weight >= 0;

              return (
                <div key={idx} className="px-4 py-3 flex items-center justify-between text-xs hover:bg-slate-800/30 transition">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-medium text-slate-200">{name}</span>
                  </div>

                  <div className="flex items-center gap-8">
                    <span className="font-mono text-slate-300 font-semibold">
                      {val !== null && val !== undefined ? (typeof val === 'number' ? val.toFixed(2) : String(val)) : '—'}
                    </span>

                    <div className="w-24 flex items-center justify-end gap-1.5 font-medium">
                      {isPositive ? (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold text-[11px]">
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>+{(Math.abs(weight) * 100).toFixed(0)}%</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                          <TrendingDown className="w-3.5 h-3.5" />
                          <span>-{(Math.abs(weight) * 100).toFixed(0)}%</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-xs text-slate-400 italic">No individual feature weight breakdowns available.</p>
      )}

      {/* Model Attribution Disclaimer */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-[11px] text-indigo-200/80 leading-relaxed">
        <HelpCircle className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
        <span>
          <strong>Interpretability Note:</strong> Attributions represent the mathematical contribution of individual flow features toward the model risk score, not proof of causality.
        </span>
      </div>
    </div>
  );
}

export default XAIExplanationView;
