import type { HealthResponse } from '../../types/api';
import { StatusBadge } from '../common/StatusBadge';
import { Bot, RefreshCw, Server, Database, Menu } from 'lucide-react';

interface HeaderProps {
  health: HealthResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  isLoading,
  onRefresh,
  onToggleSidebar,
}) => {
  const backendConnected = health !== null;
  const dbConnected = health?.database?.connected ?? false;

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30 px-4 md:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 md:hidden transition-colors"
            aria-label="Toggle menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-tight text-white">Personal AI Agent</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                Phase 0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-none mt-0.5">Engineering Foundation</p>
          </div>
        </div>
      </div>

      {/* Live System Diagnostics Badges */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2.5 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800/80 text-xs">
          {/* API Status */}
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">API:</span>
            <StatusBadge
              status={backendConnected ? 'healthy' : 'disconnected'}
              label={backendConnected ? 'Online' : 'Offline'}
              size="sm"
            />
          </div>

          <div className="h-3 w-px bg-slate-800" />

          {/* DB Status */}
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">PostgreSQL:</span>
            <StatusBadge
              status={dbConnected ? 'healthy' : 'disconnected'}
              label={dbConnected ? 'Connected' : 'Offline'}
              size="sm"
            />
          </div>
        </div>

        {/* Refresh Diagnostics Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/50 transition-colors cursor-pointer disabled:opacity-50"
          title="Refresh connection status"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
