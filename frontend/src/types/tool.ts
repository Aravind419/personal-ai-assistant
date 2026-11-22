export type PermissionLevel = 'safe' | 'sensitive' | 'critical';

export type ToolCategory =
  | 'system'
  | 'math'
  | 'text'
  | 'file'
  | 'web'
  | 'productivity'
  | 'communication'
  | 'developer'
  | 'database'
  | 'mcp'
  | 'custom';

export type ExecutionEnvironment = 'builtin' | 'mcp' | 'external_api' | 'custom';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';

export type ExecutionStatus =
  | 'pending'
  | 'awaiting_approval'
  | 'approved'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'rejected'
  | 'cancelled'
  | 'timed_out';

export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  parameters_schema: Record<string, any>;
  output_schema?: Record<string, any> | null;
  permission_level: PermissionLevel;
  risk_classification: string;
  timeout_seconds: number;
  requires_approval: boolean;
  is_enabled: boolean;
  execution_environment: ExecutionEnvironment;
  availability_status: string;
}

export interface ToolExecutionSummary {
  id: string;
  conversation_id?: string | null;
  tool_id: string;
  tool_name: string;
  requested_arguments: Record<string, any>;
  status: ExecutionStatus;
  approval_id?: string | null;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  result_summary?: string | null;
  error_details?: string | null;
  user_identity: string;
  execution_environment: string;
}

export interface ToolExecutionDetail {
  id: string;
  tool_id: string;
  tool_name: string;
  status: ExecutionStatus;
  success: boolean;
  result?: any;
  error?: string | null;
  duration_ms?: number | null;
  approval_id?: string | null;
  approval_required: boolean;
  started_at: string;
  completed_at?: string | null;
}

export interface Approval {
  id: string;
  conversation_id?: string | null;
  tool_id: string;
  tool_name: string;
  action: string;
  arguments: Record<string, any>;
  arguments_hash: string;
  target_resource?: string | null;
  expected_consequences?: string | null;
  permission_level: PermissionLevel;
  risk_level: string;
  reason: string;
  status: ApprovalStatus;
  created_at: string;
  expires_at: string;
  decided_at?: string | null;
  decided_by?: string | null;
  decision_reason?: string | null;
  execution_id?: string | null;
}

export interface McpServer {
  id: string;
  name: string;
  server_type: string;
  command?: string | null;
  url?: string | null;
  is_enabled: boolean;
  status: string;
  last_health_check?: string | null;
  last_error?: string | null;
  discovered_tools_count: number;
  created_at: string;
  updated_at: string;
}

export interface ToolsHealth {
  status: string;
  total_tools_count: number;
  enabled_tools_count: number;
  mcp_servers_count: number;
  connected_mcp_servers: number;
}
