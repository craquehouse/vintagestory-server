/**
 * Tests for TimeRangeSelector component.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 3: Create TimeRangeSelector component + tests (AC: 3)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  TimeRangeSelector,
  TIME_RANGES,
  DEFAULT_TIME_RANGE,
} from './TimeRangeSelector';

describe('TimeRangeSelector', () => {
  describe('rendering', () => {
    it('renders all time range options', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      expect(screen.getByTestId('time-range-selector')).toBeInTheDocument();
      expect(screen.getByText('15m')).toBeInTheDocument();
      expect(screen.getByText('1h')).toBeInTheDocument();
      expect(screen.getByText('6h')).toBeInTheDocument();
      expect(screen.getByText('24h')).toBeInTheDocument();
    });

    it('has correct test IDs for each button', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      expect(screen.getByTestId('time-range-15')).toBeInTheDocument();
      expect(screen.getByTestId('time-range-60')).toBeInTheDocument();
      expect(screen.getByTestId('time-range-360')).toBeInTheDocument();
      expect(screen.getByTestId('time-range-1440')).toBeInTheDocument();
    });

    it('renders with custom className', () => {
      render(
        <TimeRangeSelector
          value={60}
          onChange={vi.fn()}
          className="custom-class"
        />
      );

      const selector = screen.getByTestId('time-range-selector');
      expect(selector).toHaveClass('custom-class');
    });
  });

  describe('selection state', () => {
    it('highlights the selected time range (1h default)', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      const selectedButton = screen.getByTestId('time-range-60');
      expect(selectedButton).toHaveAttribute('aria-pressed', 'true');
      expect(selectedButton).toHaveClass('bg-primary');
    });

    it('highlights 15m when selected', () => {
      render(<TimeRangeSelector value={15} onChange={vi.fn()} />);

      const selectedButton = screen.getByTestId('time-range-15');
      expect(selectedButton).toHaveAttribute('aria-pressed', 'true');
      expect(selectedButton).toHaveClass('bg-primary');

      const unselectedButton = screen.getByTestId('time-range-60');
      expect(unselectedButton).toHaveAttribute('aria-pressed', 'false');
      expect(unselectedButton).toHaveClass('bg-muted');
    });

    it('highlights 6h when selected', () => {
      render(<TimeRangeSelector value={360} onChange={vi.fn()} />);

      const selectedButton = screen.getByTestId('time-range-360');
      expect(selectedButton).toHaveAttribute('aria-pressed', 'true');
    });

    it('highlights 24h when selected', () => {
      render(<TimeRangeSelector value={1440} onChange={vi.fn()} />);

      const selectedButton = screen.getByTestId('time-range-1440');
      expect(selectedButton).toHaveAttribute('aria-pressed', 'true');
    });
  });

  describe('interaction (AC: 3)', () => {
    it('calls onChange with 15 when 15m is clicked', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<TimeRangeSelector value={60} onChange={onChange} />);

      await user.click(screen.getByText('15m'));
      expect(onChange).toHaveBeenCalledWith(15);
    });

    it('calls onChange with 60 when 1h is clicked', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<TimeRangeSelector value={15} onChange={onChange} />);

      await user.click(screen.getByText('1h'));
      expect(onChange).toHaveBeenCalledWith(60);
    });

    it('calls onChange with 360 when 6h is clicked', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<TimeRangeSelector value={60} onChange={onChange} />);

      await user.click(screen.getByText('6h'));
      expect(onChange).toHaveBeenCalledWith(360);
    });

    it('calls onChange with 1440 when 24h is clicked', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<TimeRangeSelector value={60} onChange={onChange} />);

      await user.click(screen.getByText('24h'));
      expect(onChange).toHaveBeenCalledWith(1440);
    });

    it('calls onChange even when clicking already selected option', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<TimeRangeSelector value={60} onChange={onChange} />);

      await user.click(screen.getByText('1h'));
      expect(onChange).toHaveBeenCalledWith(60);
    });
  });

  describe('accessibility', () => {
    it('has correct role=group with aria-label', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      const selector = screen.getByRole('group', {
        name: 'Time range selector',
      });
      expect(selector).toBeInTheDocument();
    });

    it('buttons have type="button" to prevent form submission', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });

    it('buttons have correct aria-pressed state', () => {
      render(<TimeRangeSelector value={60} onChange={vi.fn()} />);

      // 1h should be pressed
      expect(screen.getByTestId('time-range-60')).toHaveAttribute(
        'aria-pressed',
        'true'
      );

      // Others should not be pressed
      expect(screen.getByTestId('time-range-15')).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByTestId('time-range-360')).toHaveAttribute(
        'aria-pressed',
        'false'
      );
      expect(screen.getByTestId('time-range-1440')).toHaveAttribute(
        'aria-pressed',
        'false'
      );
    });
  });

  describe('exports', () => {
    it('exports TIME_RANGES with correct values', () => {
      expect(TIME_RANGES).toHaveLength(4);
      expect(TIME_RANGES[0]).toEqual({ label: '15m', minutes: 15 });
      expect(TIME_RANGES[1]).toEqual({ label: '1h', minutes: 60 });
      expect(TIME_RANGES[2]).toEqual({ label: '6h', minutes: 360 });
      expect(TIME_RANGES[3]).toEqual({ label: '24h', minutes: 1440 });
    });

    it('exports DEFAULT_TIME_RANGE as 60 (1 hour)', () => {
      expect(DEFAULT_TIME_RANGE).toBe(60);
    });
  });
});
