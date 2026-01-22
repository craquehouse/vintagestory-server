import { describe, it, expect, vi } from 'vitest';
import { queryClient } from './query-client';
import { UnauthorizedError, ForbiddenError, ApiError } from './errors';
import * as errorHandler from './error-handler';

describe('queryClient', () => {
  describe('default query options', () => {
    it('has staleTime of 30 seconds', () => {
      const defaults = queryClient.getDefaultOptions();
      expect(defaults.queries?.staleTime).toBe(30 * 1000);
    });

    it('refetches on window focus', () => {
      const defaults = queryClient.getDefaultOptions();
      expect(defaults.queries?.refetchOnWindowFocus).toBe(true);
    });
  });

  describe('retry logic', () => {
    it('does not retry UnauthorizedError', () => {
      const defaults = queryClient.getDefaultOptions();
      const retry = defaults.queries?.retry;

      if (typeof retry !== 'function') {
        throw new Error('Expected retry to be a function');
      }

      const error = new UnauthorizedError('Invalid API key');
      expect(retry(0, error)).toBe(false);
      expect(retry(1, error)).toBe(false);
      expect(retry(2, error)).toBe(false);
    });

    it('does not retry ForbiddenError', () => {
      const defaults = queryClient.getDefaultOptions();
      const retry = defaults.queries?.retry;

      if (typeof retry !== 'function') {
        throw new Error('Expected retry to be a function');
      }

      const error = new ForbiddenError('Admin role required');
      expect(retry(0, error)).toBe(false);
      expect(retry(1, error)).toBe(false);
      expect(retry(2, error)).toBe(false);
    });

    it('retries other errors up to 3 times', () => {
      const defaults = queryClient.getDefaultOptions();
      const retry = defaults.queries?.retry;

      if (typeof retry !== 'function') {
        throw new Error('Expected retry to be a function');
      }

      const error = new ApiError('SERVER_ERROR', 'Internal error', 500);
      expect(retry(0, error)).toBe(true); // 1st retry
      expect(retry(1, error)).toBe(true); // 2nd retry
      expect(retry(2, error)).toBe(true); // 3rd retry
      expect(retry(3, error)).toBe(false); // No more retries
    });

    it('retries network errors up to 3 times', () => {
      const defaults = queryClient.getDefaultOptions();
      const retry = defaults.queries?.retry;

      if (typeof retry !== 'function') {
        throw new Error('Expected retry to be a function');
      }

      const error = new Error('Network request failed');
      expect(retry(0, error)).toBe(true);
      expect(retry(1, error)).toBe(true);
      expect(retry(2, error)).toBe(true);
      expect(retry(3, error)).toBe(false);
    });
  });

  describe('mutation error handling', () => {
    it('calls handleApiError on mutation errors', () => {
      const handleApiErrorSpy = vi.spyOn(errorHandler, 'handleApiError');
      const defaults = queryClient.getDefaultOptions();
      const onError = defaults.mutations?.onError;

      if (typeof onError !== 'function') {
        throw new Error('Expected onError to be a function');
      }

      const error = new ApiError('SERVER_ERROR', 'Mutation failed', 500);
      // onError signature: (error, variables, context, mutation)
      onError(error, undefined, undefined, {} as never);

      expect(handleApiErrorSpy).toHaveBeenCalledWith(error);
      handleApiErrorSpy.mockRestore();
    });
  });
});
