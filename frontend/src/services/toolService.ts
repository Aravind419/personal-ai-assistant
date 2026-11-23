import { apiClient } from './api';
import type {
  ToolDefinition,
  ToolExecutionSummary,
  ToolExecutionDetail,
  Approval,
  McpServer,
  ToolsHealth,
} from '../types/tool';

export const toolService = {
  // Tools
  async getTools(): Promise<ToolDefinition[]> {
    return apiClient<ToolDefinition[]>('/tools');
  },

  async getToolsHealth(): Promise<ToolsHealth> {
    return apiClient<ToolsHealth>('/tools/health');
  },

  async getTool(toolId: string): Promise<ToolDefinition> {
    return apiClient<ToolDefinition>(`/tools/${toolId}`);
  },

  async executeTool(
    toolId: string,
    argumentsPayload: Record<string, any>,
    conversationId?: string,
    idempotencyKey?: string
  ): Promise<ToolExecutionDetail> {
    return apiClient<ToolExecutionDetail>(`/tools/${toolId}/execute`, {
      method: 'POST',
      body: JSON.stringify({
        arguments: argumentsPayload,
        conversation_id: conversationId,
        idempotency_key: idempotencyKey,
      }),
    });
  },

  async getExecutionHistory(params?: {
    status?: string;
    tool_id?: string;
    conversation_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ToolExecutionSummary[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.tool_id) query.append('tool_id', params.tool_id);
    if (params?.conversation_id) query.append('conversation_id', params.conversation_id);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const qs = query.toString();
    return apiClient<ToolExecutionSummary[]>(`/tools/executions/history${qs ? `?${qs}` : ''}`);
  },

  async getExecutionDetail(id: string): Promise<ToolExecutionDetail> {
    return apiClient<ToolExecutionDetail>(`/tools/executions/${id}`);
  },

  // MCP Servers
  async getMcpServers(): Promise<McpServer[]> {
    return apiClient<McpServer[]>('/tools/mcp/servers');
  },

  async createMcpServer(payload: {
    name: string;
    server_type?: string;
    command?: string;
    args?: string[];
    url?: string;
    headers?: Record<string, string>;
    env?: Record<string, string>;
  }): Promise<McpServer> {
    return apiClient<McpServer>('/tools/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async discoverMcpTools(serverId: string): Promise<{
    server_id: string;
    name: string;
    status: string;
    discovered_tools_count: number;
  }> {
    return apiClient(`/tools/mcp/servers/${serverId}/discover`, {
      method: 'POST',
    });
  },

  async testMcpServer(serverId: string): Promise<{
    success: boolean;
    latency_ms: number;
    server_id: string;
    name: string;
    status: string;
    tools_count?: number;
    tools?: Array<{ name: string; description?: string }>;
    message: string;
    error?: string;
  }> {
    return apiClient(`/tools/mcp/servers/${serverId}/test`, {
      method: 'POST',
    });
  },

  async updateMcpServer(
    serverId: string,
    payload: { is_enabled?: boolean; name?: string; command?: string; url?: string }
  ): Promise<McpServer> {
    return apiClient<McpServer>(`/tools/mcp/servers/${serverId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteMcpServer(serverId: string): Promise<void> {
    return apiClient<void>(`/tools/mcp/servers/${serverId}`, {
      method: 'DELETE',
    });
  },

  // Approvals
  async getApprovals(params?: {
    status?: string;
    tool_id?: string;
    conversation_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Approval[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.tool_id) query.append('tool_id', params.tool_id);
    if (params?.conversation_id) query.append('conversation_id', params.conversation_id);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const qs = query.toString();
    return apiClient<Approval[]>(`/approvals${qs ? `?${qs}` : ''}`);
  },

  async getApproval(approvalId: string): Promise<Approval> {
    return apiClient<Approval>(`/approvals/${approvalId}`);
  },

  async approveAction(
    approvalId: string,
    executeNow = true,
    reason?: string,
    confirmCritical = false
  ): Promise<{ approval: Approval; execution?: ToolExecutionDetail }> {
    return apiClient(`/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        execute_now: executeNow,
        reason,
        confirm_critical: confirmCritical,
      }),
    });
  },

  async rejectAction(approvalId: string, reason?: string): Promise<Approval> {
    return apiClient<Approval>(`/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  async cancelAction(approvalId: string): Promise<Approval> {
    return apiClient<Approval>(`/approvals/${approvalId}/cancel`, {
      method: 'POST',
    });
  },
};
