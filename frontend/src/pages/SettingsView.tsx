import React, { useState, useEffect } from 'react';
import { providerService } from '../services/providerService';
import type {
  ProviderConfigResponse,
  ProviderTestResult,
  ModelInfo,
} from '../types/provider';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingState } from '../components/common/LoadingState';
import {
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Activity,
  Layers,
  Sparkles,
  Server,
  Lock,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [providers, setProviders] = useState<ProviderConfigResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('openai/gpt-4o-mini');
  const [openRouterModels, setOpenRouterModels] = useState<ModelInfo[]>([]);
  const [testResult, setTestResult] = useState<ProviderTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const pList = await providerService.listProviders();
      setProviders(pList);

      const or = pList.find((p) => p.provider_type === 'openrouter');
      if (or) {
        setSelectedModel(or.default_model);
      }

      const mList = await providerService.listModels('openrouter');
      setOpenRouterModels(mList);
    } catch (err: any) {
      setError(err?.message || 'Failed to load provider settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await providerService.testProvider('openrouter', {
        api_key: openRouterKey.trim() || undefined,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.message || 'Connection test failed',
        error: 'Network or server error',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveOpenRouter = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    setError(null);
    try {
      await providerService.saveProvider('openrouter', {
        name: 'OpenRouter',
        base_url: 'https://openrouter.ai/api/v1',
        api_key: openRouterKey.trim() || undefined,
        default_model: selectedModel,
        is_active: true,
        enabled: true,
      });
      setSaveSuccess(true);
      setOpenRouterKey('');
      await loadData();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save OpenRouter configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const openRouterConfig = providers.find((p) => p.provider_type === 'openrouter');

  if (loading) {
    return <LoadingState message="Loading provider configurations..." />;
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Title */}
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-white">AI Provider Settings</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure model providers, manage API credentials, and select default reasoning models.
        </p>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-900/50 bg-rose-950/40 text-xs text-rose-300 flex items-center gap-3">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {saveSuccess && (
        <div className="p-4 rounded-xl border border-emerald-900/50 bg-emerald-950/40 text-xs text-emerald-300 flex items-center gap-3">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>Configuration saved securely! Credentials encrypted at rest with master key.</span>
        </div>
      )}

      {/* Primary Implemented Provider: OpenRouter */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">OpenRouter</h2>
                <StatusBadge
                  status={openRouterConfig?.has_api_key ? 'active' : 'warning'}
                  label={openRouterConfig?.has_api_key ? 'Configured' : 'Key Required'}
                  size="sm"
                />
                {openRouterConfig?.is_active && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Active Provider
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Unified gateway to 100+ LLMs (OpenAI, Anthropic, Meta, Google, DeepSeek) through one API.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* API Key Input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              OpenRouter API Key
            </label>
            <div className="relative flex items-center max-w-xl">
              <input
                type={showKey ? 'text' : 'password'}
                value={openRouterKey}
                onChange={(e) => setOpenRouterKey(e.target.value)}
                placeholder={
                  openRouterConfig?.has_api_key
                    ? `Configured (${openRouterConfig.masked_api_key}) — Enter new key to update`
                    : 'sk-or-v1-...'
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 pr-10 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/40 outline-none font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 p-1 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-emerald-400" />
              <span>Keys are encrypted with Fernet symmetric encryption and never returned in plaintext.</span>
            </p>
          </div>

          {/* Model Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              Default Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full max-w-xl bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-indigo-500/80 outline-none cursor-pointer"
            >
              {openRouterModels.map((m) => (
                <option key={m.id} value={m.id} className="bg-slate-900">
                  {m.name} ({m.id})
                </option>
              ))}
            </select>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={handleTestConnection}
              disabled={isTesting}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors cursor-pointer disabled:opacity-50"
            >
              <Activity className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin text-indigo-400' : ''}`} />
              <span>{isTesting ? 'Testing connection...' : 'Test Connection'}</span>
            </button>

            <button
              onClick={handleSaveOpenRouter}
              disabled={isSaving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-sm cursor-pointer disabled:opacity-50"
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>

          {/* Connection Test Diagnostics Result */}
          {testResult && (
            <div
              className={`p-3.5 rounded-lg border text-xs max-w-xl ${
                testResult.success
                  ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-300'
                  : 'bg-rose-950/30 border-rose-800/60 text-rose-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                )}
                <span className="font-semibold">{testResult.message}</span>
                {testResult.latency_ms && (
                  <span className="text-[11px] opacity-80">({testResult.latency_ms} ms)</span>
                )}
              </div>
              {testResult.error && (
                <p className="mt-1 text-[11px] font-mono opacity-90">{testResult.error}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Prepared Future Providers: NVIDIA and Ollama */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Future AI Providers (Prepared in Architecture)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* NVIDIA NIM */}
          <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400">
                  <Server className="w-4 h-4" />
                </div>
                <span className="text-sm font-bold text-white">NVIDIA NIM</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-500 border border-slate-800">
                Prepared
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enterprise AI inference endpoints powered by NVIDIA accelerated compute infrastructure.
            </p>
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
              <span>Adapter Status:</span>
              <span className="text-slate-400 font-mono">Stub Prepared (Phase 1.x)</span>
            </div>
          </div>

          {/* Ollama Local */}
          <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-violet-950/60 border border-violet-800/40 flex items-center justify-center text-violet-400">
                  <Layers className="w-4 h-4" />
                </div>
                <span className="text-sm font-bold text-white">Ollama (Local Edge)</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-500 border border-slate-800">
                Prepared
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Run open weights models locally on your GPU/CPU with zero data transmission to cloud providers.
            </p>
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
              <span>Adapter Status:</span>
              <span className="text-slate-400 font-mono">Stub Prepared (Phase 1.x)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
