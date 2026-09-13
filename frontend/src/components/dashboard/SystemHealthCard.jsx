import React from 'react';
import { Activity, Server, Database, Cpu, RefreshCw, AlertCircle } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { formatDate } from '../../utils/formatters';

export function SystemHealthCard({ health, loading, error, onRefresh }) {
  if (loading && !health) {
    return (
      <div className="cyber-card animate-pulse p-6">
        <div className="h-5 bg-slate-700/50 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-10 bg-slate-800/60 rounded"></div>
          <div className="h-10 bg-slate-800/60 rounded"></div>
        </div>
      </div>
    );
  }

  if (error && !health) {
    return (
      <div className="cyber-card p-6 border-rose-500/30 bg-rose-950/10">
        <div className="flex items-center gap-3 text-rose-400 mb-2">
          <AlertCircle className="w-5 h-5" />
          <h3 className="font-semibold text-sm">Backend Disconnected</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">{error}</p>
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 bg-rose-500/20 text-rose-300 rounded text-xs hover:bg-rose-500/30 transition flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
        </button>
      </div>
    );
  }

  const services = health?.services || {};

  return (
    <div className="cyber-card p-6">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-slate-100 text-sm tracking-wide">System Health & Telemetry</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Checked: {formatDate(health?.timestamp)}</span>
          <button
            onClick={onRefresh}
            title="Refresh Health"
            className="p-1 text-slate-400 hover:text-indigo-400 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* FastAPI Status */}
        <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-md bg-indigo-500/10 text-indigo-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-slate-400">Backend API</div>
              <div className="text-sm font-semibold text-slate-100">FastAPI v{health?.version || '1.0.0'}</div>
            </div>
          </div>
          <StatusBadge status={services.api?.status || 'healthy'} />
        </div>

        {/* MongoDB Status */}
        <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-md bg-emerald-500/10 text-emerald-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-slate-400">Database</div>
              <div className="text-sm font-semibold text-slate-100">MongoDB</div>
            </div>
          </div>
          <StatusBadge
            status={services.database?.status || 'disconnected'}
            label={services.database?.status === 'healthy' ? 'Connected' : 'Standby'}
          />
        </div>

        {/* ML Engine Status */}
        <div className="p-4 rounded-lg bg-slate-800/40 border border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-md bg-purple-500/10 text-purple-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-medium text-slate-400">ML Engine</div>
              <div className="text-sm font-semibold text-slate-100">4 Model Ensemble</div>
            </div>
          </div>
          <StatusBadge status={services.ml_engine?.status || 'initialized'} label="Initialized" />
        </div>
      </div>
    </div>
  );
}
