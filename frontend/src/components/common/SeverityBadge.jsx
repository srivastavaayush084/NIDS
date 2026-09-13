import React from 'react';
import { AlertCircle, AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import { SEVERITY_TIERS } from '../../utils/constants';

export function SeverityBadge({ severity = 'LOW', showIcon = true, size = 'md' }) {
  const normSev = (severity || 'LOW').toUpperCase();
  const config = SEVERITY_TIERS[normSev] || SEVERITY_TIERS.LOW;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size] || 'px-2.5 py-1 text-xs';

  const iconSize = {
    sm: 11,
    md: 13,
    lg: 15,
  }[size] || 13;

  const getIcon = () => {
    switch (normSev) {
      case 'CRITICAL':
        return <ShieldAlert size={iconSize} className="shrink-0" />;
      case 'HIGH':
        return <AlertTriangle size={iconSize} className="shrink-0" />;
      case 'MEDIUM':
        return <AlertCircle size={iconSize} className="shrink-0" />;
      default:
        return <Info size={iconSize} className="shrink-0" />;
    }
  };

  const isCritical = normSev === 'CRITICAL';
  const isHigh = normSev === 'HIGH';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold tracking-wide rounded-md border transition-shadow ${sizeClasses} ${
        isCritical ? 'glow-critical' : isHigh ? 'shadow-sm' : ''
      }`}
      style={{
        backgroundColor: config.bg,
        borderColor: config.border,
        color: config.color,
        boxShadow: isCritical ? '0 0 12px rgba(244, 63, 94, 0.35)' : undefined,
      }}
      aria-label={`Severity tier: ${config.label}`}
    >
      {showIcon && getIcon()}
      <span>{config.label}</span>
    </span>
  );
}

export default SeverityBadge;
