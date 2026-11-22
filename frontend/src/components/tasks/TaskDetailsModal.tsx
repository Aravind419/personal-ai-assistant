import React, { useState } from 'react';
import {
  X,
  Clock,
  CheckCircle2,
  RotateCcw,
  Ban,
  Server,
  Cpu,
  Layers,
  ShieldCheck,
  Copy,
  Check,
  Sparkles,
  GitCompare,
  FileText,
  AlertTriangle,
  Info,
} from 'lucide-react';
import type { TaskItem } from '../../types/task';

interface TaskDetailsModalProps {
  task: TaskItem | null;
  isOpen: boolean;
  onClose: () => void;
  onRetry?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
}

export const TaskDetailsModal: React.FC<TaskDetailsModalProps> = ({
  task,
  isOpen,
  onClose,
  onRetry,
  onCancel,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'extraction' | 'raw'>('overview');
  const [copiedId, setCopiedId] = useState(false);

  if (!isOpen || !task) return null;

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const formatDuration = (ms?: number | null) => {
    if (ms === null || ms === undefined) return '—';
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
  };

  const formatTimestamp = (ts?: string | null) => {
    if (!ts) return '—';
    const d = new Date(ts);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
  };

  const inputParams = task.input_params || {};
  const resultMeta = task.result_metadata || {};
  const trace = resultMeta.extraction_trace || {};

  const isExtractionTask = task.task_type === 'memory_extraction';
  const executionMode = task.execution_mode || resultMeta.execution_mode;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-neutral-950 border-l border-neutral-800 h-full flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-neutral-800 bg-neutral-900/60 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-base font-semibold text-neutral-100">{task.task_name}</h2>
              <span
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${
                  task.status === 'succeeded'
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80'
                    : task.status === 'running'
                    ? 'bg-blue-950/60 text-blue-300 border-blue-800/80'
                    : task.status === 'failed'
                    ? 'bg-rose-950/60 text-rose-300 border-rose-800/80'
                    : task.status === 'cancelled'
                    ? 'bg-neutral-800 text-neutral-400 border-neutral-700'
                    : 'bg-amber-950/60 text-amber-300 border-amber-800/80'
                }`}
              >
                {task.status.toUpperCase()}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
                {task.task_type}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-neutral-400">
              <span className="font-mono text-[11px] text-neutral-500">ID: {task.id}</span>
              <button
                onClick={() => handleCopyId(task.id)}
                className="text-neutral-500 hover:text-neutral-300 transition"
                title="Copy Task ID"
              >
                {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex items-center gap-1 px-5 border-b border-neutral-800 bg-neutral-900/30 text-xs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-3 px-3 font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <Info className="w-3.5 h-3.5" />
            Overview & Source
          </button>

          {isExtractionTask && (
            <button
              onClick={() => setActiveTab('extraction')}
              className={`py-3 px-3 font-medium border-b-2 transition flex items-center gap-1.5 ${
                activeTab === 'extraction'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Memory Extraction
              {trace.memories_extracted !== undefined && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-blue-900/40 text-blue-300 border border-blue-700/50">
                  {trace.memories_extracted}
                </span>
              )}
            </button>
          )}

          <button
            onClick={() => setActiveTab('raw')}
            className={`py-3 px-3 font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'raw'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Input & Raw Results
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {activeTab === 'overview' && (
            <>
              {/* Section A: General Lifecycle Information */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-blue-400" />
                  Task Lifecycle & Timing
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Created At</span>
                    <span className="text-neutral-200 font-mono text-[11px] mt-0.5 block">
                      {formatTimestamp(task.created_at)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Started At</span>
                    <span className="text-neutral-200 font-mono text-[11px] mt-0.5 block">
                      {formatTimestamp(task.started_at)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Completed At</span>
                    <span className="text-neutral-200 font-mono text-[11px] mt-0.5 block">
                      {formatTimestamp(task.completed_at)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Execution Duration</span>
                    <span className="text-emerald-400 font-mono font-medium mt-0.5 block">
                      {formatDuration(task.duration_ms)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Queue Wait Time</span>
                    <span className="text-amber-400 font-mono font-medium mt-0.5 block">
                      {formatDuration(task.queue_wait_ms)}
                    </span>
                  </div>

                  <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-2.5">
                    <span className="text-neutral-500 text-[11px] block">Retries Attempted</span>
                    <span className="text-neutral-200 font-mono font-medium mt-0.5 block">
                      {task.retry_count} / {task.max_retries}
                    </span>
                  </div>
                </div>
              </div>

              {/* Section B: Execution Runtime & Infrastructure */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                  <Server className="w-3.5 h-3.5 text-blue-400" />
                  Execution Runtime & Infrastructure
                </h3>
                <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 space-y-2.5 text-xs">
                  <div className="flex items-center justify-between py-1 border-b border-neutral-800/60">
                    <span className="text-neutral-400">Execution Mode</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1.5 ${
                        executionMode === 'celery_worker'
                          ? 'bg-purple-950/60 text-purple-300 border border-purple-800/80'
                          : executionMode === 'local_async'
                          ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-800/80'
                          : 'bg-neutral-800 text-neutral-300 border border-neutral-700'
                      }`}
                    >
                      <Cpu className="w-3 h-3" />
                      {executionMode === 'celery_worker'
                        ? 'Celery Worker (Distributed)'
                        : executionMode === 'local_async'
                        ? 'Local Async Runtime (In-Process Fallback)'
                        : 'Queued (Pending Dispatch)'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-neutral-800/60">
                    <span className="text-neutral-400">Worker Node / Hostname</span>
                    <span className="font-mono text-neutral-200 text-[11px]">
                      {task.worker_id || resultMeta.worker_id || (task.status === 'queued' ? 'Awaiting Worker' : 'Local Event Loop')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-neutral-800/60">
                    <span className="text-neutral-400">Celery Task ID</span>
                    <span className="font-mono text-neutral-300 text-[11px]">
                      {task.celery_task_id || 'None (Processed via async runtime)'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1">
                    <span className="text-neutral-400">Queue / Broker Target</span>
                    <span className="font-mono text-neutral-300 text-[11px]">celery / redis://localhost:6379/0</span>
                  </div>
                </div>
              </div>

              {/* Section C: Source Information */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-blue-400" />
                  Source Context
                </h3>
                <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 space-y-3 text-xs">
                  {task.source_conversation_id && (
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-400">Conversation</span>
                      <div className="text-right">
                        <span className="text-neutral-200 font-medium block">
                          {task.source_conversation_title || 'Conversation'}
                        </span>
                        <span className="font-mono text-neutral-500 text-[10px] block">
                          {task.source_conversation_id}
                        </span>
                      </div>
                    </div>
                  )}

                  {task.source_message_id && (
                    <div className="flex items-center justify-between border-t border-neutral-800/60 pt-2">
                      <span className="text-neutral-400">Source Message ID</span>
                      <span className="font-mono text-neutral-300 text-[11px]">{task.source_message_id}</span>
                    </div>
                  )}

                  {inputParams.user_content && (
                    <div className="space-y-1.5 border-t border-neutral-800/60 pt-2">
                      <span className="text-neutral-400 text-[11px] block">Extracted User Message:</span>
                      <div className="p-2.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-200 font-mono text-[11px] whitespace-pre-wrap">
                        {inputParams.user_content}
                      </div>
                    </div>
                  )}

                  {inputParams.assistant_content && (
                    <div className="space-y-1.5">
                      <span className="text-neutral-400 text-[11px] block">Assistant Response Context:</span>
                      <div className="p-2.5 rounded-lg bg-neutral-950 border border-neutral-800 text-neutral-400 font-mono text-[11px] whitespace-pre-wrap max-h-32 overflow-y-auto">
                        {inputParams.assistant_content}
                      </div>
                    </div>
                  )}

                  <p className="text-[10px] text-neutral-500 flex items-center gap-1 pt-1">
                    <ShieldCheck className="w-3 h-3 text-emerald-400 shrink-0" />
                    <span>Secrets, credentials, and API keys are automatically redacted from stored task input.</span>
                  </p>
                </div>
              </div>

              {/* Error Message if Failed */}
              {task.error_message && (
                <div className="p-3.5 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1">
                  <div className="flex items-center gap-2 text-rose-300 text-xs font-semibold">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    <span>Task Execution Failure</span>
                  </div>
                  <p className="text-xs text-rose-200/90 font-mono">{task.error_message}</p>
                </div>
              )}
            </>
          )}

          {activeTab === 'extraction' && (
            <div className="space-y-5">
              {/* Pipeline Stages Checklist */}
              <div className="space-y-2.5">
                <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                  Extraction Pipeline Stages Executed
                </h3>
                <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-3.5 space-y-2 text-xs">
                  {(trace.stages_executed || [
                    '1. Source conversation identified',
                    '2. Relevant messages collected',
                    '3. Candidate memories extracted',
                    '4. Sensitive information filtering performed',
                    '5. Existing vector memories searched',
                    '6. Duplicate detection performed',
                    '7. Conflicts or outdated information reconciled',
                    '8. Embeddings generated',
                    '9. Memories persisted to PostgreSQL',
                  ]).map((stage: string, idx: number) => (
                    <div key={idx} className="flex items-center gap-2 text-neutral-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>{stage}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Extraction Metrics Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-center">
                  <span className="text-[11px] text-neutral-400 block">Created</span>
                  <span className="text-lg font-bold text-emerald-400 block mt-0.5">
                    {trace.created_memories?.length || resultMeta.memories_extracted || 0}
                  </span>
                </div>

                <div className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-center">
                  <span className="text-[11px] text-neutral-400 block">Updated</span>
                  <span className="text-lg font-bold text-blue-400 block mt-0.5">
                    {trace.updated_memories?.length || 0}
                  </span>
                </div>

                <div className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-center">
                  <span className="text-[11px] text-neutral-400 block">Duplicates</span>
                  <span className="text-lg font-bold text-amber-400 block mt-0.5">
                    {trace.duplicate_memories?.length || 0}
                  </span>
                </div>

                <div className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-center">
                  <span className="text-[11px] text-neutral-400 block">Filtered</span>
                  <span className="text-lg font-bold text-neutral-400 block mt-0.5">
                    {trace.filtered_candidates?.length || 0}
                  </span>
                </div>
              </div>

              {/* Created Memories List */}
              {trace.created_memories && trace.created_memories.length > 0 && (
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Created New Memories ({trace.created_memories.length})
                  </h4>
                  <div className="space-y-2">
                    {trace.created_memories.map((m: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-1.5 text-xs"
                      >
                        <p className="text-neutral-100 font-medium">"{m.content}"</p>
                        <div className="flex items-center gap-2 flex-wrap text-[10px] text-neutral-400">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300 font-medium">
                            {m.category}
                          </span>
                          <span>Importance: {m.importance}</span>
                          <span>Confidence: {m.confidence}</span>
                          {m.embedding_model && <span>Model: {m.embedding_model}</span>}
                          {m.embedding_dim && <span>Dim: {m.embedding_dim}</span>}
                          <span className="text-emerald-400 font-medium">✓ Persisted</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Updated / Superseded Memories */}
              {trace.updated_memories && trace.updated_memories.length > 0 && (
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold text-blue-400 flex items-center gap-1.5">
                    <GitCompare className="w-3.5 h-3.5" />
                    Superseded / Updated Memories ({trace.updated_memories.length})
                  </h4>
                  <div className="space-y-2">
                    {trace.updated_memories.map((m: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 bg-blue-950/20 border border-blue-800/40 rounded-xl space-y-2 text-xs"
                      >
                        <div>
                          <span className="text-[10px] text-neutral-500 block">Updated Content:</span>
                          <p className="text-neutral-100 font-medium">"{m.content}"</p>
                        </div>
                        {m.previous_content && (
                          <div className="border-t border-blue-900/40 pt-1.5">
                            <span className="text-[10px] text-neutral-500 block">Previous Version (Preserved in History):</span>
                            <p className="text-neutral-400 line-through text-[11px]">"{m.previous_content}"</p>
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-[10px] text-neutral-400">
                          <span className="px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-medium">
                            {m.category}
                          </span>
                          <span>Action: {m.action}</span>
                          {m.similarity && <span>Match Sim: {m.similarity}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Duplicate Memories Ignored */}
              {trace.duplicate_memories && trace.duplicate_memories.length > 0 && (
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5" />
                    Duplicate Facts Confirmed ({trace.duplicate_memories.length})
                  </h4>
                  <div className="space-y-2">
                    {trace.duplicate_memories.map((m: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-xl space-y-1 text-xs"
                      >
                        <p className="text-neutral-200">"{m.content}"</p>
                        <p className="text-[11px] text-amber-400/80">
                          Semantic similarity: {m.similarity}. Identical fact already exists in database; touched timestamp and bumped confidence.
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Filtered Sensitive Candidates */}
              {trace.filtered_candidates && trace.filtered_candidates.length > 0 && (
                <div className="space-y-2.5">
                  <h4 className="text-xs font-semibold text-neutral-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-neutral-500" />
                    Filtered Candidates ({trace.filtered_candidates.length})
                  </h4>
                  <div className="space-y-1.5">
                    {trace.filtered_candidates.map((m: any, i: number) => (
                      <div key={i} className="p-2.5 bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-neutral-400">
                        {m.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'raw' && (
            <div className="space-y-4">
              <div>
                <span className="text-xs font-semibold text-neutral-400 block mb-1">
                  Input Parameters JSON:
                </span>
                <pre className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-300 font-mono text-xs overflow-x-auto max-h-60">
                  {JSON.stringify(inputParams, null, 2)}
                </pre>
              </div>

              <div>
                <span className="text-xs font-semibold text-neutral-400 block mb-1">
                  Stored Result Metadata JSON:
                </span>
                {task.status === 'queued' ? (
                  <div className="p-3.5 bg-neutral-900 border border-neutral-800 rounded-xl text-xs text-neutral-400 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-400" />
                    <span>This task has not started execution yet. Results are not available.</span>
                  </div>
                ) : task.status === 'running' ? (
                  <div className="p-3.5 bg-neutral-900 border border-neutral-800 rounded-xl text-xs text-neutral-400 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-400 animate-spin" />
                    <span>This task is currently being processed.</span>
                  </div>
                ) : (
                  <pre className="p-3 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-300 font-mono text-xs overflow-x-auto max-h-80">
                    {JSON.stringify(resultMeta, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-neutral-800 bg-neutral-900/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {(task.status === 'failed' || task.status === 'cancelled') && onRetry && (
              <button
                onClick={() => onRetry(task.id)}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Retry Task
              </button>
            )}

            {(task.status === 'queued' || task.status === 'running') && onCancel && (
              <button
                onClick={() => onCancel(task.id)}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-neutral-800 hover:bg-rose-950/60 text-neutral-300 hover:text-rose-300 rounded-lg text-xs font-medium border border-neutral-700 transition"
              >
                <Ban className="w-3.5 h-3.5" />
                Cancel Task
              </button>
            )}
          </div>

          <button
            onClick={onClose}
            className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-lg text-xs font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
