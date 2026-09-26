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
    <div className={`p-4 rounded-xl bg-red-50 border border-[#EF4444]/30 text-[#991B1B] flex items-start justify-between gap-3 ${className}`}>
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-[#EF4444] shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-[#991B1B]">{displayTitle}</h4>
          <p className="text-xs text-[#7F1D1D] mt-1 leading-relaxed">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#EF4444] hover:bg-red-600 text-white text-xs font-semibold shadow-sm transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}

export default ErrorAlert;
