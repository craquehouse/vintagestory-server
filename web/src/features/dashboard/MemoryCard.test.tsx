import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryCard } from './MemoryCard';
import type { ApiResponse } from '@/api/types';

// Mock the useCurrentMetrics hook
const mockUseCurrentMetrics = vi.fn();
vi.mock('@/hooks/use-metrics', () => ({
  useCurrentMetrics: () => mockUseCurrentMetrics(),
}));

// Mock the StatCard component
vi.mock('@/components/StatCard', () => ({
  StatCard: ({
    icon: Icon,
    title,
    value,
    subtitle,
    testId,
    children,
  }: {
    icon: React.ComponentType;
    title: string;
    value: string | number;
    subtitle?: string;
    testId?: string;
    children?: React.ReactNode;
  }) => (
    <div data-testid={testId}>
      <div data-testid={`${testId}-icon`}>
        <Icon />
      </div>
      <div data-testid={`${testId}-title`}>{title}</div>
      <div data-testid={`${testId}-value`}>{value}</div>
      {subtitle && <div data-testid={`${testId}-subtitle`}>{subtitle}</div>}
      {children}
    </div>
  ),
}));

interface MetricsData {
  timestamp: string;
  apiMemoryMb: number;
  apiCpuPercent: number;
  gameMemoryMb: number | null;
  gameCpuPercent: number | null;
}

describe('MemoryCard', () => {
  describe('loading state', () => {
    it('renders loading state when isLoading is true', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card')).toBeInTheDocument();
      expect(screen.getByTestId('memory-card-title')).toHaveTextContent('Memory Usage');
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('Loading...');
      expect(screen.queryByTestId('memory-card-subtitle')).not.toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('renders error state when error is present', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch metrics'),
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('Error');
      expect(screen.getByTestId('memory-card-subtitle')).toHaveTextContent(
        'Failed to fetch metrics'
      );
    });

    it('handles error without message', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: {},
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('Error');
    });
  });

  describe('no data state', () => {
    it('renders "No data" when metrics response has no data', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: { status: 'ok', data: null },
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('No data');
      expect(screen.getByTestId('memory-card-subtitle')).toHaveTextContent(
        'Waiting for metrics...'
      );
    });

    it('renders "No data" when data is undefined', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('No data');
      expect(screen.getByTestId('memory-card-subtitle')).toHaveTextContent(
        'Waiting for metrics...'
      );
    });
  });

  describe('rendering with valid metrics - game server running', () => {
    it('displays total memory (API + Game) when both are valid', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.0,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      // Total: 128.5 + 512.0 = 640.5 MB
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('640.5 MB');
    });

    it('displays API and Game memory breakdowns', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.0,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 128.5 MB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent(
        'Game: 512.0 MB'
      );
    });

    it('uses GB for large total memory (>= 1024 MB)', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 512.0,
          apiCpuPercent: 2.3,
          gameMemoryMb: 1536.0, // 1.5 GB
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      // Total: 512 + 1536 = 2048 MB = 2.0 GB
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('2.0 GB');
    });

    it('uses GB for individual values >= 1024 MB', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 256.0,
          apiCpuPercent: 2.3,
          gameMemoryMb: 2048.0, // 2.0 GB
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 256.0 MB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: 2.0 GB');
    });
  });

  describe('rendering with game server not running', () => {
    it('displays only API memory when game memory is null', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: null,
          gameCpuPercent: null,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      // Total should be just API memory
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('128.5 MB');
    });

    it('displays N/A for game memory when null', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: null,
          gameCpuPercent: null,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 128.5 MB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: N/A');
    });
  });

  describe('edge cases with invalid numeric values', () => {
    it('handles zero memory values', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 0.0,
          apiCpuPercent: 0.0,
          gameMemoryMb: 0.0,
          gameCpuPercent: 0.0,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('0.0 MB');
      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 0.0 MB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: 0.0 MB');
    });

    it('handles NaN values as invalid', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: NaN as unknown as number,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.0,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      // API memory is NaN, so only game memory should be used
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('N/A');
      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: N/A');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent(
        'Game: 512.0 MB'
      );
    });

    it('handles negative values as invalid', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: -100,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.0,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: N/A');
    });

    it('handles Infinity as invalid', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: Infinity,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: N/A');
    });

    it('displays N/A for total when all values are invalid', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: null as unknown as number,
          apiCpuPercent: 2.3,
          gameMemoryMb: null,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('N/A');
    });
  });

  describe('memory formatting precision', () => {
    it('formats MB values to 1 decimal place', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.456,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.789,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toHaveTextContent('API: 128.5 MB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent(
        'Game: 512.8 MB'
      );
    });

    it('formats GB values to 1 decimal place', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 512.0,
          apiCpuPercent: 2.3,
          gameMemoryMb: 2560.5, // 2.5 GB
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      // Total: 512 + 2560.5 = 3072.5 MB = 3.0 GB
      expect(screen.getByTestId('memory-card-value')).toHaveTextContent('3.0 GB');
      expect(screen.getByTestId('memory-card-game')).toHaveTextContent('Game: 2.5 GB');
    });
  });

  describe('component structure', () => {
    it('uses MemoryStick icon', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-icon')).toBeInTheDocument();
    });

    it('has consistent title in all states', () => {
      // Loading
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      const { unmount: unmount1 } = render(<MemoryCard />);
      expect(screen.getByTestId('memory-card-title')).toHaveTextContent('Memory Usage');
      unmount1();

      // Error
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Test error'),
      });
      const { unmount: unmount2 } = render(<MemoryCard />);
      expect(screen.getByTestId('memory-card-title')).toHaveTextContent('Memory Usage');
      unmount2();

      // No data
      mockUseCurrentMetrics.mockReturnValue({
        data: { status: 'ok', data: null },
        isLoading: false,
        error: null,
      });
      const { unmount: unmount3 } = render(<MemoryCard />);
      expect(screen.getByTestId('memory-card-title')).toHaveTextContent('Memory Usage');
      unmount3();

      // Valid data
      mockUseCurrentMetrics.mockReturnValue({
        data: {
          status: 'ok',
          data: {
            timestamp: '2026-01-17T10:30:00Z',
            apiMemoryMb: 128.5,
            apiCpuPercent: 2.3,
            gameMemoryMb: 512.0,
            gameCpuPercent: 15.2,
          },
        },
        isLoading: false,
        error: null,
      });
      render(<MemoryCard />);
      expect(screen.getByTestId('memory-card-title')).toHaveTextContent('Memory Usage');
    });

    it('uses memory-card as testId', () => {
      mockUseCurrentMetrics.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card')).toBeInTheDocument();
    });

    it('renders breakdown section with API and Game memory', () => {
      const metricsResponse: ApiResponse<MetricsData> = {
        status: 'ok',
        data: {
          timestamp: '2026-01-17T10:30:00Z',
          apiMemoryMb: 128.5,
          apiCpuPercent: 2.3,
          gameMemoryMb: 512.0,
          gameCpuPercent: 15.2,
        },
      };

      mockUseCurrentMetrics.mockReturnValue({
        data: metricsResponse,
        isLoading: false,
        error: null,
      });

      render(<MemoryCard />);

      expect(screen.getByTestId('memory-card-api')).toBeInTheDocument();
      expect(screen.getByTestId('memory-card-game')).toBeInTheDocument();
    });
  });
});
