export interface DatabaseHealth {
  connected: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
}

export interface SystemInfoResponse {
  app_name: string;
  version: string;
  phase: string;
  environment: string;
  architecture: Record<string, string>;
  status_summary: Record<string, string>;
}

export interface ApiError {
  message: string;
  statusCode?: number;
  details?: unknown;
}
