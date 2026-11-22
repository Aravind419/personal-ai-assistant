import React, { useState, useEffect } from 'react';
import { providerService } from '../services/providerService';
import { modelService } from '../services/modelService';
import { personalityService } from '../services/personalityService';
import type {
  ProviderConfigResponse,
  ProviderTestResult,
  CentralModelInfo,
  ModelPolicyResponse,
  ModelUsageSummary,
  ModelMode,
} from '../types/provider';
import type { AssistantPersonalityConfig } from '../types/personality';
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
  ShieldCheck,
  Coins,
  Cpu,
  Sliders,
  DollarSign,
  Bot,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [providers, setProviders] = useState<ProviderConfigResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testResult, setTestResult] = useState<ProviderTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSavingProvider, setIsSavingProvider] = useState(false);
  const [providerSaveSuccess, setProviderSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Model Policy State
  const [modelPolicy, setModelPolicy] = useState<ModelPolicyResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<ModelMode>('free_only');
  const [selectedModel, setSelectedModel] = useState<string>('nvidia/nemotron-3.5-lightning:free');
  const [enableFallback, setEnableFallback] = useState<boolean>(true);
  const [maxCostPerRequest, setMaxCostPerRequest] = useState<number>(0.05);
  const [isSavingPolicy, setIsSavingPolicy] = useState(false);
  const [policySaveSuccess, setPolicySaveSuccess] = useState(false);

  // Catalog & Metrics State
  const [catalogModels, setCatalogModels] = useState<CentralModelInfo[]>([]);
  const [catalogFilter, setCatalogFilter] = useState<'all' | 'free' | 'paid'>('all');
  const [metrics, setMetrics] = useState<ModelUsageSummary | null>(null);

  // Personality State
  const [personality, setPersonality] = useState<AssistantPersonalityConfig>({
    name: 'Personal AI Assistant',
    communication_style: 'natural',
    formality: 'balanced',
    detail_level: 'balanced',
    memory_usage: 'natural_weave',
    emoji_usage: 'minimal',
    custom_instructions: '',
  });
  const [isSavingPersonality, setIsSavingPersonality] = useState(false);
  const [personalitySaveSuccess, setPersonalitySaveSuccess] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [pList, policy, catalog, usage, personCfg] = await Promise.all([
        providerService.listProviders(),
        modelService.getModelPolicy(),
        modelService.listModels(),
        modelService.getModelMetrics().catch(() => null),
        personalityService.getPersonality().catch(() => null),
      ]);

      setProviders(pList);
      setModelPolicy(policy);
      setSelectedMode(policy.model_mode);
      setSelectedModel(policy.selected_model);
      setEnableFallback(policy.enable_fallback);
      setMaxCostPerRequest(policy.max_cost_per_request);
      setCatalogModels(catalog);
      setMetrics(usage);
      if (personCfg) {
        setPersonality(personCfg);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load system settings.');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePersonality = async () => {
    setIsSavingPersonality(true);
    setPersonalitySaveSuccess(false);
    setError(null);
    try {
      const updated = await personalityService.updatePersonality(personality);
      setPersonality(updated);
      setPersonalitySaveSuccess(true);
      setTimeout(() => setPersonalitySaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to update assistant personality.');
    } finally {
      setIsSavingPersonality(false);
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
    setIsSavingProvider(true);
    setProviderSaveSuccess(false);
    setError(null);
    try {
      if (!openRouterKey.trim() && !openRouterConfig?.has_api_key) {
        setError('Please enter a valid OpenRouter API key before saving.');
        setIsSavingProvider(false);
        return;
      }
      await providerService.saveProvider('openrouter', {
        name: 'OpenRouter',
        base_url: 'https://openrouter.ai/api/v1',
        api_key: openRouterKey.trim() || undefined,
        default_model: selectedModel,
        is_active: true,
        enabled: true,
      });
      setProviderSaveSuccess(true);
      setOpenRouterKey('');
      await loadData();
      setTimeout(() => setProviderSaveSuccess(false), 4000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save OpenRouter configuration.');
    } finally {
      setIsSavingProvider(false);
    }
  };

  const handleSaveModelPolicy = async () => {
    setIsSavingPolicy(true);
    setPolicySaveSuccess(false);
    setError(null);
    try {
      const updated = await modelService.updateModelPolicy({
        model_mode: selectedMode,
        selected_model: selectedModel,
        enable_fallback: enableFallback,
        max_cost_per_request: maxCostPerRequest,
      });
      setModelPolicy(updated);
      setSelectedModel(updated.selected_model);
      setPolicySaveSuccess(true);
      setTimeout(() => setPolicySaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save model policy.');
    } finally {
      setIsSavingPolicy(false);
    }
  };

  const openRouterConfig = providers.find((p) => p.provider_type === 'openrouter');

  const filteredCatalog = catalogModels.filter((m) => {
    if (catalogFilter === 'free') return m.pricing_category === 'free';
    if (catalogFilter === 'paid') return m.pricing_category === 'paid';
    return true;
  });

  if (loading) {
    return <LoadingState message="Loading provider and model policy configurations..." />;
  }

  return (
    <div className="space-y-8 max-w-5xl pb-12">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-white">AI Model & Provider Architecture</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure provider gateways, operational modes (Free-Only vs Paid), model fallback chains, and cost guardrails.
        </p>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-900/50 bg-rose-950/40 text-xs text-rose-300 flex items-center gap-3">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Model Policy & Cost Control Guardrails */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>Model Execution Policy & Modes</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  {selectedMode === 'free_only' ? 'Free-Only Active' : selectedMode === 'paid_enabled' ? 'Paid-Enabled' : 'Manual Lock'}
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Never automatically incurs paid model charges when Free-Only mode is active.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-6">
          {/* Operational Mode Radios */}
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Operational Mode
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Free-Only */}
              <div
                onClick={() => setSelectedMode('free_only')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedMode === 'free_only'
                    ? 'border-emerald-500 bg-emerald-950/20 shadow-sm shadow-emerald-900/20'
                    : 'border-slate-800 bg-slate-950/30 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Coins className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-white">Free-Only (Default)</span>
                  </div>
                  <input
                    type="radio"
                    name="model_mode"
                    checked={selectedMode === 'free_only'}
                    onChange={() => setSelectedMode('free_only')}
                    className="accent-emerald-500"
                  />
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Strictly allows only free AI models. Paid models and paid fallbacks are blocked with 100% guarantee.
                </p>
              </div>

              {/* Paid-Enabled */}
              <div
                onClick={() => setSelectedMode('paid_enabled')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedMode === 'paid_enabled'
                    ? 'border-indigo-500 bg-indigo-950/20 shadow-sm shadow-indigo-900/20'
                    : 'border-slate-800 bg-slate-950/30 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-white">Paid-Enabled</span>
                  </div>
                  <input
                    type="radio"
                    name="model_mode"
                    checked={selectedMode === 'paid_enabled'}
                    onChange={() => setSelectedMode('paid_enabled')}
                    className="accent-indigo-500"
                  />
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Access flagship commercial models (Claude 3.5 Sonnet, GPT-4o) with strict cost caps and fallback guards.
                </p>
              </div>

              {/* Manual Selection */}
              <div
                onClick={() => setSelectedMode('manual')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedMode === 'manual'
                    ? 'border-amber-500 bg-amber-950/20 shadow-sm shadow-amber-900/20'
                    : 'border-slate-800 bg-slate-950/30 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold text-white">Manual Selection</span>
                  </div>
                  <input
                    type="radio"
                    name="model_mode"
                    checked={selectedMode === 'manual'}
                    onChange={() => setSelectedMode('manual')}
                    className="accent-amber-500"
                  />
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Locks strictly to your chosen model. Automatic fallback to other models is disabled.
                </p>
              </div>
            </div>
          </div>

          {/* Model Selection and Cost Cap Inputs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2 border-t border-slate-800/80">
            {/* Preferred Model */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Primary Selected Model
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-indigo-500/80 outline-none cursor-pointer"
              >
                {catalogModels
                  .filter((m) => selectedMode !== 'free_only' || m.pricing_category === 'free')
                  .map((m) => (
                    <option key={m.id} value={m.id} className="bg-slate-900">
                      {m.pricing_category === 'free' ? '🟢 [Free] ' : '💎 [Paid] '}
                      {m.name} ({m.id})
                    </option>
                  ))}
              </select>
              <p className="text-[11px] text-slate-500">
                {selectedMode === 'free_only'
                  ? 'Showing free models only. Switch to Paid-Enabled to select premium models.'
                  : 'All free and premium models available.'}
              </p>
            </div>

            {/* Per-Request Max Cost Limit */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Max Cost Ceiling Per Request (USD)
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-mono">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={maxCostPerRequest}
                  onChange={(e) => setMaxCostPerRequest(parseFloat(e.target.value) || 0)}
                  disabled={selectedMode === 'free_only'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-indigo-500/80 outline-none font-mono disabled:opacity-40"
                />
              </div>
              <p className="text-[11px] text-slate-500">
                {selectedMode === 'free_only'
                  ? 'Fixed at $0.00 in Free-Only mode.'
                  : 'Rejects requests expected to exceed this cost threshold.'}
              </p>
            </div>
          </div>

          {/* Fallback Chain Controls */}
          <div className="space-y-2 pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-300">Automatic Fallback Chain</span>
                <p className="text-[11px] text-slate-400">
                  When primary model encounters rate limits (429) or provider outages, automatically switches to next candidate.
                </p>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableFallback && selectedMode !== 'manual'}
                  disabled={selectedMode === 'manual'}
                  onChange={(e) => setEnableFallback(e.target.checked)}
                  className="accent-indigo-500 rounded"
                />
                <span className="text-xs text-slate-300 font-medium">Enable Fallback</span>
              </label>
            </div>

            {enableFallback && selectedMode !== 'manual' && modelPolicy?.fallback_models && (
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs space-y-1.5">
                <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
                  Configured Fallback Priority Order:
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {modelPolicy.fallback_models.map((fb, i) => (
                    <div key={fb} className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-[11px] text-slate-300">
                      <span className="text-slate-500 font-mono">#{i + 1}</span>
                      <span className="font-mono">{fb}</span>
                      {selectedMode === 'free_only' && (
                        <span className="text-[9px] text-emerald-400 bg-emerald-950/60 px-1 rounded">Free</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Save Policy Button */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSaveModelPolicy}
              disabled={isSavingPolicy}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors shadow-sm cursor-pointer disabled:opacity-50"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{isSavingPolicy ? 'Saving Policy...' : 'Save Model Policy'}</span>
            </button>
            {policySaveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Policy updated and active!</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Assistant Identity & Personality Controls */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>Assistant Identity & Conversational Personality</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                  Anti-Robotic Harness Active
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Controls communication style, formality, memory integration, and tone without robotic meta-announcements.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {/* Assistant Name */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Assistant Name</label>
              <input
                type="text"
                value={personality.name}
                onChange={(e) => setPersonality({ ...personality, name: e.target.value })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                placeholder="Personal AI Assistant"
              />
            </div>

            {/* Communication Style */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Communication Style</label>
              <select
                value={personality.communication_style}
                onChange={(e) => setPersonality({ ...personality, communication_style: e.target.value as any })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="natural">Natural & Conversational (Default)</option>
                <option value="concise">Concise & Direct</option>
                <option value="technical">Technical & Architectural</option>
                <option value="detailed">Detailed & Comprehensive</option>
              </select>
            </div>

            {/* Formality Level */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Formality Level</label>
              <select
                value={personality.formality}
                onChange={(e) => setPersonality({ ...personality, formality: e.target.value as any })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="balanced">Balanced (Default)</option>
                <option value="casual">Casual & Relaxed</option>
                <option value="formal">Formal & Structured</option>
              </select>
            </div>

            {/* Detail Level */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Detail Level</label>
              <select
                value={personality.detail_level}
                onChange={(e) => setPersonality({ ...personality, detail_level: e.target.value as any })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="balanced">Balanced (Default)</option>
                <option value="concise">Concise</option>
                <option value="in_depth">In-Depth Explanations</option>
              </select>
            </div>

            {/* Memory Usage Mode */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Memory Integration</label>
              <select
                value={personality.memory_usage}
                onChange={(e) => setPersonality({ ...personality, memory_usage: e.target.value as any })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="natural_weave">Natural Weave (Zero Announcements)</option>
                <option value="minimal">Minimal (Only When Essential)</option>
                <option value="explicit">Explicit Acknowledgment</option>
              </select>
            </div>

            {/* Emoji Usage */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">Emoji Usage</label>
              <select
                value={personality.emoji_usage}
                onChange={(e) => setPersonality({ ...personality, emoji_usage: e.target.value as any })}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="minimal">Minimal (Context-Appropriate)</option>
                <option value="none">Strictly None</option>
                <option value="expressive">Expressive</option>
              </select>
            </div>
          </div>

          {/* Custom Persona Instructions */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-300">Custom Behavioral Guidelines</label>
            <textarea
              value={personality.custom_instructions || ''}
              onChange={(e) => setPersonality({ ...personality, custom_instructions: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
              placeholder="e.g. Prefer TypeScript examples, emphasize modular design, keep explanations focused on production standards."
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSavePersonality}
              disabled={isSavingPersonality}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-colors shadow-sm cursor-pointer disabled:opacity-50"
            >
              <Bot className="w-3.5 h-3.5" />
              <span>{isSavingPersonality ? 'Saving Personality...' : 'Save Personality Settings'}</span>
            </button>
            {personalitySaveSuccess && (
              <span className="text-xs text-cyan-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Personality settings updated!</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 3. Primary Implemented Gateway: OpenRouter */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">OpenRouter Unified Gateway</h2>
                <StatusBadge
                  status={openRouterConfig?.has_api_key ? 'active' : 'warning'}
                  label={openRouterConfig?.has_api_key ? 'Key Configured' : 'Key Optional for Free Models'}
                  size="sm"
                />
                {openRouterConfig?.is_active && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Active Gateway
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Single unified API accessing 100+ open-weights, free, and commercial models.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Active Key Status Card */}
          {openRouterConfig?.has_api_key ? (
            <div className="flex items-center justify-between p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 max-w-xl">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-emerald-900/60 border border-emerald-700/60 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-emerald-200 flex items-center gap-2">
                    <span>API Key Configured & Active</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700/60 font-medium">
                      Encrypted in Database
                    </span>
                  </div>
                  <div className="text-[11px] text-emerald-400 font-mono mt-0.5">
                    {openRouterConfig.masked_api_key}
                  </div>
                </div>
              </div>
              <span className="text-[11px] text-emerald-400/90 font-medium hidden sm:inline">Ready for requests</span>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 p-3 rounded-lg bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300 max-w-xl">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>No API key configured. Enter your OpenRouter key below to access models.</span>
            </div>
          )}

          {/* API Key Input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              {openRouterConfig?.has_api_key ? 'Update OpenRouter API Key (Optional)' : 'OpenRouter API Key'}
            </label>
            <div className="relative flex items-center max-w-xl">
              <input
                type={showKey ? 'text' : 'password'}
                value={openRouterKey}
                onChange={(e) => setOpenRouterKey(e.target.value)}
                placeholder={
                  openRouterConfig?.has_api_key
                    ? `Key active (${openRouterConfig.masked_api_key}) — Enter new key to replace`
                    : 'sk-or-v1-...'
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 pr-10 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/40 outline-none font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 p-1 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
                title={showKey ? "Hide input" : "Show input"}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-emerald-400" />
              <span>
                {openRouterConfig?.has_api_key
                  ? 'Your key is securely saved in the database. Leave input blank to keep the active key.'
                  : 'Keys are encrypted with Fernet symmetric cipher at rest and never exposed to the frontend.'}
              </span>
            </p>
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
              disabled={isSavingProvider}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-sm cursor-pointer disabled:opacity-50"
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>{isSavingProvider ? 'Saving...' : 'Save Gateway Credentials'}</span>
            </button>

            {providerSaveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Credentials saved securely!</span>
              </span>
            )}
          </div>

          {/* Connection Diagnostics Result */}
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

      {/* 3. Usage, Cost & Telemetry Analytics */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/40 flex items-center justify-center text-violet-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Token Usage & Estimated Cost Analytics</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time tracking of prompt tokens, completion tokens, costs in USD, and latency across all model calls.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Tokens</span>
              <p className="text-xl font-bold font-mono text-white">
                {metrics?.total_tokens ? metrics.total_tokens.toLocaleString() : '0'}
              </p>
              <span className="text-[10px] text-slate-500">
                {metrics?.total_prompt_tokens.toLocaleString() || '0'} prompt / {metrics?.total_completion_tokens.toLocaleString() || '0'} comp
              </span>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Estimated Cost</span>
              <p className="text-xl font-bold font-mono text-emerald-400">
                ${metrics?.total_estimated_cost_usd !== undefined ? metrics.total_estimated_cost_usd.toFixed(4) : '0.0000'}
              </p>
              <span className="text-[10px] text-slate-500">Free models billed at $0.00</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Requests</span>
              <p className="text-xl font-bold font-mono text-white">
                {metrics?.total_requests || 0}
              </p>
              <span className="text-[10px] text-emerald-400">
                {metrics?.successful_requests || 0} ok
                {metrics?.fallback_requests ? ` • ${metrics.fallback_requests} fallbacks` : ''}
              </span>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Latency</span>
              <p className="text-xl font-bold font-mono text-slate-200">
                {metrics?.average_latency_ms ? `${metrics.average_latency_ms.toFixed(0)} ms` : '—'}
              </p>
              <span className="text-[10px] text-slate-500">End-to-end response time</span>
            </div>
          </div>

          {/* Model Breakdown Table */}
          {metrics?.model_breakdown && metrics.model_breakdown.length > 0 && (
            <div className="space-y-2 pt-2">
              <span className="text-xs font-semibold text-slate-300">Performance By Model</span>
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-medium">
                    <tr>
                      <th className="py-2 px-3">Model</th>
                      <th className="py-2 px-3">Category</th>
                      <th className="py-2 px-3">Requests</th>
                      <th className="py-2 px-3">Tokens</th>
                      <th className="py-2 px-3">Estimated Cost</th>
                      <th className="py-2 px-3">Avg Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {metrics.model_breakdown.map((row) => (
                      <tr key={row.model_id} className="hover:bg-slate-800/20">
                        <td className="py-2 px-3 text-slate-200">{row.model_id}</td>
                        <td className="py-2 px-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            row.pricing_category === 'free'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                          }`}>
                            {row.pricing_category.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-slate-300">{row.requests}</td>
                        <td className="py-2 px-3 text-slate-300">{row.total_tokens.toLocaleString()}</td>
                        <td className="py-2 px-3 text-emerald-400">${row.estimated_cost_usd.toFixed(6)}</td>
                        <td className="py-2 px-3 text-slate-400">{row.avg_latency_ms ? `${row.avg_latency_ms} ms` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 4. Central Model Registry Explorer */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-600/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Central Model Registry</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Catalog of curated free models and optional paid models with context limits and capability tags.
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setCatalogFilter('all')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                catalogFilter === 'all' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({catalogModels.length})
            </button>
            <button
              onClick={() => setCatalogFilter('free')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                catalogFilter === 'free' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Free Models
            </button>
            <button
              onClick={() => setCatalogFilter('paid')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                catalogFilter === 'paid' ? 'bg-indigo-950 text-indigo-300 border border-indigo-800' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Paid Models
            </button>
          </div>
        </div>

        <div className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCatalog.map((model) => (
              <div
                key={model.id}
                className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-2.5 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white truncate pr-2">{model.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      model.pricing_category === 'free'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                    }`}
                  >
                    {model.pricing_category === 'free' ? '100% Free' : 'Commercial'}
                  </span>
                </div>

                <p className="text-[11px] font-mono text-slate-400 truncate">{model.id}</p>

                {model.description && (
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {model.description}
                  </p>
                )}

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                  <span>Context: {(model.context_limit / 1000).toFixed(0)}k tokens</span>
                  <span>
                    {model.pricing_category === 'free'
                      ? '$0.00 / 1M'
                      : `$${model.cost_per_million_input} in / $${model.cost_per_million_output} out`}
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {model.supported_capabilities.map((cap) => (
                    <span key={cap} className="px-1.5 py-0.5 rounded text-[9px] bg-slate-900 border border-slate-800 text-slate-400">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 5. Prepared Future Providers: NVIDIA and Ollama */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Modular Provider Integrations (Prepared in Architecture)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* NVIDIA NIM */}
          <div className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400">
                  <Server className="w-4 h-4" />
                </div>
                <span className="text-sm font-bold text-white">NVIDIA NIM Direct API</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-500 border border-slate-800">
                Prepared
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Direct enterprise inference endpoints powered by NVIDIA accelerated compute infrastructure.
            </p>
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
              <span>Adapter Interface:</span>
              <span className="text-slate-400 font-mono">BaseLLMProvider Ready</span>
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
              Run open weights models locally on your GPU/CPU with zero external cloud transmission.
            </p>
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
              <span>Adapter Interface:</span>
              <span className="text-slate-400 font-mono">BaseLLMProvider Ready</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
