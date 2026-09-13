import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { MainLayout } from './layouts/MainLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Monitoring } from './pages/Monitoring';
import { Alerts } from './pages/Alerts';
import { AlertDetails } from './pages/AlertDetails';
import { DetectionHistory } from './pages/DetectionHistory';
import { DetectionDetails } from './pages/DetectionDetails';
import { Models } from './pages/Models';
import { SystemHealth } from './pages/SystemHealth';
import { Users } from './pages/Users';
import { NotFound } from './pages/NotFound';

import { useHealth } from './hooks/useHealth';
import { useStatistics } from './hooks/useStatistics';
import { useMonitoring } from './hooks/useMonitoring';
import { useAlerts } from './hooks/useAlerts';
import { useModels } from './hooks/useModels';

function AuthenticatedApp() {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { health, refetch: refetchHealth } = useHealth(10000);
  const { summary, alertStats, loading: statsLoading, error: statsError, refetch: refetchStats } = useStatistics(5000);
  const { status: monitoringStatus, refetch: refetchMonitoring } = useMonitoring(3000);
  const { alerts: recentAlerts, refetch: refetchAlerts } = useAlerts({ page_size: 5 }, true);
  const { models, refetch: refetchModels } = useModels('synthetic');

  const openAlertsCount = summary?.open_alerts ?? alertStats?.status_distribution?.OPEN ?? 0;

  const handleGlobalRefresh = async () => {
    setIsRefreshing(true);
    await Promise.allSettled([
      refetchHealth(),
      refetchStats(),
      refetchMonitoring(),
      refetchAlerts(),
      refetchModels(),
    ]);
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <Routes>
      {/* Public Authentication Route */}
      <Route path="/login" element={<Login />} />

      {/* Protected Operations Center Routes */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout
              health={health}
              monitoringStatus={monitoringStatus}
              openAlertsCount={openAlertsCount}
              isRefreshing={isRefreshing}
              onRefresh={handleGlobalRefresh}
            />
          </ProtectedRoute>
        }
      >
        {/* Default Route */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* SOC Dashboard */}
        <Route
          path="/dashboard"
          element={
            <Dashboard
              summary={summary}
              alertStats={alertStats}
              monitoringStatus={monitoringStatus}
              recentAlerts={recentAlerts}
              models={models}
              loading={statsLoading && !summary}
              error={statsError}
              onRefresh={handleGlobalRefresh}
            />
          }
        />

        {/* Real-time Network Monitoring */}
        <Route path="/monitoring" element={<Monitoring />} />

        {/* Security Incident Alerts */}
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/alerts/:alertId" element={<AlertDetails />} />

        {/* Detection History */}
        <Route path="/detections" element={<DetectionHistory />} />
        <Route path="/detections/:detectionId" element={<DetectionDetails />} />

        {/* AI Model Registry & Comparisons */}
        <Route path="/models" element={<Models />} />

        {/* System Health Diagnostics */}
        <Route path="/health" element={<SystemHealth />} />

        {/* User Management (Admin Only) */}
        <Route
          path="/users"
          element={
            <ProtectedRoute requiredRole="admin">
              <Users />
            </ProtectedRoute>
          }
        />

        {/* Fallback 404 Route */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
