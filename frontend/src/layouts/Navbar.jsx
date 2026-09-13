import React, { useState, useEffect } from 'react';
import { RefreshCw, Radio, Menu, Wifi, WifiOff, Clock, ShieldCheck, ShieldAlert } from 'lucide-react';

export function Navbar({
  systemStatus = 'HEALTHY',
  isMonitoring = false,
  isRefreshing = false,
  onRefresh,
  onOpenMobileMenu,
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
    <header className="h-16 border-b border-white/10 bg-slate-900/75 backdrop-blur-xl sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between shadow-sm">
      {/* Left: Mobile Toggle & Status Indicators */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 md:hidden transition"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-white/5 text-xs font-semibold">
            {isOnline ? (
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="text-slate-400">API:</span>
            <span className={isOnline ? 'text-emerald-400 font-mono' : 'text-rose-400 font-mono'}>
              {systemStatus}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-white/5 text-xs font-semibold">
            <Radio className={`w-3.5 h-3.5 ${isMonitoring ? 'text-emerald-400 animate-pulse' : 'text-slate-400'}`} />
            <span className="text-slate-400">Ingestion:</span>
            <span className={isMonitoring ? 'text-emerald-400 font-mono' : 'text-slate-400 font-mono'}>
              {isMonitoring ? 'STREAMING' : 'STANDBY'}
            </span>
          </div>
        </div>
      </div>

      {/* Center / Right: Live SOC HUD Clock & Quick Actions */}
      <div className="flex items-center gap-3">
        {/* Live HUD Digital Clock */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-950/80 border border-white/10 shadow-inner">
          <Clock className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-200 font-semibold">{localString}</span>
            <span className="text-slate-500">|</span>
            <span className="text-indigo-300 font-medium">{utcString} <span className="text-[10px] text-slate-500">UTC</span></span>
          </div>
        </div>

        <span className="text-[10px] font-mono uppercase font-bold tracking-widest px-2.5 py-1 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-500/30">
          {environment}
        </span>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold border border-indigo-500/30 transition disabled:opacity-50 shadow-sm"
          title="Refresh All Telemetry"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          <span className="hidden sm:inline">Sync</span>
        </button>
      </div>
    </header>
  );
}

export default Navbar;
