import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Shield, Lock, User, Eye, EyeOff, AlertCircle, ArrowRight, Radio, Cpu, ShieldAlert, BarChart3, ShieldCheck } from 'lucide-react';

export function Login() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please enter both your username/email and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login({ username: identifier.trim(), password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Radio, label: 'Real-time\nMonitoring' },
    { icon: Cpu, label: 'AI-Powered\nDetection' },
    { icon: ShieldAlert, label: 'Zero-Day\nThreats' },
    { icon: BarChart3, label: 'Detailed\nAnalytics' },
  ];

  return (
    <div className="login-page">
      {/* ═══════ LEFT HERO PANEL ═══════ */}
      <div className="login-hero">
        {/* Globe background image */}
        <div className="login-hero-globe">
          <img src="/cyber-globe.jpg" alt="" />
        </div>

        {/* Gradient overlay */}
        <div className="login-hero-overlay" />

        {/* Content over the globe */}
        <div className="login-hero-content">
          {/* Branding */}
          <div className="login-hero-brand">
            <div className="login-hero-brand-icon">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="login-hero-brand-title">
                ZERO-DAY <span>NIDS</span>
              </h1>
              <p className="login-hero-brand-sub">
                AI-Powered Cyber Defense &<br />Anomaly Detection Platform
              </p>
            </div>
          </div>

          {/* Headline */}
          <div className="login-hero-headline">
            <h2>
              Detect. Analyze.<br />
              <span>Prevent.</span>
            </h2>
            <p>
              Real-time network monitoring, AI-driven anomaly
              detection, and zero-day attack identification
              to keep your systems secure.
            </p>
          </div>

          {/* Feature Icons */}
          <div className="login-hero-features">
            {features.map((f, idx) => {
              const Icon = f.icon;
              return (
                <div key={idx} className="login-hero-feature">
                  <div className="login-hero-feature-icon">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span>{f.label.split('\n').map((line, i) => (
                    <React.Fragment key={i}>{line}{i === 0 && <br />}</React.Fragment>
                  ))}</span>
                </div>
              );
            })}
          </div>

          {/* Floating status badges */}
          <div className="login-hero-badges">
            <div className="login-badge login-badge-green">
              <span className="login-badge-dot login-badge-dot-green" />
              Normal Traffic
            </div>
            <div className="login-badge login-badge-amber">
              <span className="login-badge-dot login-badge-dot-amber" />
              Suspicious Activity
            </div>
            <div className="login-badge login-badge-red">
              <span className="login-badge-dot login-badge-dot-red" />
              Potential Attack
            </div>
          </div>
        </div>
      </div>

      {/* ═══════ RIGHT LOGIN PANEL ═══════ */}
      <div className="login-form-panel">
        <div className="login-form-wrapper">
          {/* Brand Header */}
          <div className="login-form-header">
            <div className="login-form-shield">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="login-form-title">
              ZERO-DAY <span>NIDS</span>
            </h1>
            <p className="login-form-subtitle">
              AI-Powered Cyber Defense & Anomaly Detection Platform
            </p>
          </div>

          {/* Login Card */}
          <div className="login-card">
            <div className="login-card-heading">
              <h2>Security Clearance Login</h2>
              <p>Enter your authorized credentials to access SOC telemetry.</p>
            </div>

            {error && (
              <div className="login-error">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form">
              {/* Username Field */}
              <div className="login-field">
                <label>Username or Email</label>
                <div className="login-input-wrapper">
                  <div className="login-input-icon">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    autoComplete="username"
                    placeholder="admin or analyst@zeroday.ai"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="login-field">
                <label>Password</label>
                <div className="login-input-wrapper">
                  <div className="login-input-icon">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="login-eye-btn"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="login-submit-btn"
              >
                {loading ? (
                  <>
                    <div className="login-spinner" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <span>AUTHENTICATE SESSION</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Security Footer */}
            <div className="login-card-footer">
              <p className="login-footer-title">Secure Access Only</p>
              <div className="login-footer-note">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Authorized personnel only. All access attempts are logged.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
