import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { type ReactNode } from 'react';
import { toast } from 'sonner';
import { ConfigHistoryPanel, formatSize, relativeTime } from './ConfigHistoryPanel';

vi.mock('@/components/code-view/LazyCodeView', () => import('@/test/mocks/lazy-code-view'));
vi.mock(
  '@/components/code-view/LazyRevisionCompare',
  () => import('@/test/mocks/lazy-revision-compare')
);
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const media = vi.hoisted(() => ({ wide: true }));
vi.mock('@/hooks/use-media-query', () => ({ useMediaQuery: () => media.wide }));

const REVISIONS = [
  { id: 'r2', saved_at: '2026-11-19T11:00:00Z', saved_by: 'admin', size: 2048, sha256: 'b' },
  { id: 'r1', saved_at: '2026-11-18T11:00:00Z', saved_by: 'admin', size: 10, sha256: 'a' },
];

function stubApi(
  options: { revisions?: unknown[]; restore?: { status: number; body: unknown } } = {}
) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  globalThis.fetch = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    calls.push({ method, url, body: init?.body ? JSON.parse(String(init.body)) : null });
    const json = (status: number, body: unknown) => ({
      ok: status < 400,
      status,
      statusText: String(status),
      json: () => Promise.resolve(body),
    });
    if (method === 'POST' && url.endsWith('/restore')) {
      const answer = options.restore ?? {
        status: 200,
        body: { status: 'ok', data: { filename: 'ModConfig/x.json', version: 'v2' } },
      };
      return json(answer.status, answer.body);
    }
    if (url.includes('?revision=')) {
      return json(200, {
        status: 'ok',
        data: { filename: 'ModConfig/x.json', revision: REVISIONS[1], text: '{"old": true}' },
      });
    }
    return json(200, {
      status: 'ok',
      data: { filename: 'ModConfig/x.json', revisions: options.revisions ?? REVISIONS },
    });
  });
  return calls;
}

function setup(props: Partial<Parameters<typeof ConfigHistoryPanel>[0]> = {}) {
  const onClose = vi.fn();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  }
  render(
    <ConfigHistoryPanel
      path={['ModConfig', 'x.json']}
      displayPath="ModConfig/x.json"
      currentText='{"now": true}'
      currentVersion="v1"
      serverStopped
      wordWrap={false}
      onClose={onClose}
      {...props}
    />,
    { wrapper: Wrapper }
  );
  return { onClose };
}

async function choose(id = 'r1') {
  await waitFor(() => expect(screen.getByTestId(`config-history-item-${id}`)).toBeInTheDocument());
  fireEvent.click(screen.getByTestId(`config-history-item-${id}`));
  await waitFor(() => expect(screen.getByTestId('config-history-restore')).toBeEnabled());
}

describe('ConfigHistoryPanel (Story 23.7)', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
    media.wide = true;
  });

  it('lists the versions newest first with who saved them and their size', async () => {
    stubApi();
    setup();

    await waitFor(() => expect(screen.getByTestId('config-history-list')).toBeInTheDocument());
    const items = screen.getAllByRole('button', { name: /admin/ });
    expect(items.map((item) => item.dataset.testid)).toEqual([
      'config-history-item-r2',
      'config-history-item-r1',
    ]);
    expect(items[0]).toHaveTextContent('2.0 KiB');
    expect(items[1]).toHaveTextContent('10 B');
  });

  it('says when there are no earlier versions', async () => {
    stubApi({ revisions: [] });
    setup();

    expect(await screen.findByTestId('config-history-empty')).toHaveTextContent(
      'No earlier versions. Versions are kept when the file is saved here.'
    );
  });

  it('compares a chosen version side by side on a wide screen', async () => {
    stubApi();
    setup();
    await choose();

    const compare = screen.getByTestId('config-history-compare');
    expect(compare).toHaveAttribute('data-split', 'true');
    expect(screen.getByTestId('compare-original')).toHaveTextContent('{"old": true}');
    expect(screen.getByTestId('compare-current')).toHaveTextContent('{"now": true}');
  });

  it('compares unified on a narrow screen', async () => {
    media.wide = false;
    stubApi();
    setup();
    await choose();

    expect(screen.getByTestId('config-history-compare')).toHaveAttribute('data-split', 'false');
  });

  it('shows the version alone, and back', async () => {
    stubApi();
    setup();
    await choose();

    fireEvent.click(screen.getByTestId('config-history-toggle'));
    expect(screen.getByTestId('config-history-version')).toHaveValue('{"old": true}');

    fireEvent.click(screen.getByTestId('config-history-toggle'));
    expect(screen.getByTestId('config-history-compare')).toBeInTheDocument();
  });

  it('restores after confirmation with the current version', async () => {
    const calls = stubApi();
    const { onClose } = setup();
    await choose();

    fireEvent.click(screen.getByTestId('config-history-restore'));
    expect(
      await screen.findByText(/The current text is kept in the history\./)
    ).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Restore' }));
    });

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(calls.find((c) => c.method === 'POST')).toEqual({
      method: 'POST',
      url: expect.stringContaining('/config/history/ModConfig%2Fx.json/restore'),
      body: { revision: 'r1', version: 'v1' },
    });
    expect(toast.success).toHaveBeenCalledWith('Restored ModConfig/x.json');
  });

  it('shows a refused restore', async () => {
    stubApi({
      restore: {
        status: 409,
        body: { detail: { code: 'CONFIG_FILE_CHANGED', message: 'The file changed on disk' } },
      },
    });
    const { onClose } = setup();
    await choose();

    fireEvent.click(screen.getByTestId('config-history-restore'));
    await act(async () => {
      fireEvent.click(await screen.findByRole('button', { name: 'Restore' }));
    });

    expect(await screen.findByTestId('config-history-error')).toHaveTextContent(
      'The file changed on disk'
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it('disables Restore and says why while the server is not stopped', async () => {
    stubApi();
    setup({ serverStopped: false });
    await waitFor(() => expect(screen.getByTestId('config-history-item-r1')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('config-history-item-r1'));

    await waitFor(() => expect(screen.getByTestId('compare-original')).toBeInTheDocument());
    expect(screen.getByTestId('config-history-restore')).toBeDisabled();
    expect(screen.getByTestId('config-editor-server-note')).toBeInTheDocument();
  });

  it('closes', async () => {
    stubApi();
    const { onClose } = setup();

    fireEvent.click(screen.getByTestId('config-history-close'));

    expect(onClose).toHaveBeenCalled();
  });
});

describe('relativeTime and formatSize', () => {
  it('describes a time relative to now', () => {
    const now = Date.parse('2026-11-19T12:00:00Z');
    expect(relativeTime('2026-11-19T09:00:00Z', now)).toMatch(/3 hours ago/);
    expect(relativeTime('2026-11-18T12:00:00Z', now)).toMatch(/yesterday|1 day ago/);
  });

  it('formats sizes', () => {
    expect(formatSize(512)).toBe('512 B');
    expect(formatSize(1536)).toBe('1.5 KiB');
  });
});
