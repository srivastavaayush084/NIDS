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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const systemStatus = health?.status || (health ? 'HEALTHY' : 'UNAVAILABLE');
  const isMonitoring = Boolean(monitoringStatus?.running);

  return (
    <div className="flex min-h-screen bg-[#060913] text-slate-100 antialiased font-sans">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          openAlertsCount={openAlertsCount}
          isMonitoring={isMonitoring}
        />
      </div>

      {/* Mobile Drawer Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/75 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Mobile Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 ease-in-out md:hidden ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar
          openAlertsCount={openAlertsCount}
          isMonitoring={isMonitoring}
          onCloseMobile={() => setMobileMenuOpen(false)}
        />
      </div>

      {/* Main View Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          systemStatus={systemStatus}
          isMonitoring={isMonitoring}
          isRefreshing={isRefreshing}
          onRefresh={onRefresh}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          environment={health?.environment || 'development'}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default MainLayout;
