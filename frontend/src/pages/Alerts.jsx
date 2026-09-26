import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAlerts } from '../hooks/useAlerts';
import { useAuth } from '../hooks/useAuth';
import { AlertsTable } from '../components/alerts/AlertsTable';
import { AlertFilters } from '../components/alerts/AlertFilters';
import { AlertActionModal } from '../components/alerts/AlertActionModal';
import { Card } from '../components/common/Card';
import { Pagination } from '../components/common/Pagination';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ShieldAlert, RefreshCw, ShieldCheck, XCircle, X } from 'lucide-react';

export function Alerts() {
  const navigate = useNavigate();
  const { isAnalyst } = useAuth();
  const {
    alerts,
    pagination,
    params,
    loading,
    error,
    actionLoading,
    refetch,
    updateFilters,
    setPage,
    acknowledgeAlert,
    resolveAlert,
    dismissAlert,
    bulkUpdateAlerts,
  } = useAlerts({ page_size: 20 }, true);

  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkFeedback, setBulkFeedback] = useState(null);

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'resolve',
    alertId: null,
    isBulk: false,
    count: 1,
  });

  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    const pageIds = alerts.map((a) => a.alert_id || a._id || a.id).filter(Boolean);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...pageIds])));
    }
  };

  const handleClearSelection = () => {
    setSelectedIds([]);
  };

  const handleOpenActionModal = (type, alertId) => {
    setModalState({
      isOpen: true,
      type,
      alertId,
      isBulk: false,
      count: 1,
    });
  };

  const handleOpenBulkModal = (type) => {
    if (selectedIds.length === 0) return;
    setModalState({
      isOpen: true,
      type,
      alertId: null,
      isBulk: true,
      count: selectedIds.length,
    });
  };

  const handleModalSubmit = async (noteOrReason) => {
    const { type, alertId, isBulk } = modalState;
    if (isBulk) {
      try {
        const res = await bulkUpdateAlerts(selectedIds, type, noteOrReason);
        const count = res?.updated_count ?? selectedIds.length;
        setBulkFeedback({
          type: 'success',
          message:
            type === 'resolve'
              ? `Successfully resolved ${count} security incident${count > 1 ? 's' : ''}.`
              : `Successfully confirmed ${count} incident${count > 1 ? 's' : ''} as normal / dismissed.`,
        });
        setSelectedIds([]);
        setTimeout(() => setBulkFeedback(null), 5000);
      } catch (err) {
        setBulkFeedback({
          type: 'error',
          message: err.response?.data?.detail || err.message || 'Bulk operation failed.',
        });
      }
    } else {
      if (type === 'acknowledge') {
        await acknowledgeAlert(alertId);
      } else if (type === 'resolve') {
        await resolveAlert(alertId, noteOrReason);
      } else if (type === 'dismiss') {
        await dismissAlert(alertId, noteOrReason);
      }
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-rose-500" />
            <span>Security Incident Triage</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review, investigate, acknowledge, resolve, and dismiss active multi-model security alerts.
          </p>
        </div>

        <button
          onClick={refetch}
          disabled={loading}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-[#0F172A] text-xs font-semibold border border-[#CBD5E1] shadow-2xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#2563EB]' : 'text-[#64748B]'}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={refetch} />}

      {bulkFeedback && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between shadow-lg animate-fade-in ${
            bulkFeedback.type === 'success'
              ? 'bg-emerald-950/70 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-950/70 border-rose-500/40 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {bulkFeedback.type === 'success' ? (
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span className="font-medium">{bulkFeedback.message}</span>
          </div>
          <button
            onClick={() => setBulkFeedback(null)}
            className="text-slate-400 hover:text-white p-1 rounded transition"
            title="Dismiss notification"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Backend Filter Controls */}
      <AlertFilters
        filters={params}
        onFilterChange={(newFilters) => {
          setSelectedIds([]);
          updateFilters(newFilters);
        }}
        onReset={() => {
          setSelectedIds([]);
          updateFilters({});
        }}
      />

      {/* Bulk Action Sticky/Floating Bar */}
      {selectedIds.length > 0 && isAnalyst && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 rounded-xl bg-slate-900/95 border border-indigo-500/40 shadow-xl backdrop-blur-md animate-fade-in text-xs">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded-full bg-indigo-600 text-white font-bold text-[11px]">
              {selectedIds.length}
            </span>
            <span className="font-semibold text-slate-100">
              {selectedIds.length} incident{selectedIds.length > 1 ? 's' : ''} selected
            </span>
            <button
              type="button"
              onClick={handleClearSelection}
              className="text-slate-400 hover:text-white underline text-[11px] ml-1 transition"
            >
              Clear selection
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleOpenBulkModal('resolve')}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-xs transition"
              title="Resolve all selected incidents at once"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Resolve Selected ({selectedIds.length})</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenBulkModal('dismiss')}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 hover:text-white font-semibold shadow-xs transition"
              title="Confirm selected incidents as normal benign traffic (false positives)"
            >
              <XCircle className="w-4 h-4" />
              <span>Confirm as Normal ({selectedIds.length})</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Alerts Table Card */}
      <Card
        title="Security Alerts"
        subtitle={`Displaying ${pagination.total} incident records`}
        headerClassName="py-3 px-4"
        bodyClassName="p-0"
      >
        {loading && alerts.length === 0 ? (
          <LoadingSpinner message="Querying security incident records..." className="py-16" />
        ) : (
          <>
            <AlertsTable
              alerts={alerts}
              selectedIds={selectedIds}
              onToggleSelect={isAnalyst ? handleToggleSelect : undefined}
              onToggleSelectAll={isAnalyst ? handleToggleSelectAll : undefined}
              onViewDetails={(alertId) => navigate(`/alerts/${alertId}`)}
              onAcknowledge={(alertId) => handleOpenActionModal('acknowledge', alertId)}
              onResolve={(alertId) => handleOpenActionModal('resolve', alertId)}
              onDismiss={(alertId) => handleOpenActionModal('dismiss', alertId)}
              actionLoading={actionLoading}
            />

            <Pagination
              currentPage={pagination.page}
              totalPages={pagination.total_pages}
              totalItems={pagination.total}
              pageSize={pagination.page_size}
              onPageChange={(page) => {
                setSelectedIds([]);
                setPage(page);
              }}
            />
          </>
        )}
      </Card>

      {/* Alert Lifecycle Action Modal */}
      <AlertActionModal
        isOpen={modalState.isOpen}
        type={modalState.type}
        alertId={modalState.alertId}
        count={modalState.count || 1}
        onClose={() => setModalState({ isOpen: false, type: 'resolve', alertId: null, isBulk: false, count: 1 })}
        onSubmit={handleModalSubmit}
        loading={actionLoading}
      />
    </div>
  );
}

export default Alerts;
