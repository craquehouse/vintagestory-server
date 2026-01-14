import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { uninstallServer } from './server';

/**
 * Server API Tests - Story 13.7
 *
 * Tests for the uninstallServer API function.
 */

describe('uninstallServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('calls DELETE /api/v1alpha1/server endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          data: { state: 'not_installed' },
        }),
    });
    globalThis.fetch = mockFetch;

    await uninstallServer();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/server');
    expect(options.method).toBe('DELETE');
  });

  it('returns success response with not_installed state', async () => {
    const mockResponse = {
      status: 'ok',
      data: { state: 'not_installed' },
    };
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await uninstallServer();

    expect(result).toEqual(mockResponse);
  });

  it('throws error when server is running (409)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: () =>
        Promise.resolve({
          detail: 'Server is running',
          code: 'SERVER_RUNNING',
        }),
    });
    globalThis.fetch = mockFetch;

    await expect(uninstallServer()).rejects.toThrow();
  });

  it('throws error when server is not installed (404)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () =>
        Promise.resolve({
          detail: 'Server not installed',
          code: 'SERVER_NOT_INSTALLED',
        }),
    });
    globalThis.fetch = mockFetch;

    await expect(uninstallServer()).rejects.toThrow();
  });
});
