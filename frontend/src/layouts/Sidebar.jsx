import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  ShieldAlert,
  History,
  Cpu,
  Activity,
  Shield,
  Layers,
  Users as UsersIcon,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function Sidebar({ openAlertsCount = 0, isMonitoring = false, onCloseMobile }) {
  const { user, role, isAdmin, logout } = useAuth();

  const navItems = [
    {
      to: '/dashboard',
      label: 'SOC Dashboard',
      icon: LayoutDashboard,
    },
    {
      to: '/monitoring',
      label: 'Live Monitoring',
      icon: Radio,
      badge: isMonitoring ? (
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      ) : null,
    },
    {
      to: '/alerts',
      label: 'Security Alerts',
      icon: ShieldAlert,
      badge: openAlertsCount > 0 ? (
        <span className="px-1.5 py-0.2 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-bold font-mono">
          {openAlertsCount}
        </span>
      ) : null,
    },
    {
      to: '/detections',
      label: 'Detection History',
      icon: History,
    },
    {
      to: '/models',
      label: 'Model Registry',
      icon: Cpu,
    },
    {
      to: '/health',
      label: 'System Health',
      icon: Activity,
    },
  ];

  return (
    <aside className="w-64 border-r border-white/10 bg-slate-900/80 backdrop-blur-xl flex flex-col justify-between p-4 min-h-screen shrink-0">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white shadow-lg shadow-indigo-600/30">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-black tracking-wider text-white uppercase font-mono">
              ZERO-DAY <span className="text-indigo-400">NIDS</span>
            </h1>
            <p className="text-[10px] text-slate-400 tracking-wide font-medium">
              AI Cyber Defense Console
            </p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="space-y-1">
          <div className="px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-slate-500">
            Operations Center
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.badge}
              </NavLink>
            );
          })}

          {/* Admin Navigation Section */}
          {isAdmin && (
            <>
              <div className="pt-3 px-3 py-1 text-[10px] uppercase font-bold tracking-wider text-indigo-400">
                Administration
              </div>
              <NavLink
                to="/users"
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <UsersIcon className="w-4 h-4" />
                  <span>User Management</span>
                </div>
              </NavLink>
            </>
          )}
        </nav>
      </div>

      <div className="space-y-3">
        {/* Authenticated User Profile & Logout */}
        {user && (
          <div className="p-3 rounded-xl bg-slate-800/60 border border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 font-bold font-mono text-xs flex items-center justify-center shrink-0">
                {(user.username || 'U').substring(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold text-slate-200 truncate">{user.username}</div>
                <div className="text-[10px] font-mono font-semibold uppercase tracking-wider text-indigo-400">
                  {role}
                </div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Log out of session"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Pipeline Stack Banner */}
        <div className="p-3.5 rounded-xl bg-slate-800/40 border border-white/5 space-y-2">
          <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold">
            <Layers className="w-3.5 h-3.5" />
            <span>Active ML Ensemble</span>
          </div>
          <div className="flex flex-wrap gap-1 text-[9px] font-mono text-slate-400">
            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-white/5">IsolationForest</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-white/5">Autoencoder</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-white/5">LSTM</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-white/5">RandomForest</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;

