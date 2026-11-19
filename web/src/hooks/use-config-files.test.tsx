import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useConfigFiles,
  useConfigFileContent,
  useConfigDirectories,
  useSaveConfigFile,
  useConfigTextCheck,
} from './use-config-files';
import { act } from '@testing-library/react';
import { queryKeys } from '@/api/query-keys';

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
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
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

      expect(result.current.data?.data.directories).toEqual(['ModConfigs', 'Playerdata']);
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
      const { result } = renderHook(() => useConfigDirectories(['Cache']), {
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
      const { result } = renderHook(() => useConfigDirectories(['Cache', 'My Folder']), {
        wrapper: createWrapper(queryClient),
      });

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
      const { result } = renderHook(() => useConfigFiles(['ModConfigs']), {
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
      const { result } = renderHook(() => useConfigFiles(['My Folder']), {
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
      const { result } = renderHook(() => useConfigFileContent(['serverconfig.json']), {
        wrapper: createWrapper(queryClient),
      });

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
      const { result } = renderHook(() => useConfigFileContent(['serverconfig.json']), {
        wrapper: createWrapper(queryClient),
      });

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
      const { result } = renderHook(() => useConfigFileContent(['serverconfig.json']), {
        wrapper: createWrapper(queryClient),
      });

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
      const { result } = renderHook(() => useConfigFileContent(['nonexistent.json']), {
        wrapper: createWrapper(queryClient),
      });

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
      const { result } = renderHook(() => useConfigFileContent(['file with spaces.json']), {
        wrapper: createWrapper(queryClient),
      });

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
        ({ path }: { path: readonly string[] | null }) => useConfigFileContent(path),
        {
          wrapper: createWrapper(queryClient),
          initialProps: { path: ['serverconfig.json'] as readonly string[] | null },
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.data.filename).toBe('serverconfig.json');

      // Change filename
      rerender({ path: ['worldconfig.json'] });

      await waitFor(() => expect(result.current.data?.data.filename).toBe('worldconfig.json'));
      expect(result.current.data?.data.content).toEqual({
        WorldName: 'Test World',
      });
    });
  });
});

// Story 23.5: saving and checking config file text
describe('useSaveConfigFile', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("refetches the file's read after a save", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { filename: 'x.json', version: 'v2' } }),
    });
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(queryKeys.config.file('ModConfig/x.json'), { status: 'ok' });
    const { result } = renderHook(() => useSaveConfigFile(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        path: ['ModConfig', 'x.json'],
        text: '{}',
        version: 'v1',
      });
    });

    expect(
      queryClient.getQueryState(queryKeys.config.file('ModConfig/x.json'))?.isInvalidated
    ).toBe(true);
  });
});

describe('useConfigTextCheck', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  function answer(valid: boolean) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          data: valid
            ? { valid: true, parse_error: null }
            : { valid: false, parse_error: { message: 'm', line: 1, column: 2 } },
        }),
    });
  }

  it('checks on opening, then the latest text once typing has paused for 500 ms', async () => {
    answer(true);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { result, rerender } = renderHook(
      ({ text }: { text: string }) => useConfigTextCheck(['x.json'], text, true),
      { wrapper: createWrapper(createTestQueryClient()), initialProps: { text: '{' } }
    );

    rerender({ text: '{"' });
    rerender({ text: '{}' });
    expect(result.current.isPending).toBe(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });

    await waitFor(() => expect(result.current.check).toEqual({ valid: true, parseError: null }));
    expect(result.current.isPending).toBe(false);
    const bodies = vi
      .mocked(globalThis.fetch)
      .mock.calls.map(([, init]) => JSON.parse(String((init as RequestInit).body)) as object);
    expect(bodies).toEqual([
      { filename: 'x.json', text: '{' },
      { filename: 'x.json', text: '{}' },
    ]);
  });

  it('reports an invalid text with its position', async () => {
    answer(false);
    const { result } = renderHook(() => useConfigTextCheck(['x.json'], '{,}', true), {
      wrapper: createWrapper(createTestQueryClient()),
    });

    await waitFor(() =>
      expect(result.current.check).toEqual({
        valid: false,
        parseError: { message: 'm', line: 1, column: 2 },
      })
    );
  });

  it('sends nothing when disabled', async () => {
    answer(true);
    renderHook(() => useConfigTextCheck(['x.json'], '{}', false), {
      wrapper: createWrapper(createTestQueryClient()),
    });

    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
