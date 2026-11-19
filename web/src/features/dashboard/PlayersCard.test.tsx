/**
 * Tests for the Players card.
 *
 * Story 22.1: Players Online Are Counted (AC 8)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { PlayersCard } from './PlayersCard';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function metricsResponse(playersOnline: number | null) {
  return {
    status: 'ok',
    data: {
      timestamp: '2026-11-18T10:30:00Z',
      apiMemoryMb: 128.5,
      apiCpuPercent: 2.3,
      gameMemoryMb: playersOnline === null ? null : 512.0,
      gameCpuPercent: playersOnline === null ? null : 15.2,
      playersOnline,
    },
  };
}

function stubFetchWith(body: unknown) {
  const mockFetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal('fetch', mockFetch);
  return mockFetch;
}

function renderCard(isRunning: boolean) {
  render(<PlayersCard isRunning={isRunning} />, {
    wrapper: createWrapper(createTestQueryClient()),
  });
}

describe('PlayersCard', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows Loading... while the metrics load', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => new Promise(() => {}))
    );

    renderCard(true);

    expect(screen.getByTestId('players-card')).toBeInTheDocument();
    expect(screen.getByTestId('players-card-value')).toHaveTextContent('Loading...');
    expect(screen.queryByTestId('players-card-subtitle')).not.toBeInTheDocument();
  });

  it('shows Stopped with "Server stopped" when the game is not running', async () => {
    const mockFetch = stubFetchWith(metricsResponse(null));

    renderCard(false);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('Stopped');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Server stopped');
    expect(mockFetch).toHaveBeenCalled();
  });

  it('shows Stopped when not running even if the snapshot still has players', async () => {
    stubFetchWith(metricsResponse(3));

    renderCard(false);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('Stopped');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Server stopped');
  });

  it('shows Error with the error message when the metrics request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () =>
          Promise.resolve({
            detail: { code: 'FORBIDDEN', message: 'Admin role required' },
          }),
      })
    );

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('Error');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Admin role required');
  });

  it('shows N/A when no snapshot has been collected yet', async () => {
    stubFetchWith({ status: 'ok', data: null });

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('N/A');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Waiting for metrics...');
  });

  it('shows N/A when playersOnline is null', async () => {
    stubFetchWith(metricsResponse(null));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('N/A');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Waiting for metrics...');
  });

  it('shows N/A when playersOnline is not a valid number', async () => {
    stubFetchWith(metricsResponse(NaN));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('N/A');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('Waiting for metrics...');
  });

  it('shows 0 with "No players online"', async () => {
    stubFetchWith(metricsResponse(0));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('0');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('No players online');
  });

  it('shows 1 with "1 player online"', async () => {
    stubFetchWith(metricsResponse(1));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('1');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('1 player online');
  });

  it('shows n with "n players online"', async () => {
    stubFetchWith(metricsResponse(2));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('2');
    });
    expect(screen.getByTestId('players-card-subtitle')).toHaveTextContent('2 players online');
  });

  it('asks for the current metrics and nothing else', async () => {
    const mockFetch = stubFetchWith(metricsResponse(2));

    renderCard(true);

    await waitFor(() => {
      expect(screen.getByTestId('players-card-value')).toHaveTextContent('2');
    });
    const urls = mockFetch.mock.calls.map(([url]) => String(url));
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) {
      expect(url).toMatch(/\/api\/v1alpha1\/metrics\/current$/);
    }
  });
});
