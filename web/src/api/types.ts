/**
 * Type definitions for API responses.
 *
 * These types match the backend API response envelope pattern:
 * - Success: { status: "ok", data: {...} }
 * - Error: { detail: { code: "...", message: "..." } }
 */

/**
 * Standard success response envelope from the API.
 */
export interface ApiResponse<T> {
  status: 'ok';
  data: T;
}

/**
 * Error detail structure from FastAPI HTTPException.
 */
export interface ApiErrorDetail {
  code?: string;
  message?: string;
}

/**
 * Error response envelope from the API.
 */
export interface ApiErrorResponse {
  detail?: ApiErrorDetail | string;
}

/**
 * Server state values from the backend API.
 */
export type ServerState =
  | 'not_installed'
  | 'installing'
  | 'installed' // This means stopped
  | 'starting'
  | 'running'
  | 'stopping'
  | 'error';

/**
 * Server status response from GET /api/v1alpha1/server/status.
 * Note: API returns snake_case, but apiClient transforms to camelCase.
 */
export interface ServerStatus {
  state: ServerState;
  version: string | null;
  uptimeSeconds: number | null;
  lastExitCode: number | null;
}

/**
 * Installation status response from GET /api/v1alpha1/server/install/status.
 */
export type InstallState =
  | 'idle'
  | 'downloading'
  | 'extracting'
  | 'configuring'
  | 'complete'
  | 'error';

export interface InstallStatus {
  state: InstallState;
  progress: number;
  message: string;
}

/**
 * Generic message response from server action endpoints.
 */
export interface ActionMessage {
  message: string;
}
