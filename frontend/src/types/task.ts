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

  // Extended telemetry & source inspectability
  source_conversation_id?: string | null;
  source_conversation_title?: string | null;
  source_message_id?: string | null;
  execution_mode?: 'celery_worker' | 'local_async' | string | null;
  worker_id?: string | null;
  queue_wait_ms?: number | null;
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
  oldest_queued_wait_seconds?: number | null;
  average_wait_seconds?: number | null;
  stale_queued_count?: number;
}

export interface WorkerHealth {
  redis_connected: boolean;
  redis_latency_ms?: number | null;
  celery_online: boolean;
  worker_count: number;
  active_workers: string[];
  registered_task_types: string[];
  active_tasks_count: number;
  reserved_tasks_count: number;
  last_heartbeat?: string | null;
  last_successful_task?: {
    id: string;
    task_name: string;
    completed_at: string;
  } | null;
}

export interface SweepStaleTasksResponse {
  swept_count: number;
  task_ids: string[];
  message: string;
}
