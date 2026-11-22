import { apiClient } from './api';
import type { HealthResponse, DatabaseHealth, SystemInfoResponse } from '../types/api';

export const healthService = {
  /**
   * Retrieves overall application health, including environment and DB check.
   */
  async getHealth(): Promise<HealthResponse> {
    return apiClient<HealthResponse>('/health');
  },

  /**
   * Checks database connectivity directly.
   */
  async getDatabaseHealth(): Promise<DatabaseHealth> {
    return apiClient<DatabaseHealth>('/health/db');
  },

  /**
   * Retrieves architectural info and phase metadata.
   */
  async getSystemInfo(): Promise<SystemInfoResponse> {
    return apiClient<SystemInfoResponse>('/info');
  },
};
