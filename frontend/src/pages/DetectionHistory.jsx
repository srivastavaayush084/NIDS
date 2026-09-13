import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDetection } from '../hooks/useDetection';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { Card } from '../components/common/Card';
import { Pagination } from '../components/common/Pagination';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { formatDate, formatRelativeTime } from '../utils/formatters';
import { History, Eye, RotateCcw, ShieldAlert, ShieldCheck, RefreshCw } from 'lucide-react';

export function DetectionHistory() {
  const navigate = useNavigate();
  const {
    detections,
    pagination,
    params,
    loading,
    error,
    refetch,
    updateFilters,
    setPage,
  } = useDetection({ page_size: 20 }, false);

  const [localFilters, setLocalFilters] = useState({
    severity: params.severity || '',
    prediction: params.prediction || '',
    min_risk_score: params.min_risk_score || '',
  });

  const handleFilterChange = (key, val) => {
    const updated = { ...localFilters, [key]: val };
    setLocalFilters(updated);
    updateFilters(updated);
  };

  const handleReset = () => {
    const cleared = { severity: '', prediction: '', min_risk_score: '' };
    setLocalFilters(cleared);
    updateFilters(cleared);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide flex items-center gap-2.5">
            <History className="w-5 h-5 text-indigo-400" />
            <span>Detection Event History</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Audit log of all network events evaluated across the ML Ensemble Detection subsystem.
          </p>
        </div>

        <button
          onClick={refetch}
          disabled={loading}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-white/10 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={refetch} />}

      {/* Filters */}
      <div className="p-4 rounded-xl border border-white/10 bg-slate-900/60 flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5 min-w-[130px]">
          <label className="text-slate-400 text-[11px] font-semibold uppercase">Severity:</label>
          <select
            value={localFilters.severity}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
            className="bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 min-w-[130px]">
          <label className="text-slate-400 text-[11px] font-semibold uppercase">Prediction:</label>
          <select
            value={localFilters.prediction}
            onChange={(e) => handleFilterChange('prediction', e.target.value)}
            className="bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All</option>
            <option value="attack">Attack</option>
            <option value="normal">Normal</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-slate-400 text-[11px] font-semibold uppercase">Min Risk:</label>
          <input
            type="number"
            min="0"
            max="100"
            value={localFilters.min_risk_score}
            onChange={(e) => handleFilterChange('min_risk_score', e.target.value)}
            placeholder="0"
            className="w-16 bg-slate-800 border border-white/10 rounded-lg px-2 py-1.5 font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <button
          onClick={handleReset}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      </div>

      {/* Main Table */}
      <Card
        title="Evaluated Events"
        subtitle={`Total evaluated flows: ${pagination.total}`}
        bodyClassName="p-0"
      >
        {loading && detections.length === 0 ? (
          <LoadingSpinner message="Querying detection history..." className="py-16" />
        ) : detections.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            No detection records match current filters.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-800/40">
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3">Detection ID</th>
                    <th className="px-4 py-3">Endpoints</th>
                    <th className="px-4 py-3">Risk Score</th>
                    <th className="px-4 py-3">Prediction</th>
                    <th className="px-4 py-3">Model Agreement</th>
                    <th className="px-4 py-3">Evaluated At</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {detections.map((det) => {
                    const detId = det.detection_id || det._id || det.id;
                    const src = det.flow_context?.src_ip || det.source_ip || '—';
                    const dst = det.flow_context?.dst_ip || det.destination_ip || '—';
                    const risk = Number(det.risk_score || 0).toFixed(1);
                    const isAttack = det.prediction === 'attack' || det.is_anomaly;
                    const agreement = det.model_agreement?.agreement_ratio
                      ? `${(det.model_agreement.agreement_ratio * 100).toFixed(0)}%`
                      : '—';

                    return (
                      <tr
                        key={detId}
                        onClick={() => navigate(`/detections/${detId}`)}
                        className="hover:bg-slate-800/30 transition cursor-pointer"
                      >
                        <td className="px-4 py-3">
                          <SeverityBadge severity={det.severity} size="sm" />
                        </td>

                        <td className="px-4 py-3 font-mono font-medium text-slate-300">
                          {detId}
                        </td>

                        <td className="px-4 py-3 font-mono text-slate-300">
                          <span>{src}</span>
                          <span className="text-slate-500 mx-1.5">&rarr;</span>
                          <span>{dst}</span>
                        </td>

                        <td className="px-4 py-3 font-mono font-bold text-rose-400">
                          {risk}
                        </td>

                        <td className="px-4 py-3">
                          {isAttack ? (
                            <span className="inline-flex items-center gap-1 font-semibold text-rose-400">
                              <ShieldAlert className="w-3.5 h-3.5" />
                              <span>ATTACK</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 font-semibold text-emerald-400">
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>NORMAL</span>
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3 font-mono text-indigo-300 font-semibold">
                          {agreement}
                        </td>

                        <td className="px-4 py-3 text-slate-400" title={formatDate(det.timestamp)}>
                          {formatRelativeTime(det.timestamp)}
                        </td>

                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/detections/${detId}`);
                            }}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <Pagination
              currentPage={pagination.page}
              totalPages={pagination.total_pages}
              totalItems={pagination.total}
              pageSize={pagination.page_size}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>
    </div>
  );
}

export default DetectionHistory;
