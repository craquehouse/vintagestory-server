import { describe, it, expect, vi, beforeEach } from 'vitest';
import { toast } from 'sonner';
import { handleApiError } from './error-handler';
import { UnauthorizedError, ForbiddenError, ApiError } from './errors';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

describe('handleApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('401 Unauthorized handling (AC: 3)', () => {
    it('shows "Authentication Failed" toast for UnauthorizedError', () => {
      const error = new UnauthorizedError('Invalid API key');

      handleApiError(error);

      expect(toast.error).toHaveBeenCalledTimes(1);
      expect(toast.error).toHaveBeenCalledWith('Authentication Failed', {
        description: 'Please check your API key configuration.',
      });
    });

    it('shows consistent message regardless of error message', () => {
      const error = new UnauthorizedError('Custom message');

      handleApiError(error);

      // Always shows the same user-friendly message for 401 errors
      expect(toast.error).toHaveBeenCalledWith('Authentication Failed', {
        description: 'Please check your API key configuration.',
      });
    });
  });

  describe('403 Forbidden handling (AC: 4)', () => {
    it('shows "Access Denied" toast for ForbiddenError', () => {
      const error = new ForbiddenError('Admin role required');

      handleApiError(error);

      expect(toast.error).toHaveBeenCalledTimes(1);
      expect(toast.error).toHaveBeenCalledWith('Access Denied', {
        description: 'Admin role required',
      });
    });

    it('shows the specific permission error message', () => {
      const error = new ForbiddenError('Console access requires admin role');

      handleApiError(error);

      expect(toast.error).toHaveBeenCalledWith('Access Denied', {
        description: 'Console access requires admin role',
      });
    });
  });

  describe('other API errors', () => {
    it('shows generic error toast for other ApiErrors', () => {
      const error = new ApiError('NOT_FOUND', 'Resource not found', 404);

      handleApiError(error);

      expect(toast.error).toHaveBeenCalledTimes(1);
      expect(toast.error).toHaveBeenCalledWith('Error', {
        description: 'Resource not found',
      });
    });

    it('shows error toast for standard Error instances', () => {
      const error = new Error('Network request failed');

      handleApiError(error);

      expect(toast.error).toHaveBeenCalledWith('Error', {
        description: 'Network request failed',
      });
    });

    it('shows generic message for unknown error types', () => {
      handleApiError('string error');

      expect(toast.error).toHaveBeenCalledWith('Error', {
        description: 'An unexpected error occurred',
      });
    });

    it('handles null/undefined errors', () => {
      handleApiError(null);

      expect(toast.error).toHaveBeenCalledWith('Error', {
        description: 'An unexpected error occurred',
      });
    });
  });
});
