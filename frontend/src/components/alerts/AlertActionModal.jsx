import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { ShieldCheck, XCircle, CheckCircle2, Loader2 } from 'lucide-react';

export function AlertActionModal({
  isOpen = false,
  type = 'resolve', // 'resolve', 'dismiss', 'acknowledge'
  alertId = null,
  count = 1,
  onClose,
  onSubmit,
  loading = false,
}) {
  const isBulk = count > 1;
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);

  React.useEffect(() => {
    if (isOpen) {
      setNote(
        isBulk
          ? (type === 'resolve' ? 'Bulk resolved by security analyst.' : 'Confirmed as normal benign traffic / false positive.')
          : ''
      );
      setError(null);
    }
  }, [isOpen, isBulk, type]);

  const getTitle = () => {
    if (isBulk) {
      switch (type) {
        case 'resolve':
          return `Resolve ${count} Security Incidents`;
        case 'dismiss':
          return `Confirm ${count} Incidents as Normal`;
        default:
          return `Acknowledge ${count} Incidents`;
      }
    }
    switch (type) {
      case 'resolve':
        return 'Resolve Security Incident';
      case 'dismiss':
        return 'Confirm as Normal / Dismiss Alert';
      default:
        return 'Acknowledge Alert';
    }
  };

  const getSubtitle = () => {
    if (isBulk) {
      switch (type) {
        case 'resolve':
          return `Transition all ${count} selected incidents to RESOLVED status`;
        case 'dismiss':
          return `Confirm all ${count} selected incidents as normal / false positive (DISMISSED)`;
        default:
          return `Acknowledge all ${count} selected incidents`;
      }
    }
    switch (type) {
      case 'resolve':
        return `Provide remediation notes for alert ${alertId}`;
      case 'dismiss':
        return `State reason for confirming alert ${alertId} as normal`;
      default:
        return `Confirm taking ownership of alert ${alertId}`;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if ((type === 'resolve' || type === 'dismiss') && note.trim().length < 3) {
      setError('Please provide at least 3 characters explaining your action.');
      return;
    }
    setError(null);
    try {
      await onSubmit(note);
      setNote('');
      onClose();
    } catch (err) {
      setError(err.message || 'Action failed.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getTitle()}
      subtitle={getSubtitle()}
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 text-xs">
        {error && (
          <div className="p-3 rounded-lg bg-red-950/50 border border-red-500/30 text-red-300">
            {error}
          </div>
        )}

        {(type === 'resolve' || type === 'dismiss') && (
          <div>
            <label className="block text-[#0F172A] font-semibold mb-1.5">
              {type === 'resolve' ? 'Remediation Note *' : 'Dismissal Reason *'}
            </label>
            <textarea
              rows={3}
              required
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={
                type === 'resolve'
                  ? 'e.g., Blocked malicious source IP on firewall and patched internal host.'
                  : 'e.g., Authorized internal vulnerability scan.'
              }
              className="w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 text-[#0F172A] placeholder-[#64748B] focus:outline-none focus:border-[#2563EB]"
            />
          </div>
        )}

        {type === 'acknowledge' && (
          <p className="text-[#0F172A] text-xs leading-relaxed">
            You are acknowledging alert <span className="font-mono text-[#2563EB] font-bold">{alertId}</span>.
            This assigns ownership to you and marks the incident as under active investigation.
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-[#0F172A] border border-[#CBD5E1] font-semibold transition"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-white transition shadow-sm ${
              type === 'resolve'
                ? 'bg-[#10B981] hover:bg-emerald-600'
                : type === 'dismiss'
                ? 'bg-[#64748B] hover:bg-slate-600'
                : 'bg-[#2563EB] hover:bg-blue-600'
            }`}
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>Confirm {isBulk ? `${count} Incidents` : type.charAt(0).toUpperCase() + type.slice(1)}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default AlertActionModal;
