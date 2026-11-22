import { env } from '../config/env';
import type { ApiError } from '../types/api';

/**
 * Core API client with typed response handling and centralized error formatting.
 */
export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${env.apiBaseUrl}${normalizedEndpoint}`;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status} ${response.statusText}`;
      let errorDetails: unknown = null;

      try {
        const errorJson = await response.json();
        if (errorJson.error?.message) {
          errorMessage = errorJson.error.message;
          errorDetails = errorJson.error.details;
        } else if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fall back to default status text if not JSON
      }

      const apiError: ApiError = {
        message: errorMessage,
        statusCode: response.status,
        details: errorDetails,
      };
      throw apiError;
    }

    return (await response.json()) as T;
  } catch (error: any) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw {
        message: 'Request timed out after 10 seconds. Check if backend is running.',
        statusCode: 408,
      } as ApiError;
    }

    if (error.statusCode) {
      throw error as ApiError;
    }

    throw {
      message: error.message || 'Unable to connect to backend server. Ensure FastAPI is running.',
      statusCode: 0,
    } as ApiError;
  }
}
