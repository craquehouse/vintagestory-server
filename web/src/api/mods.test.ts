import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  fetchBrowseMods,
  fetchGameVersions,
  fetchMods,
  lookupMod,
  installMod,
  enableMod,
  disableMod,
  removeMod,
  fetchModTags,
} from './mods';
import type {
  ApiResponse,
  GameVersionsData,
  ModBrowseData,
  ModsListData,
  ModLookupData,
  ModInstallData,
  ModEnableDisableData,
  ModRemoveData,
  ModTagsData,
} from './types';

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
          urlalias: 'test-mod',
          assetId: 12345,
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

  // VSS-y7u: Server-side filter tests
  it('includes side parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ side: 'server' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('side=server');
  });

  it('includes modType parameter when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ modType: 'mod' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('mod_type=mod');
  });

  it('includes tags parameter as comma-separated string', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ tags: ['farming', 'tools', 'utility'] });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('tags=farming%2Ctools%2Cutility');
  });

  it('handles single tag in array', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ tags: ['farming'] });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('tags=farming');
  });

  it('does not send tags parameter when empty array', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ tags: [] });

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('tags');
  });

  it('excludes name sort parameter (client-side only)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ sort: 'name' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('sort');
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/browse');
  });

  it('combines all filter types correctly', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({
      page: 2,
      pageSize: 50,
      sort: 'downloads',
      search: 'farming',
      version: '1.21.3',
      side: 'both',
      modType: 'mod',
      tags: ['farming', 'crops'],
    });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=50');
    expect(url).toContain('sort=downloads');
    expect(url).toContain('search=farming');
    expect(url).toContain('version=1.21.3');
    expect(url).toContain('side=both');
    expect(url).toContain('mod_type=mod');
    expect(url).toContain('tags=farming%2Ccrops');
  });

  it('handles special characters in search parameter', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ search: 'mod & tool' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('search=mod+%26+tool');
  });

  it('handles special characters in version parameter', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchBrowseMods({ version: '1.21.3-rc.1' });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('version=1.21.3-rc.1');
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

// VSS-y7u: Mod tags endpoint tests
describe('fetchModTags', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockTagsResponse: ApiResponse<ModTagsData> = {
    status: 'ok',
    data: {
      tags: ['farming', 'tools', 'utility', 'decorative', 'magic'],
    },
  };

  it('calls the tags endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTagsResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchModTags();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/tags');
  });

  it('returns the list of tags', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTagsResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await fetchModTags();

    expect(result.status).toBe('ok');
    expect(result.data.tags).toHaveLength(5);
    expect(result.data.tags).toContain('farming');
    expect(result.data.tags).toContain('magic');
  });
});

describe('fetchMods', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockModsResponse: ApiResponse<ModsListData> = {
    status: 'ok',
    data: {
      mods: [
        {
          filename: 'testmod.zip',
          slug: 'testmod',
          version: '1.0.0',
          enabled: true,
          installedAt: '2026-01-15T10:00:00Z',
          assetId: 12345,
          name: 'Test Mod',
          authors: ['TestAuthor'],
          description: 'A test mod',
          side: 'Both',
        },
      ],
      pendingRestart: false,
    },
  };

  it('calls the mods list endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockModsResponse),
    });
    globalThis.fetch = mockFetch;

    await fetchMods();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods');
  });

  it('returns the list of installed mods', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockModsResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await fetchMods();

    expect(result.status).toBe('ok');
    expect(result.data.mods).toHaveLength(1);
    expect(result.data.mods[0].slug).toBe('testmod');
    expect(result.data.mods[0].enabled).toBe(true);
    expect(result.data.pendingRestart).toBe(false);
  });
});

describe('lookupMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockLookupResponse: ApiResponse<ModLookupData> = {
    status: 'ok',
    data: {
      slug: 'testmod',
      urlalias: 'test-mod',
      assetId: 12345,
      name: 'Test Mod',
      author: 'TestAuthor',
      description: 'A comprehensive test mod',
      latestVersion: '1.0.0',
      downloads: 1000,
      follows: 50,
      side: 'Both',
      compatibility: {
        status: 'compatible',
        gameVersion: '1.21.3',
        modVersion: '1.0.0',
        message: 'Compatible with game version',
      },
      logoUrl: 'https://example.com/logo.png',
      releases: [],
      tags: ['utility', 'tools'],
      homepageUrl: 'https://example.com',
      sourceUrl: 'https://github.com/example/testmod',
      created: '2024-01-01T00:00:00Z',
      lastReleased: '2024-01-15T10:00:00Z',
    },
  };

  it('calls the lookup endpoint with URL-encoded slug', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockLookupResponse),
    });
    globalThis.fetch = mockFetch;

    await lookupMod('testmod');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/lookup/testmod');
  });

  it('URL-encodes special characters in slug', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockLookupResponse),
    });
    globalThis.fetch = mockFetch;

    await lookupMod('mod/with/slashes');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/lookup/mod%2Fwith%2Fslashes');
  });

  it('URL-encodes URLs with protocols', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockLookupResponse),
    });
    globalThis.fetch = mockFetch;

    await lookupMod('https://mods.vintagestory.at/testmod');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('lookup/https%3A%2F%2Fmods.vintagestory.at%2Ftestmod');
  });

  it('returns mod details with compatibility information', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockLookupResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await lookupMod('testmod');

    expect(result.status).toBe('ok');
    expect(result.data.slug).toBe('testmod');
    expect(result.data.name).toBe('Test Mod');
    expect(result.data.compatibility.status).toBe('compatible');
  });
});

