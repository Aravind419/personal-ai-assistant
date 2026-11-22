import { apiClient } from './api';
import type {
  MemoryItem,
  MemoryListResponse,
  MemoryStats,
  MemorySearchResult,
  MemoryCreatePayload,
  MemoryUpdatePayload,
} from '../types/memory';

export const memoryService = {
  async listMemories(params?: {
    category?: string;
    search?: string;
    is_archived?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<MemoryListResponse> {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.search) query.append('search', params.search);
    if (params?.is_archived !== undefined) query.append('is_archived', String(params.is_archived));
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const qs = query.toString();
    return apiClient<MemoryListResponse>(`/memories${qs ? `?${qs}` : ''}`);
  },

  async getStats(): Promise<MemoryStats> {
    return apiClient<MemoryStats>('/memories/stats');
  },

  async getMemory(id: string): Promise<MemoryItem> {
    return apiClient<MemoryItem>(`/memories/${id}`);
  },

  async createMemory(payload: MemoryCreatePayload): Promise<MemoryItem> {
    return apiClient<MemoryItem>('/memories', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateMemory(id: string, payload: MemoryUpdatePayload): Promise<MemoryItem> {
    return apiClient<MemoryItem>(`/memories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteMemory(id: string): Promise<void> {
    await apiClient<void>(`/memories/${id}`, {
      method: 'DELETE',
    });
  },

  async toggleArchive(id: string, isArchived: boolean): Promise<MemoryItem> {
    return apiClient<MemoryItem>(`/memories/${id}/archive?is_archived=${isArchived}`, {
      method: 'POST',
    });
  },

  async searchMemories(query: string, category?: string, limit = 5, threshold = 0.35): Promise<MemorySearchResult[]> {
    return apiClient<MemorySearchResult[]>('/memories/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        category: category || null,
        limit,
        threshold,
      }),
    });
  },
};
