import React from 'react';
import { Loader2 } from 'lucide-react';

export function LoadingSpinner({ message = 'Loading...', size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }[size] || 'w-6 h-6';

  return (
    <div className={`flex flex-col items-center justify-center p-8 gap-3 text-slate-400 ${className}`}>
      <Loader2 className={`${sizeClasses} animate-spin text-indigo-400`} />
      {message && <p className="text-xs font-medium text-slate-400 tracking-wide">{message}</p>}
    </div>
  );
}

export default LoadingSpinner;
