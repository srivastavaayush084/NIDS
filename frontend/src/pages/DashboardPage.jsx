import React from 'react';
import { ShieldCheck, ArrowRight, Layers, FileCode, CheckCircle } from 'lucide-react';
import { SystemHealthCard } from '../components/dashboard/SystemHealthCard';
import { AlertSummary } from '../components/alerts/AlertSummary';
import { ModelStatusGrid } from '../components/analytics/ModelStatusGrid';
import { Card } from '../components/common/Card';

export function DashboardPage({ health, healthLoading, healthError, refetchHealth, models, setTab }) {
  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-slate-900 p-6 md:p-8 border border-indigo-500/20 shadow-2xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-medium mb-3 border border-indigo-500/30">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>AI-Driven Zero-Day Cyber Defense Architecture</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
            Next-Gen Network Anomaly & Zero-Day Threat Detection
          </h2>
          <p className="text-slate-300 text-xs md:text-sm mt-2 leading-relaxed">
            Multi-tier detection pipeline combining Unsupervised Isolation Forests, Deep Reconstruction Autoencoders,
            Temporal LSTM Networks, and Random Forest baselines for zero-day network anomaly scoring.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setTab('models')}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition"
            >
              <span>Explore ML Registry</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTab('settings')}
              className="px-4 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-white/10 transition"
            >
              System Configuration
            </button>
          </div>
        </div>
      </div>

      {/* System Telemetry & Health */}
      <SystemHealthCard
        health={health}
        loading={healthLoading}
        error={healthError}
        onRefresh={refetchHealth}
      />

      {/* Grid of Alerts and ML Models */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelStatusGrid models={models} />
        <AlertSummary alerts={[]} />
      </div>

      {/* Architecture Pipeline Verification Card */}
      <Card
        title="Phase 1 Architectural Pipeline Verification"
        subtitle="End-to-end component readiness status"
        icon={Layers}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-slate-800/30 border border-white/5 space-y-2">
            <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>Backend API Layer</span>
            </div>
            <p className="text-[11px] text-slate-400">
              FastAPI service with Pydantic v2 schemas, CORS middleware, unified logging, and health probe endpoints.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/30 border border-white/5 space-y-2">
            <div className="flex items-center gap-2 text-purple-400 font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>ML Architecture Ensemble</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Scaffolding for 4 models (Isolation Forest, Autoencoder, LSTM, Random Forest) with decoupled inference engines.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/30 border border-white/5 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
              <span>Frontend Dashboard</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Modular React + Vite monitoring dashboard with live backend telemetry polling and modular layouts.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
