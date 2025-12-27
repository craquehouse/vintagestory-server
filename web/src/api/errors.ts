/**
 * Custom error classes for API responses.
 *
 * These errors are thrown by the API client when specific HTTP status codes
 * are received, allowing consumers to handle different error types appropriately.
 */

/**
 * Base error class for all API errors.
 */
export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(
    code: string,
    message: string,
    status: number,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/**
 * Thrown when the API returns a 401 Unauthorized response.
 * Indicates that authentication is required or the provided credentials are invalid.
 */
export class UnauthorizedError extends ApiError {
  constructor(message: string = 'Authentication required') {
    super('UNAUTHORIZED', message, 401);
    this.name = 'UnauthorizedError';
  }
}

/**
 * Thrown when the API returns a 403 Forbidden response.
 * Indicates that the user is authenticated but lacks permission for the operation.
 */
export class ForbiddenError extends ApiError {
  constructor(message: string = 'Access denied') {
    super('FORBIDDEN', message, 403);
    this.name = 'ForbiddenError';
  }
}
