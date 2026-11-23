import React, { useState, useEffect, useCallback } from 'react';
import {
  Zap,
  Play,
  Pause,
  Plus,
  Trash2,
  Clock,
  History,
  Sparkles,
  RefreshCw,
  X,
  ShieldAlert,
} from 'lucide-react';
import { automationService } from '../services/automationService';
import type {
  Automation,
  AutomationStats,
  AutomationExecution,
  ParseInstructionResponse,
} from '../types/automations';

export const AutomationsView: React.FC = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [stats, setStats] = useState<AutomationStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Creation Modal State
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [naturalInstruction, setNaturalInstruction] = useState<string>(
    'Every morning at 8 AM, prepare a briefing with today\'s calendar events, important emails, and pending tasks.'
  );
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [parsedPreview, setParsedPreview] = useState<ParseInstructionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Executions History Modal State
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null);
  const [executions, setExecutions] = useState<AutomationExecution[]>([]);
  const [loadingExecutions, setLoadingExecutions] = useState<boolean>(false);

  // Action status message
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [list, statsData] = await Promise.all([
        automationService.listAutomations(),
        automationService.getStats(),
      ]);
      setAutomations(list);
      setStats(statsData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load automations.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleParseInstruction = async () => {
    if (!naturalInstruction.trim()) return;
    setIsParsing(true);
    try {
      const preview = await automationService.parseInstruction(naturalInstruction);
      setParsedPreview(preview);
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to parse instruction.' });
    } finally {
      setIsParsing(false);
    }
  };

  const handleCreateConfirm = async () => {
    if (!parsedPreview) return;
    setIsSubmitting(true);
    try {
      await automationService.createAutomation({
        name: parsedPreview.name,
        description: parsedPreview.description,
        natural_instruction: parsedPreview.natural_instruction,
        trigger_type: parsedPreview.trigger_type,
        schedule_config: parsedPreview.schedule_config,
        timezone: parsedPreview.timezone,
        actions: parsedPreview.actions,
        associated_tools: parsedPreview.associated_tools,
        approval_policy: parsedPreview.approval_policy,
        is_enabled: true,
      });
      setShowCreateModal(false);
      setParsedPreview(null);
      setActionNotice({ type: 'success', message: `Automation '${parsedPreview.name}' scheduled successfully.` });
      fetchData();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to schedule automation.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleEnable = async (auto: Automation) => {
    try {
      if (auto.is_enabled) {
        await automationService.disableAutomation(auto.id);
        setActionNotice({ type: 'success', message: `Paused automation '${auto.name}'.` });
      } else {
        await automationService.enableAutomation(auto.id);
        setActionNotice({ type: 'success', message: `Enabled automation '${auto.name}'.` });
      }
      fetchData();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to toggle automation status.' });
    }
  };

  const handleRunNow = async (auto: Automation) => {
    try {
      setActionNotice({ type: 'success', message: `Triggering execution for '${auto.name}'...` });
      const exec = await automationService.runAutomation(auto.id);
      if (exec.status === 'WAITING_FOR_APPROVAL') {
        setActionNotice({
          type: 'error',
          message: `Execution paused: Tool action requires human-in-the-loop approval. Check the Approvals tab.`,
        });
      } else if (exec.status === 'SUCCEEDED') {
        setActionNotice({
          type: 'success',
          message: `Execution for '${auto.name}' completed successfully in ${exec.duration_ms}ms.`,
        });
      }
      fetchData();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Execution failed.' });
    }
  };

  const handleDelete = async (auto: Automation) => {
    if (!confirm(`Are you sure you want to permanently delete automation '${auto.name}'?`)) return;
    try {
      await automationService.deleteAutomation(auto.id);
      setActionNotice({ type: 'success', message: `Deleted automation '${auto.name}'.` });
      fetchData();
    } catch (err: any) {
      setActionNotice({ type: 'error', message: err?.message || 'Failed to delete automation.' });
    }
  };

  const handleOpenExecutions = async (auto: Automation) => {
    setSelectedAutomation(auto);
    setLoadingExecutions(true);
    try {
      const historyList = await automationService.listExecutions(auto.id);
      setExecutions(historyList);
    } catch {
      // Ignore
    } finally {
      setLoadingExecutions(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCEEDED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">SUCCEEDED</span>;
      case 'WAITING_FOR_APPROVAL':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-400 border border-amber-800 animate-pulse">WAITING APPROVAL</span>;
      case 'FAILED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-400 border border-rose-800">FAILED</span>;
      case 'RUNNING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-950 text-sky-400 border border-sky-800">RUNNING</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Automations & Schedulers</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
              Phase 4
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Proactive background schedules, recurring cron triggers, and autonomous workflows.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors cursor-pointer"
            title="Refresh automations"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => {
              setParsedPreview(null);
              setShowCreateModal(true);
            }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/20 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Create Automation
          </button>
        </div>
      </div>

      {/* Global Error Alert */}
      {error && (
        <div className="p-3 rounded-lg text-sm bg-rose-950/40 text-rose-200 border border-rose-800/60 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-slate-400 hover:text-white cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Action Notice Alert */}
      {actionNotice && (
        <div
          className={`p-3 rounded-lg text-sm flex items-center justify-between border ${
            actionNotice.type === 'success'
              ? 'bg-emerald-950/40 text-emerald-200 border-emerald-800/60'
              : 'bg-rose-950/40 text-rose-200 border-rose-800/60'
          }`}
        >
          <span>{actionNotice.message}</span>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total</p>
          <p className="text-2xl font-bold text-white mt-1">{stats?.total_automations ?? automations.length}</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">{stats?.active_automations ?? 0}</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Paused</p>
          <p className="text-2xl font-bold text-amber-400 mt-1">{stats?.paused_automations ?? 0}</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Failed Runs</p>
          <p className="text-2xl font-bold text-rose-400 mt-1">{stats?.failed_executions ?? 0}</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-sm col-span-2 md:col-span-1">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Next Run</p>
          <p className="text-xs font-semibold text-sky-400 mt-2 truncate">
            {stats?.next_scheduled_run
              ? new Date(stats.next_scheduled_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'None'}
          </p>
        </div>
      </div>

      {/* Automations Table / List */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <h2 className="font-semibold text-sm text-white">Configured Workflows</h2>
          <span className="text-xs text-slate-400">{automations.length} workflows defined</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-sm text-slate-400">Loading automations...</div>
        ) : automations.length === 0 ? (
          <div className="p-12 text-center">
            <Zap className="w-10 h-10 mx-auto text-slate-600 mb-3" />
            <h3 className="font-semibold text-white text-base">No automations configured</h3>
            <p className="text-slate-400 text-sm max-w-md mx-auto mt-1">
              Create your first scheduled workflow using natural language like "Every morning at 8 AM, prepare a briefing".
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors cursor-pointer"
            >
              Create Automation
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {automations.map((auto) => (
              <div key={auto.id} className="p-4 hover:bg-slate-850/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center gap-2.5">
                    <span className="font-semibold text-white text-base">{auto.name}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                        auto.is_enabled
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800/60'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {auto.is_enabled ? 'Active' : 'Paused'}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-950/70 text-indigo-300 border border-indigo-800/60">
                      {auto.trigger_type}
                    </span>
                  </div>

                  {auto.natural_instruction && (
                    <p className="text-xs text-slate-300 italic">"{auto.natural_instruction}"</p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-2">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      Next run: {auto.next_run_at ? new Date(auto.next_run_at).toLocaleString() : 'Manual only'}
                    </span>
                    <span>•</span>
                    <span>Executions: <strong className="text-slate-200">{auto.execution_count}</strong></span>
                    {auto.last_status && (
                      <>
                        <span>•</span>
                        <span>Last status: {getStatusBadge(auto.last_status.toUpperCase())}</span>
                      </>
                    )}
                  </div>

                  {/* Associated tools */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {auto.associated_tools.map((tool) => (
                      <span key={tool} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700">
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleRunNow(auto)}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 transition-colors cursor-pointer"
                    title="Run Now (Manual Execution)"
                  >
                    <Play className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleToggleEnable(auto)}
                    className={`p-2 rounded-lg border transition-colors cursor-pointer ${
                      auto.is_enabled
                        ? 'bg-slate-800 hover:bg-slate-700 text-amber-400 border-slate-700'
                        : 'bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border-indigo-800'
                    }`}
                    title={auto.is_enabled ? 'Pause' : 'Enable'}
                  >
                    {auto.is_enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>

                  <button
                    onClick={() => handleOpenExecutions(auto)}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
                    title="Execution History"
                  >
                    <History className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleDelete(auto)}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-rose-950 text-slate-400 hover:text-rose-400 border border-slate-700 transition-colors cursor-pointer"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Creation Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-base">Create Scheduled Automation</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 overflow-y-auto flex-1">
              {/* Natural Language Prompt */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                  Describe what you want to automate
                </label>
                <textarea
                  value={naturalInstruction}
                  onChange={(e) => setNaturalInstruction(e.target.value)}
                  rows={3}
                  placeholder="e.g. Every Monday at 9 AM, review my open issues and prepare a status summary."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
                <button
                  type="button"
                  onClick={handleParseInstruction}
                  disabled={isParsing || !naturalInstruction.trim()}
                  className="mt-2.5 w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-600/40 text-sm font-medium transition-colors cursor-pointer disabled:opacity-50"
                >
                  <Sparkles className={`w-4 h-4 ${isParsing ? 'animate-spin' : ''}`} />
                  {isParsing ? 'Analyzing with AI...' : 'Parse & Validate with AI'}
                </button>
              </div>

              {/* Structured Configuration Preview */}
              {parsedPreview && (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                      Structured Configuration
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                      Validated
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-300">
                    <p><strong>Name:</strong> {parsedPreview.name}</p>
                    <p><strong>Trigger:</strong> <span className="capitalize">{parsedPreview.trigger_type}</span> ({JSON.stringify(parsedPreview.schedule_config)})</p>
                    <p><strong>Timezone:</strong> {parsedPreview.timezone}</p>
                  </div>

                  {parsedPreview.requires_confirmation && (
                    <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-xs text-amber-300 flex items-start gap-2">
                      <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>One or more tools in this workflow require explicit human approval before execution.</span>
                    </div>
                  )}

                  <div>
                    <span className="text-xs font-medium text-slate-400 block mb-1">Actions to Execute:</span>
                    <div className="space-y-1">
                      {parsedPreview.actions.map((act, i) => (
                        <div key={i} className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs flex items-center justify-between">
                          <span className="font-mono text-indigo-300">{act.tool}</span>
                          <span className="text-slate-400 text-[11px]">{act.description || 'Action'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 flex items-center justify-end gap-3 bg-slate-950/40">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateConfirm}
                disabled={!parsedPreview || isSubmitting}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors shadow-lg shadow-indigo-600/20 cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? 'Scheduling...' : 'Confirm & Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Execution History Drawer */}
      {selectedAutomation && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-base">Execution History: {selectedAutomation.name}</h3>
              </div>
              <button
                onClick={() => setSelectedAutomation(null)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto divide-y divide-slate-800/60 flex-1">
              {loadingExecutions ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading history...</div>
              ) : executions.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">No executions recorded yet.</div>
              ) : (
                executions.map((e) => (
                  <div key={e.id} className="py-3 text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusBadge(e.status)}
                        <span className="text-slate-400">Trigger: {e.trigger_type}</span>
                      </div>
                      <span className="text-slate-500 font-mono">
                        {new Date(e.created_at).toLocaleString()}
                      </span>
                    </div>

                    {e.duration_ms !== undefined && (
                      <p className="text-slate-400">Duration: <strong className="text-slate-200">{e.duration_ms}ms</strong></p>
                    )}

                    {e.error_message && (
                      <div className="p-2 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-[11px]">
                        Error: {e.error_message}
                      </div>
                    )}

                    {e.results && e.results.length > 0 && (
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[11px] font-mono overflow-x-auto max-h-32">
                        <pre>{JSON.stringify(e.results, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
