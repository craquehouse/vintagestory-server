/**
 * Tests for specialized metric card components.
 *
 * Story 12.4: Dashboard Stats Cards
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { MemoryCard } from './MemoryCard';
import { DiskSpaceCard } from './DiskSpaceCard';
import { UptimeCard } from './UptimeCard';
import { ServerStatusCard } from './ServerStatusCard';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Wrapper component for rendering components with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock metrics with game server running
const mockMetricsWithGame = {
  status: 'ok',
  data: {
    timestamp: '2026-01-17T10:30:00Z',
    apiMemoryMb: 128.5,
    apiCpuPercent: 2.3,
    gameMemoryMb: 512.0,
    gameCpuPercent: 15.2,
  },
};

// Mock metrics with game server NOT running (AC: 4)
const mockMetricsNoGame = {
  status: 'ok',
  data: {
    timestamp: '2026-01-17T10:30:00Z',
    apiMemoryMb: 128.5,
    apiCpuPercent: 2.3,
    gameMemoryMb: null,
    gameCpuPercent: null,
  },
};

describe('MemoryCard', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('shows loading state while fetching', () => {
    const mockFetch = vi.fn().mockImplementation(() => new Promise(() => {}));
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    render(<MemoryCard />, { wrapper: createWrapper(queryClient) });

    expect(screen.getByTestId('memory-card')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays memory usage with game server running (AC: 2)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMetricsWithGame),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    render(<MemoryCard />, { wrapper: createWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('640.5 MB');
    });

    expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 128.5 MB');
    expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: 512.0 MB');
  });

  it('shows N/A for game memory when server not running (AC: 4)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMetricsNoGame),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    render(<MemoryCard />, { wrapper: createWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 128.5 MB');
    });

    expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: N/A');
    // Total should be just API memory
    expect(screen.getByTestId('memory-card-value')).toHaveTextContent('128.5 MB');
  });

  it('shows error state on API failure', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: () =>
        Promise.resolve({
          detail: { code: 'FORBIDDEN', message: 'Admin role required' },
        }),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    render(<MemoryCard />, { wrapper: createWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });

  it('shows no data state when metrics not collected yet', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: null }),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    render(<MemoryCard />, { wrapper: createWrapper(queryClient) });

    await waitFor(() => {
      expect(screen.getByText('No data')).toBeInTheDocument();
    });
  });
});

describe('DiskSpaceCard', () => {
  it('shows loading state', () => {
    render(<DiskSpaceCard diskSpace={null} isLoading={true} />);

    expect(screen.getByTestId('disk-card')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays disk space data', () => {
    const diskSpace = {
      totalGb: 100,
      usedGb: 55,
      availableGb: 45,
      usagePercent: 55,
      warning: false,
    };

    render(<DiskSpaceCard diskSpace={diskSpace} />);

    expect(screen.getByTestId('disk-card-value')).toHaveTextContent('45.0 GB');
    expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
      'Free of 100.0 GB (55% used)'
    );
  });

  it('shows N/A when disk space unavailable', () => {
    render(<DiskSpaceCard diskSpace={null} />);

    expect(screen.getByTestId('disk-card-value')).toHaveTextContent('N/A');
  });
});

describe('UptimeCard', () => {
  it('shows loading state', () => {
    render(<UptimeCard uptimeSeconds={null} isRunning={false} isLoading={true} />);

    expect(screen.getByTestId('uptime-card')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows stopped state when server not running', () => {
    render(<UptimeCard uptimeSeconds={null} isRunning={false} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('Stopped');
    expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
      'Server is not running'
    );
  });

  it('formats seconds correctly', () => {
    render(<UptimeCard uptimeSeconds={45} isRunning={true} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('45s');
  });

  it('formats minutes correctly', () => {
    render(<UptimeCard uptimeSeconds={125} isRunning={true} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2m 5s');
  });

  it('formats hours correctly', () => {
    render(<UptimeCard uptimeSeconds={3665} isRunning={true} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1h 1m');
  });

  it('formats days correctly', () => {
    render(<UptimeCard uptimeSeconds={90061} isRunning={true} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1d 1h');
  });

  it('shows N/A when uptime unavailable but server running', () => {
    render(<UptimeCard uptimeSeconds={null} isRunning={true} />);

    expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
  });
});

describe('ServerStatusCard', () => {
  it('shows loading state', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="running" isLoading={true} />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays server status with badge (AC: 3)', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="running" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
    // Badge should show running state
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('displays version when provided', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="running" version="1.21.6" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByTestId('server-status-card-version')).toHaveTextContent(
      'Version 1.21.6'
    );
  });

  it('includes server controls (AC: 3)', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="running" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByTestId('server-status-card-controls')).toBeInTheDocument();
  });

  it('shows stopped state', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="installed" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  it('shows starting state', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="starting" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByText('Starting')).toBeInTheDocument();
  });

  it('shows stopping state', () => {
    const queryClient = createTestQueryClient();
    render(<ServerStatusCard state="stopping" />, {
      wrapper: createWrapper(queryClient),
    });

    expect(screen.getByText('Stopping')).toBeInTheDocument();
  });
});
