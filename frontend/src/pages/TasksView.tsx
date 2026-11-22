import React, { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  RotateCw,
  Search,
  Server,
  Zap,
  RefreshCw,
  Info,
  ChevronRight,
  Database,
  Layers,
  Cpu,
} from 'lucide-react';
import { taskService } from '../services/taskService';
import type { TaskItem, TaskStats, WorkerHealth } from '../types/task';
import { TaskDetailsModal } from '../components/tasks/TaskDetailsModal';

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [health, setHealth] = useState<WorkerHealth | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('created_desc');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isSweeping, setIsSweeping] = useState<boolean>(false);
  const [sweepResult, setSweepResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      const [fetchedTasksRes, fetchedStats, fetchedHealth] = await Promise.all([
        taskService.listTasks({
          status: statusFilter !== 'all' ? statusFilter : undefined,
          task_type: taskTypeFilter !== 'all' ? taskTypeFilter : undefined,
          search: searchQuery.trim() || undefined,
          sort_by: sortBy,
          limit: 50,
          offset: 0,
        }),
        taskService.getStats(),
        taskService.getHealth(),
      ]);

      setTasks(fetchedTasksRes.items);
      setStats(fetchedStats);
      setHealth(fetchedHealth);
    } catch (err: any) {
      console.error('Failed to load tasks and health:', err);
      setError(err?.message || 'Failed to load background worker data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [statusFilter, taskTypeFilter, searchQuery, sortBy]);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      loadData(true);
    }, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleSweepStale = async () => {
    setIsSweeping(true);
    setSweepResult(null);
    try {
      const res = await taskService.sweepStaleTasks(300);
      setSweepResult(`Swept ${res.swept_count} stale queued tasks successfully.`);
      await loadData(true);
      setTimeout(() => setSweepResult(null), 6000);
    } catch (err: any) {
      console.error('Failed to sweep stale tasks:', err);
      setSweepResult(`Error sweeping tasks: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsSweeping(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'succeeded':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Succeeded
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/40 text-rose-400 border border-rose-800/40">
            <XCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-950/40 text-blue-400 border border-blue-800/40 animate-pulse">
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
            Running
          </span>
        );
      case 'queued':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950/40 text-amber-400 border border-amber-800/40">
            <Clock className="w-3.5 h-3.5" />
            Queued
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            <AlertTriangle className="w-3.5 h-3.5" />
            {status}
          </span>
        );
    }
  };

  const getExecutionBadge = (mode?: string | null) => {
    if (mode === 'celery_worker') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-purple-950/40 text-purple-300 border border-purple-800/40">
          <Server className="w-3 h-3 text-purple-400" />
          Celery Worker
        </span>
      );
    }
    if (mode === 'local_async') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-cyan-950/40 text-cyan-300 border border-cyan-800/40">
          <Zap className="w-3 h-3 text-cyan-400" />
          Local Async Fallback
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-800/60 text-zinc-400 border border-zinc-700/50">
        <Clock className="w-3 h-3 text-zinc-500" />
        Pending Execution
      </span>
    );
  };

  const formatWaitTime = (seconds?: number | null) => {
    if (seconds === undefined || seconds === null) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-zinc-950 text-zinc-100 p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Cpu className="w-7 h-7 text-indigo-400" />
              Background Task Workers
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
              Phase 2 Engine
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Distributed task queue telemetry, live worker health monitoring, and semantic memory extraction transparency.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {Boolean(stats?.stale_queued_count && stats.stale_queued_count > 0) && (
            <button
              onClick={handleSweepStale}
              disabled={isSweeping}
              className="px-3.5 py-2 rounded-lg text-xs font-medium bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              title="Process older queued tasks using local async execution"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isSweeping ? 'animate-spin' : ''}`} />
              {isSweeping ? 'Processing Tasks...' : `Process ${stats?.stale_queued_count} Stale Tasks`}
            </button>
          )}

          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sweep Result Banner */}
      {sweepResult && (
        <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-300 text-xs flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{sweepResult}</span>
          </div>
          <button onClick={() => setSweepResult(null)} className="text-amber-400 hover:text-amber-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Worker Health & Queue Metrics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Worker & Broker Health Card */}
        <div className="lg:col-span-2 rounded-xl bg-zinc-900/60 border border-zinc-800/80 p-4 backdrop-blur-sm shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800/60">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              Worker System Health
            </span>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  health?.celery_online ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
              <span className="text-xs text-zinc-300 font-medium">
                {health?.celery_online ? 'Celery Active' : 'Fallback Active'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1">
            {/* Redis Status */}
            <div className="bg-zinc-950/50 rounded-lg p-2.5 border border-zinc-800/50">
              <div className="text-[11px] text-zinc-400 font-medium flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-rose-400" />
                Redis Broker
              </div>
              <div className="mt-1 flex items-baseline gap-1.5">
                <span
                  className={`text-sm font-semibold ${
                    health?.redis_connected ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {health?.redis_connected ? 'Connected' : 'Offline'}
                </span>
                {health?.redis_latency_ms != null && (
                  <span className="text-[10px] text-zinc-500">
                    ({Math.round(health.redis_latency_ms)}ms)
                  </span>
                )}
              </div>
            </div>

            {/* Celery Online Workers */}
            <div className="bg-zinc-950/50 rounded-lg p-2.5 border border-zinc-800/50">
              <div className="text-[11px] text-zinc-400 font-medium flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-purple-400" />
                Celery Workers
              </div>
              <div className="mt-1 flex items-baseline gap-1.5">
                <span
                  className={`text-sm font-semibold ${
                    health?.celery_online ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {health?.worker_count ?? 0} Online
                </span>
                <span className="text-[10px] text-zinc-500">
                  {health?.celery_online ? 'Consuming' : 'Idle'}
                </span>
              </div>
            </div>

            {/* Execution Strategy */}
            <div className="bg-zinc-950/50 rounded-lg p-2.5 border border-zinc-800/50 col-span-2 sm:col-span-1">
              <div className="text-[11px] text-zinc-400 font-medium flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Current Strategy
              </div>
              <div className="mt-1">
                <span className="text-xs font-semibold text-zinc-200">
                  {health?.celery_online ? 'Worker Queue' : 'In-Process Loop'}
                </span>
                <p className="text-[10px] text-zinc-500 truncate">
                  {health?.celery_online
                    ? 'Celery pool (Redis broker)'
                    : 'AsyncIO background task'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Queue Metrics Card */}
        <div className="rounded-xl bg-zinc-900/60 border border-zinc-800/80 p-4 backdrop-blur-sm shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800/60">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              Queue Latency
            </span>
            <span className="text-[11px] text-zinc-400">
              Oldest: <strong className="text-zinc-200">{formatWaitTime(stats?.oldest_queued_wait_seconds)}</strong>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="bg-zinc-950/50 rounded-lg p-2.5 border border-zinc-800/50">
              <span className="text-[11px] text-zinc-400 block font-medium">Avg Wait Time</span>
              <span className="text-base font-semibold text-zinc-200 mt-0.5 block">
                {stats?.average_wait_seconds ? `${Math.round(stats.average_wait_seconds)}s` : '0s'}
              </span>
            </div>

            <div className="bg-zinc-950/50 rounded-lg p-2.5 border border-zinc-800/50">
              <span className="text-[11px] text-zinc-400 block font-medium">Stale (&gt;5m)</span>
              <span
                className={`text-base font-semibold mt-0.5 block ${
                  (stats?.stale_queued_count ?? 0) > 0 ? 'text-amber-400' : 'text-zinc-400'
                }`}
              >
                {stats?.stale_queued_count ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Total Tasks Counter Card */}
        <div className="rounded-xl bg-zinc-900/60 border border-zinc-800/80 p-4 backdrop-blur-sm shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800/60">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              Task Execution Counts
            </span>
            <span className="text-xs text-zinc-400 font-mono">
              Total: {stats?.total ?? 0}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-2 pt-1 text-center">
            <div className="bg-zinc-950/50 rounded p-1.5 border border-zinc-800/40">
              <span className="text-[10px] text-amber-400 block font-medium">Queued</span>
              <span className="text-sm font-bold text-amber-300">{stats?.queued ?? 0}</span>
            </div>
            <div className="bg-zinc-950/50 rounded p-1.5 border border-zinc-800/40">
              <span className="text-[10px] text-blue-400 block font-medium">Running</span>
              <span className="text-sm font-bold text-blue-300">{stats?.running ?? 0}</span>
            </div>
            <div className="bg-zinc-950/50 rounded p-1.5 border border-zinc-800/40">
              <span className="text-[10px] text-emerald-400 block font-medium">Done</span>
              <span className="text-sm font-bold text-emerald-300">{stats?.succeeded ?? 0}</span>
            </div>
            <div className="bg-zinc-950/50 rounded p-1.5 border border-zinc-800/40">
              <span className="text-[10px] text-rose-400 block font-medium">Failed</span>
              <span className="text-sm font-bold text-rose-300">{stats?.failed ?? 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter, Search & Sort Toolbar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-2">
        {/* Status Tabs */}
        <div className="flex items-center bg-zinc-900/80 p-1 rounded-lg border border-zinc-800 overflow-x-auto">
          {['all', 'queued', 'running', 'succeeded', 'failed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize whitespace-nowrap transition-colors ${
                statusFilter === st
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {st}
              {stats && (
                <span className="ml-1.5 text-[10px] opacity-60">
                  {st === 'all'
                    ? stats.total
                    : st === 'queued'
                    ? stats.queued
                    : st === 'running'
                    ? stats.running
                    : st === 'succeeded'
                    ? stats.succeeded
                    : stats.failed}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Search, Type Filter and Sort */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tasks or IDs..."
              className="w-full pl-9 pr-3 py-1.5 bg-zinc-900/80 border border-zinc-800 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
            />
          </div>

          {/* Task Type Filter */}
          <div className="relative">
            <select
              value={taskTypeFilter}
              onChange={(e) => setTaskTypeFilter(e.target.value)}
              className="bg-zinc-900/80 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/80 transition-colors cursor-pointer"
            >
              <option value="all">All Types</option>
              <option value="extract_conversation_memories">Memory Extraction</option>
              <option value="consolidate_memories">Memory Consolidation</option>
              <option value="generate_embeddings">Embedding Generation</option>
            </select>
          </div>

          {/* Sort Selector */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-zinc-900/80 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/80 transition-colors cursor-pointer"
            >
              <option value="created_desc">Newest First</option>
              <option value="created_asc">Oldest First</option>
              <option value="duration_desc">Longest Duration</option>
              <option value="duration_asc">Shortest Duration</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Task List Table */}
      <div className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden flex flex-col min-h-0">
        <div className="overflow-y-auto flex-1 divide-y divide-zinc-800/60">
          {isLoading ? (
            <div className="p-12 text-center text-zinc-500 flex flex-col items-center justify-center gap-3">
              <RotateCw className="w-6 h-6 animate-spin text-indigo-400" />
              <p className="text-sm">Loading background tasks and worker metrics...</p>
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-12 text-center text-zinc-500 flex flex-col items-center justify-center gap-2">
              <Layers className="w-8 h-8 text-zinc-600" />
              <p className="text-sm font-medium text-zinc-400">No background tasks found</p>
              <p className="text-xs text-zinc-600 max-w-sm">
                Tasks are automatically created during chat conversations to extract semantic memories asynchronously.
              </p>
            </div>
          ) : (
            tasks.map((task) => {
              const resultData = (task.result_metadata_json || {}) as Record<string, any>;
              const trace = resultData.extraction_trace;
              const memoriesCount =
                resultData.memories_extracted ??
                trace?.pipeline_summary?.created_count ??
                0;

              return (
                <div
                  key={task.id}
                  onClick={() => setSelectedTask(task)}
                  className="p-4 hover:bg-zinc-800/40 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                >
                  {/* Left Column: Task Info */}
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-semibold text-sm text-zinc-200 group-hover:text-indigo-300 transition-colors truncate">
                        {task.task_name}
                      </span>
                      {getStatusBadge(task.status)}
                      {getExecutionBadge(task.execution_mode ?? undefined)}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-zinc-500 flex-wrap">
                      <span className="font-mono text-[11px] text-zinc-400">ID: {task.id.slice(0, 8)}</span>
                      <span>•</span>
                      <span>Created {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>

                      {task.queue_wait_ms !== undefined && task.queue_wait_ms !== null && (
                        <>
                          <span>•</span>
                          <span>Wait: {(task.queue_wait_ms / 1000).toFixed(1)}s</span>
                        </>
                      )}

                      {task.duration_ms !== undefined && task.duration_ms !== null && (
                        <>
                          <span>•</span>
                          <span>Execution: {(task.duration_ms / 1000).toFixed(2)}s</span>
                        </>
                      )}

                      {task.source_conversation_title && (
                        <>
                          <span>•</span>
                          <span className="text-zinc-400 truncate max-w-[200px]" title={task.source_conversation_title}>
                            Conv: "{task.source_conversation_title}"
                          </span>
                        </>
                      )}
                    </div>

                    {/* Extraction preview summary */}
                    {task.status.toLowerCase() === 'succeeded' && (
                      <div className="text-[11px] text-zinc-400 flex items-center gap-2 pt-0.5">
                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-indigo-300 font-mono">
                          {memoriesCount} memory saved
                        </span>
                        {trace?.pipeline_summary && (
                          <span className="text-zinc-500">
                            ({trace.pipeline_summary.duplicates_detected} duplicates, {trace.pipeline_summary.sensitive_filtered} sensitive filtered)
                          </span>
                        )}
                      </div>
                    )}

                    {/* Error preview */}
                    {task.error_message && (
                      <p className="text-xs text-rose-400 font-mono truncate max-w-xl">
                        Error: {task.error_message}
                      </p>
                    )}
                  </div>

                  {/* Right Column: Click Details Arrow */}
                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    <span className="text-xs text-zinc-500 group-hover:text-zinc-300 font-medium transition-colors hidden sm:inline">
                      View Transparency Trace
                    </span>
                    <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-300 transition-colors" />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Slide-Over Drawer Details Modal */}
      {selectedTask && (
        <TaskDetailsModal
          task={selectedTask}
          isOpen={Boolean(selectedTask)}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
};
export default TasksView;
