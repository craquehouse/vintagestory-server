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
