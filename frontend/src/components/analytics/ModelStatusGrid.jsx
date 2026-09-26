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
            className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex flex-col justify-between hover:border-[#2563EB]/30 hover:shadow-sm transition-all duration-200"
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-[#0F172A]">{model.model_name}</span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-[#EAF2FF] text-[#2563EB] border border-[#2563EB]/15 font-medium">
                  {model.model_type}
                </span>
              </div>
              <p className="text-[11px] text-[#64748B]">ID: <code className="text-[#0F172A] bg-[#F1F5F9] px-1 py-0.5 rounded text-[10px]">{model.model_id}</code></p>
            </div>
            <div className="mt-3 pt-2.5 border-t border-[#E2E8F0] flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-[11px]">
                {model.is_trained ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5 text-[#10B981]" />
                    <span className="text-[#065F46] font-medium">Trained</span>
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5 text-[#F59E0B]" />
                    <span className="text-[#92400E] font-medium">Ready for Training</span>
                  </>
                )}
              </span>
              <span className="text-[11px] text-[#64748B] font-mono">v{model.version}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
