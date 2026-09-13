import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { LoadingSpinner } from './LoadingSpinner';
import { ShieldAlert } from 'lucide-react';

export function ProtectedRoute({ children, requiredRole = null }) {
  const { isAuthenticated, loading, role, isAdmin, isAnalyst } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#060913] flex items-center justify-center">
        <LoadingSpinner message="Validating security authorization..." size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Role validation
  if (requiredRole === 'admin' && !isAdmin) {
    return (
      <div className="p-8 max-w-xl mx-auto mt-12 rounded-2xl bg-slate-900/80 border border-rose-500/30 text-center space-y-4 shadow-2xl">
        <div className="inline-flex p-3 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-100">Access Restricted</h3>
        <p className="text-xs text-slate-400">
          This management section requires <span className="font-mono text-rose-400 font-bold">ADMINISTRATOR</span> privileges.
          Your current session role is <span className="font-mono text-indigo-400 font-bold">{role.toUpperCase()}</span>.
        </p>
      </div>
    );
  }

  if (requiredRole === 'analyst' && !isAnalyst) {
    return (
      <div className="p-8 max-w-xl mx-auto mt-12 rounded-2xl bg-slate-900/80 border border-rose-500/30 text-center space-y-4 shadow-2xl">
        <div className="inline-flex p-3 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-100">Analyst Permission Required</h3>
        <p className="text-xs text-slate-400">
          This operation requires <span className="font-mono text-rose-400 font-bold">ANALYST</span> or <span className="font-mono text-indigo-400 font-bold">ADMIN</span> role.
        </p>
      </div>
    );
  }

  return children;
}

export default ProtectedRoute;
