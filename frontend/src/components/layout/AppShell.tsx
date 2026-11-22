import { useState, type ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import type { HealthResponse } from '../../types/api';
import type { NavTabId } from '../../types/navigation';

interface AppShellProps {
  currentTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  health: HealthResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  children: ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentTab,
  onSelectTab,
  health,
  isLoading,
  onRefresh,
  children,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={onSelectTab}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main App Layout */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          health={health}
          isLoading={isLoading}
          onRefresh={onRefresh}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />

        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
