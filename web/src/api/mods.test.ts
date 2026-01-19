import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchBrowseMods, fetchGameVersions } from './mods';
import type { ApiResponse, GameVersionsData, ModBrowseData } from './types';

describe('fetchBrowseMods', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockBrowseResponse: ApiResponse<ModBrowseData> = {
    status: 'ok',
    data: {
      mods: [
        {
          slug: 'test-mod',
          name: 'Test Mod',
          author: 'TestAuthor',
          summary: 'A test mod',
          downloads: 1000,
          follows: 50,
          trendingPoints: 100,
          side: 'both',
          modType: 'mod',
          logoUrl: 'https://example.com/logo.png',
          tags: ['utility', 'tools'],
          lastReleased: '2024-01-15T10:00:00Z',
        },
      ],
      pagination: {
        page: 1,
        pageSize: 20,
        totalItems: 100,
        totalPages: 5,
        hasNext: true,
        hasPrev: false,
      },
    },
  };

  it('calls the browse endpoint with no parameters', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse');
  });

  it('includes page parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ page: 2 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse?page=2');
  });

  it('includes pageSize parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ pageSize: 50 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse?page_size=50');
  });

  it('includes sort parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ sort: 'downloads' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse?sort=downloads');
  });

  it('combines multiple parameters correctly', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ page: 3, pageSize: 25, sort: 'trending' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/v1alpha1/mods/browse?');
    expect(url).toContain('page=3');
    expect(url).toContain('page_size=25');
    expect(url).toContain('sort=trending');
  });

  it('sends search parameter to API', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ search: 'test' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('search=test');
  });

  it('trims search parameter before sending', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ search: '  farming  ' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('search=farming');
  });

  it('does not send empty search parameter', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ search: '   ' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('search');
  });

  it('returns the API response with mods and pagination', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await fetchBrowseMods();

    expect(result.status).toBe('ok');
    expect(result.data.mods).toHaveLength(1);
    expect(result.data.mods[0].slug).toBe('test-mod');
    expect(result.data.pagination.totalItems).toBe(100);
  });

  it('includes page=0 when explicitly set (API validates min value)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    // page=0 is still sent - API will validate the min value
    await fetchBrowseMods({ page: 0 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse?page=0');
  });

  // VSS-vth: Game version filter tests
  it('includes version parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ version: '1.21.3' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('version=1.21.3');
  });

  it('trims version parameter before sending', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ version: '  1.21.3  ' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('version=1.21.3');
    expect(url).not.toContain('version=++');
  });

  it('does not send empty version parameter', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ version: '   ' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('version');
  });

  it('combines version with other parameters', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ page: 2, version: '1.21.3', search: 'farming' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('page=2');
    expect(url).toContain('version=1.21.3');
    expect(url).toContain('search=farming');
  });
});

// VSS-vth: Game versions endpoint tests
describe('fetchGameVersions', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockVersionsResponse: ApiResponse<GameVersionsData> = {
    status: 'ok',
    data: {
      versions: ['1.21.3', '1.21.2', '1.21.1', '1.21.0', '1.20.0'],
    },
  };

  it('calls the gameversions endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockVersionsResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchGameVersions();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/gameversions');
  });

  it('returns the list of versions', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockVersionsResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await fetchGameVersions();

    expect(result.status).toBe('ok');
    expect(result.data.versions).toHaveLength(5);
    expect(result.data.versions[0]).toBe('1.21.3');
  });
});
