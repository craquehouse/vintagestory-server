/**
 * DurationInput component for human-readable duration editing.
 *
 * VSS-s9s: Human-readable duration input for refresh intervals
 *
 * Accepts inputs like "4h", "30m", "1d" and converts to/from seconds.
 * Displays the current value in human-readable format when not editing.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { parseDuration, formatDurationSimple } from '@/lib/duration-utils';

export interface DurationInputProps {
  /**
   * Current value in seconds.
   */
  value: number;

  /**
   * Callback when duration changes (value in seconds).
   */
  onChange: (seconds: number) => void;

  /**
   * Callback when input loses focus.
   */
  onBlur?: () => void;

  /**
   * Callback when Enter key is pressed.
   */
  onKeyDown?: (e: React.KeyboardEvent) => void;

  /**
   * Whether the input is disabled.
   */
  disabled?: boolean;

  /**
   * Input ID for accessibility.
   */
  id?: string;

  /**
   * aria-describedby for accessibility.
   */
  'aria-describedby'?: string;

  /**
   * aria-invalid for accessibility.
   */
  'aria-invalid'?: boolean;

  /**
   * Additional CSS class names.
   */
  className?: string;

  /**
   * Placeholder text.
   */
  placeholder?: string;
}

/**
 * Input component that accepts human-readable duration strings.
 *
 * @example
 * <DurationInput
 *   value={14400}  // 4 hours in seconds
 *   onChange={(seconds) => setSetting(seconds)}
 * />
 *
 * User can type "4h", "240m", "14400", etc.
 */
export function DurationInput({
  value,
  onChange,
  onBlur,
  onKeyDown,
  disabled = false,
  id,
  'aria-describedby': ariaDescribedBy,
  'aria-invalid': ariaInvalid,
  className,
  placeholder = 'e.g., 4h, 30m, 1d',
}: DurationInputProps) {
  // Track whether user is currently editing
  const [isEditing, setIsEditing] = useState(false);
  // Store the raw text input while editing
  const [inputText, setInputText] = useState('');
  // Track if there's a parse error
  const [parseError, setParseError] = useState<string | null>(null);
  // Ref to track if we should update display on value change
  const lastParsedSeconds = useRef<number>(value);

  // Initialize input text from value
  useEffect(() => {
    // Only update display if not editing and value changed externally
    if (!isEditing && value !== lastParsedSeconds.current) {
      lastParsedSeconds.current = value;
    }
  }, [value, isEditing]);

  // Display value: show formatted duration when not editing, raw input when editing
  const displayValue = isEditing ? inputText : formatDurationSimple(value);

  const handleFocus = useCallback(() => {
    setIsEditing(true);
    // Start editing with the current formatted value
    setInputText(formatDurationSimple(value));
    setParseError(null);
  }, [value]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newText = e.target.value;
    setInputText(newText);

    // Try to parse as user types for immediate feedback
    if (newText.trim()) {
      const result = parseDuration(newText);
      if (result.success) {
        setParseError(null);
        // Update the value immediately for responsive feel
        onChange(result.seconds);
        lastParsedSeconds.current = result.seconds;
      } else {
        setParseError(result.error ?? 'Invalid duration');
      }
    } else {
      setParseError(null);
    }
  }, [onChange]);

  const handleBlur = useCallback(() => {
    setIsEditing(false);

    // Final parse on blur
    if (inputText.trim()) {
      const result = parseDuration(inputText);
      if (result.success) {
        onChange(result.seconds);
        lastParsedSeconds.current = result.seconds;
        setParseError(null);
      }
      // If parse fails, keep the error state but revert display to last valid value
    }

    onBlur?.();
  }, [inputText, onChange, onBlur]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      // Parse and apply on Enter
      if (inputText.trim()) {
        const result = parseDuration(inputText);
        if (result.success) {
          onChange(result.seconds);
          lastParsedSeconds.current = result.seconds;
          setParseError(null);
        }
      }
    }
    onKeyDown?.(e);
  }, [inputText, onChange, onKeyDown]);

  return (
    <Input
      id={id}
      type="text"
      value={displayValue}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      placeholder={placeholder}
      aria-describedby={ariaDescribedBy}
      aria-invalid={ariaInvalid || !!parseError}
      className={cn(
        parseError && 'border-destructive focus-visible:ring-destructive',
        className
      )}
    />
  );
}
