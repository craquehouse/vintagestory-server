/**
 * DurationSettingField component for duration settings with human-readable input.
 *
 * VSS-s9s: Human-readable duration input for refresh intervals
 *
 * Like SettingField but specialized for duration values.
 * Accepts inputs like "4h", "30m", "1d" and converts to/from seconds.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { parseDuration, formatDurationSimple } from '@/lib/duration-utils';

export interface DurationSettingFieldProps {
  /**
   * Setting key for display and API updates.
   */
  settingKey: string;

  /**
   * Display label for the setting.
   */
  label: string;

  /**
   * Current value in seconds.
   */
  value: number;

  /**
   * Optional description/help text.
   */
  description?: string;

  /**
   * Minimum duration in seconds.
   */
  min?: number;

  /**
   * Maximum duration in seconds.
   */
  max?: number;

  /**
   * Custom min error message. Supports {min} placeholder for formatted duration.
   */
  minMessage?: string;

  /**
   * Custom max error message. Supports {max} placeholder for formatted duration.
   */
  maxMessage?: string;

  /**
   * Whether the setting is managed by environment variable.
   */
  envManaged?: boolean;

  /**
   * Environment variable name (shown in badge).
   */
  envVar?: string;

  /**
   * Mutation function to save the value.
   */
  onSave: (params: { key: string; value: number }) => Promise<unknown>;

  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Renders a duration setting field with human-readable input.
 *
 * @example
 * <DurationSettingField
 *   settingKey="mod_list_refresh_interval"
 *   label="Mod List Refresh"
 *   value={14400}
 *   min={60}
 *   max={86400}
 *   description="How often to refresh the mod list"
 *   onSave={handleSave}
 * />
 */
export function DurationSettingField({
  settingKey,
  label,
  value,
  description,
  min,
  max,
  minMessage,
  maxMessage,
  envManaged = false,
  envVar,
  onSave,
  className,
}: DurationSettingFieldProps) {
  // Track the initial value from props
  const initialRef = useRef(value);

  // Update initial ref when value changes externally
  useEffect(() => {
    initialRef.current = value;
    // Also update display when external value changes (and not editing)
    if (!isEditing) {
      setInputText(formatDurationSimple(value));
    }
  }, [value]);

  // Track whether user is currently editing
  const [isEditing, setIsEditing] = useState(false);
  // Store the raw text input
  const [inputText, setInputText] = useState(() => formatDurationSimple(value));
  // Track current seconds value
  const [currentSeconds, setCurrentSeconds] = useState(value);
  // Track error state
  const [error, setError] = useState<string | null>(null);
  // Track save pending state
  const [isPending, setIsPending] = useState(false);

  const isDisabled = envManaged || isPending;

  // Validate seconds against min/max
  const validateRange = useCallback((seconds: number): string | null => {
    if (min !== undefined && seconds < min) {
      const formatted = formatDurationSimple(min);
      return minMessage?.replace('{min}', formatted) ?? `Must be at least ${formatted}`;
    }
    if (max !== undefined && seconds > max) {
      const formatted = formatDurationSimple(max);
      return maxMessage?.replace('{max}', formatted) ?? `Must be at most ${formatted}`;
    }
    return null;
  }, [min, max, minMessage, maxMessage]);

  const handleFocus = useCallback(() => {
    setIsEditing(true);
    // Start editing with the current formatted value
    setInputText(formatDurationSimple(currentSeconds));
    setError(null);
  }, [currentSeconds]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newText = e.target.value;
    setInputText(newText);

    // Try to parse as user types for immediate feedback
    if (newText.trim()) {
      const result = parseDuration(newText);
      if (result.success) {
        const rangeError = validateRange(result.seconds);
        setError(rangeError);
        setCurrentSeconds(result.seconds);
      } else {
        setError(result.error ?? 'Invalid duration');
      }
    } else {
      setError('Duration cannot be empty');
    }
  }, [validateRange]);

  const save = useCallback(async () => {
    if (isDisabled) return;

    // Parse current input
    const result = parseDuration(inputText);
    if (!result.success) {
      setError(result.error ?? 'Invalid duration');
      return;
    }

    // Validate range
    const rangeError = validateRange(result.seconds);
    if (rangeError) {
      setError(rangeError);
      return;
    }

    // Check if value changed
    if (result.seconds === initialRef.current) {
      setIsEditing(false);
      return;
    }

    setError(null);
    setIsPending(true);

    try {
      await onSave({ key: settingKey, value: result.seconds });
      initialRef.current = result.seconds;
      setCurrentSeconds(result.seconds);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save setting';
      setError(message);
    } finally {
      setIsPending(false);
      setIsEditing(false);
    }
  }, [inputText, isDisabled, onSave, settingKey, validateRange]);

  const handleBlur = useCallback(() => {
    save();
  }, [save]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      save();
    }
  }, [save]);

  // Display value: formatted duration when not editing, raw input when editing
  const displayValue = isEditing ? inputText : formatDurationSimple(currentSeconds);

  return (
    <div className={cn('space-y-1', className)}>
      {/* Label and badges row */}
      <div className="flex items-center gap-2">
        <label
          htmlFor={settingKey}
          className="text-sm font-medium text-foreground"
        >
          {label}
        </label>

        {/* Env managed badge */}
        {envManaged && (
          <Badge
            variant="outline"
            className="text-xs bg-warning/10 text-warning border-warning/30"
          >
            Env: {envVar || `VS_CFG_${settingKey.toUpperCase()}`}
          </Badge>
        )}

        {/* Loading indicator */}
        {isPending && (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        )}
      </div>

      {/* Duration input */}
      <Input
        id={settingKey}
        type="text"
        value={displayValue}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder="e.g., 4h, 30m, 1d"
        aria-describedby={
          error ? `${settingKey}-error` : description ? `${settingKey}-desc` : undefined
        }
        aria-invalid={!!error}
        className={cn(
          error && 'border-destructive focus-visible:ring-destructive'
        )}
      />

      {/* Description text */}
      {description && !error && (
        <p
          id={`${settingKey}-desc`}
          className="text-xs text-muted-foreground"
        >
          {description}
        </p>
      )}

      {/* Error message */}
      {error && (
        <p
          id={`${settingKey}-error`}
          className="text-xs text-destructive"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}
