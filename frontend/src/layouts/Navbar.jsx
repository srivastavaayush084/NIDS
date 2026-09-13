import React from 'react';
import { RefreshCw, Radio, Menu, Wifi, WifiOff } from 'lucide-react';

export function Navbar({
  systemStatus = 'HEALTHY',
  isMonitoring = false,
  isRefreshing = false,
  onRefresh,
  onOpenMobileMenu,
  environment = 'development',
}) {
  const isOnline = systemStatus !== 'UNAVAILABLE';

  return (
    <header className="h-16 border-b border-white/10 bg-slate-900/60 backdrop-blur-md sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between">
      {/* Left: Mobile Toggle & Status Indicators */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 md:hidden transition"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/50 border border-white/5 text-xs font-semibold">
            {isOnline ? (
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="text-slate-300">Backend API:</span>
            <span className={isOnline ? 'text-emerald-400' : 'text-rose-400'}>
              {systemStatus}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/50 border border-white/5 text-xs font-semibold">
            <Radio className={`w-3.5 h-3.5 ${isMonitoring ? 'text-emerald-400 animate-pulse' : 'text-slate-400'}`} />
            <span className="text-slate-300">Traffic Ingestion:</span>
            <span className={isMonitoring ? 'text-emerald-400' : 'text-slate-400'}>
              {isMonitoring ? 'CAPTURING' : 'IDLE'}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Environment Badge & Refresh Action */}
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-mono uppercase font-bold tracking-widest px-2.5 py-1 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-500/30">
          ENV: {environment}
        </span>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700/80 text-slate-200 text-xs font-semibold border border-white/10 transition disabled:opacity-50"
          title="Refresh All Telemetry"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>
    </header>
  );
}

export default Navbar;
