import React, { useState, useEffect } from 'react';
import { RefreshCw, Radio, Wifi, WifiOff, Clock, ShieldCheck } from 'lucide-react';

export function Navbar({
  systemStatus = 'HEALTHY',
  isMonitoring = false,
  isRefreshing = false,
  onRefresh,
  environment = 'development',
}) {
  const isOnline = systemStatus !== 'UNAVAILABLE';

  // Real-time ticking HUD Clock (UTC and Local)
  const [currentTime, setCurrentTime] = useState(() => new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const utcString = currentTime.toISOString().substring(11, 19);
  const localString = currentTime.toLocaleTimeString([], { hour12: false });

  return (
    <header
      className="nids-navbar h-16 border-b border-[#E2E8F0] px-6 sm:px-8 flex items-center justify-between shadow-2xs"
      style={{
        backgroundColor: '#FFFFFF',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        borderBottom: '1px solid #E2E8F0',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
      }}
    >
      {/* Left: SOC Telemetry Indicators */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-xs font-semibold text-[#2563EB]">
          <ShieldCheck className="w-4 h-4 text-[#10B981]" />
          <span className="font-mono text-[11px] tracking-wider uppercase">Active Defense</span>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] text-xs font-semibold text-[#0F172A]">
            {isOnline ? (
              <Wifi className="w-3.5 h-3.5 text-[#10B981]" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-[#EF4444]" />
            )}
            <span className="text-[#64748B]">API:</span>
            <span className={isOnline ? 'text-[#10B981] font-mono' : 'text-[#EF4444] font-mono'}>
              {systemStatus}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] text-xs font-semibold text-[#0F172A]">
            <Radio className={`w-3.5 h-3.5 ${isMonitoring ? 'text-[#10B981] animate-pulse' : 'text-[#64748B]'}`} />
            <span className="text-[#64748B]">Ingestion:</span>
            <span className={isMonitoring ? 'text-[#10B981] font-mono' : 'text-[#64748B] font-mono'}>
              {isMonitoring ? 'STREAMING' : 'STANDBY'}
            </span>
          </div>
        </div>
      </div>

      {/* Center / Right: Live SOC HUD Clock & Quick Actions */}
      <div className="flex items-center gap-3">
        {/* Live HUD Digital Clock */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
          <Clock className="w-3.5 h-3.5 text-[#2563EB] animate-pulse" />
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-[#0F172A] font-semibold">{localString}</span>
            <span className="text-[#64748B]">|</span>
            <span className="text-[#4F46E5] font-medium">{utcString} <span className="text-[10px] text-[#64748B]">UTC</span></span>
          </div>
        </div>

        <span className="text-[10px] font-mono uppercase font-bold tracking-widest px-2.5 py-1 rounded-md bg-[#EAF2FF] text-[#2563EB] border border-[#2563EB]/25">
          {environment}
        </span>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold transition disabled:opacity-50 shadow-sm"
          title="Refresh All Telemetry"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Sync</span>
        </button>
      </div>
    </header>
  );
}

export default Navbar;
