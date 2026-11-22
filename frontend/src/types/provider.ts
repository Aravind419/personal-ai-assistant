export type ProviderType = 'openrouter' | 'nvidia' | 'ollama' | 'custom';

export type PricingCategory = 'free' | 'paid';
export type ModelMode = 'free_only' | 'paid_enabled' | 'manual';

export interface ModelInfo {
  id: string;
  name: string;
  context_length?: number | null;
  description?: string | null;
  pricing?: Record<string, unknown> | null;
  pricing_category?: PricingCategory;
  capabilities?: string[];
}

export interface CentralModelInfo {
  id: string;
  name: string;
  provider_type: ProviderType;
  pricing_category: PricingCategory;
  cost_per_million_input: number;
  cost_per_million_output: number;
  context_limit: number;
  supported_capabilities: string[];
  is_available: boolean;
  is_default: boolean;
  description?: string | null;
}

export interface ModelPolicyResponse {
  id: string;
  model_mode: ModelMode;
  selected_model: string;
  fallback_models: string[];
  enable_fallback: boolean;
  max_cost_per_request: number;
  monthly_budget_limit: number;
}

export interface ModelPolicyUpdate {
  model_mode?: ModelMode;
  selected_model?: string;
  fallback_models?: string[];
  enable_fallback?: boolean;
  max_cost_per_request?: number;
  monthly_budget_limit?: number;
}

export interface ModelBreakdownItem {
  model_id: string;
  pricing_category: string;
  requests: number;
  total_tokens: number;
  estimated_cost_usd: number;
  avg_latency_ms?: number | null;
}

export interface ModelUsageSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  fallback_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  average_latency_ms?: number | null;
  model_breakdown: ModelBreakdownItem[];
}

export interface ProviderConfigResponse {
  provider_type: ProviderType;
  name: string;
  base_url?: string | null;
  default_model: string;
  is_active: boolean;
  enabled: boolean;
  has_api_key: boolean;
  masked_api_key?: string | null;
}

export interface ProviderConfigCreate {
  name: string;
  base_url?: string | null;
  api_key?: string;
  default_model: string;
  is_active?: boolean;
  enabled?: boolean;
}

export interface ProviderTestResult {
  success: boolean;
  latency_ms?: number | null;
  message: string;
  models_found?: number | null;
  error?: string | null;
}
