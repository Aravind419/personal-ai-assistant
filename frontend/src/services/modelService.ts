import { apiClient } from './api';
import type {
  CentralModelInfo,
  ModelPolicyResponse,
  ModelPolicyUpdate,
  ModelUsageSummary,
} from '../types/provider';

export const modelService = {
  /**
   * Retrieves all models from the central model registry with optional filtering.
   */
  async listModels(params?: {
    pricing_category?: string;
    provider_type?: string;
    mode?: string;
  }): Promise<CentralModelInfo[]> {
    const query = new URLSearchParams();
    if (params?.pricing_category) query.append('pricing_category', params.pricing_category);
    if (params?.provider_type) query.append('provider_type', params.provider_type);
    if (params?.mode) query.append('mode', params.mode);

    const qs = query.toString();
    const endpoint = qs ? `/models?${qs}` : '/models';
    return apiClient<CentralModelInfo[]>(endpoint);
  },

  /**
   * Retrieves the current AI model policy, operating mode, and fallback settings.
   */
  async getModelPolicy(): Promise<ModelPolicyResponse> {
    return apiClient<ModelPolicyResponse>('/models/policy');
  },

  /**
   * Updates model mode (free-only/paid-enabled/manual), fallback chains, and budget caps.
   */
  async updateModelPolicy(payload: ModelPolicyUpdate): Promise<ModelPolicyResponse> {
    return apiClient<ModelPolicyResponse>('/models/policy', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Retrieves aggregated usage statistics, estimated costs, and model performance.
   */
  async getModelMetrics(): Promise<ModelUsageSummary> {
    return apiClient<ModelUsageSummary>('/models/metrics');
  },
};
