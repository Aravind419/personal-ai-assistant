import { apiClient } from './api';
import type {
  Automation,
  AutomationStats,
  AutomationExecution,
  ParseInstructionResponse,
  IntegrationStatus,
  NotificationItem,
  Briefing,
} from '../types/automations';

export const automationService = {
  // Automations
  async getStats(): Promise<AutomationStats> {
    return apiClient<AutomationStats>('/automations/stats');
  },

  async listAutomations(isEnabled?: boolean): Promise<Automation[]> {
    const url = isEnabled !== undefined ? `/automations?is_enabled=${isEnabled}` : '/automations';
    return apiClient<Automation[]>(url);
  },

  async getAutomation(id: string): Promise<Automation> {
    return apiClient<Automation>(`/automations/${id}`);
  },

  async createAutomation(data: Partial<Automation>): Promise<Automation> {
    return apiClient<Automation>('/automations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateAutomation(id: string, data: Partial<Automation>): Promise<Automation> {
    return apiClient<Automation>(`/automations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteAutomation(id: string): Promise<void> {
    await apiClient<void>(`/automations/${id}`, {
      method: 'DELETE',
    });
  },

  async enableAutomation(id: string): Promise<Automation> {
    return apiClient<Automation>(`/automations/${id}/enable`, {
      method: 'POST',
    });
  },

  async disableAutomation(id: string): Promise<Automation> {
    return apiClient<Automation>(`/automations/${id}/disable`, {
      method: 'POST',
    });
  },

  async runAutomation(id: string): Promise<AutomationExecution> {
    return apiClient<AutomationExecution>(`/automations/${id}/run`, {
      method: 'POST',
    });
  },

  async listExecutions(automationId?: string): Promise<AutomationExecution[]> {
    const url = automationId ? `/automations/${automationId}/executions` : '/automations/executions';
    return apiClient<AutomationExecution[]>(url);
  },

  async cancelExecution(executionId: string): Promise<AutomationExecution> {
    return apiClient<AutomationExecution>(`/automations/executions/${executionId}/cancel`, {
      method: 'POST',
    });
  },

  async parseInstruction(instruction: string, timezone?: string): Promise<ParseInstructionResponse> {
    return apiClient<ParseInstructionResponse>('/automations/parse', {
      method: 'POST',
      body: JSON.stringify({
        instruction,
        timezone: timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      }),
    });
  },

  // Integrations
  async listIntegrations(category?: string, search?: string): Promise<IntegrationStatus[]> {
    const params = new URLSearchParams();
    if (category && category !== 'all') params.append('category', category);
    if (search && search.trim()) params.append('search', search.trim());
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiClient<IntegrationStatus[]>(`/integrations${query}`);
  },

  async listCategories(): Promise<{ id: string; label: string }[]> {
    return apiClient<{ id: string; label: string }[]>('/integrations/categories');
  },

  async getAuthUrl(providerId: string): Promise<{ authorization_url: string; state: string }> {
    return apiClient<{ authorization_url: string; state: string }>(`/integrations/${providerId}/auth-url`);
  },

  async callbackIntegration(providerId: string, code: string, state: string): Promise<IntegrationStatus> {
    return apiClient<IntegrationStatus>(`/integrations/${providerId}/callback`, {
      method: 'POST',
      body: JSON.stringify({ code, state }),
    });
  },

  async testIntegration(providerId: string): Promise<{ connected: boolean; message?: string; error?: string }> {
    return apiClient<{ connected: boolean; message?: string; error?: string }>(`/integrations/${providerId}/test`, {
      method: 'POST',
    });
  },

  async syncIntegration(providerId: string): Promise<any> {
    return apiClient<any>(`/integrations/${providerId}/sync`, {
      method: 'POST',
    });
  },

  async disconnectIntegration(providerId: string): Promise<void> {
    await apiClient<void>(`/integrations/${providerId}/disconnect`, {
      method: 'POST',
    });
  },

  // Notifications
  async listNotifications(unreadOnly = false): Promise<NotificationItem[]> {
    const url = unreadOnly ? '/notifications?unread_only=true' : '/notifications';
    return apiClient<NotificationItem[]>(url);
  },

  async getUnreadCount(): Promise<number> {
    const res = await apiClient<{ unread_count: number }>('/notifications/unread-count');
    return res.unread_count;
  },

  async markNotificationRead(id: string): Promise<void> {
    await apiClient<void>(`/notifications/${id}/read`, {
      method: 'POST',
    });
  },

  async markAllNotificationsRead(): Promise<void> {
    await apiClient<void>('/notifications/read-all', {
      method: 'POST',
    });
  },

  async dismissNotification(id: string): Promise<void> {
    await apiClient<void>(`/notifications/${id}`, {
      method: 'DELETE',
    });
  },

  // Briefings
  async getLatestBriefing(): Promise<Briefing | null> {
    return apiClient<Briefing | null>('/briefings/latest');
  },

  async generateBriefing(): Promise<Briefing> {
    return apiClient<Briefing>('/briefings/generate', {
      method: 'POST',
    });
  },
};
