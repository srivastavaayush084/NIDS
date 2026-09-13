import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Home } from 'lucide-react';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center p-12 text-center min-h-[60vh]">
      <div className="p-4 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-4">
        <ShieldAlert className="w-10 h-10" />
      </div>
      <h2 className="text-2xl font-black text-slate-100 uppercase tracking-wide">404 — Page Not Found</h2>
      <p className="text-xs text-slate-400 max-w-md mt-2 mb-6">
        The requested security console route does not exist or has been relocated.
      </p>
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition"
      >
        <Home className="w-4 h-4" />
        <span>Return to SOC Dashboard</span>
      </button>
    </div>
  );
}

export default NotFound;
