import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { ShieldCheck, XCircle, CheckCircle2, Loader2 } from 'lucide-react';

export function AlertActionModal({
  isOpen = false,
  type = 'resolve', // 'resolve', 'dismiss', 'acknowledge'
  alertId = null,
  onClose,
  onSubmit,
  loading = false,
}) {
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);

  const getTitle = () => {
    switch (type) {
      case 'resolve':
        return 'Resolve Security Incident';
      case 'dismiss':
        return 'Dismiss Alert';
      default:
        return 'Acknowledge Alert';
    }
  };

  const getSubtitle = () => {
    switch (type) {
      case 'resolve':
        return `Provide remediation notes for alert ${alertId}`;
      case 'dismiss':
        return `State reason for dismissing alert ${alertId} (e.g. false positive)`;
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
            <label className="block text-slate-300 font-semibold mb-1.5">
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
              className="w-full bg-slate-800 border border-white/10 rounded-xl p-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        )}

        {type === 'acknowledge' && (
          <p className="text-slate-300 text-xs leading-relaxed">
            You are acknowledging alert <span className="font-mono text-indigo-400 font-bold">{alertId}</span>.
            This assigns ownership to you and marks the incident as under active investigation.
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={loading}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-white transition ${
              type === 'resolve'
                ? 'bg-emerald-600 hover:bg-emerald-500'
                : type === 'dismiss'
                ? 'bg-slate-700 hover:bg-slate-600'
                : 'bg-indigo-600 hover:bg-indigo-500'
            }`}
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>Confirm {type.charAt(0).toUpperCase() + type.slice(1)}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default AlertActionModal;
