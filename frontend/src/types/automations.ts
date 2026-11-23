export type TriggerType = 'one_time' | 'interval' | 'daily' | 'weekly' | 'monthly' | 'cron' | 'manual';

export type ExecutionStatus =
  | 'SCHEDULED'
  | 'QUEUED'
  | 'RUNNING'
  | 'WAITING_FOR_APPROVAL'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED'
  | 'SKIPPED'
  | 'TIMED_OUT';

export interface AutomationAction {
  tool: string;
  arguments: Record<string, any>;
  description?: string;
}

export interface Automation {
  id: string;
  name: string;
  description?: string;
  natural_instruction?: string;
  trigger_type: TriggerType;
  schedule_config: Record<string, any>;
  timezone: string;
  is_enabled: boolean;
  actions: AutomationAction[];
  associated_tools: string[];
  approval_policy: string;
  next_run_at?: string;
  last_run_at?: string;
  last_status?: string;
  execution_count: number;
  consecutive_failures: number;
  owner_identity: string;
  created_at: string;
  updated_at: string;
}

export interface AutomationStats {
  total_automations: number;
  active_automations: number;
  paused_automations: number;
  failed_executions: number;
  next_scheduled_run?: string;
  recent_executions_count: number;
}

export interface AutomationExecution {
  id: string;
  automation_id: string;
  trigger_type: string;
  idempotency_key?: string;
  status: ExecutionStatus;
  actions_snapshot: Record<string, any>[];
  results?: Record<string, any>[];
  execution_context?: Record<string, any>;
  error_message?: string;
  approval_id?: string;
  retry_count: number;
  max_retries: number;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  worker_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ParseInstructionResponse {
  success: boolean;
  name: string;
  description: string;
  natural_instruction: string;
  trigger_type: TriggerType;
  schedule_config: Record<string, any>;
  timezone: string;
  actions: AutomationAction[];
  associated_tools: string[];
  approval_policy: string;
  validation_errors: string[];
  requires_confirmation: boolean;
  confidence: number;
}

export type IntegrationStatusType =
  | 'not_connected'
  | 'configuration_required'
  | 'authorization_pending'
  | 'connected'
  | 'connected_with_limited_scopes'
  | 'token_expired'
  | 'reauthorization_required'
  | 'connection_error'
  | 'disconnected'
  | 'planned';

export interface IntegrationStatus {
  service_id: string;
  service_name: string;
  provider_family: string;
  category: string;
  description: string;
  icon_name: string;
  status: IntegrationStatusType;
  is_configured: boolean;
  account_identity?: string;
  required_scopes: string[];
  granted_scopes: string[];
  capabilities: string[];
  token_expires_at?: string;
  last_successful_connection?: string;
  last_error?: string;
  // Legacy aliases
  provider_id?: string;
  provider_name?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  is_read: boolean;
  is_dismissed: boolean;
  automation_id?: string;
  execution_id?: string;
  created_at: string;
}

export interface Briefing {
  id: string;
  title: string;
  briefing_type: string;
  content_markdown: string;
  sections: Record<string, any>;
  generated_by_model?: string;
  duration_ms?: number;
  created_at: string;
}
