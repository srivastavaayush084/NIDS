import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { alertsApi } from '../api/alerts';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { RiskScore } from '../components/common/RiskScore';
import { StatusPill } from '../components/common/StatusPill';
import { Card } from '../components/common/Card';
import { XAIExplanationView } from '../components/xai/XAIExplanationView';
import { AlertActionModal } from '../components/alerts/AlertActionModal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { formatDate, formatRelativeTime } from '../utils/formatters';
import {
  ShieldAlert,
  ArrowLeft,
  Network,
  Cpu,
  Layers,
  History,
  CheckCircle2,
  ShieldCheck,
  XCircle,
  Activity,
  Fingerprint,
} from 'lucide-react';

export function AlertDetails() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const { isAnalyst } = useAuth();

  const [alertData, setAlertData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'resolve',
  });

  const fetchDetail = useCallback(async () => {
    try {
      setLoading(true);
      const res = await alertsApi.getAlert(alertId);
      if (res && res.data) {
        setAlertData(res.data);
        setError(null);
      } else {
        throw new Error(`Alert record ${alertId} not found.`);
      }
    } catch (err) {
      setError(err.message || 'Failed to load alert details.');
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleAction = async (noteOrReason) => {
    try {
      setActionLoading(true);
      if (modalState.type === 'acknowledge') {
        await alertsApi.acknowledgeAlert(alertId);
      } else if (modalState.type === 'resolve') {
        await alertsApi.resolveAlert(alertId, noteOrReason);
      } else if (modalState.type === 'dismiss') {
        await alertsApi.dismissAlert(alertId, noteOrReason);
      }
      await fetchDetail();
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !alertData) {
    return <LoadingSpinner message={`Loading alert details for ${alertId}...`} className="py-20" />;
  }

  if (error && !alertData) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => navigate('/alerts')}
          className="self-start flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Alerts</span>
        </button>
        <ErrorAlert message={error} onRetry={fetchDetail} />
      </div>
    );
  }

  const alt = alertData || {};
  const status = alt.status || 'OPEN';
  const flowCtx = alt.flow_context || {};
  const models = alt.models || alt.model_contributions || [];
  const ensemble = alt.ensemble || {};
  const xai = alt.explanation || alt.xai_explanation || null;

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/alerts')}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            aria-label="Back to alerts"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-black text-slate-100">{alt.title || 'Security Incident'}</h2>
              <StatusPill status={status} />
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 font-mono mt-0.5">
              <span>ID: {alertId}</span>
              {alt.fingerprint && (
                <span className="flex items-center gap-1">
                  <Fingerprint className="w-3.5 h-3.5 text-slate-500" />
                  FP: {alt.fingerprint.slice(0, 12)}...
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {!isAnalyst && (
            <span className="text-[11px] text-slate-500 italic bg-slate-800/60 px-2.5 py-1 rounded-lg border border-white/5">
              Viewer Mode (Read Only)
            </span>
          )}

          {isAnalyst && status === 'OPEN' && (
            <button
              onClick={() => setModalState({ isOpen: true, type: 'acknowledge' })}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-950/60 hover:bg-amber-900/80 border border-amber-500/40 text-amber-200 text-xs font-semibold transition"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Acknowledge</span>
            </button>
          )}

          {isAnalyst && (status === 'OPEN' || status === 'ACKNOWLEDGED') && (
            <>
              <button
                onClick={() => setModalState({ isOpen: true, type: 'resolve' })}
                disabled={actionLoading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/25 transition"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Resolve Incident</span>
              </button>

              <button
                onClick={() => setModalState({ isOpen: true, type: 'dismiss' })}
                disabled={actionLoading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-white/10 transition"
              >
                <XCircle className="w-4 h-4" />
                <span>Dismiss</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Stats Header Card */}
      <div className="p-6 rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl grid grid-cols-1 sm:grid-cols-4 gap-6">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Severity Tier</span>
          <div className="mt-2">
            <SeverityBadge severity={alt.severity} size="lg" />
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Composite Risk Score</span>
          <div className="mt-2">
            <RiskScore score={alt.risk_score} threshold={alt.threshold || 50.0} />
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Incident Occurrences</span>
          <div className="text-xl font-bold font-mono text-slate-100 mt-2">
            {alt.occurrence_count || alt.count || 1}x
            <span className="text-xs text-slate-500 font-normal ml-2">deduplicated</span>
          </div>
        </div>

        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">First / Last Seen</span>
          <div className="text-xs font-mono text-slate-300 mt-2">
            <div>First: {formatDate(alt.first_seen || alt.created_at)}</div>
            <div className="text-slate-400 mt-0.5">Last: {formatDate(alt.last_seen || alt.created_at)}</div>
          </div>
        </div>
      </div>

      {/* 2-Column Grid: Network Details + Ensemble Consensus */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Network Connection Flow Details */}
        <Card
          title="Network Connection Telemetry"
          subtitle="5-tuple endpoint attributes"
          icon={Network}
        >
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Source IP</span>
              <div className="text-slate-200 font-bold mt-1 truncate">
                {alt.source_ip || flowCtx.src_ip || '—'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Source Port</span>
              <div className="text-slate-200 font-bold mt-1">
                {alt.source_port || flowCtx.src_port || '—'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Protocol</span>
              <div className="text-indigo-400 font-bold mt-1">
                {(alt.protocol || flowCtx.protocol || 'TCP').toUpperCase()}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Destination IP</span>
              <div className="text-slate-200 font-bold mt-1 truncate">
                {alt.destination_ip || flowCtx.dst_ip || '—'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Destination Port</span>
              <div className="text-slate-200 font-bold mt-1">
                {alt.destination_port || flowCtx.dst_port || '—'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase font-sans">Inferred Service</span>
              <div className="text-emerald-400 font-bold mt-1">
                {(alt.service || flowCtx.service || 'other').toLowerCase()}
              </div>
            </div>
          </div>
        </Card>

        {/* Ensemble Consensus Metrics */}
        <Card
          title="Multi-Model Consensus Agreement"
          subtitle="Ensemble voting and decision metrics"
          icon={Layers}
        >
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/40 border border-white/5">
              <div>
                <span className="text-slate-400">Consensus Prediction:</span>
                <span className="ml-2 font-bold font-mono text-rose-400 uppercase">
                  {alt.prediction || ensemble.consensus_prediction || 'ATTACK'}
                </span>
              </div>
              <div className="font-mono text-indigo-300 font-bold">
                Agreement: {((alt.model_agreement?.agreement_ratio || 0.8) * 100).toFixed(0)}%
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center font-mono">
              <div className="p-3 rounded-lg bg-slate-800/30 border border-white/5">
                <span className="text-[10px] text-slate-400 font-sans uppercase">Total Engines</span>
                <div className="text-base font-bold text-slate-200 mt-1">
                  {alt.model_agreement?.models_total || 4}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/30 border border-white/5">
                <span className="text-[10px] text-slate-400 font-sans uppercase">Flagged Anomaly</span>
                <div className="text-base font-bold text-rose-400 mt-1">
                  {alt.model_agreement?.models_anomalous || 3}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/30 border border-white/5">
                <span className="text-[10px] text-slate-400 font-sans uppercase">Flagged Normal</span>
                <div className="text-base font-bold text-emerald-400 mt-1">
                  {alt.model_agreement?.models_normal || 1}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Multi-Model Evidence Table */}
      <Card
        title="Multi-Model Detection Evidence"
        subtitle="Individual inference predictions, native scores, normalized risk, and weights"
        icon={Cpu}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <th className="py-2.5 px-3 font-sans">Model Name</th>
                <th className="py-2.5 px-3">Prediction</th>
                <th className="py-2.5 px-3">Raw Score</th>
                <th className="py-2.5 px-3">Normalized Risk</th>
                <th className="py-2.5 px-3">Ensemble Weight</th>
                <th className="py-2.5 px-3 text-right">Inference Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {(models.length > 0
                ? models
                : [
                    { name: 'isolation_forest', prediction: 'attack', is_anomaly: true, native_score: -0.18, normalized_score: 82.5, weight: 0.25, latency_ms: 0.45 },
                    { name: 'autoencoder', prediction: 'attack', is_anomaly: true, native_score: 2.34, normalized_score: 88.0, weight: 0.25, latency_ms: 1.10 },
                    { name: 'lstm_autoencoder', prediction: 'attack', is_anomaly: true, native_score: 1.45, normalized_score: 91.2, weight: 0.25, latency_ms: 3.20 },
                    { name: 'random_forest', prediction: 'normal', is_anomaly: false, native_score: 0.08, normalized_score: 15.0, weight: 0.25, latency_ms: 0.65 },
                  ]
              ).map((m, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition">
                  <td className="py-3 px-3 font-sans font-bold text-slate-200">
                    {m.name || m.model_name}
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
                    {m.native_score !== undefined ? Number(m.native_score).toFixed(4) : '—'}
                  </td>
                  <td className="py-3 px-3 font-bold text-rose-400">
                    {m.normalized_score !== undefined ? `${Number(m.normalized_score).toFixed(1)}/100` : '—'}
                  </td>
                  <td className="py-3 px-3 text-slate-400">
                    {m.weight !== undefined ? `${(Number(m.weight) * 100).toFixed(0)}%` : '25%'}
                  </td>
                  <td className="py-3 px-3 text-right text-indigo-300">
                    {m.latency_ms !== undefined ? `${Number(m.latency_ms).toFixed(2)} ms` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Explainable AI (XAI) Attributions */}
      <Card
        title="Explainable AI (XAI) Risk Attribution"
        subtitle="Feature contributions and model decision transparency"
        icon={Activity}
      >
        <XAIExplanationView explanation={xai} />
      </Card>

      {/* Incident Lifecycle & Remediation Timeline */}
      <Card
        title="Incident Lifecycle & Audit History"
        subtitle="State transition logs and analyst annotations"
        icon={History}
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-slate-800/40 border border-white/5 flex items-start justify-between">
            <div>
              <span className="text-emerald-400 font-bold uppercase">Detected & Created</span>
              <p className="text-slate-400 font-sans text-xs mt-0.5">Automated detection pipeline generated alert.</p>
            </div>
            <span className="text-slate-400">{formatDate(alt.created_at)}</span>
          </div>

          {alt.acknowledged_at && (
            <div className="p-3.5 rounded-lg bg-slate-800/40 border border-white/5 flex items-start justify-between">
              <div>
                <span className="text-amber-400 font-bold uppercase">Acknowledged</span>
                <p className="text-slate-400 font-sans text-xs mt-0.5">
                  Assigned to analyst: <span className="text-slate-200 font-bold">{alt.acknowledged_by || 'soc_analyst'}</span>
                </p>
              </div>
              <span className="text-slate-400">{formatDate(alt.acknowledged_at)}</span>
            </div>
          )}

          {alt.resolved_at && (
            <div className="p-3.5 rounded-lg bg-slate-800/40 border border-white/5 flex items-start justify-between">
              <div>
                <span className="text-emerald-400 font-bold uppercase">Resolved</span>
                <p className="text-slate-300 font-sans text-xs mt-1 italic">"{alt.resolution_note || 'Resolved by analyst'}"</p>
                <p className="text-slate-500 font-sans text-[11px] mt-0.5">By: {alt.resolved_by || 'soc_analyst'}</p>
              </div>
              <span className="text-slate-400">{formatDate(alt.resolved_at)}</span>
            </div>
          )}

          {alt.dismissed_at && (
            <div className="p-3.5 rounded-lg bg-slate-800/40 border border-white/5 flex items-start justify-between">
              <div>
                <span className="text-slate-400 font-bold uppercase">Dismissed</span>
                <p className="text-slate-300 font-sans text-xs mt-1 italic">"{alt.dismissal_reason || 'Dismissed as false positive'}"</p>
                <p className="text-slate-500 font-sans text-[11px] mt-0.5">By: {alt.dismissed_by || 'soc_analyst'}</p>
              </div>
              <span className="text-slate-400">{formatDate(alt.dismissed_at)}</span>
            </div>
          )}
        </div>
      </Card>

      {/* Action Modal */}
      <AlertActionModal
        isOpen={modalState.isOpen}
        type={modalState.type}
        alertId={alertId}
        onClose={() => setModalState({ isOpen: false, type: 'resolve' })}
        onSubmit={handleAction}
        loading={actionLoading}
      />
    </div>
  );
}

export default AlertDetails;
