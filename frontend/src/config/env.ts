/**
 * Environment configuration for the frontend application.
 * Safely accesses and validates Vite environment variables.
 */

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  appName: import.meta.env.VITE_APP_NAME || 'Personal AI Assistant',
  appEnv: import.meta.env.VITE_APP_ENV || 'development',
  isDev: import.meta.env.DEV,
} as const;
