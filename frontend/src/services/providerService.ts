import { apiClient } from './api';
import type {
  ProviderConfigResponse,
  ProviderConfigCreate,
  ProviderTestResult,
  ModelInfo,
  ProviderType,
} from '../types/provider';

export const providerService = {
  async listProviders(): Promise<ProviderConfigResponse[]> {
    return apiClient<ProviderConfigResponse[]>('/providers');
  },

  async saveProvider(
    type: ProviderType,
    data: ProviderConfigCreate
  ): Promise<ProviderConfigResponse> {
    return apiClient<ProviderConfigResponse>(`/providers/${type}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async activateProvider(type: ProviderType): Promise<ProviderConfigResponse> {
    return apiClient<ProviderConfigResponse>(`/providers/${type}/activate`, {
      method: 'POST',
    });
  },

  async testProvider(
    type: ProviderType,
    params?: { api_key?: string; base_url?: string }
  ): Promise<ProviderTestResult> {
    return apiClient<ProviderTestResult>(`/providers/${type}/test`, {
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  },

  async listModels(type: ProviderType): Promise<ModelInfo[]> {
    return apiClient<ModelInfo[]>(`/providers/${type}/models`);
  },
};
