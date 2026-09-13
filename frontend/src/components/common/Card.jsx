import React from 'react';

export function Card({
  title,
  subtitle,
  icon: Icon,
  action,
  children,
  className = '',
  headerClassName = '',
  bodyClassName = '',
  badge = null,
}) {
  return (
    <div className={`bg-slate-900/70 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-md shadow-xl transition-all duration-200 hover:border-white/15 relative ${className}`}>
      {/* Top subtle glow highlight line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent pointer-events-none" />
      {(title || subtitle || Icon || action) && (
        <div className={`px-5 py-4 border-b border-white/5 flex items-center justify-between gap-4 ${headerClassName}`}>
          <div className="flex items-center gap-3">
            {Icon && (
              <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Icon className="w-4 h-4" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-100 tracking-wide">{title}</h3>
                {badge}
              </div>
              {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>{children}</div>
    </div>
  );
}

export default Card;
