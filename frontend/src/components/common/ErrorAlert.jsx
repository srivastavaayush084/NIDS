import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export function ErrorAlert({
  title = null,
  message = 'An unexpected error occurred while communicating with the backend server.',
  onRetry = null,
  className = '',
}) {
  const displayTitle = title || 'System Notification';
  return (
    <div className={`p-4 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 flex items-start justify-between gap-3 ${className}`}>
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-red-300">{displayTitle}</h4>
          <p className="text-xs text-red-200/90 mt-1 leading-relaxed">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-900/60 hover:bg-red-800/80 text-white text-xs font-medium border border-red-500/40 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}

export default ErrorAlert;
