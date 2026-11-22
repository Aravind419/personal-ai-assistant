import { apiClient } from './api';
import type { TaskItem, TaskListResponse, TaskStats } from '../types/task';

export const taskService = {
  async listTasks(params?: {
    status?: string;
    task_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<TaskListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.task_type) query.append('task_type', params.task_type);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const qs = query.toString();
    return apiClient<TaskListResponse>(`/tasks${qs ? `?${qs}` : ''}`);
  },

  async getStats(): Promise<TaskStats> {
    return apiClient<TaskStats>('/tasks/stats');
  },

  async getTask(id: string): Promise<TaskItem> {
    return apiClient<TaskItem>(`/tasks/${id}`);
  },

  async retryTask(id: string): Promise<TaskItem> {
    return apiClient<TaskItem>(`/tasks/${id}/retry`, {
      method: 'POST',
    });
  },

  async cancelTask(id: string): Promise<TaskItem> {
    return apiClient<TaskItem>(`/tasks/${id}/cancel`, {
      method: 'POST',
    });
  },
};
