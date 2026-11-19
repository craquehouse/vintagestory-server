import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { type ReactNode } from 'react';
import { toast } from 'sonner';
import { ConfigFileEditor } from './ConfigFileEditor';
import { clearAllDrafts, getDraft } from './config-drafts';
import { codeViewGoToCalls } from '@/test/mocks/lazy-code-view';

vi.mock('@/components/code-view/LazyCodeView', () => import('@/test/mocks/lazy-code-view'));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const TEXT = '{\n  // c\n  "a": 1\n}\n';

interface Answer {
  status?: number;
  body: unknown;
}

/** Answers validate and save requests in order of method; records the bodies. */
function stubApi(answers: { validate?: (text: string) => Answer; save?: () => Answer }) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  globalThis.fetch = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null;
    calls.push({ method, url, body });
    let answer: Answer = { body: { status: 'ok', data: {} } };
    if (url.endsWith('/config/files/validate') && answers.validate) {
      answer = answers.validate(String(body?.text));
    } else if (method === 'PUT' && answers.save) {
      answer = answers.save();
    }
    const status = answer.status ?? 200;
    return {
      ok: status < 400,
      status,
      statusText: String(status),
      json: () => Promise.resolve(answer.body),
    };
  });
  return calls;
}

const valid = (): Answer => ({ body: { status: 'ok', data: { valid: true, parse_error: null } } });

function setup(props: Partial<Parameters<typeof ConfigFileEditor>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const handlers = {
    onDone: vi.fn(),
    onDirtyChange: vi.fn(),
    onRequestCancel: vi.fn(),
    onReload: vi.fn(),
  };
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  }
  render(
    <ConfigFileEditor
      path={['ModConfig', 'x.json']}
      displayPath="ModConfig/x.json"
      initialText={TEXT}
      version="v1"
      serverStopped
      {...handlers}
      {...props}
    />,
    { wrapper: Wrapper }
  );
  return handlers;
}

function type(text: string) {
  fireEvent.change(screen.getByTestId('config-editor-text'), { target: { value: text } });
}

