import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DurationInput } from './DurationInput';

describe('DurationInput', () => {
  const defaultProps = {
    value: 14400, // 4 hours
    onChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders input with formatted display value when not editing', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('4h');
    });

    it('renders with default placeholder', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('e.g., 4h, 30m, 1d');
      expect(input).toBeInTheDocument();
    });

    it('renders with custom placeholder', () => {
      render(
        <DurationInput
          {...defaultProps}
          placeholder="Enter duration like 5m"
        />
      );

      const input = screen.getByPlaceholderText('Enter duration like 5m');
      expect(input).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<DurationInput {...defaultProps} className="custom-class" />);

      const input = screen.getByRole('textbox');
      expect(input.className).toContain('custom-class');
    });

    it('renders disabled input when disabled prop is true', () => {
      render(<DurationInput {...defaultProps} disabled={true} />);

      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('displays different formatted values correctly', () => {
      const { rerender } = render(<DurationInput value={30} onChange={vi.fn()} />);
      expect(screen.getByRole('textbox')).toHaveValue('30s');

      rerender(<DurationInput value={300} onChange={vi.fn()} />);
      expect(screen.getByRole('textbox')).toHaveValue('5m');

      rerender(<DurationInput value={3600} onChange={vi.fn()} />);
      expect(screen.getByRole('textbox')).toHaveValue('1h');

      rerender(<DurationInput value={86400} onChange={vi.fn()} />);
      expect(screen.getByRole('textbox')).toHaveValue('1d');

      // 5400 seconds = 90 minutes exactly, formatDurationSimple returns "90m"
      rerender(<DurationInput value={5400} onChange={vi.fn()} />);
      expect(screen.getByRole('textbox')).toHaveValue('90m');
    });
  });

  describe('editing mode (focus/blur)', () => {
    it('switches to editing mode on focus', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox') as HTMLInputElement;
      expect(input.value).toBe('4h');

      fireEvent.focus(input);

      // Value should remain the same in editing mode
      expect(input.value).toBe('4h');
    });

    it('exits editing mode on blur', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.blur(input);

      expect(input).toHaveValue('4h');
    });

    it('preserves formatted value when focusing without changes', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.blur(input);

      expect(input).toHaveValue('4h');
    });

    it('calls onBlur callback when provided', () => {
      const onBlur = vi.fn();
      render(<DurationInput {...defaultProps} onBlur={onBlur} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.blur(input);

      expect(onBlur).toHaveBeenCalledTimes(1);
    });

    it('updates display when value changes externally while not editing', () => {
      const { rerender } = render(<DurationInput value={3600} onChange={vi.fn()} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('1h');

      rerender(<DurationInput value={7200} onChange={vi.fn()} />);
      expect(input).toHaveValue('2h');
    });

    it('does not update display when value changes externally while editing', () => {
      const onChange = vi.fn();
      const { rerender } = render(
        <DurationInput value={3600} onChange={onChange} />
      );

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '5h' } });

      // External value change while editing
      rerender(<DurationInput value={7200} onChange={onChange} />);

      // Should still show the input text while editing
      expect(input).toHaveValue('5h');
    });
  });

  describe('user input and parsing', () => {
    it('updates input value as user types', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '30m' } });

      expect(input).toHaveValue('30m');
    });

    it('calls onChange immediately when valid input is typed', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '30m' } });

      expect(onChange).toHaveBeenCalledWith(1800);
    });

    it('parses various valid duration formats', () => {
      const onChange = vi.fn();
      const { rerender } = render(
        <DurationInput value={0} onChange={onChange} />
      );

      const input = screen.getByRole('textbox');

      // Test "4h"
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '4h' } });
      expect(onChange).toHaveBeenCalledWith(14400);

      // Reset
      onChange.mockClear();
      rerender(<DurationInput value={0} onChange={onChange} />);
      fireEvent.focus(input);

      // Test "30m"
      fireEvent.change(input, { target: { value: '30m' } });
      expect(onChange).toHaveBeenCalledWith(1800);

      // Reset
      onChange.mockClear();
      rerender(<DurationInput value={0} onChange={onChange} />);
      fireEvent.focus(input);

      // Test "1d"
      fireEvent.change(input, { target: { value: '1d' } });
      expect(onChange).toHaveBeenCalledWith(86400);

      // Reset
      onChange.mockClear();
      rerender(<DurationInput value={0} onChange={onChange} />);
      fireEvent.focus(input);

      // Test plain number "300"
      fireEvent.change(input, { target: { value: '300' } });
      expect(onChange).toHaveBeenCalledWith(300);

      // Reset
      onChange.mockClear();
      rerender(<DurationInput value={0} onChange={onChange} />);
      fireEvent.focus(input);

      // Test compound "1h30m"
      fireEvent.change(input, { target: { value: '1h30m' } });
      expect(onChange).toHaveBeenCalledWith(5400);
    });

    it('handles empty input gracefully', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '' } });

      // Should not call onChange for empty string
      expect(onChange).not.toHaveBeenCalled();
    });

    it('applies changes on blur with valid input', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '2h' } });
      onChange.mockClear(); // Clear the onChange call from typing

      fireEvent.blur(input);

      expect(onChange).toHaveBeenCalledWith(7200);
    });

    it('does not call onChange on blur if input is empty', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '' } });
      onChange.mockClear();

      fireEvent.blur(input);

      // Should not call onChange on blur for empty input
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe('parse error handling', () => {
    it('shows error styling for invalid input', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'invalid' } });

      expect(input.className).toContain('border-destructive');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('clears error styling when input becomes valid', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      // Invalid input
      fireEvent.change(input, { target: { value: 'invalid' } });
      expect(input.className).toContain('border-destructive');

      // Valid input
      fireEvent.change(input, { target: { value: '5m' } });
      expect(input.className).not.toContain('border-destructive');
    });

    it('shows immediate feedback for parse errors while typing', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      fireEvent.change(input, { target: { value: 'xyz' } });
      expect(input).toHaveAttribute('aria-invalid', 'true');
      expect(input.className).toContain('border-destructive');
    });

    it('handles invalid units', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '5x' } });

      expect(onChange).not.toHaveBeenCalled();
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('handles malformed duration strings', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'h4' } });

      expect(onChange).not.toHaveBeenCalled();
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('clears error on blur and reverts to last valid value', () => {
      render(<DurationInput value={3600} onChange={vi.fn()} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'invalid' } });

      expect(input).toHaveAttribute('aria-invalid', 'true');

      fireEvent.blur(input);

      // Should revert to the formatted version of the current value
      expect(input).toHaveValue('1h');
    });

    it('clears error when user clears the input', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      // Type invalid input
      fireEvent.change(input, { target: { value: 'invalid' } });
      expect(input).toHaveAttribute('aria-invalid', 'true');

      // Clear input
      fireEvent.change(input, { target: { value: '' } });
      expect(input).not.toHaveAttribute('aria-invalid', 'true');
    });
  });

  describe('keyboard interaction', () => {
    it('applies value on Enter key', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '10m' } });
      onChange.mockClear(); // Clear the onChange from typing

      fireEvent.keyDown(input, { key: 'Enter' });

      expect(onChange).toHaveBeenCalledWith(600);
    });

    it('calls onKeyDown callback when provided', () => {
      const onKeyDown = vi.fn();
      render(<DurationInput {...defaultProps} onKeyDown={onKeyDown} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(onKeyDown).toHaveBeenCalled();
    });

    it('does not apply invalid value on Enter', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'invalid' } });
      onChange.mockClear();

      fireEvent.keyDown(input, { key: 'Enter' });

      // Should not call onChange for invalid input
      expect(onChange).not.toHaveBeenCalled();
    });

    it('does not apply empty value on Enter', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '' } });

      fireEvent.keyDown(input, { key: 'Enter' });

      // Should not call onChange for empty input
      expect(onChange).not.toHaveBeenCalled();
    });

    it('forwards other key events to onKeyDown', () => {
      const onKeyDown = vi.fn();
      render(<DurationInput {...defaultProps} onKeyDown={onKeyDown} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.keyDown(input, { key: 'Escape' });

      expect(onKeyDown).toHaveBeenCalledWith(
        expect.objectContaining({ key: 'Escape' })
      );
    });
  });

  describe('accessibility', () => {
    it('uses provided id', () => {
      render(<DurationInput {...defaultProps} id="duration-input" />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('id', 'duration-input');
    });

    it('sets aria-describedby when provided', () => {
      render(
        <DurationInput
          {...defaultProps}
          aria-describedby="duration-help-text"
        />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'duration-help-text');
    });

    it('sets aria-invalid when provided externally', () => {
      render(<DurationInput {...defaultProps} aria-invalid={true} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('sets aria-invalid when parse error occurs', () => {
      render(<DurationInput {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'bad' } });

      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('combines external aria-invalid with parse error state', () => {
      render(<DurationInput {...defaultProps} aria-invalid={true} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'invalid' } });

      expect(input).toHaveAttribute('aria-invalid', 'true');
    });
  });

  describe('edge cases', () => {
    it('handles zero value', () => {
      render(<DurationInput value={0} onChange={vi.fn()} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('0s');
    });

    it('handles very large values', () => {
      // 10 days
      render(<DurationInput value={864000} onChange={vi.fn()} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('10d');
    });

    it('handles compound durations with multiple units', () => {
      // 1 day, 2 hours, 30 minutes = 95400 seconds = 1590 minutes exactly
      // formatDurationSimple returns "1590m" since it's divisible by 60
      render(<DurationInput value={95400} onChange={vi.fn()} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('1590m');
    });

    it('maintains last parsed value through multiple invalid attempts', () => {
      const onChange = vi.fn();
      const { rerender } = render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      // Type valid value
      fireEvent.change(input, { target: { value: '2h' } });
      expect(onChange).toHaveBeenCalledWith(7200);

      // Parent updates the value prop after onChange
      rerender(<DurationInput value={7200} onChange={onChange} />);

      // Type invalid values
      onChange.mockClear();
      fireEvent.change(input, { target: { value: 'xyz' } });
      fireEvent.change(input, { target: { value: 'abc' } });

      // onChange should not be called for invalid values
      expect(onChange).not.toHaveBeenCalled();

      // Blur should revert to formatted value of the current value prop (7200)
      fireEvent.blur(input);
      expect(input).toHaveValue('2h');
    });

    it('handles rapid focus/blur cycles', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');

      for (let i = 0; i < 5; i++) {
        fireEvent.focus(input);
        fireEvent.blur(input);
      }

      // Should maintain value and not cause errors
      expect(input).toHaveValue('1h');
    });

    it('handles onChange being called with the same value multiple times', () => {
      const onChange = vi.fn();
      render(<DurationInput value={0} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      // Type different values that all parse to the same result
      fireEvent.change(input, { target: { value: '1h' } });
      fireEvent.change(input, { target: { value: '60m' } }); // Also 3600 seconds
      fireEvent.change(input, { target: { value: '3600' } }); // Also 3600 seconds

      // onChange should be called each time with 3600 (component doesn't dedupe)
      expect(onChange).toHaveBeenCalledTimes(3);
      expect(onChange).toHaveBeenNthCalledWith(1, 3600);
      expect(onChange).toHaveBeenNthCalledWith(2, 3600);
      expect(onChange).toHaveBeenNthCalledWith(3, 3600);
    });
  });

  describe('props handling', () => {
    it('respects disabled state', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} disabled={true} />);

      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();

      // Disabled inputs should not allow user interaction
      // The browser prevents change events on disabled inputs, so we just verify it's disabled
    });

    it('applies custom className along with error styling', () => {
      render(<DurationInput {...defaultProps} className="my-custom-class" />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: 'invalid' } });

      expect(input.className).toContain('my-custom-class');
      expect(input.className).toContain('border-destructive');
    });

    it('works without optional callbacks', () => {
      render(
        <DurationInput
          value={3600}
          onChange={vi.fn()}
          // No onBlur or onKeyDown
        />
      );

      const input = screen.getByRole('textbox');

      // Should not throw errors
      expect(() => {
        fireEvent.focus(input);
        fireEvent.blur(input);
        fireEvent.keyDown(input, { key: 'Enter' });
      }).not.toThrow();
    });
  });

  describe('integration scenarios', () => {
    it('simulates complete user editing flow', () => {
      const onChange = vi.fn();
      const { rerender } = render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');

      // Initial display
      expect(input).toHaveValue('1h');

      // User focuses
      fireEvent.focus(input);
      expect(input).toHaveValue('1h');

      // User types new value
      fireEvent.change(input, { target: { value: '30m' } });
      expect(input).toHaveValue('30m');
      expect(onChange).toHaveBeenCalledWith(1800);

      // Parent component updates the value prop
      rerender(<DurationInput value={1800} onChange={onChange} />);

      // User finishes editing
      fireEvent.blur(input);

      // Display should show formatted value (exits editing mode)
      expect(input).toHaveValue('30m');
    });

    it('simulates user correcting a typo', () => {
      const onChange = vi.fn();
      render(<DurationInput value={3600} onChange={onChange} />);

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);

      // User makes a typo
      fireEvent.change(input, { target: { value: '5hh' } });
      expect(input).toHaveAttribute('aria-invalid', 'true');
      onChange.mockClear();

      // User corrects it
      fireEvent.change(input, { target: { value: '5h' } });
      expect(input).not.toHaveAttribute('aria-invalid', 'true');
      expect(onChange).toHaveBeenCalledWith(18000);
    });

    it('simulates form submission flow with Enter key', () => {
      const onChange = vi.fn();
      const onKeyDown = vi.fn();
      render(
        <DurationInput value={0} onChange={onChange} onKeyDown={onKeyDown} />
      );

      const input = screen.getByRole('textbox');
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: '2h' } });
      onChange.mockClear();

      fireEvent.keyDown(input, { key: 'Enter' });

      expect(onChange).toHaveBeenCalledWith(7200);
      expect(onKeyDown).toHaveBeenCalledWith(
        expect.objectContaining({ key: 'Enter' })
      );
    });
  });
});
