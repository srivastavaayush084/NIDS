import React, { useState, useEffect, useCallback } from 'react';
import { usersApi } from '../api/users';
import { useAuth } from '../hooks/useAuth';
import { StatusPill } from '../components/common/StatusPill';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { formatDate } from '../utils/formatters';
import { Users as UsersIcon, UserPlus, Shield, CheckCircle2, XCircle, RefreshCw, KeyRound, AlertTriangle, Calendar, Clock, Check } from 'lucide-react';

export function getUserSafeErrorMessage(err) {
  if (!err) return 'An unexpected error occurred.';
  if (err.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  if (err.status === 403) {
    return 'You do not have permission to manage users.';
  }
  if (err.status === 404) {
    return 'User management service is unavailable.';
  }
  if (err.status === 500) {
    return 'User management service encountered an internal error.';
  }
  if (err.status === 0 || err.name === 'TypeError' || (err.message && err.message.toLowerCase().includes('failed to fetch'))) {
    return 'Unable to communicate with the backend service.';
  }
  return err.message || 'Unable to communicate with the backend service.';
}

export function Users() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // New user form state
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'analyst',
  });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await usersApi.listUsers({ limit: 100 });
      const userList = Array.isArray(res) ? res : (res?.users || res?.items || []);
      setUsers(userList);
    } catch (err) {
      setError(getUserSafeErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormError(null);
    setActionError(null);
    setActionSuccess(null);
    setSubmitting(true);
    try {
      await usersApi.createUser(formData);
      setModalOpen(false);
      const createdUsername = formData.username;
      setFormData({ username: '', email: '', full_name: '', password: '', role: 'analyst' });
      await fetchUsers();
      setActionSuccess(`User account '${createdUsername}' provisioned successfully.`);
    } catch (err) {
      setFormError(getUserSafeErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActiveClick = (targetUser) => {
    setActionError(null);
    setActionSuccess(null);
    setConfirmTarget({
      user: targetUser,
      newStatus: !targetUser.is_active,
    });
  };

  const executeToggleActive = async () => {
    if (!confirmTarget) return;
    const { user: targetUser, newStatus } = confirmTarget;
    setActionInProgress(true);
    try {
      await usersApi.updateUser(targetUser.user_id || targetUser.id, { is_active: newStatus });
      setConfirmTarget(null);
      await fetchUsers();
      setActionSuccess(`User account '${targetUser.username}' ${newStatus ? 'reactivated' : 'deactivated'} successfully.`);
    } catch (err) {
      setConfirmTarget(null);
      setActionError(getUserSafeErrorMessage(err));
    } finally {
      setActionInProgress(false);
    }
  };

  const handleChangeRole = async (targetUser, newRole) => {
    if (targetUser.role === newRole) return;
    setActionError(null);
    setActionSuccess(null);
    try {
      await usersApi.updateUser(targetUser.user_id || targetUser.id, { role: newRole });
      await fetchUsers();
      setActionSuccess(`Role for '${targetUser.username}' updated to ${newRole.toUpperCase()}.`);
    } catch (err) {
      setActionError(getUserSafeErrorMessage(err));
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-slate-100 uppercase tracking-wide flex items-center gap-2.5">
            <UsersIcon className="w-5 h-5 text-indigo-400" />
            <span>User Management & RBAC Directory</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Manage authorized platform operators, assign security access roles, and monitor user activation status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-[#0F172A] text-xs font-semibold border border-[#CBD5E1] shadow-2xs transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#2563EB]' : 'text-[#64748B]'}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              setFormError(null);
              setModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold shadow-md shadow-[#2563EB]/25 transition"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Provision User</span>
          </button>
        </div>
      </div>

      {/* Global Fetch Error */}
      {error && <ErrorAlert title="User Directory Notice" message={error} onRetry={fetchUsers} />}

      {/* In-UI Action Error Notification */}
      {actionError && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-3 animate-fade-in">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-slate-400 hover:text-slate-200 text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* In-UI Action Success Notification */}
      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between gap-3 animate-fade-in">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-slate-400 hover:text-slate-200 text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* User Directory Table */}
      <div className="rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md overflow-hidden shadow-xl">
        {loading && !users.length ? (
          <LoadingSpinner message="Loading user directory..." className="py-20" />
        ) : !users.length ? (
          <div className="py-16 text-center text-slate-400 text-xs space-y-2">
            <UsersIcon className="w-8 h-8 mx-auto text-slate-500 opacity-60" />
            <p className="font-semibold text-slate-300">No registered users found</p>
            <p className="text-[11px] text-slate-500">Provision a new user account to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/60 border-b border-white/10 text-slate-400 uppercase font-mono text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Role Designation</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4">Last Login</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-medium">
                {users.map((u) => {
                  const isCurrent = (u.user_id || u.id) === (currentUser?.user_id || currentUser?.id);
                  const createdDate = formatDate(u.created_at);
                  const lastLoginDate = u.last_login_at ? formatDate(u.last_login_at) : 'Never';

                  return (
                    <tr key={u.user_id || u.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-bold font-mono text-xs">
                            {u.username.substring(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-slate-100 flex items-center gap-2">
                              <span>{u.username}</span>
                              {isCurrent && (
                                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/30">
                                  YOU
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400">{u.full_name || '—'}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">{u.email}</td>
                      <td className="py-3.5 px-4">
                        <select
                          value={u.role.toLowerCase()}
                          onChange={(e) => handleChangeRole(u, e.target.value)}
                          disabled={isCurrent}
                          className="px-2.5 py-1 rounded-lg bg-slate-800 border border-white/10 text-slate-200 text-xs font-semibold focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
                        >
                          <option value="admin">ADMIN</option>
                          <option value="analyst">ANALYST</option>
                          <option value="viewer">VIEWER</option>
                        </select>
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusPill status={u.is_active ? 'ACTIVE' : 'OFFLINE'} customLabel={u.is_active ? 'ACTIVE' : 'DEACTIVATED'} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                        {createdDate}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-400 text-[11px]">
                        {lastLoginDate}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleToggleActiveClick(u)}
                          disabled={isCurrent}
                          className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition disabled:opacity-40 ${
                            u.is_active
                              ? 'bg-red-50 text-[#EF4444] border-[#EF4444]/30 hover:bg-red-100'
                              : 'bg-emerald-50 text-[#10B981] border-[#10B981]/30 hover:bg-emerald-100'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Reactivate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirmation Modal for Deactivate / Reactivate */}
      {confirmTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="max-w-md w-full rounded-2xl bg-white border border-[#E2E8F0] p-6 shadow-2xl space-y-5 animate-scale-in text-[#0F172A]">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <h3 className="text-sm font-bold text-[#0F172A] flex items-center gap-2">
                <AlertTriangle className={`w-4 h-4 ${confirmTarget.newStatus ? 'text-[#10B981]' : 'text-[#EF4444]'}`} />
                <span>{confirmTarget.newStatus ? 'Confirm Account Reactivation' : 'Confirm Account Deactivation'}</span>
              </h3>
              <button
                onClick={() => setConfirmTarget(null)}
                className="text-[#64748B] hover:text-[#0F172A] text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[#64748B] leading-relaxed">
              {confirmTarget.newStatus
                ? `Are you sure you want to reactivate the account for user '${confirmTarget.user.username}'? They will regain access to platform services.`
                : `Are you sure you want to deactivate the account for user '${confirmTarget.user.username}'? Deactivated accounts cannot authenticate or access platform resources.`}
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#E2E8F0]">
              <button
                type="button"
                onClick={() => setConfirmTarget(null)}
                disabled={actionInProgress}
                className="px-3.5 py-2 rounded-xl bg-white text-[#0F172A] border border-[#CBD5E1] text-xs font-semibold hover:bg-slate-50 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeToggleActive}
                disabled={actionInProgress}
                className={`px-4 py-2 rounded-xl text-white text-xs font-bold transition disabled:opacity-50 shadow-md ${
                  confirmTarget.newStatus
                    ? 'bg-[#10B981] hover:bg-emerald-600'
                    : 'bg-[#EF4444] hover:bg-red-600'
                }`}
              >
                {actionInProgress
                  ? (confirmTarget.newStatus ? 'Reactivating...' : 'Deactivating...')
                  : (confirmTarget.newStatus ? 'Confirm Reactivation' : 'Confirm Deactivation')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provision User Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="max-w-md w-full rounded-2xl bg-slate-900 border border-white/10 p-6 shadow-2xl space-y-5 animate-scale-in">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-indigo-400" />
                <span>Provision New System User</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3.5">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Username *</label>
                <input
                  type="text"
                  required
                  placeholder="analyst_jane"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="jane@zeroday.ai"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Full Name</label>
                <input
                  type="text"
                  placeholder="Jane Doe"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Initial Password * (min 8 chars)</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="••••••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Role Designation *</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-white/10 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="analyst">ANALYST (Operations & Incident Triage)</option>
                  <option value="admin">ADMIN (Full System & User Control)</option>
                  <option value="viewer">VIEWER (Read-Only SOC Telemetry)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#E2E8F0]">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl bg-white text-[#0F172A] border border-[#CBD5E1] text-xs font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-bold transition disabled:opacity-50 shadow-md shadow-[#2563EB]/25"
                >
                  {submitting ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;

