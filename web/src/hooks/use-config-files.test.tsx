import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useConfigFiles,
  useConfigFileContent,
  useConfigDirectories,
} from './use-config-files';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Wrapper component for rendering hooks with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock responses
const mockConfigFilesResponse = {
  status: 'ok',
  data: {
    files: ['serverconfig.json', 'worldconfig.json', 'clientsettings.json'],
  },
};

const mockConfigFileContentResponse = {
  status: 'ok',
  data: {
    filename: 'serverconfig.json',
    content: {
      ServerName: 'My Test Server',
      Port: 42420,
      MaxClients: 16,
    },
  },
};

describe('useConfigFiles', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches config files from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFilesResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/files',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFilesResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns list of config files', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFilesResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.files).toEqual([
        'serverconfig.json',
        'worldconfig.json',
        'clientsettings.json',
      ]);
    });

    it('handles empty file list', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { files: [] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.files).toEqual([]);
    });

    it('handles error state', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'INTERNAL_ERROR',
              message: 'Something went wrong',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });
  });
});

describe('useConfigDirectories', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches directories from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { directories: ['ModConfigs', 'Playerdata', 'Macros'] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigDirectories(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/directories',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('returns list of directories', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { directories: ['ModConfigs', 'Playerdata'] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigDirectories(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.directories).toEqual([
        'ModConfigs',
        'Playerdata',
      ]);
    });

    it('fetches directories from subdirectory when directory param provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { directories: ['unpack', 'downloads'] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigDirectories('Cache'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/directories?directory=Cache',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('encodes special characters in directory param', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { directories: [] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigDirectories('Cache/My Folder'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/directories?directory=Cache%2FMy%20Folder',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });
  });
});

describe('useConfigFiles with directory parameter', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches files from subdirectory when directory param provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { files: ['mod1.json', 'mod2.json'] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles('ModConfigs'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/files?directory=ModConfigs',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('encodes special characters in directory param', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { files: [] },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFiles('My Folder'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/files?directory=My%20Folder',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });
  });
});

describe('useConfigFileContent', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches file content from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFileContentResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigFileContent('serverconfig.json'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/files/serverconfig.json',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('does not fetch when filename is null', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFileContentResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useConfigFileContent(null), {
        wrapper: createWrapper(queryClient),
      });

      // Wait a bit to ensure no fetch happens
      await new Promise((r) => setTimeout(r, 50));

      expect(mockFetch).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFileContentResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigFileContent('serverconfig.json'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns file content with filename and parsed JSON', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConfigFileContentResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigFileContent('serverconfig.json'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.filename).toBe('serverconfig.json');
      expect(result.current.data?.data.content).toEqual({
        ServerName: 'My Test Server',
        Port: 42420,
        MaxClients: 16,
      });
    });

    it('handles error when file not found', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'CONFIG_FILE_NOT_FOUND',
              message: 'Config file not found: nonexistent.json',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigFileContent('nonexistent.json'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it('encodes special characters in filename', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              filename: 'file with spaces.json',
              content: {},
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useConfigFileContent('file with spaces.json'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/config/files/file%20with%20spaces.json'),
        expect.any(Object)
      );
    });

    it('fetches new content when filename changes', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockConfigFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                filename: 'worldconfig.json',
                content: { WorldName: 'Test World' },
              },
            }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result, rerender } = renderHook(
        ({ filename }: { filename: string | null }) =>
          useConfigFileContent(filename),
        {
          wrapper: createWrapper(queryClient),
          initialProps: { filename: 'serverconfig.json' },
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data.filename).toBe('serverconfig.json');

      // Change filename
      rerender({ filename: 'worldconfig.json' });

      await waitFor(() =>
        expect(result.current.data?.data.filename).toBe('worldconfig.json')
      );
      expect(result.current.data?.data.content).toEqual({
        WorldName: 'Test World',
      });
    });
  });
});
