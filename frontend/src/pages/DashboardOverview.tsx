import { useState } from 'react';
import type { HealthResponse, SystemInfoResponse, DatabaseHealth } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { healthService } from '../services/healthService';
import {
  Server,
  Database,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Activity,
  Code2,
} from 'lucide-react';

interface DashboardOverviewProps {
  health: HealthResponse | null;
  systemInfo: SystemInfoResponse | null;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  health,
  systemInfo,
  isLoading,
  error,
  onRefresh,
}) => {
  const [testingDb, setTestingDb] = useState(false);
  const [dbTestResult, setDbTestResult] = useState<DatabaseHealth | null>(null);

  const handleTestDb = async () => {
    setTestingDb(true);
    try {
      const res = await healthService.getDatabaseHealth();
      setDbTestResult(res);
    } catch (e: any) {
      setDbTestResult({
        connected: false,
        latency_ms: null,
        error: e.message || 'Failed to ping database endpoint',
      });
    } finally {
      setTestingDb(false);
    }
  };

  const isDbConnected = health?.database?.connected ?? false;

  return (
    <div className="space-y-8">
      {/* Page Title & Status Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">System Overview</h1>
          <p className="mt-1 text-sm text-slate-400">
            Phase 0 Engineering Foundation: Runtime diagnostics, database connectivity, and architecture status.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors shadow-sm cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh Diagnostics</span>
          </button>
        </div>
      </div>

      {/* Global Error Alert if Backend Unreachable */}
      {error && (
        <ErrorState
          title="Backend Connection Unreachable"
          message={error}
          onRetry={onRefresh}
          details="Ensure backend server is running: `cd backend; .venv\Scripts\uvicorn app.main:app --port 8000`"
        />
      )}

      {/* Phase 0 Engineering Foundation Banner */}
      <div className="rounded-xl border border-indigo-900/50 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-indigo-950/30 p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-indigo-300">
                Phase 0 Milestone: Engineering Foundation Active
              </h2>
            </div>
            <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
              This deployment establishes the fundamental engineering layer: React + TypeScript UI shell,
              Python FastAPI modular backend, PostgreSQL configuration with pgvector readiness, Docker development
              compose, and centralized health diagnostics. Agent orchestration, LLM calling, and background execution
              are deliberately scheduled for subsequent phases.
            </p>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            <span className="px-3 py-1 rounded-md bg-slate-900/80 border border-indigo-700/50 text-indigo-300 font-mono text-xs font-semibold">
              {systemInfo?.phase || 'Phase 0: Foundation'}
            </span>
          </div>
        </div>
      </div>

      {isLoading && !health ? (
        <LoadingState />
      ) : (
        <>
          {/* Status Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* FastAPI Backend */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">FastAPI Backend</span>
                  <Server className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-xl font-bold text-white">
                    {health ? 'Online' : 'Unreachable'}
                  </span>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">API Prefix</span>
                <span className="text-xs font-mono text-slate-300">/api/v1</span>
              </div>
            </div>

            {/* PostgreSQL Database */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">PostgreSQL Storage</span>
                  <Database className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-xl font-bold text-white">
                    {isDbConnected ? 'Connected' : 'Offline / Standby'}
                  </span>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">Query Latency</span>
                <span className="text-xs font-mono text-slate-300">
                  {health?.database?.latency_ms != null ? `${health.database.latency_ms} ms` : 'N/A'}
                </span>
              </div>
            </div>

            {/* Environment Mode */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">Environment</span>
                  <Cpu className="w-4 h-4 text-violet-400" />
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-xl font-bold text-white capitalize">
                    {health?.environment || 'Development'}
                  </span>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">User Scope</span>
                <span className="text-xs font-mono text-slate-300">Single-User</span>
              </div>
            </div>

            {/* Architecture Mode */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-xs font-medium">System Health</span>
                  <Activity className="w-4 h-4 text-amber-400" />
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <StatusBadge
                    status={health?.status || 'degraded'}
                    label={health?.status ? health.status.toUpperCase() : 'DEGRADED'}
                  />
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">pgvector ready</span>
                <span className="text-xs font-medium text-emerald-400">Prepared</span>
              </div>
            </div>
          </div>

          {/* Database Connectivity Diagnostic Action Card */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-slate-200">PostgreSQL Live Ping Diagnostic</h3>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  Sends an isolated test query (<code className="text-indigo-300">SELECT 1</code>) to verify the SQLAlchemy database connection pool.
                </p>
              </div>

              <button
                onClick={handleTestDb}
                disabled={testingDb}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Activity className={`w-3.5 h-3.5 ${testingDb ? 'animate-spin text-emerald-400' : ''}`} />
                <span>{testingDb ? 'Pinging DB...' : 'Test Connection'}</span>
              </button>
            </div>

            {dbTestResult && (
              <div
                className={`mt-4 p-3 rounded-lg border text-xs ${
                  dbTestResult.connected
                    ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-300'
                    : 'bg-rose-950/30 border-rose-800/60 text-rose-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  {dbTestResult.connected ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  )}
                  <span className="font-semibold">
                    {dbTestResult.connected
                      ? `Database responded in ${dbTestResult.latency_ms} ms`
                      : 'Database ping failed'}
                  </span>
                </div>
                {dbTestResult.error && (
                  <p className="mt-1 text-[11px] font-mono opacity-90">{dbTestResult.error}</p>
                )}
              </div>
            )}
          </div>

          {/* Architectural Alignment & Roadmap Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Architectural Stack */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-slate-200">Decided Architectural Stack</h3>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-400">Frontend UI</span>
                  <span className="font-mono text-slate-200">React 19 + TypeScript + Tailwind CSS</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-400">Backend API</span>
                  <span className="font-mono text-slate-200">Python 3.13 + FastAPI</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-400">Primary Database</span>
                  <span className="font-mono text-slate-200">PostgreSQL (SQLAlchemy + Alembic)</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-400">Vector Search</span>
                  <span className="font-mono text-indigo-300">pgvector (Prepared for Phase 2)</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-slate-800/50">
                  <span className="text-slate-400">Agent Orchestration</span>
                  <span className="font-mono text-indigo-300">LangGraph (Prepared for Phase 1)</span>
                </div>
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-slate-400">Background Tasks</span>
                  <span className="font-mono text-indigo-300">Redis + Celery (Scheduled for Phase 2)</span>
                </div>
              </div>
            </div>

            {/* Scope Guardrails */}
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <Code2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-200">Phase 0 Guardrails & Integrity</h3>
              </div>

              <div className="space-y-2.5 text-xs text-slate-300">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">No Fake Functionality:</span>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      No mocked LLM chats, fabricated tool runs, or fake memory writes are present.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Safe Startup:</span>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      The application launches cleanly, pings the database, and reports degraded status gracefully if PostgreSQL is offline.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Strict Secret Hygiene:</span>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Passwords and secrets are never committed, logged, or exposed in frontend client code.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Diagnostic Raw Data Feed */}
          {health && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Raw Health Diagnostic Payload (/api/v1/health)</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">Live API Response</span>
              </div>
              <pre className="p-4 text-xs font-mono text-indigo-200/90 overflow-x-auto bg-slate-950/60 max-h-48">
                {JSON.stringify(health, null, 2)}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
};
