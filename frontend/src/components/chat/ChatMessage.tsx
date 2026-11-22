import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../../types/chat';
import {
  Bot,
  User,
  Copy,
  Check,
  Sparkles,
  Volume2,
  Square,
  RotateCw,
  ShieldAlert,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

import { toolService } from '../../services/toolService';

interface ChatMessageProps {
  message: Message;
  isPlayingAudio?: boolean;
  onToggleAudio?: () => void;
  onRegenerate?: () => void;
  isLastAssistant?: boolean;
  onApprovalDecided?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isPlayingAudio = false,
  onToggleAudio,
  onRegenerate,
  isLastAssistant = false,
  onApprovalDecided,
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);
  const [approvalResult, setApprovalResult] = useState<any | null>(null);
  const [isProcessingApproval, setIsProcessingApproval] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleInChatApprove = async (approvalId: string) => {
    setIsProcessingApproval(true);
    try {
      const res = await toolService.approveAction(approvalId, true);
      setApprovalStatus('approved');
      setApprovalResult(res.execution?.result || 'Executed successfully');
      onApprovalDecided?.();
    } catch (err: any) {
      alert(`Approval failed: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleInChatReject = async (approvalId: string) => {
    setIsProcessingApproval(true);
    try {
      await toolService.rejectAction(approvalId, 'Rejected directly from chat.');
      setApprovalStatus('rejected');
      onApprovalDecided?.();
    } catch (err: any) {
      alert(`Rejection failed: ${err?.message || 'Unknown error'}`);
    } finally {
      setIsProcessingApproval(false);
    }
  };


  return (
    <div
      className={`py-5 px-4 md:px-6 transition-colors ${
        isUser ? 'bg-slate-900/40' : 'bg-slate-950/60 border-y border-slate-900/80'
      }`}
    >
      <div className="max-w-4xl mx-auto flex items-start gap-4">
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          {isUser ? (
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300">
              <User className="w-4 h-4" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-indigo-500/20">
              <Bot className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200">
                {isUser ? 'You' : 'Personal AI Assistant'}
              </span>
              {!isUser && message.model && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
                  <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                  {message.model.split('/').pop()}
                </span>
              )}
            </div>

            {/* Actions for Assistant Message */}
            {!isUser && message.content && (
              <div className="flex items-center gap-1">
                {/* Voice Read Aloud Toggle Button */}
                {onToggleAudio && (
                  <button
                    onClick={onToggleAudio}
                    className={`p-1.5 rounded transition-colors cursor-pointer ${
                      isPlayingAudio
                        ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 animate-pulse'
                        : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                    }`}
                    title={isPlayingAudio ? 'Stop audio' : 'Read aloud'}
                  >
                    {isPlayingAudio ? (
                      <Square className="w-3.5 h-3.5 fill-indigo-300" />
                    ) : (
                      <Volume2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}

                {/* Regenerate Button */}
                {isLastAssistant && onRegenerate && !message.isStreaming && (
                  <button
                    onClick={onRegenerate}
                    className="p-1.5 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
                    title="Regenerate response"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                  </button>
                )}

                {/* Copy message button */}
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Copy message"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Message Body */}
          <div className="text-sm text-slate-200 leading-relaxed break-words prose prose-invert prose-sm max-w-none">
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Code block rendering
                  code({ className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    const isInline = !match && !String(children).includes('\n');
                    const codeString = String(children).replace(/\n$/, '');

                    if (isInline) {
                      return (
                        <code
                          className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-xs"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    }

                    return (
                      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden my-3 shadow-sm">
                        <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-950/80 border-b border-slate-800 text-xs font-mono text-slate-400">
                          <span className="text-slate-300 font-medium">{match ? match[1] : 'code'}</span>
                          <button
                            onClick={() => navigator.clipboard.writeText(codeString)}
                            className="inline-flex items-center gap-1 hover:text-slate-200 cursor-pointer transition-colors"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy code</span>
                          </button>
                        </div>
                        <pre className="p-3 text-xs font-mono overflow-x-auto text-slate-200 bg-slate-900/90 leading-relaxed">
                          <code>{codeString}</code>
                        </pre>
                      </div>
                    );
                  },
                  // GitHub Flavored Markdown (GFM) Responsive Table Components
                  table({ children, ...props }: any) {
                    return (
                      <div className="overflow-x-auto my-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
                        <table className="min-w-full divide-y divide-slate-800 text-xs text-left" {...props}>
                          {children}
                        </table>
                      </div>
                    );
                  },
                  thead({ children, ...props }: any) {
                    return (
                      <thead className="bg-slate-900/90 text-slate-200 uppercase font-semibold text-[11px] tracking-wider" {...props}>
                        {children}
                      </thead>
                    );
                  },
                  tbody({ children, ...props }: any) {
                    return (
                      <tbody className="divide-y divide-slate-800/60 bg-slate-950/30" {...props}>
                        {children}
                      </tbody>
                    );
                  },
                  tr({ children, ...props }: any) {
                    return (
                      <tr className="hover:bg-slate-800/30 transition-colors" {...props}>
                        {children}
                      </tr>
                    );
                  },
                  th({ children, ...props }: any) {
                    return (
                      <th className="px-4 py-2.5 font-semibold text-slate-200 border-b border-slate-800 whitespace-nowrap" {...props}>
                        {children}
                      </th>
                    );
                  },
                  td({ children, ...props }: any) {
                    return (
                      <td className="px-4 py-2.5 text-slate-300 border-b border-slate-800/40 leading-relaxed" {...props}>
                        {children}
                      </td>
                    );
                  },
                  ul({ children, ...props }: any) {
                    return (
                      <ul className="list-disc list-outside ml-4 space-y-1 my-2 text-slate-200" {...props}>
                        {children}
                      </ul>
                    );
                  },
                  ol({ children, ...props }: any) {
                    return (
                      <ol className="list-decimal list-outside ml-4 space-y-1 my-2 text-slate-200" {...props}>
                        {children}
                      </ol>
                    );
                  },
                  li({ children, ...props }: any) {
                    return (
                      <li className="leading-relaxed" {...props}>
                        {children}
                      </li>
                    );
                  },
                  blockquote({ children, ...props }: any) {
                    return (
                      <blockquote className="border-l-4 border-indigo-500/60 pl-3.5 py-1.5 italic text-slate-300 my-2 bg-slate-900/40 rounded-r text-xs" {...props}>
                        {children}
                      </blockquote>
                    );
                  },
                  hr({ ...props }: any) {
                    return <hr className="border-slate-800 my-4" {...props} />;
                  },
                  a({ children, ...props }: any) {
                    return (
                      <a className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer" {...props}>
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}

            {/* Pulsing streaming indicator */}
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-indigo-400 animate-pulse rounded-xs align-middle" />
            )}

            {/* Human-in-the-Loop In-Chat Approval Card */}
            {!isUser && message.metadata_json && (() => {
              try {
                const meta = JSON.parse(message.metadata_json);
                if (!meta.approval_id) return null;
                const isApproved = approvalStatus === 'approved';
                const isRejected = approvalStatus === 'rejected';

                return (
                  <div className="mt-3 p-4 rounded-xl bg-slate-900 border border-amber-500/40 shadow-sm space-y-3">
                    <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-amber-400" />
                        <span className="text-xs font-bold text-amber-300">Action Requires Human Approval</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        Tool: {meta.tool_name || 'Action'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300">
                      The assistant requested execution of <code className="text-indigo-300 font-mono">{meta.tool_name}</code>. Please review and confirm.
                    </p>

                    {isApproved ? (
                      <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 space-y-1">
                        <div className="font-semibold flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          Approved & Executed
                        </div>
                        {approvalResult && (
                          <pre className="text-[11px] font-mono bg-slate-950 p-2 rounded max-h-24 overflow-y-auto text-emerald-200">
                            {JSON.stringify(approvalResult, null, 2)}
                          </pre>
                        )}
                      </div>
                    ) : isRejected ? (
                      <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-1.5">
                        <XCircle className="w-4 h-4 text-rose-400" />
                        Action Rejected
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => handleInChatApprove(meta.approval_id)}
                          disabled={isProcessingApproval}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer transition-colors flex items-center gap-1 shadow-sm"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {isProcessingApproval ? 'Executing...' : 'Approve & Execute'}
                        </button>
                        <button
                          onClick={() => handleInChatReject(meta.approval_id)}
                          disabled={isProcessingApproval}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 cursor-pointer transition-colors flex items-center gap-1"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                );
              } catch {
                return null;
              }
            })()}

            {/* Execution Telemetry (Cost, Latency, Fallback) */}

            {!isUser && !message.isStreaming && message.metadata_json && (() => {
              try {
                const meta = JSON.parse(message.metadata_json);
                return (
                  <div className="flex items-center gap-2 pt-1 text-[10px] text-slate-500 font-mono">
                    {meta.fallback_used && (
                      <span className="text-amber-400 bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-800">
                        Fallback Model
                      </span>
                    )}
                    {meta.pricing_category === 'free' ? (
                      <span className="text-emerald-400">100% Free ($0.00)</span>
                    ) : (
                      <span>${meta.estimated_cost_usd?.toFixed(4)}</span>
                    )}
                    {meta.latency_ms && (
                      <span>• {meta.latency_ms} ms</span>
                    )}
                  </div>
                );
              } catch {
                return null;
              }
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};
