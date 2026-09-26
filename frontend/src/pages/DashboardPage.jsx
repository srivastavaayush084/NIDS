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
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#EAF2FF] via-white to-white p-6 md:p-8 border border-[#E2E8F0] shadow-sm">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#2563EB]/10 text-[#2563EB] text-xs font-semibold mb-3 border border-[#2563EB]/20">
            <ShieldCheck className="w-4 h-4 text-[#2563EB]" />
            <span>AI-Driven Zero-Day Cyber Defense Architecture</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-[#0F172A] tracking-tight">
            Next-Gen Network Anomaly & Zero-Day Threat Detection
          </h2>
          <p className="text-[#64748B] text-xs md:text-sm mt-2 leading-relaxed">
            Multi-tier detection pipeline combining Unsupervised Isolation Forests, Deep Reconstruction Autoencoders,
            Temporal LSTM Networks, and Random Forest baselines for zero-day network anomaly scoring.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setTab('models')}
              className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-[#2563EB]/25 transition"
            >
              <span>Explore ML Registry</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTab('settings')}
              className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 text-[#0F172A] text-xs font-semibold border border-[#CBD5E1] shadow-2xs transition"
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
          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2 hover:border-[#CBD5E1] transition">
            <div className="flex items-center gap-2 text-[#2563EB] font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-[#10B981]" />
              <span>Backend API Layer</span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              FastAPI service with Pydantic v2 schemas, CORS middleware, unified logging, and health probe endpoints.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2 hover:border-[#CBD5E1] transition">
            <div className="flex items-center gap-2 text-[#4F46E5] font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-[#10B981]" />
              <span>ML Architecture Ensemble</span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              Scaffolding for 4 models (Isolation Forest, Autoencoder, LSTM, Random Forest) with decoupled inference engines.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2 hover:border-[#CBD5E1] transition">
            <div className="flex items-center gap-2 text-[#10B981] font-semibold text-xs">
              <CheckCircle className="w-4 h-4 text-[#10B981]" />
              <span>Frontend Dashboard</span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              Modular React + Vite monitoring dashboard with live backend telemetry polling and modular layouts.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
