/**
 * API Client with authentication and key transformation.
 *
 * This module provides:
 * - Automatic X-API-Key header injection
 * - snake_case to camelCase transformation for responses
 * - camelCase to snake_case transformation for request bodies
 * - Typed error handling for auth errors (401, 403)
 */

import { ApiError, UnauthorizedError, ForbiddenError } from './errors';
import type { ApiErrorResponse } from './types';

/**
 * API client configuration.
 */
interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

/**
 * The web UI's API key, or '' when it has none.
 *
 * The key comes from the runtime configuration the server serves at /config.js
 * (the published image), falling back to the VITE_API_KEY build variable (the dev server).
 */
export function getApiKey(): string {
  return window.__VSM_CONFIG__?.apiKey || import.meta.env.VITE_API_KEY || '';
}

/**
 * Get API configuration.
 */
function getConfig(): ApiConfig {
  return {
    baseUrl: import.meta.env.VITE_API_BASE_URL || '',
    apiKey: getApiKey(),
  };
}

/**
 * Recursively transforms object keys from snake_case to camelCase.
 * Handles nested objects and arrays.
 *
 * @param obj - The object to transform
 * @returns A new object with camelCase keys
 *
 * @example
 * snakeToCamel({ user_name: "test", is_active: true })
 * // => { userName: "test", isActive: true }
 */
export function snakeToCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase()),
        snakeToCamel(value),
      ])
    );
  }
  return obj;
}

/**
 * Recursively transforms object keys from camelCase to snake_case.
 * Used for request bodies sent to the API.
 *
 * @param obj - The object to transform
 * @returns A new object with snake_case keys
 *
 * @example
 * camelToSnake({ userName: "test", isActive: true })
 * // => { user_name: "test", is_active: true }
 */
export function camelToSnake(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(camelToSnake);
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        key.replace(/([A-Z])/g, '_$1').toLowerCase(),
        camelToSnake(value),
      ])
    );
  }
  return obj;
}

/**
 * Parse API error response and throw appropriate error type.
 *
 * @param response - The failed fetch Response
 * @throws UnauthorizedError for 401 responses
 * @throws ForbiddenError for 403 responses
 * @throws ApiError for other error responses
 */
async function handleApiError(response: Response): Promise<never> {
  let errorData: ApiErrorResponse = {};

  try {
    errorData = await response.json();
  } catch {
    // Response wasn't JSON, use defaults
  }

  // Extract error details from FastAPI's standard format
  let code = 'UNKNOWN';
  let message = response.statusText;
  let details: Record<string, unknown> | undefined;

  if (errorData.detail) {
    if (typeof errorData.detail === 'string') {
      message = errorData.detail;
    } else {
      const {
        code: detailCode,
        message: detailMessage,
        details: detailDetails,
        ...rest
      } = errorData.detail;
      code = detailCode || 'UNKNOWN';
      message = detailMessage || response.statusText;
      // An explicit `details` object, else the detail's other keys (Story 23.5: a config
      // save's 422 puts `parse_error` directly in the detail)
      details = detailDetails ?? (Object.keys(rest).length > 0 ? rest : undefined);
    }
  }

  if (response.status === 401) {
    throw new UnauthorizedError(message);
  }
  if (response.status === 403) {
    throw new ForbiddenError(message);
  }

  throw new ApiError(code, message, response.status, details);
}

/**
 * Request options for the API client.
 */
export interface ApiClientOptions extends Omit<RequestInit, 'body'> {
  /** Request body - will be transformed to snake_case and stringified */
  body?: unknown;
  /**
   * A body sent as is, with its own content type and no JSON transform: a mod file
   * upload (Story 28.4, Epic 28 ADR-6). Takes the place of `body`.
   */
  rawBody?: Blob;
  /**
   * Whether to turn the response's snake_case keys into camelCase (default true).
   * False returns the response as sent: for data whose keys are not the API's own,
   * such as a config file's content (Story 23.1).
   */
  transformResponse?: boolean;
}

/**
 * Make an authenticated API request with automatic key transformation.
 *
 * - Automatically adds X-API-Key header from configuration
 * - Transforms request body keys from camelCase to snake_case
 * - Transforms response keys from snake_case to camelCase
 * - Throws typed errors for 401/403 responses
 *
 * @param path - API endpoint path (e.g., "/api/v1alpha1/auth/me")
 * @param options - Fetch options (method, headers, body)
 * @returns Transformed response data
 *
 * @example
 * const response = await apiClient<AuthMeResponse>("/api/v1alpha1/auth/me");
 * console.log(response.data.role); // camelCase keys
 */
export async function apiClient<T>(path: string, options: ApiClientOptions = {}): Promise<T> {
  const config = getConfig();
  const url = `${config.baseUrl}${path}`;

  const headers = new Headers(options.headers);
  headers.set('X-API-Key', config.apiKey);

  // Transform request body to snake_case if present; a raw body goes as it is
  let body: string | Blob | undefined;
  if (options.rawBody !== undefined) {
    headers.set('Content-Type', options.rawBody.type || 'application/octet-stream');
    body = options.rawBody;
  } else {
    headers.set('Content-Type', 'application/json');
    if (options.body !== undefined) {
      body = JSON.stringify(camelToSnake(options.body));
    }
  }

  const { transformResponse = true, rawBody: _rawBody, ...init } = options;
  const response = await fetch(url, {
    ...init,
    headers,
    body,
  });

  if (!response.ok) {
    await handleApiError(response);
  }

  const data = await response.json();

  // Transform snake_case to camelCase, unless the caller maps the keys itself
  return (transformResponse ? snakeToCamel(data) : data) as T;
}
