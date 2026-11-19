/**
 * FileManagerPanel: editing (Story 23.5, FR319, Epic 23 ADR-5).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { type ReactNode } from 'react';
import { queryKeys } from '@/api/query-keys';
import { FileManagerPanel } from './FileManagerPanel';
import { clearAllDrafts } from './config-drafts';

vi.mock('@/components/code-view/LazyCodeView', () => import('@/test/mocks/lazy-code-view'));
vi.mock(
  '@/components/code-view/LazyRevisionCompare',
  () => import('@/test/mocks/lazy-revision-compare')
);
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const TEXT = '{\n  // c\n  "a": 1\n}\n';

function stubApi({ state = 'installed' }: { state?: string } = {}) {
  globalThis.fetch = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    const json = (body: unknown) => ({ ok: true, status: 200, json: () => Promise.resolve(body) });
    if (url.includes('/server/status')) return json({ status: 'ok', data: { state } });
    if (url.includes('/config/history/')) {
      return json({ status: 'ok', data: { filename: 'x.json', revisions: [] } });
    }
    if (url.includes('/config/files/validate')) {
      return json({ status: 'ok', data: { valid: true, parse_error: null } });
    }
    if (url.includes('/config/directories')) {
      return json({
        status: 'ok',
        data: { directories: url.includes('directory=') ? [] : ['ModConfig'] },
      });
    }
    if (url.match(/\/config\/files\/[^?]/) && (init?.method ?? 'GET') === 'GET') {
      const name = decodeURIComponent(url.split('/config/files/')[1]);
      return json({
        status: 'ok',
        data: {
          filename: name,
          content: { a: 1 },
          parse_error: null,
          text: TEXT,
          version: 'v1',
        },
      });
    }
    if (url.includes('/config/files')) {
      return json({
        status: 'ok',
        data: { files: url.includes('directory=') ? ['y.json'] : ['x.json', 'z.json'] },
      });
    }
    return json({ status: 'ok', data: {} });
  });
}

function renderPanel(role: 'admin' | 'monitor' = 'admin') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role } });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  }
  return render(<FileManagerPanel />, { wrapper: Wrapper });
}

async function openFile(name = 'x.json') {
  await waitFor(() => expect(screen.getByTestId(`file-item-${name}`)).toBeInTheDocument());
  await act(async () => {
    fireEvent.click(screen.getByTestId(`file-item-${name}`));
  });
  await waitFor(() => expect(screen.getByTestId('file-viewer-code')).toBeInTheDocument());
}

async function startEditing() {
  await waitFor(() => expect(screen.getByTestId('file-viewer-edit')).toBeEnabled());
  fireEvent.click(screen.getByTestId('file-viewer-edit'));
  await waitFor(() => expect(screen.getByTestId('config-file-editor')).toBeInTheDocument());
}

function type(text: string) {
  fireEvent.change(screen.getByTestId('config-editor-text'), { target: { value: text } });
}

describe('FileManagerPanel editing (Story 23.5)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    clearAllDrafts();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('gives an Admin key an Edit button that opens the editor', async () => {
    stubApi();
    renderPanel();
    await openFile();

    await startEditing();

    expect(screen.getByTestId('config-editor-text')).toHaveValue(TEXT);
  });

  it('gives a Monitor key no Edit button', async () => {
    stubApi();
    renderPanel('monitor');
    await waitFor(() => expect(screen.getByTestId('file-item-x.json')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-x.json'));
    });

    await waitFor(() => expect(screen.getByTestId('file-viewer')).toBeInTheDocument());
    expect(screen.queryByTestId('file-viewer-edit')).not.toBeInTheDocument();
  });

  it.each(['running', 'starting', 'stopping', 'installing'])(
    'disables Edit and says why while the server is %s',
    async (state) => {
      stubApi({ state });
      renderPanel();
      await openFile();

      await waitFor(() =>
        expect(screen.getByTestId('config-editor-server-note')).toHaveTextContent(
          'Stop the game server to edit files'
        )
      );
      expect(screen.getByTestId('file-viewer-edit')).toBeDisabled();
    }
  );

  it('asks before leaving a file with changes, and stays on Keep editing', async () => {
    stubApi();
    renderPanel();
    await openFile();
    await startEditing();
    type('{"a": 2}');

    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-z.json'));
    });

    expect(await screen.findByText('Discard your changes to x.json?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }));
    await waitFor(() =>
      expect(screen.queryByText('Discard your changes to x.json?')).not.toBeInTheDocument()
    );
    expect(screen.getByTestId('config-editor-text')).toHaveValue('{"a": 2}');
  });

  it('runs the navigation on Discard', async () => {
    stubApi();
    renderPanel();
    await openFile();
    await startEditing();
    type('{"a": 2}');

    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-ModConfig'));
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Discard' }));

    await waitFor(() =>
      expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('ModConfig')
    );
    expect(screen.queryByTestId('config-file-editor')).not.toBeInTheDocument();
  });

  it('asks before the breadcrumb leaves a file with changes', async () => {
    stubApi();
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('file-item-ModConfig')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-ModConfig'));
    });
    await openFile('y.json');
    await startEditing();
    type('{"a": 2}');

    await act(async () => {
      fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
    });

    expect(
      await screen.findByText('Discard your changes to ModConfig/y.json?')
    ).toBeInTheDocument();
  });

  it('leaves a file without changes without asking', async () => {
    stubApi();
    renderPanel();
    await openFile();
    await startEditing();

    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-z.json'));
    });

    expect(screen.queryByText(/Discard your changes/)).not.toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId('config-file-editor')).not.toBeInTheDocument());
  });

  it('offers to resume a kept draft after the panel is opened again', async () => {
    stubApi();
    const first = renderPanel();
    await openFile();
    await startEditing();
    type('{"draft": 1}');
    first.unmount();

    renderPanel();
    await openFile();

    await waitFor(() =>
      expect(screen.getByTestId('file-viewer-edit')).toHaveTextContent('Resume editing')
    );
    fireEvent.click(screen.getByTestId('file-viewer-edit'));
    await waitFor(() =>
      expect(screen.getByTestId('config-editor-text')).toHaveValue('{"draft": 1}')
    );
  });

  // Story 23.7
  it('opens the history panel from the History button, Admin only', async () => {
    stubApi();
    renderPanel();
    await openFile();

    fireEvent.click(screen.getByTestId('file-viewer-history'));

    expect(await screen.findByTestId('config-history-panel')).toBeInTheDocument();
    expect(await screen.findByTestId('config-history-empty')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('config-history-close'));
    await waitFor(() => expect(screen.getByTestId('file-viewer-code')).toBeInTheDocument());
  });

  it('closes the history panel when another file is chosen', async () => {
    stubApi();
    renderPanel();
    await openFile();
    fireEvent.click(screen.getByTestId('file-viewer-history'));
    await screen.findByTestId('config-history-panel');

    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-z.json'));
    });

    await waitFor(() =>
      expect(screen.queryByTestId('config-history-panel')).not.toBeInTheDocument()
    );
  });

  it('gives a Monitor key no History button', async () => {
    stubApi();
    renderPanel('monitor');
    await waitFor(() => expect(screen.getByTestId('file-item-x.json')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('file-item-x.json'));
    });

    await waitFor(() => expect(screen.getByTestId('file-viewer')).toBeInTheDocument());
    expect(screen.queryByTestId('file-viewer-history')).not.toBeInTheDocument();
  });
});
