import { apiClient } from './api';
import type {
  Conversation,
  ConversationSummary,
  ConversationCreate,
  ConversationUpdate,
} from '../types/chat';

export const conversationService = {
  async listConversations(): Promise<ConversationSummary[]> {
    return apiClient<ConversationSummary[]>('/conversations');
  },

  async createConversation(data?: ConversationCreate): Promise<Conversation> {
    return apiClient<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  },

  async getConversation(id: string): Promise<Conversation> {
    return apiClient<Conversation>(`/conversations/${id}`);
  },

  async updateConversation(
    id: string,
    data: ConversationUpdate
  ): Promise<Conversation> {
    return apiClient<Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteConversation(id: string): Promise<void> {
    return apiClient<void>(`/conversations/${id}`, {
      method: 'DELETE',
    });
  },
};
