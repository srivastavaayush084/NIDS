import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { apiClient } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => apiClient.getUserProfile());
  const [token, setToken] = useState(() => apiClient.getAccessToken());
  const [loading, setLoading] = useState(true);

  const clearAuthState = useCallback(() => {
    setUser(null);
    setToken(null);
    apiClient.clearSession();
  }, []);

  const restoreSession = useCallback(async () => {
    const savedToken = apiClient.getAccessToken();
    if (!savedToken) {
      setLoading(false);
      return;
    }

    try {
      const profile = await authApi.getCurrentUser();
      if (profile && profile.is_active) {
        setUser(profile);
        setToken(savedToken);
        apiClient.setSession(savedToken, apiClient.getRefreshToken(), profile);
      } else {
        clearAuthState();
      }
    } catch (err) {
      console.warn('Session validation failed:', err.message);
      clearAuthState();
    } finally {
      setLoading(false);
    }
  }, [clearAuthState]);

  useEffect(() => {
    restoreSession();

    // Listen for unauthorized events emitted by apiClient
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('zeroday:auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('zeroday:auth:unauthorized', handleUnauthorized);
    };
  }, [restoreSession]);

  const login = async (credentials) => {
    const res = await authApi.login(credentials);
    const { access_token, refresh_token, user: userData } = res;
    apiClient.setSession(access_token, refresh_token, userData);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const logout = async () => {
    try {
      if (token) {
        await authApi.logout().catch(() => {});
      }
    } finally {
      clearAuthState();
    }
  };

  const role = (user?.role || 'viewer').toLowerCase();
  const isAdmin = role === 'admin';
  const isAnalyst = role === 'analyst' || role === 'admin';
  const isViewer = role === 'viewer';
  const isAuthenticated = Boolean(user && token);

  const value = {
    user,
    token,
    role,
    isAdmin,
    isAnalyst,
    isViewer,
    isAuthenticated,
    loading,
    login,
    logout,
    refreshUser: restoreSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
