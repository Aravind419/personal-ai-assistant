import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { conversationService } from '../services/conversationService';
import { streamChatMessage } from '../services/chatStreamService';
import { providerService } from '../services/providerService';
import { modelService } from '../services/modelService';
import { voiceService } from '../services/voiceService';
import type { Conversation, ConversationSummary, Message } from '../types/chat';
import type { ProviderConfigResponse, CentralModelInfo, ModelPolicyResponse } from '../types/provider';
import type { VoicePreferences } from '../types/voice';
import {
  Sparkles,
  AlertCircle,
  Menu,
  KeyRound,
  ShieldCheck,
  Coins,
  ArrowRightLeft,
  Volume2,
  X,
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
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [toolNotice, setToolNotice] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [models, setModels] = useState<CentralModelInfo[]>([]);
  const [modelPolicy, setModelPolicy] = useState<ModelPolicyResponse | null>(null);
  const [providers, setProviders] = useState<ProviderConfigResponse[]>([]);

  // Voice State & Settings
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [voicePrefs, setVoicePrefs] = useState<VoicePreferences>({
    enabled: true,
    auto_play: false,
    speed: 1.0,
    voice: null,
    language: 'en-US',
  });
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll helper
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load conversations, providers, models and policy
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

  const loadProviderAndModelInfo = useCallback(async () => {
    try {
      const [pList, mList, policy] = await Promise.all([
        providerService.listProviders(),
        modelService.listModels(),
        modelService.getModelPolicy(),
      ]);
      setProviders(pList);
      setModels(mList);
      setModelPolicy(policy);
    } catch {
      // Fallback silently if models cannot be fetched dynamically
    }
  }, []);

  // Initialize Voice state & preferences
  useEffect(() => {
    voiceService.setOnStateChange((isPlaying, msgId) => {
      setPlayingMessageId(isPlaying ? msgId : null);
    });

    voiceService.getPreferences().then((prefs) => {
      setVoicePrefs(prefs);
    });

    // Load available voices from SpeechSynthesis
    const updateVoices = () => {
      const voices = voiceService.getAvailableVoices();
      setAvailableVoices(voices);
    };

    updateVoices();
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    return () => {
      voiceService.stop();
    };
  }, []);

  useEffect(() => {
    loadConversations().then((list) => {
      if (list.length > 0 && !activeId) {
        selectConversation(list[0].id);
      }
    });
    loadProviderAndModelInfo();
  }, [loadConversations, loadProviderAndModelInfo]);

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation?.messages]);

  const selectConversation = async (id: string) => {
    try {
      setError(null);
      setFallbackNotice(null);
      voiceService.stop();
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
      setFallbackNotice(null);
      voiceService.stop();
      const defaultModel = modelPolicy?.selected_model || 'nvidia/nemotron-3.5-lightning:free';
      const newConv = await conversationService.createConversation({
        title: 'New Conversation',
        model: defaultModel,
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
      if (activeConversation?.id === id) {
        setActiveConversation({ ...activeConversation, title: newTitle });
      }
      await loadConversations();
    } catch (err: any) {
      setError(err?.message || 'Failed to rename conversation.');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      voiceService.stop();
      await conversationService.deleteConversation(id);
      if (activeId === id) {
        setActiveConversation(null);
        setActiveId(null);
      }
      const list = await loadConversations();
      if (list.length > 0) {
        selectConversation(list[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to delete conversation.');
    }
  };

  const handleModelChange = async (newModel: string) => {
    if (!activeConversation) return;

    if (modelPolicy?.model_mode === 'free_only') {
      const target = models.find((m) => m.id === newModel);
      if (target && target.pricing_category === 'paid') {
        setError(`Cannot switch to paid model '${target.name}'. Free-Only mode is active. Enable Paid models in Settings.`);
        return;
      }
    }

    try {
      setError(null);
      await conversationService.updateConversation(activeConversation.id, { model: newModel });
      setActiveConversation({ ...activeConversation, model: newModel });
      await loadConversations();
    } catch (err: any) {
      setError(err?.message || 'Failed to switch model.');
    }
  };

  // Voice Toggle Play/Stop
  const handleToggleAudio = (message: Message) => {
    if (playingMessageId === message.id) {
      voiceService.stop();
    } else {
      voiceService.speak(message.id, message.content, voicePrefs);
    }
  };

  const handleSaveVoicePrefs = async (updated: VoicePreferences) => {
    setVoicePrefs(updated);
    await voiceService.updatePreferences(updated);
  };

  const handleSendMessage = async (content: string) => {
    let currentConvId = activeId;

    if (!currentConvId) {
      try {
        const defaultModel = modelPolicy?.selected_model || 'nvidia/nemotron-3.5-lightning:free';
        const newConv = await conversationService.createConversation({
          title: content.slice(0, 30),
          model: defaultModel,
        });
        await loadConversations();
        setActiveConversation(newConv);
        setActiveId(newConv.id);
        currentConvId = newConv.id;
      } catch (err: any) {
        setError(err?.message || 'Failed to initialize conversation.');
        return;
      }
    }

    // Append optimistic user message
    const tempUserMsg: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: currentConvId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    // Append optimistic streaming placeholder
    const tempAssistantMsg: Message = {
      id: `temp-assistant-${Date.now()}`,
      conversation_id: currentConvId,
      role: 'assistant',
      content: '',
      model: activeConversation?.model || modelPolicy?.selected_model,
      created_at: new Date().toISOString(),
      isStreaming: true,
    };

    setActiveConversation((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, tempUserMsg, tempAssistantMsg],
      };
    });

    setIsStreaming(true);
    setError(null);
    setFallbackNotice(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    await streamChatMessage(
      currentConvId,
      content,
      {
        onToken: (token) => {
          setActiveConversation((prev) => {
            if (!prev) return null;
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
                isStreaming: true,
              };
            }
            return { ...prev, messages: updated };
          });
        },
        onNotice: (notice) => {
          setFallbackNotice(notice);
        },
        onAssistantStatus: (st) => {
          setToolNotice(st.status);
        },
        onToolExecutionStarted: (evt) => {
          setToolNotice(`Running: ${evt.tool_name}...`);
        },
        onToolExecutionCompleted: (evt) => {
          setToolNotice(
            evt.success
              ? `✓ ${evt.tool_name} completed in ${evt.duration_ms ?? 0}ms`
              : `⚠ ${evt.tool_name} failed`
          );
          setTimeout(() => setToolNotice(null), 3500);
        },
        onToolCall: (call) => {
          setToolNotice(`Calling ${call.display_name || call.tool}...`);
        },
        onToolResult: (res) => {
          setToolNotice(
            res.success
              ? `✓ ${res.display_name || res.tool} succeeded`
              : `⚠ ${res.display_name || res.tool} failed`
          );
          setTimeout(() => setToolNotice(null), 3500);
        },
        onApprovalRequired: (app) => {
          setToolNotice(`Action requires approval: ${app.display_name || app.tool}`);
        },
        onResetBuffer: () => {
          setActiveConversation((prev) => {
            if (!prev) return null;
            const updated = [...prev.messages];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: '',
                isStreaming: true,
              };
            }
            return { ...prev, messages: updated };
          });
        },
        onDone: (result) => {
          setIsStreaming(false);
          setToolNotice(null);
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
                metadata_json: JSON.stringify({
                  estimated_cost_usd: result.estimated_cost_usd,
                  pricing_category: result.pricing_category,
                  latency_ms: result.latency_ms,
                  fallback_used: result.fallback_used,
                  approval_id: result.approval_id,
                }),
                isStreaming: false,
              };
            }
            return { ...prev, messages: updated };
          });
          loadConversations();


          // Auto-play if enabled in preferences
          if (voicePrefs.enabled && voicePrefs.auto_play && result.content) {
            voiceService.speak(result.message_id, result.content, voicePrefs);
          }
        },
        onError: (streamError) => {
          setIsStreaming(false);
          abortControllerRef.current = null;
          setError(streamError);
          setActiveConversation((prev) => {
            if (!prev) return null;
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

  // Regenerate last assistant response
  const handleRegenerate = () => {
    if (!activeConversation || isStreaming) return;
    const messages = activeConversation.messages;
    const lastUserIndex = [...messages].reverse().findIndex((m) => m.role === 'user');
    if (lastUserIndex === -1) return;

    const actualUserIndex = messages.length - 1 - lastUserIndex;
    const userMessage = messages[actualUserIndex];
    if (userMessage) {
      handleSendMessage(userMessage.content);
    }
  };

  const activeProvider = providers.find((p) => p.is_active) || providers[0];
  const hasApiKey = activeProvider?.has_api_key ?? false;

  const freeModels = models.filter((m) => m.pricing_category === 'free');
  const paidModels = models.filter((m) => m.pricing_category === 'paid');

  const currentModelId = activeConversation?.model || modelPolicy?.selected_model || 'nvidia/nemotron-3.5-lightning:free';
  const currentModelMeta = models.find((m) => m.id === currentModelId);

  // Find index of last assistant message for regenerate action
  const lastAssistantIndex = activeConversation
    ? [...activeConversation.messages].map((m) => m.role).lastIndexOf('assistant')
    : -1;

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

          {/* Voice Settings & Model Selector */}
          <div className="flex items-center gap-2">
            {/* Voice Audio Settings Button */}
            <button
              onClick={() => setIsVoiceModalOpen(true)}
              className={`p-2 rounded-lg border text-xs flex items-center gap-1.5 transition-colors cursor-pointer ${
                voicePrefs.enabled
                  ? 'bg-indigo-950/40 border-indigo-700/50 text-indigo-300 hover:bg-indigo-900/50'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
              title="Voice Settings (Speech Input & Output)"
            >
              <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden md:inline font-medium">Voice</span>
            </button>

            {/* Operational Mode Pill */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border bg-slate-950 border-slate-800">
              {modelPolicy?.model_mode === 'free_only' ? (
                <>
                  <Coins className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Free-Only Mode</span>
                </>
              ) : modelPolicy?.model_mode === 'paid_enabled' ? (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="text-indigo-400">Paid-Enabled (${modelPolicy?.max_cost_per_request}/req)</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-amber-400">Manual Model Lock</span>
                </>
              )}
            </div>

            {/* Model Selector Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 text-xs">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <select
                value={currentModelId}
                onChange={(e) => handleModelChange(e.target.value)}
                className="bg-transparent text-slate-200 text-xs outline-none cursor-pointer max-w-[180px] sm:max-w-[260px] truncate"
              >
                <optgroup label="Free Models (Zero Cost)">
                  {freeModels.map((m) => (
                    <option key={m.id} value={m.id} className="bg-slate-900 text-slate-200">
                      🟢 {m.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Paid / Premium Models">
                  {paidModels.map((m) => (
                    <option
                      key={m.id}
                      value={m.id}
                      disabled={modelPolicy?.model_mode === 'free_only'}
                      className={`bg-slate-900 ${
                        modelPolicy?.model_mode === 'free_only' ? 'text-slate-500' : 'text-slate-200'
                      }`}
                    >
                      💎 {m.name} {modelPolicy?.model_mode === 'free_only' ? '(Locked: Free-Only)' : ''}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
          </div>
        </div>

        {/* Fallback Notice Banner */}
        {fallbackNotice && (
          <div className="bg-amber-950/60 border-b border-amber-800/60 px-4 py-2 flex items-center justify-between text-xs text-amber-300">
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-amber-400 shrink-0" />
              <span>{fallbackNotice}</span>
            </div>
            <button
              onClick={() => setFallbackNotice(null)}
              className="text-amber-400 hover:text-amber-200 text-[11px] underline cursor-pointer ml-3"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Missing API Key Alert Banner */}
        {!hasApiKey && (
          <div className="bg-amber-950/70 border-b border-amber-800/80 px-4 py-2.5 flex items-center justify-between text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>OpenRouter Gateway:</strong> Add your OpenRouter API key in Settings to execute completions across free and commercial models.
              </span>
            </div>
            <button
              onClick={onNavigateToSettings}
              className="px-2.5 py-1 rounded-md bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs transition-colors cursor-pointer shrink-0 ml-3"
            >
              Configure Gateway
            </button>
          </div>
        )}

        {/* Global Error Banner */}
        {error && (
          <div className="bg-rose-950/80 border-b border-rose-900/60 px-4 py-2 flex items-center justify-between text-xs text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-400 hover:text-rose-200 text-[11px] underline cursor-pointer ml-3"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Message Thread Viewport */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {!activeConversation || activeConversation.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto px-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4 shadow-lg shadow-indigo-950/40">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">Provider-Independent AI Assistant</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                {modelPolicy?.model_mode === 'free_only'
                  ? 'Free-Only mode is active. Chat using text or microphone voice input with natural formatting and real-time streaming.'
                  : 'Start a conversation with your configured AI provider and preferred model.'}
              </p>
              {currentModelMeta && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-300 font-mono">
                  <span>Current Model:</span>
                  <span className="text-indigo-300 font-semibold">{currentModelMeta.name}</span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-800">
                    {currentModelMeta.pricing_category.toUpperCase()}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <>
              {activeConversation.messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isPlayingAudio={playingMessageId === message.id}
                  onToggleAudio={() => handleToggleAudio(message)}
                  isLastAssistant={index === lastAssistantIndex}
                  onRegenerate={handleRegenerate}
                  onApprovalDecided={loadConversations}
                />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Real-time Tool Status Indicator */}
        {toolNotice && (
          <div className="mx-4 mb-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
            <span className="font-mono">{toolNotice}</span>
          </div>
        )}

        {/* Interactive Chat Input Bar with Microphone & Text Input */}

        <ChatInput
          onSendMessage={handleSendMessage}
          onStopGeneration={handleStopGeneration}
          isStreaming={isStreaming}
          disabled={false}
          placeholder={
            modelPolicy?.model_mode === 'free_only'
              ? 'Ask anything or click mic to speak (Free-Only Mode)...'
              : 'Ask anything or click mic to speak...'
          }
        />
      </div>

      {/* Voice Settings Modal */}
      {isVoiceModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative space-y-5">
            <button
              onClick={() => setIsVoiceModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
                <Volume2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">Voice Conversation Settings</h3>
                <p className="text-xs text-slate-400">Configure speech input and text-to-speech audio playback.</p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Voice Enabled Toggle */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                <div>
                  <div className="text-xs font-semibold text-slate-200">Voice Output Enabled</div>
                  <div className="text-[11px] text-slate-400">Show speaker button to read assistant responses aloud.</div>
                </div>
                <input
                  type="checkbox"
                  checked={voicePrefs.enabled}
                  onChange={(e) => handleSaveVoicePrefs({ ...voicePrefs, enabled: e.target.checked })}
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-900 border-slate-700 cursor-pointer"
                />
              </div>

              {/* Auto-Play Toggle */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                <div>
                  <div className="text-xs font-semibold text-slate-200">Auto-Play Responses</div>
                  <div className="text-[11px] text-slate-400">Automatically speak answers as soon as generation completes.</div>
                </div>
                <input
                  type="checkbox"
                  checked={voicePrefs.auto_play}
                  onChange={(e) => handleSaveVoicePrefs({ ...voicePrefs, auto_play: e.target.checked })}
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-900 border-slate-700 cursor-pointer"
                />
              </div>

              {/* Voice Selector */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Speech Voice</label>
                <select
                  value={voicePrefs.voice || ''}
                  onChange={(e) => handleSaveVoicePrefs({ ...voicePrefs, voice: e.target.value || null })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                >
                  <option value="">Default System Voice</option>
                  {availableVoices.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name} ({v.lang})
                    </option>
                  ))}
                </select>
              </div>

              {/* Speech Speed Slider */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-300">Speech Speed</span>
                  <span className="font-mono text-indigo-400">{voicePrefs.speed}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={voicePrefs.speed}
                  onChange={(e) => handleSaveVoicePrefs({ ...voicePrefs, speed: parseFloat(e.target.value) })}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>0.5x Slower</span>
                  <span>1.0x Normal</span>
                  <span>2.0x Faster</span>
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setIsVoiceModalOpen(false)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
