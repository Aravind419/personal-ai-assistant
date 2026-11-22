import { apiClient } from './api';
import type { AssistantPersonalityConfig } from '../types/personality';

export const personalityService = {
  async getPersonality(): Promise<AssistantPersonalityConfig> {
    return apiClient<AssistantPersonalityConfig>('/conversations/settings/personality');
  },

  async updatePersonality(
    config: AssistantPersonalityConfig
  ): Promise<AssistantPersonalityConfig> {
    return apiClient<AssistantPersonalityConfig>(
      '/conversations/settings/personality',
      {
        method: 'PUT',
        body: JSON.stringify(config),
      }
    );
  },
};
