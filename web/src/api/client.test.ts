import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { snakeToCamel, camelToSnake, apiClient } from './client';
import { UnauthorizedError, ForbiddenError, ApiError } from './errors';

describe('snakeToCamel', () => {
  it('transforms snake_case keys to camelCase', () => {
    const input = { user_name: 'test', is_active: true };
    const expected = { userName: 'test', isActive: true };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it('handles nested objects', () => {
    const input = { outer_key: { inner_key: 'value' } };
    const expected = { outerKey: { innerKey: 'value' } };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it('handles arrays of objects', () => {
    const input = [{ user_id: 1 }, { user_id: 2 }];
    const expected = [{ userId: 1 }, { userId: 2 }];
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it('handles deeply nested structures', () => {
    const input = {
      first_level: {
        second_level: {
          third_level: { deep_value: 'test' },
        },
      },
    };
    const expected = {
      firstLevel: {
        secondLevel: {
          thirdLevel: { deepValue: 'test' },
        },
      },
    };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it('handles arrays within objects', () => {
    const input = {
      user_list: [{ first_name: 'John' }, { first_name: 'Jane' }],
    };
    const expected = {
      userList: [{ firstName: 'John' }, { firstName: 'Jane' }],
    };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it('preserves primitive values', () => {
    expect(snakeToCamel('string')).toBe('string');
    expect(snakeToCamel(123)).toBe(123);
    expect(snakeToCamel(true)).toBe(true);
    expect(snakeToCamel(null)).toBe(null);
  });

  it('handles empty objects and arrays', () => {
    expect(snakeToCamel({})).toEqual({});
    expect(snakeToCamel([])).toEqual([]);
  });

  it('handles keys without underscores', () => {
    const input = { name: 'test', active: true };
    expect(snakeToCamel(input)).toEqual({ name: 'test', active: true });
  });
});

describe('camelToSnake', () => {
  it('transforms camelCase keys to snake_case', () => {
    const input = { userName: 'test', isActive: true };
    const expected = { user_name: 'test', is_active: true };
    expect(camelToSnake(input)).toEqual(expected);
  });

  it('handles nested objects', () => {
    const input = { outerKey: { innerKey: 'value' } };
    const expected = { outer_key: { inner_key: 'value' } };
    expect(camelToSnake(input)).toEqual(expected);
  });

  it('handles arrays of objects', () => {
    const input = [{ userId: 1 }, { userId: 2 }];
    const expected = [{ user_id: 1 }, { user_id: 2 }];
    expect(camelToSnake(input)).toEqual(expected);
  });

  it('handles deeply nested structures', () => {
    const input = {
      firstLevel: {
        secondLevel: {
          thirdLevel: { deepValue: 'test' },
        },
      },
    };
    const expected = {
      first_level: {
        second_level: {
          third_level: { deep_value: 'test' },
        },
      },
    };
    expect(camelToSnake(input)).toEqual(expected);
  });

  it('preserves primitive values', () => {
    expect(camelToSnake('string')).toBe('string');
    expect(camelToSnake(123)).toBe(123);
    expect(camelToSnake(true)).toBe(true);
    expect(camelToSnake(null)).toBe(null);
  });

  it('handles keys without uppercase letters', () => {
    const input = { name: 'test', active: true };
    expect(camelToSnake(input)).toEqual({ name: 'test', active: true });
  });
});

describe('apiClient', () => {
  const originalFetch = globalThis.fetch;
  const originalEnv = { ...import.meta.env };

  beforeEach(() => {
    vi.resetAllMocks();
    // Set up environment variables for tests
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    // Restore original env
    Object.keys(import.meta.env).forEach((key) => {
      if (!(key in originalEnv)) {
        delete import.meta.env[key];
      }
    });
    Object.assign(import.meta.env, originalEnv);
  });

  describe('header injection', () => {
    it('adds X-API-Key header to requests', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      });
      globalThis.fetch = mockFetch;

      await apiClient('/test');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const headers = options.headers as Headers;
      expect(headers.get('X-API-Key')).toBe('test-api-key');
    });

    it('adds Content-Type header to requests', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      });
      globalThis.fetch = mockFetch;

      await apiClient('/test');

      const [, options] = mockFetch.mock.calls[0];
      const headers = options.headers as Headers;
      expect(headers.get('Content-Type')).toBe('application/json');
    });

    it('uses base URL from config', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      });
      globalThis.fetch = mockFetch;

      await apiClient('/api/v1/test');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('http://localhost:8080/api/v1/test');
    });
  });

  describe('response transformation', () => {
    it('transforms snake_case response keys to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { user_name: 'john', is_admin: true },
          }),
      });
      globalThis.fetch = mockFetch;

      const result = await apiClient<{
        status: string;
        data: { userName: string; isAdmin: boolean };
      }>('/test');

      expect(result).toEqual({
        status: 'ok',
        data: { userName: 'john', isAdmin: true },
      });
    });
  });

  describe('request body transformation', () => {
    it('transforms camelCase request body to snake_case', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      });
      globalThis.fetch = mockFetch;

      await apiClient('/test', {
        method: 'POST',
        body: { userName: 'john', isAdmin: true },
      });

      const [, options] = mockFetch.mock.calls[0];
      expect(JSON.parse(options.body)).toEqual({
        user_name: 'john',
        is_admin: true,
      });
    });
  });

  describe('error handling', () => {
    it('throws UnauthorizedError for 401 responses', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () =>
          Promise.resolve({
            detail: { code: 'UNAUTHORIZED', message: 'Invalid API key' },
          }),
      });
      globalThis.fetch = mockFetch;

      await expect(apiClient('/test')).rejects.toThrow(UnauthorizedError);
      await expect(apiClient('/test')).rejects.toThrow('Invalid API key');
    });

    it('throws ForbiddenError for 403 responses', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () =>
          Promise.resolve({
            detail: { code: 'FORBIDDEN', message: 'Admin role required' },
          }),
      });
      globalThis.fetch = mockFetch;

      await expect(apiClient('/test')).rejects.toThrow(ForbiddenError);
      await expect(apiClient('/test')).rejects.toThrow('Admin role required');
    });

    it('throws ApiError for other error responses', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () =>
          Promise.resolve({
            detail: { code: 'NOT_FOUND', message: 'Resource not found' },
          }),
      });
      globalThis.fetch = mockFetch;

      await expect(apiClient('/test')).rejects.toThrow(ApiError);
      await expect(apiClient('/test')).rejects.toThrow('Resource not found');
    });

    it('handles string detail in error response', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () => Promise.resolve({ detail: 'Validation error occurred' }),
      });
      globalThis.fetch = mockFetch;

      await expect(apiClient('/test')).rejects.toThrow('Validation error occurred');
    });

    it('handles non-JSON error responses', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('Not JSON')),
      });
      globalThis.fetch = mockFetch;

      await expect(apiClient('/test')).rejects.toThrow(ApiError);
      await expect(apiClient('/test')).rejects.toThrow('Internal Server Error');
    });
  });

  // Story 13.2: Version types transformation tests
  describe('version types transformation', () => {
    it('transforms VersionInfo from snake_case to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              version: '1.21.6',
              filename: 'vs_server_linux-x64_1.21.6.tar.gz',
              filesize: '40.2 MB',
              md5: 'abc123',
              cdn_url: 'https://cdn.example.com/vs_server_1.21.6.tar.gz',
              local_url: '/downloads/vs_server_1.21.6.tar.gz',
              is_latest: true,
              channel: 'stable',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const result = await apiClient<{
        status: string;
        data: {
          version: string;
          filename: string;
          filesize: string;
          md5: string;
          cdnUrl: string;
          localUrl: string;
          isLatest: boolean;
          channel: string;
        };
      }>('/api/v1alpha1/versions/1.21.6');

      expect(result.data).toEqual({
        version: '1.21.6',
        filename: 'vs_server_linux-x64_1.21.6.tar.gz',
        filesize: '40.2 MB',
        md5: 'abc123',
        cdnUrl: 'https://cdn.example.com/vs_server_1.21.6.tar.gz',
        localUrl: '/downloads/vs_server_1.21.6.tar.gz',
        isLatest: true,
        channel: 'stable',
      });
    });

    it('transforms VersionListResponse from snake_case to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              versions: [
                {
                  version: '1.21.6',
                  filename: 'vs_server_1.21.6.tar.gz',
                  filesize: '40.2 MB',
                  md5: 'abc123',
                  cdn_url: 'https://cdn.example.com/stable/1.21.6',
                  local_url: '/downloads/stable/1.21.6',
                  is_latest: true,
                  channel: 'stable',
                },
                {
                  version: '1.21.5',
                  filename: 'vs_server_1.21.5.tar.gz',
                  filesize: '39.8 MB',
                  md5: 'def456',
                  cdn_url: 'https://cdn.example.com/stable/1.21.5',
                  local_url: '/downloads/stable/1.21.5',
                  is_latest: false,
                  channel: 'stable',
                },
              ],
              total: 2,
              cached: true,
              cached_at: '2026-01-12T10:00:00Z',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const result = await apiClient<{
        status: string;
        data: {
          versions: Array<{
            version: string;
            cdnUrl: string;
            localUrl: string;
            isLatest: boolean;
          }>;
          total: number;
          cached: boolean;
          cachedAt: string;
        };
      }>('/api/v1alpha1/versions');

      expect(result.data.versions).toHaveLength(2);
      expect(result.data.versions[0].cdnUrl).toBe('https://cdn.example.com/stable/1.21.6');
      expect(result.data.versions[0].localUrl).toBe('/downloads/stable/1.21.6');
      expect(result.data.versions[0].isLatest).toBe(true);
      expect(result.data.versions[1].isLatest).toBe(false);
      expect(result.data.total).toBe(2);
      expect(result.data.cached).toBe(true);
      expect(result.data.cachedAt).toBe('2026-01-12T10:00:00Z');
    });

    it('transforms VersionDetailResponse from snake_case to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              version: {
                version: '1.21.6',
                filename: 'vs_server_1.21.6.tar.gz',
                filesize: '40.2 MB',
                md5: 'abc123',
                cdn_url: 'https://cdn.example.com/1.21.6',
                local_url: '/downloads/1.21.6',
                is_latest: true,
                channel: 'stable',
              },
              cached: false,
              cached_at: null,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const result = await apiClient<{
        status: string;
        data: {
          version: {
            version: string;
            cdnUrl: string;
            localUrl: string;
            isLatest: boolean;
            channel: string;
          };
          cached: boolean;
          cachedAt: string | null;
        };
      }>('/api/v1alpha1/versions/1.21.6');

      expect(result.data.version.cdnUrl).toBe('https://cdn.example.com/1.21.6');
      expect(result.data.version.localUrl).toBe('/downloads/1.21.6');
      expect(result.data.version.isLatest).toBe(true);
      expect(result.data.version.channel).toBe('stable');
      expect(result.data.cached).toBe(false);
      expect(result.data.cachedAt).toBe(null);
    });
  });
});
