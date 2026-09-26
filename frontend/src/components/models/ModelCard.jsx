import React from 'react';
import { Cpu, CheckCircle2 } from 'lucide-react';
import { MODEL_DESCRIPTIONS } from '../../utils/constants';

export function ModelCard({ model = {} }) {
  const modelName = model.name || model.model_name || 'unknown';
  const meta = MODEL_DESCRIPTIONS[modelName] || {
    title: modelName,
    type: 'Detection Engine',
    description: 'AI model component for network threat analysis.',
  };

  const isTrained = model.is_trained !== false && model.status !== 'uninitialized';
  const version = model.version || '1.0.0';
  const threshold = model.threshold !== undefined ? Number(model.threshold).toFixed(4) : '—';
  const metrics = model.metrics || model.evaluation || {};

  return (
    <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white flex flex-col justify-between shadow-sm hover:shadow-md hover:border-[#CBD5E1] transition-all duration-200">
      <div>
        <div className="flex items-start justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#EAF2FF] text-[#2563EB] border border-[#2563EB]/15">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">{meta.title}</h3>
              <span className="text-[10px] font-mono text-[#64748B]">{meta.type}</span>
            </div>
          </div>

          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
              isTrained
                ? 'bg-[#D1FAE5] border-[#10B981]/30 text-[#065F46]'
                : 'bg-[#FEF3C7] border-[#F59E0B]/30 text-[#92400E]'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isTrained ? 'ACTIVE' : 'READY'}</span>
          </span>
        </div>

        <p className="text-xs text-[#64748B] mt-3 leading-relaxed">{meta.description}</p>

        <div className="grid grid-cols-2 gap-2 mt-4 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
            <span className="text-[10px] text-[#64748B] font-sans uppercase font-semibold">Version</span>
            <div className="text-[#0F172A] font-bold mt-0.5">{version}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
            <span className="text-[10px] text-[#64748B] font-sans uppercase font-semibold">Threshold</span>
            <div className="text-[#4F46E5] font-bold mt-0.5">{threshold}</div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex items-center justify-between text-xs">
          <span className="text-[#64748B] font-medium text-[11px]">Benchmark F1</span>
          <span className="font-mono font-bold text-[#10B981]">
            {metrics.f1 !== undefined ? `${(metrics.f1 * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
      )}
    </div>
  );
}

export default ModelCard;
