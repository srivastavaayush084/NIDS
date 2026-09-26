import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';

export function MainLayout({
  health = null,
  monitoringStatus = null,
  openAlertsCount = 0,
  isRefreshing = false,
  onRefresh,
}) {
  const systemStatus = health?.status || (health ? 'HEALTHY' : 'UNAVAILABLE');
  const isMonitoring = Boolean(monitoringStatus?.running);

  return (
    <div className="flex min-h-screen bg-[#F6F9FC] text-[#0F172A] antialiased font-sans">
      {/* Permanent Persistent Sidebar Navigation */}
      <Sidebar
        openAlertsCount={openAlertsCount}
        isMonitoring={isMonitoring}
      />

      {/* Main View Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">
        <Navbar
          systemStatus={systemStatus}
          isMonitoring={isMonitoring}
          isRefreshing={isRefreshing}
          onRefresh={onRefresh}
          environment={health?.environment || 'development'}
        />

        <main className="flex-1 overflow-y-auto p-6 sm:p-8 lg:p-10 max-w-[1680px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default MainLayout;
