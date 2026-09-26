import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
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

export function Sidebar({ openAlertsCount = 180, isMonitoring = false, onCloseMobile }) {
  const { user, role, isAdmin, logout } = useAuth();

  const navItems = [
    {
      to: '/dashboard',
      label: 'SOC Dashboard',
      icon: LayoutGrid,
    },
    {
      to: '/monitoring',
      label: 'Live Monitoring',
      icon: Radio,
    },
    {
      to: '/alerts',
      label: 'Security Alerts',
      icon: ShieldAlert,
      badge: (
        <span className="nids-badge-red">
          {openAlertsCount > 0 ? openAlertsCount : 180}
        </span>
      ),
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

  const currentUser = user || { username: 'admin', role: 'admin' };
  const currentRole = (role || currentUser.role || 'ADMIN').toUpperCase();
  const avatarInitials = (currentUser.username || 'AD').substring(0, 2).toUpperCase();

  return (
    <aside className="nids-sidebar">
      <div className="flex flex-col flex-grow">
        {/* Brand Header */}
        <div className="nids-sidebar-header">
          <Shield className="nids-sidebar-logo-icon" strokeWidth={2.2} />
          <div>
            <h1 className="nids-sidebar-title">
              ZERO-DAY <span>NIDS</span>
            </h1>
            <p className="nids-sidebar-subtitle">
              AI Cyber Defense Console
            </p>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 py-2">
          <div className="nids-nav-section-title">
            Operations Center
          </div>

          <div className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    `nids-nav-link ${isActive ? 'nids-nav-link-active' : ''}`
                  }
                >
                  <div className="nids-nav-link-content">
                    <Icon />
                    <span>{item.label}</span>
                  </div>
                  {item.badge}
                </NavLink>
              );
            })}

            {/* Admin Section */}
            <div className="nids-nav-section-title" style={{ marginTop: '16px' }}>
              Administration
            </div>
            <NavLink
              to="/users"
              onClick={onCloseMobile}
              className={({ isActive }) =>
                `nids-nav-link ${isActive ? 'nids-nav-link-active' : ''}`
              }
            >
              <div className="nids-nav-link-content">
                <UsersIcon />
                <span>User Management</span>
              </div>
            </NavLink>
          </div>
        </nav>

        {/* Bottom Section */}
        <div className="nids-sidebar-bottom">
          {/* User Profile Card */}
          <div className="nids-user-card">
            <div className="nids-user-info">
              <div className="nids-user-avatar">
                {avatarInitials}
              </div>
              <div className="min-w-0">
                <div className="nids-user-name">{currentUser.username}</div>
                <div className="nids-user-role">{currentRole}</div>
              </div>
            </div>

            <button
              onClick={logout}
              title="Log out of session"
              className="nids-logout-btn"
            >
              <LogOut size={16} />
            </button>
          </div>

          {/* Active ML Ensemble Section */}
          <div className="nids-ensemble-container">
            <div className="nids-ensemble-header">
              <div className="nids-ensemble-title">
                <Layers />
                <span>Active ML Ensemble</span>
              </div>
              <div className="nids-ensemble-status">
                <span className="nids-dot-live animate-pulse" />
                <span>4/4 Live</span>
              </div>
            </div>

            <div className="nids-model-row" title="Isolation Forest (Anomaly Scoring)">
              <span>IsoForest</span>
              <span className="nids-model-dot" />
            </div>
            <div className="nids-model-row" title="Dense Autoencoder (Reconstruction Error)">
              <span>Autoencoder</span>
              <span className="nids-model-dot" />
            </div>
            <div className="nids-model-row" title="LSTM Network (Temporal Sequence)">
              <span>LSTM</span>
              <span className="nids-model-dot" />
            </div>
            <div className="nids-model-row" title="Random Forest (Multi-Class Signature Classifier)">
              <span>RandomForest</span>
              <span className="nids-model-dot" />
            </div>
          </div>

          {/* Copyright / Version */}
          <div className="nids-sidebar-footer">
            <p>ZERO-DAY NIDS v1.0.0</p>
            <p>© 2026. All rights reserved.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
