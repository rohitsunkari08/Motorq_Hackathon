import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { FleetOverviewPage } from './pages/FleetOverviewPage';
import { AlertsPage } from './pages/AlertsPage';
import { VehicleDetailPage } from './pages/VehicleDetailPage';
import { CopilotPage } from './pages/CopilotPage';
import { AdminPage } from './pages/AdminPage';
import { Navbar } from './components/Navbar';
import { Sidebar, NavTab } from './components/Sidebar';
import { api } from './services/api';

export const App: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedVin, setSelectedVin] = useState<string>('1VXEV01A100000001');
  const [openAlertsCount, setOpenAlertsCount] = useState<number>(4);

  // Poll open alerts count periodically
  useEffect(() => {
    if (!isAuthenticated) return;
    async function checkAlerts() {
      try {
        const res = await api.getAlerts('open', 10);
        setOpenAlertsCount(res.items.length);
      } catch {
        // Ignore
      }
    }
    checkAlerts();
    const timer = setInterval(checkAlerts, 15000);
    return () => clearInterval(timer);
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const handleSelectVehicle = (vin: string) => {
    setSelectedVin(vin);
    setCurrentTab('vehicles');
  };

  return (
    <div className="app-container" id="app-root">
      <Sidebar
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        openAlertsCount={openAlertsCount}
      />

      <div className="main-content">
        <Navbar />

        <main style={{ flex: 1, minHeight: 0 }}>
          {currentTab === 'overview' && (
            <FleetOverviewPage onSelectVehicle={handleSelectVehicle} />
          )}

          {currentTab === 'alerts' && (
            <AlertsPage onSelectVehicle={handleSelectVehicle} />
          )}

          {currentTab === 'vehicles' && (
            <VehicleDetailPage
              vin={selectedVin}
              onBack={() => setCurrentTab('overview')}
            />
          )}

          {currentTab === 'copilot' && (
            <CopilotPage onSelectVehicle={handleSelectVehicle} />
          )}

          {currentTab === 'admin' && <AdminPage />}
        </main>
      </div>
    </div>
  );
};
