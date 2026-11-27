import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { toast } from 'sonner';
import { AddModDialog } from './AddModDialog';

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function installed(overrides: Record<string, unknown> = {}) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: {
          slug: 'demo',
          version: '1.0.0',
          filename: 'demo.zip',
          compatibility: 'not_verified',
          pending_restart: false,
          source: 'upload',
          replaced: false,
          previous_version: null,
          ...overrides,
        },
      }),
  };
}

function refused(status: number, detail: Record<string, unknown>) {
  return {
    ok: false,
    status,
    statusText: 'Error',
    json: () => Promise.resolve({ detail }),
  };
}

const demoFile = () => new File(['zipbytes'], 'demo.zip', { type: 'application/zip' });

function renderDialog(onOpenChange = vi.fn()) {
  render(<AddModDialog open onOpenChange={onOpenChange} />, { wrapper });
  return onOpenChange;
}

describe('AddModDialog (Story 28.4)', () => {
  const originalFetch = globalThis.fetch;
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('has Install disabled until a file or a link is given', async () => {
    const user = userEvent.setup();
    renderDialog();

    expect(screen.getByTestId('add-mod-install')).toBeDisabled();
    await user.click(screen.getByTestId('add-mod-tab-link'));
    expect(screen.getByTestId('add-mod-install')).toBeDisabled();
    await user.type(screen.getByTestId('add-mod-url-input'), '   ');
    expect(screen.getByTestId('add-mod-install')).toBeDisabled();
  });

  it('uploads a picked file as the request body and closes on success', async () => {
    fetchMock.mockResolvedValue(installed());
    const onOpenChange = renderDialog();

    fireEvent.change(screen.getByTestId('add-mod-file-input'), {
      target: { files: [demoFile()] },
    });
    expect(screen.getByTestId('add-mod-file-name')).toHaveTextContent('demo.zip');
    fireEvent.click(screen.getByTestId('add-mod-install'));

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1alpha1\/mods\/upload\?filename=demo\.zip$/);
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(File);
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/zip');
    expect(toast.success).toHaveBeenCalledWith('Installed demo 1.0.0', { description: undefined });
  });

  it('takes a dropped file', () => {
    renderDialog();

    fireEvent.drop(screen.getByTestId('add-mod-drop'), {
      dataTransfer: { files: [demoFile()] },
    });

    expect(screen.getByTestId('add-mod-file-name')).toHaveTextContent('demo.zip');
    expect(screen.getByTestId('add-mod-install')).toBeEnabled();
  });

  it('installs from a link and says when a restart is needed', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(installed({ source: 'url', pending_restart: true }));
    renderDialog();

    await user.click(screen.getByTestId('add-mod-tab-link'));
    await user.type(
      screen.getByTestId('add-mod-url-input'),
      ' https://github.com/me/demo/releases/download/v1/demo.zip '
    );
    await user.click(screen.getByTestId('add-mod-install'));

    await waitFor(() => expect(toast.success).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1alpha1\/mods\/install-from-url$/);
    expect(JSON.parse(String(init.body))).toEqual({
      url: 'https://github.com/me/demo/releases/download/v1/demo.zip',
      replace: false,
    });
    expect(toast.success).toHaveBeenCalledWith('Installed demo 1.0.0', {
      description: 'A server restart is required for the change to take effect.',
    });
  });

  it('offers to replace an installed mod, naming it, and resends with replace', async () => {
    fetchMock
      .mockResolvedValueOnce(
        refused(409, {
          code: 'MOD_ALREADY_INSTALLED',
          message: "Mod 'demo' is already installed (version 1.0.0)",
          slug: 'demo',
          installed_version: '1.0.0',
          source: 'moddb',
        })
      )
      .mockResolvedValueOnce(
        installed({ version: '1.0.1', replaced: true, previous_version: '1.0.0' })
      );
    const onOpenChange = renderDialog();
    fireEvent.change(screen.getByTestId('add-mod-file-input'), {
      target: { files: [demoFile()] },
    });

    fireEvent.click(screen.getByTestId('add-mod-install'));

    const notice = await screen.findByTestId('add-mod-installed');
    expect(notice).toHaveTextContent(
      'demo 1.0.0 is already installed (from the mod database). Replace it with this file?'
    );
    expect(screen.getByTestId('add-mod-install')).toBeDisabled();
    fireEvent.click(screen.getByTestId('add-mod-replace'));

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/filename=demo\.zip&replace=true$/);
    expect(toast.success).toHaveBeenCalledWith('Replaced demo 1.0.1', { description: undefined });
  });

  it('replaces from a link with replace: true, and Enter does not resend meanwhile', async () => {
    const user = userEvent.setup();
    fetchMock
      .mockResolvedValueOnce(
        refused(409, {
          code: 'MOD_ALREADY_INSTALLED',
          message: "Mod 'demo' is already installed (version 1.0.0)",
          slug: 'demo',
          installed_version: '1.0.0',
          source: 'url',
        })
      )
      .mockResolvedValueOnce(installed({ source: 'url', replaced: true }));
    renderDialog();
    await user.click(screen.getByTestId('add-mod-tab-link'));
    await user.type(screen.getByTestId('add-mod-url-input'), 'https://example.com/demo.zip{Enter}');
    expect(await screen.findByTestId('add-mod-installed')).toHaveTextContent(
      '(installed from a link). Replace it with this download?'
    );

    await user.type(screen.getByTestId('add-mod-url-input'), '{Enter}');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('add-mod-installed')).toBeInTheDocument();

    await user.click(screen.getByTestId('add-mod-replace'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [url, init] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(url).toMatch(/\/mods\/install-from-url$/);
    expect(JSON.parse(String(init.body))).toEqual({
      url: 'https://example.com/demo.zip',
      replace: true,
    });
  });

  it('shows any other error and keeps the input', async () => {
    fetchMock.mockResolvedValue(
      refused(422, {
        code: 'MOD_FILE_INVALID',
        message: 'The archive has no usable modinfo.json: it needs a mod ID, a name and a version.',
      })
    );
    const onOpenChange = renderDialog();
    fireEvent.change(screen.getByTestId('add-mod-file-input'), {
      target: { files: [demoFile()] },
    });

    fireEvent.click(screen.getByTestId('add-mod-install'));

    expect(await screen.findByTestId('add-mod-error')).toHaveTextContent(
      'The archive has no usable modinfo.json'
    );
    expect(screen.getByTestId('add-mod-file-name')).toHaveTextContent('demo.zip');
    expect(screen.getByTestId('add-mod-install')).toBeEnabled();
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('shows a blocked link with the API message', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      refused(422, {
        code: 'MOD_URL_BLOCKED',
        message: "The link's host 127.0.0.1 is on a private or local network",
      })
    );
    renderDialog();

    await user.click(screen.getByTestId('add-mod-tab-link'));
    await user.type(screen.getByTestId('add-mod-url-input'), 'https://127.0.0.1/x.zip{Enter}');

    expect(await screen.findByTestId('add-mod-error')).toHaveTextContent(
      'private or local network'
    );
    expect(screen.getByTestId('add-mod-url-input')).toHaveValue('https://127.0.0.1/x.zip');
  });

  it('clears what it showed when closed', async () => {
    fetchMock.mockResolvedValue(refused(422, { code: 'MOD_FILE_INVALID', message: 'bad file' }));
    const onOpenChange = vi.fn();
    const { rerender } = render(<AddModDialog open onOpenChange={onOpenChange} />, { wrapper });
    fireEvent.change(screen.getByTestId('add-mod-file-input'), {
      target: { files: [demoFile()] },
    });
    fireEvent.click(screen.getByTestId('add-mod-install'));
    await screen.findByTestId('add-mod-error');

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    rerender(<AddModDialog open onOpenChange={onOpenChange} />);

    expect(screen.queryByTestId('add-mod-error')).not.toBeInTheDocument();
    expect(screen.queryByTestId('add-mod-file-name')).not.toBeInTheDocument();
  });
});
