import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAlerts } from '../hooks/useAlerts';
import { AlertsTable } from '../components/alerts/AlertsTable';
import { AlertFilters } from '../components/alerts/AlertFilters';
import { AlertActionModal } from '../components/alerts/AlertActionModal';
import { Card } from '../components/common/Card';
import { Pagination } from '../components/common/Pagination';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export function Alerts() {
  const navigate = useNavigate();
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
  } = useAlerts({ page_size: 20 }, true);

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'resolve',
    alertId: null,
  });

  const handleOpenActionModal = (type, alertId) => {
    setModalState({
      isOpen: true,
      type,
      alertId,
    });
  };

  const handleModalSubmit = async (noteOrReason) => {
    const { type, alertId } = modalState;
    if (type === 'acknowledge') {
      await acknowledgeAlert(alertId);
    } else if (type === 'resolve') {
      await resolveAlert(alertId, noteOrReason);
    } else if (type === 'dismiss') {
      await dismissAlert(alertId, noteOrReason);
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
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-white/10 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={refetch} />}

      {/* Backend Filter Controls */}
      <AlertFilters
        filters={params}
        onFilterChange={updateFilters}
        onReset={() => updateFilters({})}
      />

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
              onPageChange={setPage}
            />
          </>
        )}
      </Card>

      {/* Alert Lifecycle Action Modal */}
      <AlertActionModal
        isOpen={modalState.isOpen}
        type={modalState.type}
        alertId={modalState.alertId}
        onClose={() => setModalState({ isOpen: false, type: 'resolve', alertId: null })}
        onSubmit={handleModalSubmit}
        loading={actionLoading}
      />
    </div>
  );
}

export default Alerts;
