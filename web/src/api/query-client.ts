/**
 * TanStack Query client configuration.
 *
 * Provides centralized query defaults including:
 * - Stale time configuration
 * - Retry logic that skips auth errors
 * - Window focus refetching
 * - Global error handling for mutations
 */

import { QueryClient } from '@tanstack/react-query';
import { UnauthorizedError, ForbiddenError } from './errors';
import { handleApiError } from './error-handler';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 seconds
      staleTime: 30 * 1000,

      // Custom retry logic - don't retry auth errors
      retry: (failureCount, error) => {
        // Never retry authentication/authorization errors
        if (error instanceof UnauthorizedError || error instanceof ForbiddenError) {
          return false;
        }
        // Retry other errors up to 3 times
        return failureCount < 3;
      },

      // Refetch when window regains focus (useful for detecting session expiry)
      refetchOnWindowFocus: true,
    },
    mutations: {
      // Global error handler for mutations - shows toast notifications
      onError: (error) => {
        handleApiError(error);
      },
    },
  },
});
