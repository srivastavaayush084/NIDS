import React from 'react';
import { Cpu, CheckCircle2 } from 'lucide-react';
import { MODEL_DESCRIPTIONS } from '../../utils/constants';

export function ModelOverviewGrid({ models = [], onSelectModel }) {
  const defaultModels = [
    { name: 'isolation_forest', threshold: 50.0 },
    { name: 'autoencoder', threshold: 1.0788 },
    { name: 'lstm_autoencoder', threshold: 0.6586 },
    { name: 'random_forest', threshold: 0.1000 },
    { name: 'ensemble', threshold: 50.0 },
  ];

  const list = models.length > 0 ? models : defaultModels;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      {list.slice(0, 4).map((m, idx) => {
        const mKey = m.name || m.model_name;
        const meta = MODEL_DESCRIPTIONS[mKey] || { title: mKey, type: 'ML Model' };
        const threshold = m.threshold !== undefined ? Number(m.threshold).toFixed(2) : '—';

        return (
          <div
            key={idx}
            onClick={onSelectModel}
            className="p-3 rounded-lg border border-white/5 bg-slate-800/40 hover:bg-slate-800/70 cursor-pointer transition flex items-center justify-between"
          >
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="text-xs font-bold text-slate-200">{meta.title}</div>
                <span className="text-[10px] text-slate-400 font-mono">Threshold: {threshold}</span>
              </div>
            </div>

            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>ACTIVE</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default ModelOverviewGrid;
