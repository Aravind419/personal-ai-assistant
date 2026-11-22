import React, { useState, useEffect, useCallback } from 'react';
import { ScrollText, RefreshCw, Terminal } from 'lucide-react';
import { toolService } from '../services/toolService';

import type { ToolExecutionSummary } from '../types/tool';

export const ActivityLogsView: React.FC = () => {
  const [logs, setLogs] = useState<ToolExecutionSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await toolService.getExecutionHistory({ limit: 100 });
      setLogs(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load activity logs.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <ScrollText className="w-6 h-6 text-indigo-400" />
            Activity & Execution Logs
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time audit log of tool dispatches, background processes, and system operations.
          </p>
        </div>
        <button
          onClick={() => fetchLogs()}
          className="px-3 py-1.5 rounded-lg text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors self-start cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
            Loading activity logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
            No activity logs found.
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-indigo-400" />
                  <span className="font-semibold text-slate-100 font-mono text-sm">{log.tool_name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      log.status === 'succeeded'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : log.status === 'awaiting_approval'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-rose-500/20 text-rose-300'
                    }`}
                  >
                    {log.status}
                  </span>
                  {log.duration_ms !== null && log.duration_ms !== undefined && (
                    <span className="text-slate-500">{log.duration_ms} ms</span>
                  )}
                </div>

                <div className="text-slate-400">
                  Args:{' '}
                  <code className="text-indigo-300 font-mono">{JSON.stringify(log.requested_arguments)}</code>
                </div>

                {log.result_summary && (
                  <div className="text-slate-300 truncate max-w-2xl">
                    Output: <span className="font-mono text-emerald-300">{log.result_summary}</span>
                  </div>
                )}

                {log.error_details && <div className="text-rose-400 font-mono">{log.error_details}</div>}
              </div>

              <div className="text-right text-slate-500 text-[11px] shrink-0">
                <div>{new Date(log.started_at).toLocaleString()}</div>
                <div>User: {log.user_identity}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
