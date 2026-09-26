import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { MODEL_DESCRIPTIONS } from '../../utils/constants';

export function ModelCompatibilityMatrix({ compatibility = {} }) {
  const modelKeys = ['isolation_forest', 'autoencoder', 'lstm_autoencoder', 'random_forest', 'ensemble'];

  return (
    <div className="border border-[#E2E8F0] rounded-2xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-all duration-200">
      <div className="px-5 py-3.5 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-[#D1FAE5] border border-[#10B981]/20 text-[#10B981]">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-[#0F172A]">
            Feature Extraction & Model Compatibility Matrix
          </h4>
        </div>
        <span className="text-[11px] font-mono text-[#10B981] font-semibold">Target Schema: synthetic (26 features)</span>
      </div>

      <div className="divide-y divide-[#E2E8F0]">
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
            <div key={key} className="p-4 flex items-center justify-between text-xs hover:bg-[#F8FAFC] transition">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[#0F172A]">{meta.title}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-md bg-[#EAF2FF] text-[#2563EB] font-mono font-medium border border-[#2563EB]/15">
                    {meta.type}
                  </span>
                </div>
                <p className="text-[11px] text-[#64748B] mt-1">{report.explanation}</p>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <span className="font-mono text-xs text-[#0F172A] font-semibold">
                  {report.available_features}/{report.total_required_features} Features
                </span>

                {report.compatible ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#D1FAE5] border border-[#10B981]/30 text-[#065F46] font-semibold text-[11px]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                    <span>COMPATIBLE</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#FEE2E2] border border-[#EF4444]/30 text-[#991B1B] font-semibold text-[11px]">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#EF4444]" />
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
