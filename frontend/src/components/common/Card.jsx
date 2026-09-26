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
    <div className={`bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden shadow-sm transition-all duration-200 hover:border-[#CBD5E1] hover:shadow-md relative ${className}`}>
      {/* Top subtle highlight line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#2563EB]/20 to-transparent pointer-events-none" />
      {(title || subtitle || Icon || action) && (
        <div className={`px-6 py-4 border-b border-[#E2E8F0] bg-white flex items-center justify-between gap-4 ${headerClassName}`}>
          <div className="flex items-center gap-3">
            {Icon && (
              <div className="p-2 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-[#2563EB]">
                <Icon className="w-4 h-4" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-[#0F172A] tracking-wide">{title}</h3>
                {badge}
              </div>
              {subtitle && <p className="text-xs text-[#64748B] mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={`p-6 bg-white text-[#0F172A] ${bodyClassName}`}>{children}</div>
    </div>
  );
}

export default Card;
