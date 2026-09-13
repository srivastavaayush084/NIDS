import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { detectionApi } from '../api/detection';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { RiskScore } from '../components/common/RiskScore';
import { Card } from '../components/common/Card';
import { XAIExplanationView } from '../components/xai/XAIExplanationView';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { formatDate } from '../utils/formatters';
import {
  History,
  ArrowLeft,
  Cpu,
  Layers,
  Activity,
  ShieldAlert,
  ArrowRight,
  Clock,
  Network,
} from 'lucide-react';

export function DetectionDetails() {
  const { detectionId } = useParams();
  const navigate = useNavigate();

  const [det, setDet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDetail = useCallback(async () => {
    try {
      setLoading(true);
      const res = await detectionApi.getDetection(detectionId);
      if (res && res.data) {
        setDet(res.data);
        setError(null);
      } else {
        throw new Error(`Detection record ${detectionId} not found.`);
      }
    } catch (err) {
      setError(err.message || 'Failed to load detection record.');
    } finally {
      setLoading(false);
    }
  }, [detectionId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  if (loading && !det) {
    return <LoadingSpinner message={`Loading detection ${detectionId}...`} className="py-20" />;
  }

  if (error && !det) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => navigate('/detections')}
          className="self-start flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Detection History</span>
        </button>
        <ErrorAlert message={error} onRetry={fetchDetail} />
      </div>
    );
  }

  const isAttack = det.prediction === 'attack' || det.is_anomaly;
  const flowCtx = det.flow_context || {};
  const models = det.models || [];
  const xai = det.explanation;
  const alertId = det.alert?.alert_id || det.alert_id;

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/detections')}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            aria-label="Back to detections"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-black text-slate-100">Detection Event Record</h2>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${
                  isAttack
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                }`}
              >
                {(det.prediction || 'NORMAL').toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {detectionId}</p>
          </div>
        </div>

        {alertId && (
          <button
            onClick={() => navigate(`/alerts/${alertId}`)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/25 transition"
          >
            <ShieldAlert className="w-4 h-4" />
            <span>View Security Alert</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Summary KPI Header */}
      <div className="p-6 rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl grid grid-cols-1 sm:grid-cols-4 gap-6">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Severity Tier</span>
          <div className="mt-2">
            <SeverityBadge severity={det.severity} size="lg" />
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Composite Risk</span>
          <div className="mt-2">
            <RiskScore score={det.risk_score} threshold={det.threshold || 50.0} />
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Inference Latency</span>
          <div className="text-xl font-bold font-mono text-indigo-300 mt-2 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-slate-400" />
            <span>{Number(det.processing_time_ms || 0).toFixed(2)} ms</span>
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Evaluated Timestamp</span>
          <div className="text-xs font-mono text-slate-300 mt-2">
            {formatDate(det.timestamp)}
          </div>
        </div>
      </div>

      {/* Network Endpoints & Agreement */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Flow Endpoints" subtitle="Network layer attributes" icon={Network}>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 font-sans uppercase">Source</span>
              <div className="text-slate-200 font-bold mt-1 truncate">
                {flowCtx.src_ip || '—'}
                {flowCtx.src_port && `:${flowCtx.src_port}`}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 font-sans uppercase">Destination</span>
              <div className="text-slate-200 font-bold mt-1 truncate">
                {flowCtx.dst_ip || '—'}
                {flowCtx.dst_port && `:${flowCtx.dst_port}`}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 font-sans uppercase">Protocol / Service</span>
              <div className="text-indigo-400 font-bold mt-1">
                {(flowCtx.protocol || 'TCP').toUpperCase()} / {(flowCtx.service || 'other').toLowerCase()}
              </div>
            </div>
          </div>
        </Card>

        <Card title="Model Consensus" subtitle="Agreement ratio across engines" icon={Layers}>
          <div className="p-4 rounded-xl bg-slate-800/40 border border-white/5 flex items-center justify-between text-xs">
            <div>
              <span className="text-slate-400">Consensus Prediction:</span>
              <span className="ml-2 font-bold font-mono text-rose-400 uppercase">
                {det.prediction || 'ATTACK'}
              </span>
            </div>
            <div className="font-mono text-indigo-300 font-bold">
              Agreement: {((det.model_agreement?.agreement_ratio || 0.8) * 100).toFixed(0)}%
            </div>
          </div>
        </Card>
      </div>

      {/* Multi-Model Breakdown Table */}
      <Card
        title="Individual Model Predictions & Risk Contributions"
        subtitle="Inference details for each participating detector"
        icon={Cpu}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <th className="py-2.5 px-3 font-sans">Model</th>
                <th className="py-2.5 px-3">Prediction</th>
                <th className="py-2.5 px-3">Raw Score</th>
                <th className="py-2.5 px-3">Normalized Score</th>
                <th className="py-2.5 px-3">Weight</th>
                <th className="py-2.5 px-3 text-right">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {models.map((m, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition">
                  <td className="py-3 px-3 font-sans font-bold text-slate-200">
                    {m.name}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        m.is_anomaly || m.prediction === 'attack'
                          ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                          : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {(m.prediction || 'normal').toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    {Number(m.native_score || 0).toFixed(4)}
                  </td>
                  <td className="py-3 px-3 font-bold text-rose-400">
                    {Number(m.normalized_score || 0).toFixed(1)}/100
                  </td>
                  <td className="py-3 px-3 text-slate-400">
                    {(Number(m.weight || 0.25) * 100).toFixed(0)}%
                  </td>
                  <td className="py-3 px-3 text-right text-indigo-300">
                    {Number(m.latency_ms || 0).toFixed(2)} ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Explainable AI Component */}
      <Card
        title="Explainable AI (XAI) Feature Attributions"
        subtitle="Feature importance weights explaining why this event was classified as normal or anomalous"
        icon={Activity}
      >
        <XAIExplanationView explanation={xai} />
      </Card>
    </div>
  );
}

export default DetectionDetails;
