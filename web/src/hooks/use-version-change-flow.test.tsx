import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';
import { useVersionChangeFlow, type VersionChangeRequest } from './use-version-change-flow';

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

const update: VersionChangeRequest = {
  slug: 'carryon',
  name: 'Carry On',
  version: '1.14.3',
  installedVersion: '1.14.1',
  kind: 'update',
};

function ok(data: Record<string, unknown>) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: {
          slug: 'carryon',
          previous_version: '1.14.1',
          version: '1.14.3',
          filename: 'carryon_1.14.3.zip',
          compatibility: 'compatible',
          changed: true,
          pending_restart: false,
          ...data,
        },
      }),
  };
}

function conflict(code: string, details?: Record<string, unknown>) {
  return {
    ok: false,
    status: 409,
    statusText: 'Conflict',
    json: () => Promise.resolve({ detail: { code, message: `${code} message`, details } }),
  };
}

function bodies(mockFetch: ReturnType<typeof vi.fn>) {
  return mockFetch.mock.calls.map(([, options]) => JSON.parse(options.body));
}

describe('useVersionChangeFlow', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('applies a compatible update without confirmation', async () => {
    const mockFetch = vi.fn().mockResolvedValue(ok({}));
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Updated Carry On to v1.14.3', {
        description: undefined,
      });
    });
    expect(result.current.confirmation).toBeNull();
    expect(bodies(mockFetch)).toEqual([{ version: '1.14.3', confirm: false }]);
    expect(mockFetch.mock.calls[0][0]).toBe(
      'http://localhost:8080/api/v1alpha1/mods/carryon/version'
    );
  });

  it('says a restart is required when the server is running', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ pending_restart: true }));
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start({ ...update, kind: 'switch', version: '1.14.0' }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Switched Carry On to v1.14.3', {
        description: 'A server restart is required for changes to take effect.',
      });
    });
  });

  it('reports a change that was not needed', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(ok({ changed: false, version: '1.14.1' }));
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start({ ...update, version: '1.14.1' }));

    await waitFor(() => {
      expect(toast.info).toHaveBeenCalledWith('Carry On is already at v1.14.1');
    });
  });

  it('holds a confirmation with the reasons instead of changing', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(
        conflict('MOD_CONFIRMATION_REQUIRED', {
          reasons: ['older', 'not_verified', 'something_new'],
          compatibility: 'not_verified',
        })
      );
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));

    await waitFor(() => expect(result.current.confirmation).not.toBeNull());
    expect(result.current.confirmation).toEqual({
      ...update,
      reasons: ['older', 'not_verified'],
    });
    expect(toast.error).not.toHaveBeenCalled();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('retries with confirm true when confirmed', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(conflict('MOD_CONFIRMATION_REQUIRED', { reasons: ['prerelease'] }))
      .mockResolvedValueOnce(ok({ version: '2.0.0-rc.1' }));
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start({ ...update, version: '2.0.0-rc.1' }));
    await waitFor(() => expect(result.current.confirmation).not.toBeNull());
    act(() => result.current.confirm());

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Updated Carry On to v2.0.0-rc.1', {
        description: undefined,
      });
    });
    expect(result.current.confirmation).toBeNull();
    expect(bodies(mockFetch)).toEqual([
      { version: '2.0.0-rc.1', confirm: false },
      { version: '2.0.0-rc.1', confirm: true },
    ]);
  });

  it('makes no further request when cancelled', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(conflict('MOD_CONFIRMATION_REQUIRED', { reasons: ['older'] }));
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));
    await waitFor(() => expect(result.current.confirmation).not.toBeNull());
    act(() => result.current.cancel());

    expect(result.current.confirmation).toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(toast.success).not.toHaveBeenCalled();
  });

  it('shows the API message when a change fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(conflict('MOD_VERSION_CHANGE_IN_PROGRESS'));
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update Carry On', {
        description: 'MOD_VERSION_CHANGE_IN_PROGRESS message',
      });
    });
    expect(result.current.confirmation).toBeNull();
  });

  it('reports the slug in flight', async () => {
    let resolve: (value: unknown) => void = () => {};
    globalThis.fetch = vi.fn().mockReturnValue(new Promise((r) => (resolve = r)));
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));

    await waitFor(() => expect(result.current.isPending('carryon')).toBe(true));
    await act(async () => resolve(ok({})));
    await waitFor(() => expect(result.current.isPending('carryon')).toBe(false));
  });

  it('does not reopen the confirmation when the confirmed retry asks again', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(conflict('MOD_CONFIRMATION_REQUIRED', { reasons: ['older'] }));
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));
    await waitFor(() => expect(result.current.confirmation).not.toBeNull());
    act(() => result.current.confirm());

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update Carry On', {
        description: 'MOD_CONFIRMATION_REQUIRED message',
      });
    });
    expect(result.current.confirmation).toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('reports every change when two run at once', async () => {
    const resolvers: Array<(value: unknown) => void> = [];
    const mockFetch = vi
      .fn()
      .mockImplementation(() => new Promise((r) => resolvers.push(r)));
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useVersionChangeFlow(), { wrapper });

    act(() => result.current.start(update));
    act(() =>
      result.current.start({ ...update, slug: 'demo', name: 'Demo', version: '1.1.0' })
    );

    await waitFor(() => expect(resolvers).toHaveLength(2));
    expect(result.current.isPending('carryon')).toBe(true);
    expect(result.current.isPending('demo')).toBe(true);

    await act(async () => resolvers[0](ok({})));
    await waitFor(() => expect(result.current.isPending('carryon')).toBe(false));
    expect(result.current.isPending('demo')).toBe(true);
    expect(toast.success).toHaveBeenCalledWith('Updated Carry On to v1.14.3', {
      description: undefined,
    });

    await act(async () =>
      resolvers[1](conflict('MOD_CONFIRMATION_REQUIRED', { reasons: ['older'] }))
    );
    await waitFor(() => expect(result.current.confirmation?.slug).toBe('demo'));
    expect(result.current.isPending('demo')).toBe(false);
  });
});

