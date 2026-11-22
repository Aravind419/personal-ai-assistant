export type TaskStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export interface TaskItem {
  id: string;
  celery_task_id?: string | null;
  task_name: string;
  task_type: string;
  status: TaskStatus;
  input_params_json?: string | null;
  input_params?: Record<string, any> | null;
  result_metadata_json?: string | null;
  result_metadata?: Record<string, any> | null;
  error_message?: string | null;
  retry_count: number;
  max_retries: number;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: TaskItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskStats {
  total: number;
  queued: number;
  running: number;
  succeeded: number;
  failed: number;
  cancelled: number;
}