describe('installMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockInstallResponse: ApiResponse<ModInstallData> = {
    status: 'ok',
    data: {
      slug: 'testmod',
      version: '1.0.0',
      filename: 'testmod-1.0.0.zip',
      compatibility: 'compatible',
      pendingRestart: true,
    },
  };

  it('calls the install endpoint with POST method', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockInstallResponse),
    });
    globalThis.fetch = mockFetch;

    await installMod('testmod');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods');
    expect(options.method).toBe('POST');
  });

  it('sends slug in request body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockInstallResponse),
    });
    globalThis.fetch = mockFetch;

    await installMod('testmod');

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.slug).toBe('testmod');
  });

  it('sends version in request body when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockInstallResponse),
    });
    globalThis.fetch = mockFetch;

    await installMod('testmod', '1.2.3');

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.slug).toBe('testmod');
    expect(body.version).toBe('1.2.3');
  });

  it('returns installation result', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockInstallResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await installMod('testmod');

    expect(result.status).toBe('ok');
    expect(result.data.slug).toBe('testmod');
    expect(result.data.compatibility).toBe('compatible');
    expect(result.data.pendingRestart).toBe(true);
  });
});

describe('enableMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockEnableResponse: ApiResponse<ModEnableDisableData> = {
    status: 'ok',
    data: {
      slug: 'testmod',
      enabled: true,
      pendingRestart: true,
    },
  };

  it('calls the enable endpoint with POST method', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockEnableResponse),
    });
    globalThis.fetch = mockFetch;

    await enableMod('testmod');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/testmod/enable');
    expect(options.method).toBe('POST');
  });

  it('URL-encodes special characters in slug', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockEnableResponse),
    });
    globalThis.fetch = mockFetch;

    await enableMod('mod-with-special@chars');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('mods/mod-with-special%40chars/enable');
  });

  it('returns enable result with pending restart status', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockEnableResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await enableMod('testmod');

    expect(result.status).toBe('ok');
    expect(result.data.slug).toBe('testmod');
    expect(result.data.enabled).toBe(true);
    expect(result.data.pendingRestart).toBe(true);
  });
});

describe('disableMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockDisableResponse: ApiResponse<ModEnableDisableData> = {
    status: 'ok',
    data: {
      slug: 'testmod',
      enabled: false,
      pendingRestart: true,
    },
  };

  it('calls the disable endpoint with POST method', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDisableResponse),
    });
    globalThis.fetch = mockFetch;

    await disableMod('testmod');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/testmod/disable');
    expect(options.method).toBe('POST');
  });

  it('URL-encodes special characters in slug', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDisableResponse),
    });
    globalThis.fetch = mockFetch;

    await disableMod('mod/with/slashes');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('mods/mod%2Fwith%2Fslashes/disable');
  });

  it('returns disable result with pending restart status', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDisableResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await disableMod('testmod');

    expect(result.status).toBe('ok');
    expect(result.data.slug).toBe('testmod');
    expect(result.data.enabled).toBe(false);
    expect(result.data.pendingRestart).toBe(true);
  });
});

describe('removeMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  const mockRemoveResponse: ApiResponse<ModRemoveData> = {
    status: 'ok',
    data: {
      slug: 'testmod',
      pendingRestart: true,
    },
  };

  it('calls the remove endpoint with DELETE method', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRemoveResponse),
    });
    globalThis.fetch = mockFetch;

    await removeMod('testmod');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('http://localhost:8080/api/v1alpha1/mods/testmod');
    expect(options.method).toBe('DELETE');
  });

  it('URL-encodes special characters in slug', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRemoveResponse),
    });
    globalThis.fetch = mockFetch;

    await removeMod('mod with spaces');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('mods/mod%20with%20spaces');
  });

  it('returns remove result with pending restart status', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockRemoveResponse),
    });
    globalThis.fetch = mockFetch;

    const result = await removeMod('testmod');

    expect(result.status).toBe('ok');
    expect(result.data.slug).toBe('testmod');
    expect(result.data.pendingRestart).toBe(true);
  });
});
