import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../../types/chat';
import { Bot, User, Copy, Check, Sparkles } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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

            {/* Copy button */}
            {!isUser && message.content && (
              <button
                onClick={handleCopy}
                className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
                title="Copy message"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>

          {/* Message Body */}
          <div className="text-sm text-slate-200 leading-relaxed break-words prose prose-invert prose-sm max-w-none">
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
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
                      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden my-3">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-slate-950/70 border-b border-slate-800 text-xs font-mono text-slate-400">
                          <span>{match ? match[1] : 'code'}</span>
                          <button
                            onClick={() => navigator.clipboard.writeText(codeString)}
                            className="inline-flex items-center gap-1 hover:text-slate-200 cursor-pointer"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy</span>
                          </button>
                        </div>
                        <pre className="p-3 text-xs font-mono overflow-x-auto text-slate-200 bg-slate-900/90">
                          <code>{codeString}</code>
                        </pre>
                      </div>
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
