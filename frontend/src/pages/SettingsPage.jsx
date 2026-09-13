import React from 'react';
import { Settings, Shield, Sliders, Database, Key } from 'lucide-react';
import { Card } from '../components/common/Card';

export function SettingsPage({ health }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide">System Configuration</h2>
          <p className="text-xs text-slate-400">Environment parameters, detection sensitivity, and security policies</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card
          title="Runtime Environment"
          subtitle="Backend configuration loaded from environment variables"
          icon={Sliders}
        >
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1.5 border-b border-white/5">
              <span className="text-slate-400">Environment</span>
              <span className="font-mono text-slate-200">{health?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-white/5">
              <span className="text-slate-400">Backend API Version</span>
              <span className="font-mono text-slate-200">v{health?.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-white/5">
              <span className="text-slate-400">Database Adapter</span>
              <span className="font-mono text-slate-200">MongoDB (Motor Async)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">API Documentation</span>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="font-mono text-indigo-400 hover:underline"
              >
                /docs (Swagger UI)
              </a>
            </div>
          </div>
        </Card>

        <Card
          title="Security & RBAC Architecture"
          subtitle="Prepared security and rate limiting controls"
          icon={Shield}
        >
          <div className="space-y-3 text-xs text-slate-300">
            <div className="p-3 rounded bg-slate-800/40 border border-white/5">
              <div className="font-semibold text-slate-200 mb-1">CORS Protection</div>
              <p className="text-[11px] text-slate-400">Configured with allowed origins from .env to isolate frontend communication.</p>
            </div>
            <div className="p-3 rounded bg-slate-800/40 border border-white/5">
              <div className="font-semibold text-slate-200 mb-1">Audit Trail & Access Control</div>
              <p className="text-[11px] text-slate-400">Architecture is pre-structured for JWT tokens, password hashing, and role-based policies.</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
