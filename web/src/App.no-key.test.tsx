/**
 * The real App without an API key shows the set-up screen and calls nothing
 * (Story 19.2, FR210, Epic 19 ADR-5).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );
}

describe('App without an API key', () => {
  const originalEnv = { ...import.meta.env };
  let fetchMock: ReturnType<typeof vi.fn>;
  let webSocketMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn(() => new Promise<Response>(() => {}));
    webSocketMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', webSocketMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.__VSM_CONFIG__;
    Object.keys(import.meta.env).forEach((key) => {
      if (!(key in originalEnv)) {
        delete import.meta.env[key];
      }
    });
    Object.assign(import.meta.env, originalEnv);
  });

  it('shows the set-up screen and makes no request', () => {
    delete import.meta.env.VITE_API_KEY;
    window.__VSM_CONFIG__ = { apiKey: '' };

    renderApp();

    expect(screen.getByTestId('no-api-key-screen')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(webSocketMock).not.toHaveBeenCalled();
  });

  it('renders the app shell with a key', async () => {
    window.__VSM_CONFIG__ = { apiKey: 'k' };

    renderApp();

    expect(screen.queryByTestId('no-api-key-screen')).not.toBeInTheDocument();
    expect((await screen.findAllByRole('navigation')).length).toBeGreaterThan(0);
  });
});
