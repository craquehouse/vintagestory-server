/**
 * Global error handling utilities for API errors.
 *
 * Provides toast notifications for authentication and authorization errors,
 * keeping the user informed about what went wrong.
 */

import { toast } from 'sonner';
import { UnauthorizedError, ForbiddenError, ApiError } from './errors';

/**
 * Display an appropriate toast notification for an API error.
 *
 * - 401 errors: Shows "Authentication Failed" with guidance to check API key
 * - 403 errors: Shows "Access Denied" with the specific error message
 * - Other API errors: Shows generic error with the error message
 *
 * @param error - The error to handle
 */
export function handleApiError(error: unknown): void {
  if (error instanceof UnauthorizedError) {
    toast.error('Authentication Failed', {
      description: 'Please check your API key configuration.',
    });
  } else if (error instanceof ForbiddenError) {
    toast.error('Access Denied', {
      description: error.message,
    });
  } else if (error instanceof ApiError) {
    toast.error('Error', {
      description: error.message,
    });
  } else if (error instanceof Error) {
    toast.error('Error', {
      description: error.message,
    });
  } else {
    toast.error('Error', {
      description: 'An unexpected error occurred',
    });
  }
}
