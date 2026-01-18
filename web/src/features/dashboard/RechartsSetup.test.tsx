/**
 * Smoke test to verify Recharts library is properly installed and renders.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 1: Add Recharts dependency + verify setup + tests (AC: 1)
 *
 * Note: ResponsiveContainer requires actual DOM dimensions to render properly.
 * In JSDOM (test environment), we use fixed width/height on LineChart directly
 * since getBoundingClientRect returns 0 for all values.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
} from 'recharts';

const mockData = [
  { timestamp: '10:00', value: 100 },
  { timestamp: '10:10', value: 105 },
  { timestamp: '10:20', value: 110 },
];

/**
 * Simple test component to verify Recharts renders.
 * Uses fixed dimensions instead of ResponsiveContainer for JSDOM compatibility.
 */
function TestChart() {
  return (
    <div data-testid="test-chart-container">
      <LineChart width={300} height={200} data={mockData}>
        <XAxis dataKey="timestamp" />
        <YAxis />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#8884d8"
        />
      </LineChart>
    </div>
  );
}

describe('Recharts Setup Verification', () => {
  it('renders a basic LineChart with SVG', () => {
    render(<TestChart />);

    // Verify container exists
    expect(screen.getByTestId('test-chart-container')).toBeInTheDocument();

    // Recharts renders SVG - verify SVG element is present
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders chart elements with proper structure', () => {
    render(<TestChart />);

    // Check that SVG is rendered with correct class (Recharts adds recharts-wrapper)
    const container = screen.getByTestId('test-chart-container');
    expect(container.querySelector('.recharts-wrapper')).toBeInTheDocument();
  });

  it('handles empty data array without crashing', () => {
    function EmptyChart() {
      return (
        <div data-testid="empty-chart">
          <LineChart width={300} height={200} data={[]}>
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Line type="monotone" dataKey="value" stroke="#8884d8" />
          </LineChart>
        </div>
      );
    }

    // Should not throw
    render(<EmptyChart />);
    expect(screen.getByTestId('empty-chart')).toBeInTheDocument();
    // SVG should still be rendered even with empty data
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('renders multiple lines correctly', () => {
    const multiLineData = [
      { time: '10:00', api: 100, game: 500 },
      { time: '10:10', api: 105, game: 510 },
    ];

    function MultiLineChart() {
      return (
        <div data-testid="multi-line-chart">
          <LineChart width={300} height={200} data={multiLineData}>
            <XAxis dataKey="time" />
            <YAxis />
            <Line
              type="monotone"
              dataKey="api"
              stroke="#89b4fa"
              name="API"
            />
            <Line
              type="monotone"
              dataKey="game"
              stroke="#a6e3a1"
              name="Game"
            />
          </LineChart>
        </div>
      );
    }

    render(<MultiLineChart />);
    expect(screen.getByTestId('multi-line-chart')).toBeInTheDocument();

    // Verify SVG is rendered
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
