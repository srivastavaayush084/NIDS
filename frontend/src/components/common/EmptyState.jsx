import React from 'react';
import { Inbox } from 'lucide-react';

export function EmptyState({
  title = 'No records found',
  description = 'No matching data is currently available.',
  icon: Icon = Inbox,
  action = null,
  className = '',
}) {
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-center border border-dashed border-white/10 rounded-xl bg-slate-900/30 ${className}`}>
      <div className="p-3 rounded-full bg-slate-800/80 text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
      {description && <p className="text-xs text-slate-400 max-w-sm mt-1 mb-4">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}

export default EmptyState;
