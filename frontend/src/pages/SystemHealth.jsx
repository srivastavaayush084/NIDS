import React from 'react';
import { useHealth } from '../hooks/useHealth';
import { SystemHealthGrid } from '../components/health/SystemHealthGrid';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { Activity, RefreshCw } from 'lucide-react';

export function SystemHealth() {
  const { health, detailed, loading, error, refetch } = useHealth(10000);

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-emerald-400" />
            <span>System Health & Telemetry</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time operational status across FastAPI server, MongoDB persistence engine, ML models, and network monitoring pipeline.
          </p>
        </div>

        <button
          onClick={refetch}
          disabled={loading}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-white/10 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          <span>Refresh Diagnostics</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={refetch} />}

      {loading && !health ? (
        <LoadingSpinner message="Polling system diagnostics..." className="py-20" />
      ) : (
        <SystemHealthGrid health={health} detailed={detailed} onRefresh={refetch} />
      )}
    </div>
  );
}

export default SystemHealth;
