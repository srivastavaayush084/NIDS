import React from 'react';
import { Cpu, CheckCircle, Clock } from 'lucide-react';
import { Card } from '../common/Card';

export function ModelStatusGrid({ models = [] }) {
  return (
    <Card
      title="Detection Model Ensemble"
      subtitle="4-tier AI/ML algorithm status & architecture"
      icon={Cpu}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {models.map((model) => (
          <div
            key={model.model_id}
            className="p-3.5 rounded-lg bg-slate-800/40 border border-white/5 flex flex-col justify-between hover:border-indigo-500/30 transition"
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-100">{model.model_name}</span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {model.model_type}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">ID: <code className="text-slate-300">{model.model_id}</code></p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                {model.is_trained ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Trained</span>
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-amber-400">Ready for Training</span>
                  </>
                )}
              </span>
              <span className="text-[11px] text-slate-400 font-mono">v{model.version}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
