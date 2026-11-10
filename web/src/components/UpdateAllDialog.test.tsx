import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { toast } from 'sonner';
import { UpdateAllDialog } from './UpdateAllDialog';
import type { ModUpdateStatus } from '@/api/types';

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function offer(
  slug: string,
  installed: string,
  offered: string,
  compatibility: 'compatible' | 'not_verified' = 'compatible'
): ModUpdateStatus {
  return {
    slug,
    name: slug.toUpperCase(),
    installedVersion: installed,
    status: 'update_available',
    offeredVersion: offered,
    offeredCompatibility: compatibility,
    offeredPrerelease: false,
    reason: null,
    checkedAt: null,
    error: null,
  };
}

const updates = [
  offer('alpha', '1.0.0', '1.1.0'),
  offer('beta', '2.0.0', '2.1.0', 'not_verified'),
  offer('delta', '4.0.0', '4.1.0'),
];

function summaryResponse(pendingRestart: boolean) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: {
          results: [
            {
              slug: 'alpha',
              name: 'ALPHA',
              from_version: '1.0.0',
              to_version: '1.1.0',
              outcome: 'updated',
              reasons: [],
              error: null,
            },
            {
              slug: 'beta',
              name: 'BETA',
              from_version: '2.0.0',
              to_version: '2.1.0',
              outcome: 'skipped',
              reasons: ['not_verified'],
              error: null,
            },
            {
              slug: 'delta',
              name: 'DELTA',
              from_version: '4.0.0',
              to_version: '4.1.0',
              outcome: 'failed',
              reasons: [],
              error: 'Failed to download mod',
            },
          ],
          updated: 1,
          skipped: 1,
          failed: 1,
          pending_restart: pendingRestart,
        },
      }),
  };
}

function renderDialog(onOpenChange = vi.fn()) {
  render(
    <UpdateAllDialog
      open
      onOpenChange={onOpenChange}
      updates={updates}
      gameVersion="1.22.7"
    />,
    { wrapper }
  );
  return onOpenChange;
}

describe('UpdateAllDialog', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('lists the planned updates and the not verified mods', () => {
    globalThis.fetch = vi.fn();
    renderDialog();

    const planned = screen.getByTestId('update-all-planned');
    expect(planned).toHaveTextContent('ALPHA v1.0.0 → v1.1.0');
    expect(planned).toHaveTextContent('DELTA v4.0.0 → v4.1.0');
    expect(planned).not.toHaveTextContent('BETA');
    expect(screen.getByText('Skipped: not verified for game version 1.22.7')).toBeInTheDocument();
    expect(screen.getByTestId('update-all-skipped')).toHaveTextContent('BETA v2.0.0 → v2.1.0');
    expect(screen.getByTestId('update-all-confirm')).toHaveTextContent('Update 2 mods');
  });

  it('shows each outcome and the restart message once', async () => {
    const mockFetch = vi.fn().mockResolvedValue(summaryResponse(true));
    globalThis.fetch = mockFetch;
    renderDialog();

    fireEvent.click(screen.getByTestId('update-all-confirm'));

    const results = await screen.findByTestId('update-all-results');
    expect(mockFetch.mock.calls[0][0]).toBe(
      'http://localhost:8080/api/v1alpha1/mods/updates/apply-all'
    );
    expect(mockFetch.mock.calls[0][1].method).toBe('POST');
    expect(screen.getByTestId('update-all-counts')).toHaveTextContent(
      '1 updated, 1 skipped, 1 failed'
    );
    const items = results.querySelectorAll('li');
    expect(items[0]).toHaveTextContent('ALPHA v1.0.0 → v1.1.0Updated');
    expect(items[1]).toHaveTextContent('Skipped: not verified');
    expect(items[2]).toHaveTextContent('Failed: Failed to download mod');
    expect(
      screen.getAllByText('A server restart is required for changes to take effect.')
    ).toHaveLength(1);
  });

  it('omits the restart message when no restart is needed', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(summaryResponse(false));
    renderDialog();

    fireEvent.click(screen.getByTestId('update-all-confirm'));

    await screen.findByTestId('update-all-results');
    expect(screen.queryByTestId('update-all-restart')).not.toBeInTheDocument();
  });

  it('sends nothing when cancelled', () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;
    const onOpenChange = renderDialog();

    fireEvent.click(screen.getByTestId('update-all-cancel'));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('closes with an error toast when the request fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: () =>
        Promise.resolve({
          detail: { code: 'MOD_UPDATE_ALL_IN_PROGRESS', message: 'Update all is already running' },
        }),
    });
    const onOpenChange = renderDialog();

    fireEvent.click(screen.getByTestId('update-all-confirm'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Update all failed', {
        description: 'Update all is already running',
      });
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('disables confirm when nothing is compatible', () => {
    globalThis.fetch = vi.fn();
    render(
      <UpdateAllDialog
        open
        onOpenChange={vi.fn()}
        updates={[offer('beta', '2.0.0', '2.1.0', 'not_verified')]}
        gameVersion="1.22.7"
      />,
      { wrapper }
    );

    expect(screen.getByTestId('update-all-confirm')).toBeDisabled();
  });
});
