import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { conversationService } from '../services/conversationService';
import { streamChatMessage } from '../services/chatStreamService';
import { providerService } from '../services/providerService';
import type { Conversation, ConversationSummary, Message } from '../types/chat';
import type { ModelInfo, ProviderConfigResponse } from '../types/provider';
import {
  Sparkles,
  AlertCircle,
  Menu,
  KeyRound,
  Bot,
  Terminal,
} from 'lucide-react';

interface ChatViewProps {
  onNavigateToSettings: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({ onNavigateToSettings }) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [providers, setProviders] = useState<ProviderConfigResponse[]>([]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load conversations and active provider models
  const loadConversations = useCallback(async () => {
    try {
      const list = await conversationService.listConversations();
      setConversations(list);
      return list;
    } catch (err: any) {
      setError(err?.message || 'Failed to load conversations.');
      return [];
    }
  }, []);

  const loadProviderInfo = useCallback(async () => {
    try {
      const pList = await providerService.listProviders();
      setProviders(pList);
      const active = pList.find((p) => p.is_active) || pList[0];
      if (active) {
        const mList = await providerService.listModels(active.provider_type);
        setModels(mList);
      }
    } catch {
      // Fallback silently if models cannot be fetched dynamically
    }
  }, []);

  useEffect(() => {
    loadConversations().then((list) => {
      if (list.length > 0 && !activeId) {
        selectConversation(list[0].id);
      }
    });
    loadProviderInfo();
  }, [loadConversations, loadProviderInfo]);

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation?.messages]);

  const selectConversation = async (id: string) => {
    try {
      setError(null);
      const conv = await conversationService.getConversation(id);
      setActiveConversation(conv);
      setActiveId(id);
    } catch (err: any) {
      setError(err?.message || 'Failed to load conversation.');
    }
  };

  const handleNewConversation = async () => {
    try {
      setError(null);
      const activeProvider = providers.find((p) => p.is_active);
      const model = activeProvider?.default_model || 'openai/gpt-4o-mini';

      const newConv = await conversationService.createConversation({
        title: 'New Conversation',
        model: model,
      });
      await loadConversations();
      setActiveConversation(newConv);
      setActiveId(newConv.id);
    } catch (err: any) {
      setError(err?.message || 'Failed to create conversation.');
    }
  };

  const handleRename = async (id: string, newTitle: string) => {
    try {
      await conversationService.updateConversation(id, { title: newTitle });
      await loadConversations();
      if (activeConversation && activeConversation.id === id) {
        setActiveConversation({ ...activeConversation, title: newTitle });
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to rename conversation.');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await conversationService.deleteConversation(id);
      const remaining = await loadConversations();
      if (activeId === id) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConversation(null);
          setActiveId(null);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to delete conversation.');
    }
  };

  const handleModelChange = async (newModel: string) => {
    if (!activeConversation) return;
    try {
      await conversationService.updateConversation(activeConversation.id, { model: newModel });
      setActiveConversation({ ...activeConversation, model: newModel });
      await loadConversations();
    } catch (err: any) {
      setError(err?.message || 'Failed to switch model.');
    }
  };

  const handleSendMessage = async (content: string) => {
    let currentConvId = activeId;

    // Create a new conversation if none active
    if (!currentConvId || !activeConversation) {
      try {
        const activeProvider = providers.find((p) => p.is_active);
        const model = activeProvider?.default_model || 'openai/gpt-4o-mini';
        const newConv = await conversationService.createConversation({
          title: content.slice(0, 30) + '...',
          model: model,
        });
        currentConvId = newConv.id;
        setActiveConversation(newConv);
        setActiveId(newConv.id);
        await loadConversations();
      } catch (err: any) {
        setError(err?.message || 'Failed to initialize conversation.');
        return;
      }
    }

    // Append optimistic user message
    const tempUserMessage: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: currentConvId,
      role: 'user',
      content: content,
      created_at: new Date().toISOString(),
    };

    // Prepare assistant streaming placeholder
    const streamingAssistantMessage: Message = {
      id: `temp-asst-${Date.now()}`,
      conversation_id: currentConvId,
      role: 'assistant',
      content: '',
      model: activeConversation?.model,
      created_at: new Date().toISOString(),
      isStreaming: true,
    };

    setActiveConversation((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, tempUserMessage, streamingAssistantMessage],
      };
    });

    setIsStreaming(true);
    setError(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulatedContent = '';

    await streamChatMessage(
      currentConvId,
      content,
      {
        onToken: (token) => {
          accumulatedContent += token;
          setActiveConversation((prev) => {
            if (!prev) return null;
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: accumulatedContent,
              };
            }
            return { ...prev, messages: updated };
          });
        },
        onDone: (result) => {
          setIsStreaming(false);
          abortControllerRef.current = null;
          setActiveConversation((prev) => {
            if (!prev) return null;
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                id: result.message_id,
                content: result.content,
                model: result.model,
                isStreaming: false,
              };
            }
            return { ...prev, messages: updated };
          });
          loadConversations();
        },
        onError: (streamError) => {
          setIsStreaming(false);
          abortControllerRef.current = null;
          setError(streamError);
          setActiveConversation((prev) => {
            if (!prev) return null;
            // Remove the empty streaming message if failed
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant' && !last.content) {
              updated.pop();
            } else if (last && last.role === 'assistant') {
              updated[updated.length - 1] = { ...last, isStreaming: false };
            }
            return { ...prev, messages: updated };
          });
        },
      },
      {
        model: activeConversation?.model,
        signal: controller.signal,
      }
    );
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setActiveConversation((prev) => {
        if (!prev) return null;
        const updated = [...prev.messages];
        const last = updated[updated.length - 1];
        if (last && last.role === 'assistant') {
          updated[updated.length - 1] = { ...last, isStreaming: false };
        }
        return { ...prev, messages: updated };
      });
    }
  };

  const activeProvider = providers.find((p) => p.is_active) || providers[0];
  const hasApiKey = activeProvider?.has_api_key ?? false;

  return (
    <div className="flex h-[calc(100vh-4rem)] -m-4 md:-m-8 bg-slate-950 overflow-hidden">
      {/* Conversation Thread Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={handleNewConversation}
        onRename={handleRename}
        onDelete={handleDelete}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Conversation Container */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-950">
        {/* Top Chat Header */}
        <div className="h-14 border-b border-slate-800 bg-slate-900/50 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden cursor-pointer"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="min-w-0">
              <h2 className="text-sm font-bold text-slate-100 truncate">
                {activeConversation?.title || 'Personal Assistant'}
              </h2>
            </div>
          </div>

          {/* Model Selector & Provider Status */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 text-xs">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <select
                value={activeConversation?.model || activeProvider?.default_model || 'openai/gpt-4o-mini'}
                onChange={(e) => handleModelChange(e.target.value)}
                className="bg-transparent text-slate-200 text-xs outline-none cursor-pointer"
              >
                {models.length > 0 ? (
                  models.map((m) => (
                    <option key={m.id} value={m.id} className="bg-slate-900 text-slate-200">
                      {m.name}
                    </option>
                  ))
                ) : (
                  <option value="openai/gpt-4o-mini" className="bg-slate-900 text-slate-200">
                    OpenAI: GPT-4o Mini
                  </option>
                )}
              </select>
            </div>
          </div>
        </div>

        {/* Missing API Key Alert Banner */}
        {!hasApiKey && (
          <div className="bg-amber-950/70 border-b border-amber-800/80 px-4 py-2.5 flex items-center justify-between text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>OpenRouter API Key required:</strong> Configure your API key in Settings to begin chatting with live models.
              </span>
            </div>
            <button
              onClick={onNavigateToSettings}
              className="px-2.5 py-1 rounded-md bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs transition-colors cursor-pointer shrink-0 ml-3"
            >
              Open Settings
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="bg-rose-950/70 border-b border-rose-800/80 px-4 py-2 flex items-center gap-2 text-xs text-rose-200">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="hover:text-white font-bold ml-2">
              &times;
            </button>
          </div>
        )}

        {/* Messages Stream Container */}
        <div className="flex-1 overflow-y-auto">
          {!activeConversation || activeConversation.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center max-w-xl mx-auto space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <Bot className="w-7 h-7" />
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-100">Personal AI Assistant</h3>
                <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                  Phase 1 conversational engine connected to OpenRouter. Ask questions, analyze code, or brainstorm ideas.
                </p>
              </div>

              {/* Starter Prompt Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
                <button
                  onClick={() => handleSendMessage("What can you help me with in this project?")}
                  className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:bg-slate-900 hover:border-indigo-500/40 transition-colors text-xs space-y-1 cursor-pointer group"
                >
                  <div className="flex items-center gap-2 text-indigo-400 font-medium">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Project Overview</span>
                  </div>
                  <p className="text-[11px] text-slate-400">What can you help me with in this project?</p>
                </button>

                <button
                  onClick={() => handleSendMessage("Summarize the system architecture and tech stack.")}
                  className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:bg-slate-900 hover:border-indigo-500/40 transition-colors text-xs space-y-1 cursor-pointer group"
                >
                  <div className="flex items-center gap-2 text-violet-400 font-medium">
                    <Terminal className="w-3.5 h-3.5" />
                    <span>Architecture</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Summarize the system architecture and tech stack.</p>
                </button>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-transparent">
              {activeConversation.messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Message Input Bar */}
        <ChatInput
          onSendMessage={handleSendMessage}
          isStreaming={isStreaming}
          onStopGeneration={handleStopGeneration}
          disabled={!hasApiKey && !isStreaming}
        />
      </div>
    </div>
  );
};
