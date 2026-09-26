import React from 'react';
import { Activity, Server, Database, Cpu, RefreshCw, AlertCircle } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { formatDate } from '../../utils/formatters';

export function SystemHealthCard({ health, loading, error, onRefresh }) {
  if (loading && !health) {
    return (
      <div className="cyber-card animate-pulse p-6">
        <div className="h-5 bg-[#E2E8F0] rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-10 bg-[#F1F5F9] rounded"></div>
          <div className="h-10 bg-[#F1F5F9] rounded"></div>
        </div>
      </div>
    );
  }

  if (error && !health) {
    return (
      <div className="cyber-card p-6 border-[#EF4444]/30" style={{ backgroundColor: '#FEF2F2' }}>
        <div className="flex items-center gap-3 text-[#EF4444] mb-2">
          <AlertCircle className="w-5 h-5" />
          <h3 className="font-semibold text-sm">Backend Disconnected</h3>
        </div>
        <p className="text-xs text-[#64748B] mb-4">{error}</p>
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 bg-[#EF4444] text-white rounded-lg text-xs hover:bg-red-600 transition flex items-center gap-1.5 font-semibold shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
        </button>
      </div>
    );
  }

  const services = health?.services || {};

  return (
    <div className="cyber-card p-6">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-[#2563EB]">
            <Activity className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-[#0F172A] text-sm tracking-wide">System Health & Telemetry</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[#64748B]">Checked: {formatDate(health?.timestamp)}</span>
          <button
            onClick={onRefresh}
            title="Refresh Health"
            className="p-1.5 text-[#64748B] hover:text-[#2563EB] hover:bg-[#EAF2FF] rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* FastAPI Status */}
        <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between hover:border-[#CBD5E1] transition">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/15 text-[#2563EB]">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-[#64748B]">Backend API</div>
              <div className="text-sm font-semibold text-[#0F172A]">FastAPI v{health?.version || '1.0.0'}</div>
            </div>
          </div>
          <StatusBadge status={services.api?.status || 'healthy'} />
        </div>

        {/* MongoDB Status */}
        <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between hover:border-[#CBD5E1] transition">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-[#D1FAE5] border border-[#10B981]/15 text-[#10B981]">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-[#64748B]">Database</div>
              <div className="text-sm font-semibold text-[#0F172A]">MongoDB</div>
            </div>
          </div>
          <StatusBadge
            status={services.database?.status || 'disconnected'}
            label={services.database?.status === 'healthy' ? 'Connected' : 'Standby'}
          />
        </div>

        {/* ML Engine Status */}
        <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between hover:border-[#CBD5E1] transition">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-[#EDE9FE] border border-[#4F46E5]/15 text-[#4F46E5]">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-[#64748B]">ML Engine</div>
              <div className="text-sm font-semibold text-[#0F172A]">4 Model Ensemble</div>
            </div>
          </div>
          <StatusBadge status={services.ml_engine?.status || 'initialized'} label="Initialized" />
        </div>
      </div>
    </div>
  );
}
