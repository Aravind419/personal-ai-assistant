import { useState, useEffect, useCallback } from 'react';
import { AppShell } from './components/layout/AppShell';
import { DashboardOverview } from './pages/DashboardOverview';
import { PlaceholderView } from './components/common/PlaceholderView';
import { NAVIGATION_ITEMS } from './components/layout/Sidebar';
import type { NavTabId } from './types/navigation';
import type { HealthResponse, SystemInfoResponse } from './types/api';
import { healthService } from './services/healthService';

export function App() {
  const [currentTab, setCurrentTab] = useState<NavTabId>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagnostics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [healthData, infoData] = await Promise.allSettled([
        healthService.getHealth(),
        healthService.getSystemInfo(),
      ]);

      if (healthData.status === 'fulfilled') {
        setHealth(healthData.value);
      } else {
        setError(
          healthData.reason?.message ||
            'Failed to connect to backend API. Please ensure FastAPI server is running on http://localhost:8000'
        );
        setHealth(null);
      }

      if (infoData.status === 'fulfilled') {
        setSystemInfo(infoData.value);
      }
    } catch (err: any) {
      setError(err?.message || 'An unexpected error occurred while communicating with backend.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDiagnostics();
  }, [fetchDiagnostics]);

  const activeNavItem = NAVIGATION_ITEMS.find((item) => item.id === currentTab);

  return (
    <AppShell
      currentTab={currentTab}
      onSelectTab={setCurrentTab}
      health={health}
      isLoading={isLoading}
      onRefresh={fetchDiagnostics}
    >
      {currentTab === 'overview' ? (
        <DashboardOverview
          health={health}
          systemInfo={systemInfo}
          isLoading={isLoading}
          error={error}
          onRefresh={fetchDiagnostics}
        />
      ) : activeNavItem ? (
        <PlaceholderView item={activeNavItem} />
      ) : null}
    </AppShell>
  );
}

export default App;
