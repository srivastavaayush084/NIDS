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
    <div className="p-5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md flex flex-col justify-between shadow-lg">
      <div>
        <div className="flex items-start justify-between gap-3 pb-3 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">{meta.title}</h3>
              <span className="text-[10px] font-mono text-slate-400">{meta.type}</span>
            </div>
          </div>

          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
              isTrained
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isTrained ? 'ACTIVE' : 'READY'}</span>
          </span>
        </div>

        <p className="text-xs text-slate-300 mt-3 leading-relaxed">{meta.description}</p>

        <div className="grid grid-cols-2 gap-2 mt-4 text-xs font-mono">
          <div className="p-2 rounded-lg bg-slate-800/40 border border-white/5">
            <span className="text-[10px] text-slate-400 font-sans uppercase">Version</span>
            <div className="text-slate-200 font-bold mt-0.5">{version}</div>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/40 border border-white/5">
            <span className="text-[10px] text-slate-400 font-sans uppercase">Threshold</span>
            <div className="text-indigo-300 font-bold mt-0.5">{threshold}</div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium text-[11px]">Benchmark F1</span>
          <span className="font-mono font-bold text-emerald-400">
            {metrics.f1 !== undefined ? `${(metrics.f1 * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
      )}
    </div>
  );
}

export default ModelCard;
