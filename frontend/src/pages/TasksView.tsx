import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  CheckSquare,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Ban,
  Activity,
  Server,
} from 'lucide-react';
import { taskService } from '../services/taskService';
import type { TaskItem, TaskStats, TaskStatus } from '../types/task';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; icon: React.ElementType; colorClass: string; badgeClass: string }
> = {
  queued: {
    label: 'Queued',
    icon: Clock,
    colorClass: 'text-amber-400',
    badgeClass: 'bg-amber-950/40 text-amber-300 border-amber-800/60',
  },
  running: {
    label: 'Running',
    icon: RefreshCw,
    colorClass: 'text-blue-400 animate-spin',
    badgeClass: 'bg-blue-950/40 text-blue-300 border-blue-800/60',
  },
  succeeded: {
    label: 'Succeeded',
    icon: CheckCircle2,
    colorClass: 'text-emerald-400',
    badgeClass: 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    colorClass: 'text-rose-400',
    badgeClass: 'bg-rose-950/40 text-rose-300 border-rose-800/60',
  },
  cancelled: {
    label: 'Cancelled',
    icon: Ban,
    colorClass: 'text-neutral-400',
    badgeClass: 'bg-neutral-800 text-neutral-400 border-neutral-700',
  },
};

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [actionAlert, setActionAlert] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasksAndStats = useCallback(async (isPolling = false) => {
    if (!isPolling) setIsLoading(true);
    setError(null);
    try {
      const [tasksRes, statsRes] = await Promise.all([
        taskService.listTasks({
          status: statusFilter === 'all' ? undefined : statusFilter,
          limit: 50,
        }),
        taskService.getStats(),
      ]);
      setTasks(tasksRes.items);
      setStats(statsRes);
    } catch (err: any) {
      if (!isPolling) {
        setError(err?.message || 'Failed to fetch background tasks.');
      }
    } finally {
      if (!isPolling) setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchTasksAndStats(false);
  }, [fetchTasksAndStats]);

  // Real-time polling timer for active background jobs
  useEffect(() => {
    if (autoRefresh) {
      pollTimerRef.current = setInterval(() => {
        fetchTasksAndStats(true);
      }, 4000);
    }
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [autoRefresh, fetchTasksAndStats]);

  const handleRetryTask = async (taskId: string) => {
    try {
      await taskService.retryTask(taskId);
      setActionAlert('Task queued for retry.');
      fetchTasksAndStats(true);
      setTimeout(() => setActionAlert(null), 3500);
    } catch (err: any) {
      alert(err?.message || 'Failed to retry task.');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await taskService.cancelTask(taskId);
      setActionAlert('Task cancelled successfully.');
      fetchTasksAndStats(true);
      setTimeout(() => setActionAlert(null), 3500);
    } catch (err: any) {
      alert(err?.message || 'Failed to cancel task.');
    }
  };

  const formatDuration = (ms?: number | null) => {
    if (ms === null || ms === undefined) return '—';
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-neutral-950 text-neutral-100 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400">
              <CheckSquare className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Background Task Workers</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-blue-900/40 text-blue-300 border border-blue-700/50 flex items-center gap-1.5">
              <Server className="w-3 h-3 text-blue-400" />
              Redis + Celery
            </span>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Asynchronous background workers executing memory extraction, index maintenance, and proactive agent jobs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-neutral-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded bg-neutral-900 border-neutral-700 accent-blue-500"
            />
            Auto-refresh (4s)
          </label>
          <button
            onClick={() => fetchTasksAndStats(false)}
            className="p-2 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 rounded-lg border border-neutral-700 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Action Alert Banner */}
        {actionAlert && (
          <div className="flex items-center gap-2 p-3 bg-blue-950/60 border border-blue-800 text-blue-300 rounded-lg text-xs">
            <Activity className="w-4 h-4 shrink-0 text-blue-400" />
            <span>{actionAlert}</span>
          </div>
        )}

        {/* Status Metrics Cards */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs">Total Tasks</div>
              <div className="text-2xl font-bold mt-1 text-white">{stats.total}</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs flex items-center gap-1">
                <Clock className="w-3 h-3 text-amber-400" />
                Queued
              </div>
              <div className="text-2xl font-bold mt-1 text-amber-400">{stats.queued}</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs flex items-center gap-1">
                <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
                Running
              </div>
              <div className="text-2xl font-bold mt-1 text-blue-400">{stats.running}</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Succeeded
              </div>
              <div className="text-2xl font-bold mt-1 text-emerald-400">{stats.succeeded}</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs flex items-center gap-1">
                <XCircle className="w-3 h-3 text-rose-400" />
                Failed
              </div>
              <div className="text-2xl font-bold mt-1 text-rose-400">{stats.failed}</div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5">
              <div className="text-neutral-400 text-xs flex items-center gap-1">
                <Ban className="w-3 h-3 text-neutral-400" />
                Cancelled
              </div>
              <div className="text-2xl font-bold mt-1 text-neutral-400">{stats.cancelled}</div>
            </div>
          </div>
        )}

        {/* Filter Navigation Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-neutral-800">
          {['all', 'running', 'queued', 'succeeded', 'failed', 'cancelled'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition shrink-0 ${
                statusFilter === st
                  ? 'bg-neutral-800 text-white border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Task Items List */}
        {isLoading ? (
          <LoadingState message="Loading background tasks..." />
        ) : error ? (
          <ErrorState message={error} onRetry={() => fetchTasksAndStats(false)} />
        ) : tasks.length === 0 ? (
          <EmptyState
            title="No background tasks found"
            description="Tasks dispatched during chat memory extraction or maintenance routines will appear here."
          />
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => {
              const statusCfg = STATUS_CONFIG[task.status as TaskStatus] || STATUS_CONFIG.queued;
              const StatusIcon = statusCfg.icon;

              const createdDate = new Date(task.created_at).toLocaleTimeString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              });

              return (
                <div
                  key={task.id}
                  className="bg-neutral-900 border border-neutral-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-neutral-700 transition"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-neutral-200">{task.task_name}</span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-neutral-800 border border-neutral-700 text-neutral-400">
                        {task.task_type}
                      </span>
                      <span
                        className={`text-[11px] font-medium px-2 py-0.5 rounded-md border flex items-center gap-1 ${statusCfg.badgeClass}`}
                      >
                        <StatusIcon className={`w-3 h-3 ${statusCfg.colorClass}`} />
                        {statusCfg.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-neutral-400 flex-wrap">
                      <span>Created: {createdDate}</span>
                      <span>Duration: {formatDuration(task.duration_ms)}</span>
                      {task.retry_count > 0 && <span>Retries: {task.retry_count} / {task.max_retries}</span>}
                      {task.celery_task_id && (
                        <span className="font-mono text-[10px] text-neutral-500">
                          id: {task.celery_task_id.slice(0, 8)}...
                        </span>
                      )}
                    </div>

                    {task.error_message && (
                      <div className="p-2 bg-rose-950/30 border border-rose-800/40 rounded text-rose-300 text-xs mt-1">
                        {task.error_message}
                      </div>
                    )}

                    {task.result_metadata && (
                      <div className="text-[11px] text-neutral-400">
                        Result:{' '}
                        <span className="font-mono text-neutral-300">
                          {JSON.stringify(task.result_metadata)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {(task.status === 'failed' || task.status === 'cancelled') && (
                      <button
                        onClick={() => handleRetryTask(task.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-lg text-xs font-medium border border-neutral-700 transition"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        Retry
                      </button>
                    )}

                    {(task.status === 'queued' || task.status === 'running') && (
                      <button
                        onClick={() => handleCancelTask(task.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 hover:bg-rose-950/40 text-neutral-400 hover:text-rose-300 rounded-lg text-xs font-medium border border-neutral-700 transition"
                      >
                        <Ban className="w-3.5 h-3.5" />
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
