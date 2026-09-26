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
      <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
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
      <div className="p-8 max-w-xl mx-auto mt-12 rounded-2xl bg-white border border-[#EF4444]/30 text-center space-y-4 shadow-lg">
        <div className="inline-flex p-3 rounded-full bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-[#0F172A]">Access Restricted</h3>
        <p className="text-xs text-[#64748B]">
          This management section requires <span className="font-mono text-[#EF4444] font-bold">ADMINISTRATOR</span> privileges.
          Your current session role is <span className="font-mono text-[#2563EB] font-bold">{role?.toUpperCase()}</span>.
        </p>
      </div>
    );
  }

  if (requiredRole === 'analyst' && !isAnalyst) {
    return (
      <div className="p-8 max-w-xl mx-auto mt-12 rounded-2xl bg-white border border-[#EF4444]/30 text-center space-y-4 shadow-lg">
        <div className="inline-flex p-3 rounded-full bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-[#0F172A]">Analyst Permission Required</h3>
        <p className="text-xs text-[#64748B]">
          This operation requires <span className="font-mono text-[#EF4444] font-bold">ANALYST</span> or <span className="font-mono text-[#2563EB] font-bold">ADMIN</span> role.
        </p>
      </div>
    );
  }

  return children;
}

export default ProtectedRoute;
