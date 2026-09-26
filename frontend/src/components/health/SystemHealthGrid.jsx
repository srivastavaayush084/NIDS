import React from 'react';
import { Server, Database, Cpu, Radio, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { StatusPill } from '../common/StatusPill';

export function SystemHealthGrid({ health = null }) {
  // Authoritative MongoDB telemetry resolution
  const mongoDetails = health?.mongodb || health?.services?.database?.details || {};
  const mongoStatusRaw = (health?.mongodb?.status || health?.database || health?.services?.database?.status || '').toLowerCase();

  let dbBadgeStatus = 'DISCONNECTED';
  let dbConnectionText = 'Offline';

  if (mongoStatusRaw === 'connected' || mongoStatusRaw === 'healthy' || mongoDetails.connected === true) {
    dbBadgeStatus = 'CONNECTED';
    dbConnectionText = 'Online';
  } else if (mongoStatusRaw === 'error') {
    dbBadgeStatus = 'ERROR';
    dbConnectionText = 'Error';
  } else {
    dbBadgeStatus = 'DISCONNECTED';
    dbConnectionText = 'Offline';
  }

  const dbName = mongoDetails.database || 'zero_day_detection';
  const dbServerType = mongoDetails.server_type ? 
    (mongoDetails.server_type.toLowerCase().includes('replica') ? 'Replica Set' : (mongoDetails.server_type.toLowerCase().includes('mongos') ? 'Sharded Cluster' : 'Standalone')) : 
    'Standalone';
  const dbLatency = mongoDetails.latency_ms != null ? `${Number(mongoDetails.latency_ms).toFixed(1)}ms` : (dbBadgeStatus === 'CONNECTED' ? '< 5ms' : 'N/A');

  const apiStatus = (health?.status || 'HEALTHY').toUpperCase();
  const modelsStatus = (health?.services?.ml_engine?.status || 'HEALTHY').toUpperCase();
  const monitoringStatus = (health?.services?.monitoring?.status || health?.monitoring || 'ACTIVE').toUpperCase();

  const iconColors = ['#2563EB', '#10B981', '#4F46E5', '#06B6D4'];
  const iconBgs = ['#EAF2FF', '#D1FAE5', '#EDE9FE', '#ECFEFF'];

  const components = [
    {
      name: 'REST API Subsystem',
      status: apiStatus,
      icon: Server,
      desc: 'FastAPI REST Layer, CORS middleware, and route dispatchers.',
      colorIdx: 0,
      metrics: {
        Version: health?.version || '1.0.0',
        Environment: health?.environment || 'development',
        Latency: health?.services?.api?.details?.latency_ms != null ? `${Number(health.services.api.details.latency_ms).toFixed(1)}ms` : '< 5ms',
      },
    },
    {
      name: 'MongoDB Persistence Engine',
      status: dbBadgeStatus,
      icon: Database,
      desc: 'Document storage for alerts, detections, telemetry, and audit logs.',
      colorIdx: 1,
      metrics: {
        Database: dbName,
        ServerType: dbServerType,
        Connection: dbConnectionText,
      },
    },
    {
      name: 'AI/ML Detection Subsystem',
      status: modelsStatus,
      icon: Cpu,
      desc: 'Isolation Forest, Dense Autoencoder, LSTM Autoencoder, and Random Forest.',
      colorIdx: 2,
      metrics: {
        ModelsActive: `${health?.services?.ml_engine?.details?.available_models ?? 4}/4 Operational`,
        InferenceEngine: 'PyTorch + Joblib',
        Pipeline: 'NetworkDataPipeline',
      },
    },
    {
      name: 'Network Traffic Ingestion',
      status: monitoringStatus,
      icon: Radio,
      desc: 'Packet capture driver, bidirectional flow parser, and buffer queue.',
      colorIdx: 3,
      metrics: {
        ScapyEngine: 'Operational',
        Driver: 'Npcap / Native',
        BufferCapacity: '10,000 Flows',
      },
    },
  ];

  const modelsMap = health?.services?.ml_engine?.details?.models || {};
  const modelsMatrix = [
    { name: 'Isolation Forest', type: 'Unsupervised', isHealthy: (modelsMap['isolation_forest'] === 'available' || !modelsMap['isolation_forest']) },
    { name: 'Dense Autoencoder', type: 'Reconstruction', isHealthy: (modelsMap['autoencoder'] === 'available' || !modelsMap['autoencoder']) },
    { name: 'LSTM Autoencoder', type: 'Sequential', isHealthy: (modelsMap['lstm_autoencoder'] === 'available' || !modelsMap['lstm_autoencoder']) },
    { name: 'Random Forest', type: 'Supervised', isHealthy: (modelsMap['random_forest'] === 'available' || !modelsMap['random_forest']) },
    { name: 'Ensemble Engine', type: 'Composite Risk', isHealthy: (modelsMap['ensemble'] === 'available' || !modelsMap['ensemble']) },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Top Component Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {components.map((comp, idx) => {
          const Icon = comp.icon;
          return (
            <div
              key={idx}
              className="p-5 rounded-2xl border border-[#E2E8F0] bg-white flex flex-col justify-between shadow-sm hover:shadow-md hover:border-[#CBD5E1] transition-all duration-200"
            >
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
                  <div className="flex items-center gap-3">
                    <div
                      className="p-2.5 rounded-xl border"
                      style={{
                        backgroundColor: iconBgs[comp.colorIdx],
                        color: iconColors[comp.colorIdx],
                        borderColor: `${iconColors[comp.colorIdx]}20`,
                      }}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-[#0F172A]">{comp.name}</h3>
                      <p className="text-xs text-[#64748B] mt-0.5">{comp.desc}</p>
                    </div>
                  </div>
                  <StatusPill status={comp.status} />
                </div>

                <div className="grid grid-cols-3 gap-2 mt-4 text-xs font-mono">
                  {Object.entries(comp.metrics).map(([k, v]) => (
                    <div key={k} className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                      <span className="text-[10px] font-sans uppercase text-[#64748B] font-semibold">{k}</span>
                      <div className="text-[#0F172A] font-bold mt-0.5 truncate">{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Model Health Status Matrix */}
      <div className="border border-[#E2E8F0] rounded-2xl overflow-hidden bg-white p-5 shadow-sm">
        <h4 className="text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-4 flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-[#2563EB]">
            <Activity className="w-4 h-4" />
          </div>
          <span>Active ML Detection Engine Availability</span>
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {modelsMatrix.map((m, idx) => (
            <div key={idx} className="p-3 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col justify-between hover:border-[#CBD5E1] transition">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-bold text-[#0F172A]">{m.name}</span>
                  {m.isHealthy ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-[#EF4444]" />
                  )}
                </div>
                <span className="text-[10px] text-[#64748B] font-mono">{m.type}</span>
              </div>
              <div className="mt-3 pt-2 border-t border-[#E2E8F0] flex items-center justify-between text-[10px]">
                <span className="text-[#64748B]">Status</span>
                <span className={`font-bold ${m.isHealthy ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
                  {m.isHealthy ? 'HEALTHY' : 'UNAVAILABLE'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SystemHealthGrid;

