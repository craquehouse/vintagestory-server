/**
 * UnusedFilesNotice tests (Story 24.6, FR339, Epic 24 ADR-3).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { queryKeys } from '@/api/query-keys';
import type { UnusedFile } from '@/api/types';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

import { toast } from 'sonner';
import { UnusedFilesNotice, formatFileSize, unusedReason } from './UnusedFilesNotice';

function file(overrides: Partial<UnusedFile> = {}): UnusedFile {
  return {
    name: 'old.zip.bak',
    sizeBytes: 2048,
    modifiedAt: new Date(Date.now() - 3 * 86400 * 1000).toISOString(),
    reason: 'leftover',
    installedAs: null,
    ...overrides,
  };
}

function setup(
  role: string,
  files: UnusedFile[],
  remove: () => Promise<Partial<Response>> = () =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { name: 'x', pending_restart: false } }),
    })
) {
  let listed = files;
  const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (url.includes('/mods/unused-files/') && init?.method === 'DELETE') {
      const name = decodeURIComponent(url.split('/unused-files/')[1]);
      return remove().then((response) => {
        if (response.ok) listed = listed.filter((f) => f.name !== name);
        return response;
      });
    }
    if (url.includes('/mods/unused-files')) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              files: listed.map((f) => ({
                name: f.name,
                size_bytes: f.sizeBytes,
                modified_at: f.modifiedAt,
                reason: f.reason,
                installed_as: f.installedAs,
              })),
            },
          }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ status: 'ok', data: {} }) });
  });
  globalThis.fetch = fetchMock;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  render(<UnusedFilesNotice />, { wrapper: Wrapper });
  return fetchMock;
}

describe('UnusedFilesNotice', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('says how many files are not used, collapsed at first', async () => {
    setup('admin', [file(), file({ name: 'x.tmp' })]);

    const toggle = await screen.findByTestId('unused-files-toggle');
    expect(toggle).toHaveTextContent('2 files in the mods folder are not used');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByTestId('unused-files-list')).not.toBeVisible();
    expect(toggle).toHaveAttribute('aria-controls', 'unused-files-list');
  });

  it('uses the singular for one file', async () => {
    setup('admin', [file()]);

    expect(await screen.findByTestId('unused-files-toggle')).toHaveTextContent(
      '1 file in the mods folder is not used'
    );
  });

  it('expands to each file with its size, age and reason', async () => {
    setup('admin', [
      file(),
      file({
        name: 'carryon_0.9.zip',
        sizeBytes: 3 * 1024 * 1024,
        reason: 'duplicate_mod_id',
        installedAs: 'carryon_1.0.zip',
      }),
    ]);

    fireEvent.click(await screen.findByTestId('unused-files-toggle'));

    expect(screen.getByTestId('unused-files-toggle')).toHaveAttribute('aria-expanded', 'true');
    const bak = screen.getByTestId('unused-file-old.zip.bak');
    expect(bak).toHaveTextContent('2.0 KiB');
    expect(bak).toHaveTextContent('3 days ago');
    expect(bak).toHaveTextContent('Leftover temporary or backup file');
    expect(screen.getByTestId('unused-file-carryon_0.9.zip')).toHaveTextContent(
      'Another copy of a mod installed as carryon_1.0.zip'
    );
  });

  it('deletes a file after confirming, and the notice goes when none are left', async () => {
    const fetchMock = setup('admin', [file()]);

    fireEvent.click(await screen.findByTestId('unused-files-toggle'));
    fireEvent.click(screen.getByTestId('unused-file-delete-old.zip.bak'));
    expect(screen.getByTestId('unused-file-delete-dialog')).toHaveTextContent(
      'Delete old.zip.bak?'
    );
    fireEvent.click(screen.getByTestId('unused-file-delete-confirm'));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith('Deleted old.zip.bak', {
        description: undefined,
      })
    );
    const deletes = fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE');
    expect(deletes.map(([url]) => url)).toEqual([
      expect.stringContaining('/api/v1alpha1/mods/unused-files/old.zip.bak'),
    ]);
    await waitFor(() =>
      expect(screen.queryByTestId('unused-files-notice')).not.toBeInTheDocument()
    );
  });

  it('deletes nothing when the dialog is cancelled', async () => {
    const fetchMock = setup('admin', [file()]);

    fireEvent.click(await screen.findByTestId('unused-files-toggle'));
    fireEvent.click(screen.getByTestId('unused-file-delete-old.zip.bak'));
    fireEvent.click(screen.getByTestId('unused-file-delete-cancel'));

    await waitFor(() =>
      expect(screen.queryByTestId('unused-file-delete-dialog')).not.toBeInTheDocument()
    );
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false);
    expect(screen.getByTestId('unused-files-notice')).toBeInTheDocument();
  });

  it('reports a refused delete', async () => {
    setup('admin', [file()], () =>
      Promise.resolve({
        ok: false,
        status: 409,
        statusText: 'Conflict',
        json: () =>
          Promise.resolve({
            detail: { code: 'MODS_BUSY', message: 'A mod install is running.' },
          }),
      })
    );

    fireEvent.click(await screen.findByTestId('unused-files-toggle'));
    fireEvent.click(screen.getByTestId('unused-file-delete-old.zip.bak'));
    fireEvent.click(screen.getByTestId('unused-file-delete-confirm'));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Could not delete old.zip.bak', {
        description: 'A mod install is running.',
      })
    );
    // As Story 21.4: the dialog stays open with Delete enabled again
    expect(screen.getByTestId('unused-file-delete-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('unused-file-delete-confirm')).toBeEnabled();
  });

  it('keeps the dialog open and locked while the delete runs', async () => {
    let answer: (response: Partial<Response>) => void = () => {};
    setup(
      'admin',
      [file()],
      () =>
        new Promise((resolve) => {
          answer = resolve;
        })
    );

    fireEvent.click(await screen.findByTestId('unused-files-toggle'));
    fireEvent.click(screen.getByTestId('unused-file-delete-old.zip.bak'));
    fireEvent.click(screen.getByTestId('unused-file-delete-confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('unused-file-delete-confirm')).toHaveTextContent('Deleting...')
    );
    expect(screen.getByTestId('unused-file-delete-confirm')).toBeDisabled();
    expect(screen.getByTestId('unused-file-delete-cancel')).toBeDisabled();
    fireEvent.keyDown(screen.getByTestId('unused-file-delete-dialog'), { key: 'Escape' });
    expect(screen.getByTestId('unused-file-delete-dialog')).toBeInTheDocument();

    answer({
      ok: true,
      json: () =>
        Promise.resolve({ status: 'ok', data: { name: 'old.zip.bak', pending_restart: false } }),
    });
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByTestId('unused-file-delete-dialog')).not.toBeInTheDocument()
    );
  });

  it('says so when the mods folder cannot be checked', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({ detail: { code: 'INTERNAL_ERROR', message: 'boom' } }),
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role: 'admin' } });
    render(
      <QueryClientProvider client={queryClient}>
        <UnusedFilesNotice />
      </QueryClientProvider>
    );

    expect(await screen.findByTestId('unused-files-error')).toHaveTextContent(
      'Could not check the mods folder for unused files.'
    );
  });

  it('renders nothing when the folder holds no unused files', async () => {
    const fetchMock = setup('admin', []);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByTestId('unused-files-notice')).not.toBeInTheDocument();
  });

  it('shows nothing to a Monitor key and never asks for the list', async () => {
    const fetchMock = setup('monitor', [file()]);

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByTestId('unused-files-notice')).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('formatFileSize', () => {
  it.each([
    [512, '512 B'],
    [1536, '1.5 KiB'],
    [5 * 1024 * 1024 + 300 * 1024, '5.3 MiB'],
  ])('formats %d bytes as %s', (bytes, text) => {
    expect(formatFileSize(bytes)).toBe(text);
  });
});

describe('unusedReason', () => {
  it('names the reason of each kind', () => {
    expect(unusedReason(file({ reason: 'unreadable' }))).toBe(
      'Archive without a readable modinfo.json'
    );
    expect(unusedReason(file({ reason: 'duplicate_mod_id', installedAs: null }))).toBe(
      'Another copy of an installed mod'
    );
  });
});