describe('ConfigFileEditor (Story 23.5)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    clearAllDrafts();
    codeViewGoToCalls.length = 0;
    vi.mocked(toast.success).mockClear();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('shows the text and checks it on opening', async () => {
    const calls = stubApi({ validate: valid });
    setup();

    expect(screen.getByTestId('config-editor-text')).toHaveValue(TEXT);
    await waitFor(() =>
      expect(screen.getByTestId('config-editor-status')).toHaveTextContent('Valid')
    );
    expect(calls.filter((c) => c.url.endsWith('/validate'))[0].body).toEqual({
      filename: 'ModConfig/x.json',
      text: TEXT,
    });
  });

  it('shows an error with its position and moves the cursor there', async () => {
    stubApi({
      validate: () => ({
        body: {
          status: 'ok',
          data: { valid: false, parse_error: { message: 'Expected comma', line: 3, column: 5 } },
        },
      }),
    });
    setup();

    await waitFor(() =>
      expect(screen.getByTestId('config-editor-status')).toHaveTextContent('Expected comma')
    );
    fireEvent.click(screen.getByTestId('config-editor-goto'));

    expect(screen.getByTestId('config-editor-goto')).toHaveTextContent('line 3, column 5');
    expect(codeViewGoToCalls).toEqual([[3, 5]]);
  });

  it('disables Save while the text is unchanged', async () => {
    stubApi({ validate: valid });
    setup();

    await waitFor(() =>
      expect(screen.getByTestId('config-editor-status')).toHaveTextContent('Valid')
    );
    expect(screen.getByTestId('config-editor-save')).toBeDisabled();
  });

  it('saves changed, valid text with the version, then ends editing', async () => {
    const calls = stubApi({
      validate: valid,
      save: () => ({
        body: { status: 'ok', data: { filename: 'ModConfig/x.json', version: 'v2' } },
      }),
    });
    const handlers = setup();

    type('{"a": 2}');
    await waitFor(() => expect(screen.getByTestId('config-editor-save')).toBeEnabled(), {
      timeout: 2000,
    });
    expect(getDraft('ModConfig/x.json', 'v1')?.text).toBe('{"a": 2}');
    await act(async () => {
      fireEvent.click(screen.getByTestId('config-editor-save'));
    });

    await waitFor(() => expect(handlers.onDone).toHaveBeenCalledWith(true));
    expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({
      text: '{"a": 2}',
      version: 'v1',
    });
    expect(toast.success).toHaveBeenCalledWith('Saved ModConfig/x.json');
    expect(getDraft('ModConfig/x.json', 'v1')).toBeUndefined();
  });

  it('keeps the text and offers Reload when the file changed on disk', async () => {
    stubApi({
      validate: valid,
      save: () => ({
        status: 409,
        body: { detail: { code: 'CONFIG_FILE_CHANGED', message: 'changed' } },
      }),
    });
    const handlers = setup();

    type('{"a": 2}');
    await waitFor(() => expect(screen.getByTestId('config-editor-save')).toBeEnabled(), {
      timeout: 2000,
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('config-editor-save'));
    });

    await waitFor(() =>
      expect(screen.getByTestId('config-editor-conflict')).toHaveTextContent(
        'The file changed on disk since you opened it.'
      )
    );
    expect(screen.getByTestId('config-editor-text')).toHaveValue('{"a": 2}');
    expect(screen.getByTestId('config-editor-save')).toBeDisabled();

    fireEvent.click(screen.getByTestId('config-editor-reload'));
    fireEvent.click(await screen.findByRole('button', { name: 'Discard and reload' }));

    expect(handlers.onReload).toHaveBeenCalled();
    expect(getDraft('ModConfig/x.json', 'v1')).toBeUndefined();
  });

  it.each([
    ['CONFIG_FILE_SERVER_RUNNING', 'Stop the game server to save config files'],
    ['CONFIG_FILE_SERVER_BUSY', 'The game server is starting'],
  ])('keeps the text and explains a %s refusal', async (code, message) => {
    stubApi({
      validate: valid,
      save: () => ({ status: 409, body: { detail: { code, message } } }),
    });
    setup();

    type('{"a": 2}');
    await waitFor(() => expect(screen.getByTestId('config-editor-save')).toBeEnabled(), {
      timeout: 2000,
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('config-editor-save'));
    });

    await waitFor(() =>
      expect(screen.getByTestId('config-editor-error')).toHaveTextContent(message)
    );
    expect(screen.getByTestId('config-editor-text')).toHaveValue('{"a": 2}');
  });

  it("shows a save's parse error with its position", async () => {
    stubApi({
      validate: valid,
      save: () => ({
        status: 422,
        body: {
          detail: {
            code: 'CONFIG_FILE_INVALID',
            message: 'bad',
            parse_error: { message: 'Unexpected', line: 2, column: 1 },
          },
        },
      }),
    });
    setup();

    type('{"a": 2}');
    await waitFor(() => expect(screen.getByTestId('config-editor-save')).toBeEnabled(), {
      timeout: 2000,
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('config-editor-save'));
    });

    await waitFor(() =>
      expect(screen.getByTestId('config-editor-status')).toHaveTextContent('Unexpected')
    );
    expect(screen.getByTestId('config-editor-goto')).toHaveTextContent('line 2, column 1');
  });

  it('disables Save and says why while the server is not stopped', async () => {
    stubApi({ validate: valid });
    setup({ serverStopped: false, draft: '{"a": 2}' });

    await waitFor(
      () => expect(screen.getByTestId('config-editor-status')).toHaveTextContent('Valid'),
      {
        timeout: 2000,
      }
    );
    expect(screen.getByTestId('config-editor-save')).toBeDisabled();
    expect(screen.getByTestId('config-editor-server-note')).toHaveTextContent(
      'Stop the game server to edit files'
    );
    expect(screen.getByRole('link', { name: 'Go to the server controls' })).toHaveAttribute(
      'href',
      '/'
    );
  });

  it('starts from a kept draft', () => {
    stubApi({ validate: valid });
    setup({ draft: '{"draft": true}' });

    expect(screen.getByTestId('config-editor-text')).toHaveValue('{"draft": true}');
  });

  it('asks the panel before cancelling with changes, and ends at once without', () => {
    stubApi({ validate: valid });
    const handlers = setup();

    fireEvent.click(screen.getByTestId('config-editor-cancel'));
    expect(handlers.onDone).toHaveBeenCalledWith(false);

    type('{"a": 2}');
    fireEvent.click(screen.getByTestId('config-editor-cancel'));
    expect(handlers.onRequestCancel).toHaveBeenCalled();
  });

  it('prevents leaving the page only while there are changes', () => {
    stubApi({ validate: valid });
    setup();

    const clean = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(clean);
    expect(clean.defaultPrevented).toBe(false);

    type('{"a": 2}');
    const dirty = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(dirty);
    expect(dirty.defaultPrevented).toBe(true);
  });
});
