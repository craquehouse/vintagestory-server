import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { toast } from 'sonner';
import { ModUpdateWebhookSetting } from './ModUpdateWebhookSetting';

const URL_VALUE = 'https://discord.com/api/webhooks/1/test-token';

let queryClient: QueryClient;
function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function okResponse(configured: boolean) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: { key: 'mod_update_webhook_url', configured },
      }),
  };
}

describe('ModUpdateWebhookSetting', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('shows only whether a webhook is configured', () => {
    globalThis.fetch = vi.fn();
    render(<ModUpdateWebhookSetting configured />, { wrapper });

    expect(screen.getByTestId('mod-update-webhook-status')).toHaveTextContent('Configured');
    expect(screen.getByTestId('mod-update-webhook-input')).toHaveValue('');
    expect(screen.getByTestId('mod-update-webhook-clear')).toBeInTheDocument();
  });

  it('shows Not configured without a Clear action', () => {
    globalThis.fetch = vi.fn();
    render(<ModUpdateWebhookSetting configured={false} />, { wrapper });

    expect(screen.getByTestId('mod-update-webhook-status')).toHaveTextContent('Not configured');
    expect(screen.queryByTestId('mod-update-webhook-clear')).not.toBeInTheDocument();
    expect(screen.getByTestId('mod-update-webhook-save')).toBeDisabled();
  });

  it('saves a URL, clears the field and refetches settings without caching the URL', async () => {
    const mockFetch = vi.fn().mockResolvedValue(okResponse(true));
    globalThis.fetch = mockFetch;
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const setDataSpy = vi.spyOn(queryClient, 'setQueryData');
    render(<ModUpdateWebhookSetting configured={false} />, { wrapper });

    fireEvent.change(screen.getByTestId('mod-update-webhook-input'), {
      target: { value: URL_VALUE },
    });
    fireEvent.click(screen.getByTestId('mod-update-webhook-save'));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Webhook saved'));
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe(
      'http://localhost:8080/api/v1alpha1/config/api/settings/mod_update_webhook_url'
    );
    expect(JSON.parse(options.body)).toEqual({ value: URL_VALUE });
    expect(screen.getByTestId('mod-update-webhook-input')).toHaveValue('');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['config', 'api'] });
    expect(setDataSpy).not.toHaveBeenCalled();
  });

  it('rejects a URL that is not http or https without sending it', () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;
    render(<ModUpdateWebhookSetting configured={false} />, { wrapper });

    fireEvent.change(screen.getByTestId('mod-update-webhook-input'), {
      target: { value: 'ftp://example.com/hook' },
    });
    fireEvent.click(screen.getByTestId('mod-update-webhook-save'));

    expect(screen.getByRole('alert')).toHaveTextContent('Enter an http or https URL');
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('clears the webhook', async () => {
    const mockFetch = vi.fn().mockResolvedValue(okResponse(false));
    globalThis.fetch = mockFetch;
    render(<ModUpdateWebhookSetting configured />, { wrapper });

    fireEvent.click(screen.getByTestId('mod-update-webhook-clear'));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Webhook removed'));
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ value: null });
  });

  it('shows the API error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () =>
        Promise.resolve({
          detail: {
            code: 'API_SETTING_INVALID',
            message: "Invalid value for 'mod_update_webhook_url': must be an http or https URL",
          },
        }),
    });
    render(<ModUpdateWebhookSetting configured={false} />, { wrapper });

    fireEvent.change(screen.getByTestId('mod-update-webhook-input'), {
      target: { value: 'https://example.com/hook' },
    });
    fireEvent.click(screen.getByTestId('mod-update-webhook-save'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Update failed', {
        description: "Invalid value for 'mod_update_webhook_url': must be an http or https URL",
      });
    });
  });
});
