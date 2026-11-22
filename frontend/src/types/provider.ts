export type ProviderType = 'openrouter' | 'nvidia' | 'ollama' | 'custom';

export interface ModelInfo {
  id: string;
  name: string;
  context_length?: number | null;
  description?: string | null;
  pricing?: Record<string, unknown> | null;
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
