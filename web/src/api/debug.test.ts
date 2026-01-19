import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchDebugStatus, enableDebug, disableDebug } from './debug';
import type { ApiResponse, DebugStatusData, DebugToggleData } from './types';

// Mock the API client
vi.mock('./client', () => ({
  apiClient: vi.fn(),
}));

import { apiClient } from './client';

describe('api/debug', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('fetchDebugStatus', () => {
    it('calls correct endpoint with GET method', async () => {
      const mockResponse: ApiResponse<DebugStatusData> = {
        status: 'ok',
        data: {
          debugEnabled: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchDebugStatus();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/debug');
      expect(result).toEqual(mockResponse);
    });

    it('returns debug status when enabled', async () => {
      const mockResponse: ApiResponse<DebugStatusData> = {
        status: 'ok',
        data: {
          debugEnabled: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchDebugStatus();

      expect(result.status).toBe('ok');
      expect(result.data.debugEnabled).toBe(true);
    });

    it('returns debug status when disabled', async () => {
      const mockResponse: ApiResponse<DebugStatusData> = {
        status: 'ok',
        data: {
          debugEnabled: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchDebugStatus();

      expect(result.data.debugEnabled).toBe(false);
    });

    it('propagates errors from apiClient', async () => {
      const mockError = new Error('Unauthorized');
      vi.mocked(apiClient).mockRejectedValue(mockError);

      await expect(fetchDebugStatus()).rejects.toThrow('Unauthorized');
    });
  });

  describe('enableDebug', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: true,
          changed: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await enableDebug();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/debug/enable', {
        method: 'POST',
      });
    });

    it('returns changed=true when state changes', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: true,
          changed: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await enableDebug();

      expect(result.data.debugEnabled).toBe(true);
      expect(result.data.changed).toBe(true);
    });

    it('returns changed=false when already enabled', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: true,
          changed: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await enableDebug();

      expect(result.data.debugEnabled).toBe(true);
      expect(result.data.changed).toBe(false);
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Forbidden'));

      await expect(enableDebug()).rejects.toThrow('Forbidden');
    });
  });

  describe('disableDebug', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: false,
          changed: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await disableDebug();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/debug/disable', {
        method: 'POST',
      });
    });

    it('returns changed=true when state changes', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: false,
          changed: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await disableDebug();

      expect(result.data.debugEnabled).toBe(false);
      expect(result.data.changed).toBe(true);
    });

    it('returns changed=false when already disabled', async () => {
      const mockResponse: ApiResponse<DebugToggleData> = {
        status: 'ok',
        data: {
          debugEnabled: false,
          changed: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await disableDebug();

      expect(result.data.debugEnabled).toBe(false);
      expect(result.data.changed).toBe(false);
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Server error'));

      await expect(disableDebug()).rejects.toThrow('Server error');
    });
  });

  describe('API prefix constant', () => {
    it('uses consistent API prefix across all endpoints', async () => {
      const mockResponse = { status: 'ok' as const, data: {} as DebugStatusData };
      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchDebugStatus();
      await enableDebug();
      await disableDebug();

      const calls = vi.mocked(apiClient).mock.calls;
      calls.forEach(([url]) => {
        expect(url).toMatch(/^\/api\/v1alpha1\/debug/);
      });
    });
  });
});
