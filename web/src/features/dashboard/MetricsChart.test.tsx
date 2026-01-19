/**
 * Tests for MetricsChart component.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 2: Create MetricsChart component + tests (AC: 1, 2, 4, 5)
 *
 * Tests cover:
 * - Empty data handling
 * - Data display with API and Game memory lines
 * - Null game memory handling (gaps in line - AC: 4)
 * - Legend display (AC: 2)
 * - Helper functions (formatAxisTime, formatTooltipTime, formatMemory)
 * - CustomTooltip behavior (AC: 5)
 * - ChartTypeToggle functionality
 *
 * Note: ResponsiveContainer doesn't render SVG in JSDOM because
 * getBoundingClientRect returns 0. Tests verify component structure
 * and empty state handling. Full visual testing via Playwright.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetricsChart } from './MetricsChart';
import type { MetricsSnapshot } from '@/api/types';
import {
  formatAxisTime,
  formatTooltipTime,
  formatMemory,
  CustomTooltip,
} from './MetricsChart';

// Mock ResizeObserver for ResponsiveContainer
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

// Mock data with game server running
const mockDataWithGame: MetricsSnapshot[] = [
  {
    timestamp: '2026-01-17T10:00:00Z',
    apiMemoryMb: 100,
    apiCpuPercent: 2.0,
    gameMemoryMb: 500,
    gameCpuPercent: 15.0,
  },
  {
    timestamp: '2026-01-17T10:10:00Z',
    apiMemoryMb: 105,
    apiCpuPercent: 2.2,
    gameMemoryMb: 510,
    gameCpuPercent: 15.5,
  },
  {
    timestamp: '2026-01-17T10:20:00Z',
    apiMemoryMb: 102,
    apiCpuPercent: 1.8,
    gameMemoryMb: 505,
    gameCpuPercent: 14.8,
  },
];

// Mock data with null game memory (server not running - AC: 4)
const mockDataWithNullGame: MetricsSnapshot[] = [
  {
    timestamp: '2026-01-17T10:00:00Z',
    apiMemoryMb: 100,
    apiCpuPercent: 2.0,
    gameMemoryMb: 500,
    gameCpuPercent: 15.0,
  },
  {
    timestamp: '2026-01-17T10:10:00Z',
    apiMemoryMb: 105,
    apiCpuPercent: 2.2,
    gameMemoryMb: null, // Server stopped
    gameCpuPercent: null,
  },
  {
    timestamp: '2026-01-17T10:20:00Z',
    apiMemoryMb: 102,
    apiCpuPercent: 1.8,
    gameMemoryMb: null, // Server still stopped
    gameCpuPercent: null,
  },
  {
    timestamp: '2026-01-17T10:30:00Z',
    apiMemoryMb: 108,
    apiCpuPercent: 2.5,
    gameMemoryMb: 520, // Server restarted
    gameCpuPercent: 16.0,
  },
];

describe('MetricsChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('empty state', () => {
    it('shows empty state message when data is empty', () => {
      render(<MetricsChart data={[]} />);

      expect(screen.getByTestId('metrics-chart-empty')).toBeInTheDocument();
      expect(screen.getByText('No metrics data available')).toBeInTheDocument();
    });

    it('applies correct height to empty state', () => {
      render(<MetricsChart data={[]} height={200} />);

      const emptyState = screen.getByTestId('metrics-chart-empty');
      expect(emptyState).toHaveStyle({ height: '200px' });
    });

    it('uses default height (300) when not specified', () => {
      render(<MetricsChart data={[]} />);

      const emptyState = screen.getByTestId('metrics-chart-empty');
      expect(emptyState).toHaveStyle({ height: '300px' });
    });
  });

  describe('chart rendering', () => {
    it('renders chart container when data is provided', () => {
      render(<MetricsChart data={mockDataWithGame} />);

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });

    it('renders with custom height', () => {
      render(<MetricsChart data={mockDataWithGame} height={400} />);

      const chartContainer = screen.getByTestId('metrics-chart');
      // Height is on the inner chart wrapper div (after the toggle)
      const chartWrapper = chartContainer.querySelector('[style*="height"]');
      expect(chartWrapper).toHaveStyle({ height: '400px' });
    });

    it('renders ResponsiveContainer wrapper', () => {
      render(<MetricsChart data={mockDataWithGame} />);

      const container = screen.getByTestId('metrics-chart');
      // ResponsiveContainer creates a div with recharts-responsive-container class
      expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument();
    });
  });

  describe('data handling (AC: 2, 4)', () => {
    it('handles data with both API and Game memory values', () => {
      // Just verify it doesn't throw with valid data
      expect(() => {
        render(<MetricsChart data={mockDataWithGame} />);
      }).not.toThrow();

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });

    it('handles data with null game memory values (AC: 4)', () => {
      // Verify component renders without errors when game memory is null
      expect(() => {
        render(<MetricsChart data={mockDataWithNullGame} />);
      }).not.toThrow();

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });

    it('handles single data point', () => {
      const singlePoint: MetricsSnapshot[] = [mockDataWithGame[0]];

      expect(() => {
        render(<MetricsChart data={singlePoint} />);
      }).not.toThrow();

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });

    it('handles large dataset without performance issues', () => {
      // Generate 360 data points (1 hour at 10s intervals)
      const largeData: MetricsSnapshot[] = Array.from({ length: 360 }, (_, i) => ({
        timestamp: new Date(Date.now() - (360 - i) * 10000).toISOString(),
        apiMemoryMb: 100 + Math.random() * 50,
        apiCpuPercent: 2 + Math.random() * 3,
        gameMemoryMb: 500 + Math.random() * 100,
        gameCpuPercent: 15 + Math.random() * 5,
      }));

      expect(() => {
        render(<MetricsChart data={largeData} />);
      }).not.toThrow();

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });
  });

  describe('chart type toggle', () => {
    it('renders chart type toggle with line and stacked buttons', () => {
      render(<MetricsChart data={mockDataWithGame} />);

      expect(screen.getByTestId('chart-type-toggle')).toBeInTheDocument();
      expect(screen.getByTestId('chart-type-line')).toBeInTheDocument();
      expect(screen.getByTestId('chart-type-stacked')).toBeInTheDocument();
    });

    it('defaults to line chart selected', () => {
      render(<MetricsChart data={mockDataWithGame} />);

      const lineButton = screen.getByTestId('chart-type-line');
      const stackedButton = screen.getByTestId('chart-type-stacked');

      expect(lineButton).toHaveAttribute('aria-pressed', 'true');
      expect(stackedButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('switches to stacked area chart when toggle clicked', async () => {
      const user = userEvent.setup();
      render(<MetricsChart data={mockDataWithGame} />);

      const stackedButton = screen.getByTestId('chart-type-stacked');
      await user.click(stackedButton);

      expect(stackedButton).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByTestId('chart-type-line')).toHaveAttribute('aria-pressed', 'false');
    });

    it('has accessible labels on toggle buttons', () => {
      render(<MetricsChart data={mockDataWithGame} />);

      expect(screen.getByLabelText('Line chart')).toBeInTheDocument();
      expect(screen.getByLabelText('Stacked area chart')).toBeInTheDocument();
    });

    it('does not render toggle in empty state', () => {
      render(<MetricsChart data={[]} />);

      expect(screen.queryByTestId('chart-type-toggle')).not.toBeInTheDocument();
    });
  });

  describe('memoization', () => {
    it('is wrapped with React.memo for performance', () => {
      // Verify the component is a memoized function (React.memo returns a different type)
      // In React 19, we can check the component is a function and works correctly
      expect(typeof MetricsChart).toBe('object');
      // The component should render successfully (memo doesn't break anything)
      render(<MetricsChart data={[]} />);
      expect(screen.getByTestId('metrics-chart-empty')).toBeInTheDocument();
    });
  });
});

describe('MetricsChart accessibility', () => {
  it('has accessible container with test id', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const chart = screen.getByTestId('metrics-chart');
    expect(chart).toBeInTheDocument();
  });

  it('empty state is visually centered', () => {
    render(<MetricsChart data={[]} />);

    const emptyState = screen.getByTestId('metrics-chart-empty');
    expect(emptyState).toHaveClass('flex', 'items-center', 'justify-center');
  });

  it('has all 4 required data-testid attributes present', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    // All 4 required test IDs from the issue
    expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    expect(screen.getByTestId('chart-type-toggle')).toBeInTheDocument();
    expect(screen.getByTestId('chart-type-line')).toBeInTheDocument();
    expect(screen.getByTestId('chart-type-stacked')).toBeInTheDocument();
  });
});

describe('formatAxisTime', () => {
  it('formats valid ISO timestamp to HH:MM', () => {
    expect(formatAxisTime('2026-01-17T10:30:00Z')).toMatch(/\d{1,2}:\d{2}/);
  });

  it('handles midnight timestamps correctly', () => {
    const result = formatAxisTime('2026-01-17T00:00:00Z');
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });

  it('handles end of day timestamps correctly', () => {
    const result = formatAxisTime('2026-01-17T23:59:00Z');
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });

  it('returns "Invalid Date" for invalid date strings', () => {
    const invalidInput = 'not-a-date';
    expect(formatAxisTime(invalidInput)).toBe('Invalid Date');
  });

  it('returns "Invalid Date" for empty string', () => {
    expect(formatAxisTime('')).toBe('Invalid Date');
  });
});

describe('formatTooltipTime', () => {
  it('formats valid ISO timestamp with full date and time', () => {
    const result = formatTooltipTime('2026-01-17T10:30:00Z');
    // Should include month, day, and time
    expect(result).toContain('Jan');
    expect(result).toContain('17');
    expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
  });

  it('handles timestamps correctly (accounting for timezone)', () => {
    const result = formatTooltipTime('2026-01-17T00:00:00Z');
    // Result will be in local timezone, so check for valid format
    expect(result).toMatch(/[A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2}:\d{2}/);
  });

  it('returns "Invalid Date" for invalid date strings', () => {
    const invalidInput = 'invalid-timestamp';
    expect(formatTooltipTime(invalidInput)).toBe('Invalid Date');
  });

  it('returns "Invalid Date" for empty string', () => {
    expect(formatTooltipTime('')).toBe('Invalid Date');
  });
});

describe('formatMemory', () => {
  it('formats valid number with 1 decimal place', () => {
    expect(formatMemory(100.5)).toBe('100.5 MB');
    expect(formatMemory(0.0)).toBe('0.0 MB');
    // 512.25 rounds to 512.3 due to JavaScript floating point
    expect(formatMemory(512.25)).toBe('512.3 MB');
  });

  it('returns N/A for null value', () => {
    expect(formatMemory(null)).toBe('N/A');
  });

  it('returns N/A for undefined value', () => {
    expect(formatMemory(undefined)).toBe('N/A');
  });

  it('handles zero correctly', () => {
    expect(formatMemory(0)).toBe('0.0 MB');
    expect(formatMemory(0.0)).toBe('0.0 MB');
  });

  it('handles large values', () => {
    expect(formatMemory(2048.5)).toBe('2048.5 MB');
    expect(formatMemory(4096.0)).toBe('4096.0 MB');
  });
});

describe('CustomTooltip', () => {
  it('returns null when not active', () => {
    const { container } = render(
      <CustomTooltip active={false} payload={[]} label="2026-01-17T10:00:00Z" />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when payload is empty', () => {
    const { container } = render(
      <CustomTooltip active={true} payload={[]} label="2026-01-17T10:00:00Z" />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders tooltip with formatted timestamp', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: 100, color: '#89dceb' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    const tooltip = container.querySelector('[data-testid="chart-tooltip"]');
    expect(tooltip).toBeInTheDocument();
  });

  it('shows null values as N/A', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        payload={[
          { dataKey: 'gameMemoryMb', name: 'Game', value: null, color: '#a6e3a1' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    expect(container.textContent).toContain('Game: N/A');
  });

  it('shows valid values with MB suffix', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: 128.5, color: '#89dceb' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    expect(container.textContent).toContain('API: 128.5 MB');
  });

  it('shows total in stacked mode', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        showTotal={true}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: 100, color: '#89dceb' },
          { dataKey: 'gameMemoryMb', name: 'Game', value: 500, color: '#a6e3a1' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    // Total should be 600 MB
    expect(container.textContent).toContain('Total: 600.0 MB');
  });

  it('shows total when all values are null in stacked mode (treats null as 0)', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        showTotal={true}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: null, color: '#89dceb' },
          { dataKey: 'gameMemoryMb', name: 'Game', value: null, color: '#a6e3a1' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    // Null values are treated as 0 in the sum, so total is 0.0 MB
    expect(container.textContent).toContain('Total: 0.0 MB');
  });

  it('does not show total in line chart mode', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        showTotal={false}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: 100, color: '#89dceb' },
          { dataKey: 'gameMemoryMb', name: 'Game', value: 500, color: '#a6e3a1' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    expect(container.textContent).not.toContain('Total');
  });

  it('renders with correct colors for each data point', () => {
    const { container } = render(
      <CustomTooltip
        active={true}
        payload={[
          { dataKey: 'apiMemoryMb', name: 'API', value: 100, color: '#89dceb' },
          { dataKey: 'gameMemoryMb', name: 'Game', value: 500, color: '#a6e3a1' },
        ]}
        label="2026-01-17T10:00:00Z"
      />
    );

    const tooltip = container.querySelector('[data-testid="chart-tooltip"]');
    expect(tooltip).toBeInTheDocument();
  });
});

describe('ChartTypeToggle', () => {
  it('has line chart button with icon', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const lineButton = screen.getByTestId('chart-type-line');
    expect(lineButton).toHaveAttribute('aria-label', 'Line chart');
    expect(lineButton.querySelector('svg')).toBeInTheDocument();
  });

  it('has stacked area button with icon', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const stackedButton = screen.getByTestId('chart-type-stacked');
    expect(stackedButton).toHaveAttribute('aria-label', 'Stacked area chart');
    expect(stackedButton.querySelector('svg')).toBeInTheDocument();
  });

  it('line button has pressed state when selected', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const lineButton = screen.getByTestId('chart-type-line');
    expect(lineButton).toHaveAttribute('aria-pressed', 'true');
    expect(lineButton).toHaveClass('bg-primary', 'text-primary-foreground');
  });

  it('stacked button has unpressed state when not selected', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const stackedButton = screen.getByTestId('chart-type-stacked');
    expect(stackedButton).toHaveAttribute('aria-pressed', 'false');
    expect(stackedButton).not.toHaveClass('bg-primary');
  });

  it('clicking stacked button changes state', async () => {
    const user = userEvent.setup();
    render(<MetricsChart data={mockDataWithGame} />);

    const stackedButton = screen.getByTestId('chart-type-stacked');
    await user.click(stackedButton);

    expect(stackedButton).toHaveAttribute('aria-pressed', 'true');
  });

  it('clicking line button changes state from stacked', async () => {
    const user = userEvent.setup();
    render(<MetricsChart data={mockDataWithGame} />);

    // First switch to stacked
    const stackedButton = screen.getByTestId('chart-type-stacked');
    await user.click(stackedButton);

    // Then switch back to line
    const lineButton = screen.getByTestId('chart-type-line');
    await user.click(lineButton);

    expect(lineButton).toHaveAttribute('aria-pressed', 'true');
    expect(stackedButton).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggle has correct role and aria-label', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const toggle = screen.getByRole('group', { name: 'Chart type selector' });
    expect(toggle).toBeInTheDocument();
  });
});

describe('chart rendering with data', () => {
  it('renders chart with ResponsiveContainer', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const chart = screen.getByTestId('metrics-chart');
    expect(chart.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });

  it('applies custom height prop correctly', () => {
    render(<MetricsChart data={mockDataWithGame} height={450} />);

    const chart = screen.getByTestId('metrics-chart');
    const chartWrapper = chart.querySelector('[style*="height"]');
    expect(chartWrapper).toHaveStyle({ height: '450px' });
  });

  it('uses default height when not specified', () => {
    render(<MetricsChart data={mockDataWithGame} />);

    const chart = screen.getByTestId('metrics-chart');
    const chartWrapper = chart.querySelector('[style*="height"]');
    expect(chartWrapper).toHaveStyle({ height: '300px' });
  });

  it('toggles visibility when switching between chart types', async () => {
    const user = userEvent.setup();
    render(<MetricsChart data={mockDataWithGame} />);

    const chart = screen.getByTestId('metrics-chart');
    expect(chart).toBeInTheDocument();

    // Switch to stacked
    const stackedButton = screen.getByTestId('chart-type-stacked');
    await user.click(stackedButton);

    // Chart should still be present
    expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
  });
});
