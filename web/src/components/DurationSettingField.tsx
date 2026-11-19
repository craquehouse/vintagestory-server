/**
 * DurationSettingField component for duration settings with human-readable input.
 *
 * VSS-s9s: Human-readable duration input for refresh intervals
 * Story 22.5: optional On switch (offValue/onValue)
 *
 * Like SettingField but specialized for duration values.
 * Accepts inputs like "4h", "30m", "1d" and converts to/from seconds.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { parseDuration, formatDurationSimple } from '@/lib/duration-utils';

/**
 * Story 22.5: the last value other than the off value each On switch has seen, by setting
 * key. Module level so it survives the tab switches that unmount the field; a reload
 * clears it (Epic 22 ADR-11 decision 1, controller decision 3).
 */
const lastOnValues = new Map<string, number>();

/**
 * Clears what the On switches remember; the page forgets on reload. For tests.
 */
export function forgetRememberedDurations(): void {
  lastOnValues.clear();
}

interface DurationSettingFieldBaseProps {
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

/** Story 22.5: an On switch; both values or neither (Epic 22 ADR-11 decision 5) */
type OnOffProps =
  | {
      /** Saved when the switch is turned off (0: the job is not registered) */
      offValue: number;
      /** Saved when turned on and the page has seen no non-zero value for the setting (the API's default) */
      onValue: number;
    }
  | { offValue?: undefined; onValue?: undefined };

export type DurationSettingFieldProps = DurationSettingFieldBaseProps & OnOffProps;

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
 *
 * With `offValue` and `onValue` the field has an On switch: off saves `offValue` and shows
 * "Off" in place of the input; on saves the last other value this page has seen for the
 * setting, else `onValue`. Neither is range-checked: `min` and `max` apply to typed input.
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
  offValue,
  onValue,
}: DurationSettingFieldProps) {
  const hasSwitch = offValue !== undefined && onValue !== undefined;

  // The last saved value the field knows: an unchanged typed value is not saved
  const initialRef = useRef(value);
  // The last value prop the field has taken (Story 22.5)
  const appliedValueRef = useRef(value);
  // The latest value prop, read after a switch save settles
  const latestValueRef = useRef(value);
  latestValueRef.current = value;
  // Set synchronously while a save is in flight, before a re-render can disable the field
  const savingRef = useRef(false);

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

  // Story 22.5: remember any value other than the off value for the switch to restore
  const remember = useCallback(
    (seconds: number) => {
      if (offValue !== undefined && onValue !== undefined && seconds !== offValue) {
        lastOnValues.set(settingKey, seconds);
      }
    },
    [offValue, onValue, settingKey]
  );

  // Remember the value the field mounts with
  useEffect(() => {
    remember(appliedValueRef.current);
  }, [remember]);

  // Story 22.5: follow a changed value prop whenever the field is neither being edited nor
  // saving; a change that arrives during a save is taken once the save settles
  useEffect(() => {
    if (isEditing || isPending || value === appliedValueRef.current) return;
    appliedValueRef.current = value;
    initialRef.current = value;
    setCurrentSeconds(value);
    setInputText(formatDurationSimple(value));
    remember(value);
  }, [value, isEditing, isPending, remember]);

  const isDisabled = envManaged || isPending;

  // Validate seconds against min/max
  const validateRange = useCallback(
    (seconds: number): string | null => {
      if (min !== undefined && seconds < min) {
        const formatted = formatDurationSimple(min);
        return minMessage?.replace('{min}', formatted) ?? `Must be at least ${formatted}`;
      }
      if (max !== undefined && seconds > max) {
        const formatted = formatDurationSimple(max);
        return maxMessage?.replace('{max}', formatted) ?? `Must be at most ${formatted}`;
      }
      return null;
    },
    [min, max, minMessage, maxMessage]
  );

  const handleFocus = useCallback(() => {
    setIsEditing(true);
    // Start editing with the current formatted value
    setInputText(formatDurationSimple(currentSeconds));
    setError(null);
  }, [currentSeconds]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
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
    },
    [validateRange]
  );

  const save = useCallback(async () => {
    if (isDisabled || savingRef.current) return;

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
    savingRef.current = true;
    setIsPending(true);

    try {
      await onSave({ key: settingKey, value: result.seconds });
      initialRef.current = result.seconds;
      setCurrentSeconds(result.seconds);
      remember(result.seconds);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save setting';
      setError(message);
    } finally {
      savingRef.current = false;
      setIsPending(false);
      setIsEditing(false);
    }
  }, [inputText, isDisabled, onSave, settingKey, validateRange, remember]);

  // Story 22.5: the On switch saves at once, optimistically, and reverts on failure
  const handleToggle = useCallback(
    async (checked: boolean) => {
      if (offValue === undefined || onValue === undefined) return;
      if (isDisabled || savingRef.current) return;

      const next = checked ? (lastOnValues.get(settingKey) ?? onValue) : offValue;
      const previous = currentSeconds;
      savingRef.current = true;
      setError(null);
      setIsEditing(false);
      setCurrentSeconds(next);
      setIsPending(true);

      try {
        await onSave({ key: settingKey, value: next });
        initialRef.current = next;
        setInputText(formatDurationSimple(next));
        remember(next);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to save setting';
        setError(message);
        // A parent that echoes saves moves the prop (the optimistic value, then the
        // rollback or the kept value); follow it instead of reverting here
        if (latestValueRef.current === appliedValueRef.current) {
          setCurrentSeconds(previous);
        }
      } finally {
        savingRef.current = false;
        setIsPending(false);
      }
    },
    [offValue, onValue, isDisabled, settingKey, currentSeconds, onSave, remember]
  );

  const handleBlur = useCallback(() => {
    save();
  }, [save]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        save();
      }
    },
    [save]
  );

  // Display value: formatted duration when not editing, raw input when editing
  const displayValue = isEditing ? inputText : formatDurationSimple(currentSeconds);
  // With the switch, the setting is on unless its value is the off value; a value being
  // typed (perhaps 0, which the range check refuses) keeps the input shown
  const isOn = !hasSwitch || isEditing || currentSeconds !== offValue;
  const describedBy = error
    ? `${settingKey}-error`
    : description
      ? `${settingKey}-desc`
      : undefined;

  return (
    <div className={cn('space-y-1', className)}>
      {/* Label and badges row */}
      <div className="flex items-center gap-2">
        <label
          htmlFor={isOn ? settingKey : undefined}
          className="text-sm font-medium text-foreground"
        >
          {label}
        </label>

        {/* Story 22.5: the On switch, inside a 44px-below-lg tap target */}
        {hasSwitch && (
          <label
            data-testid={`${settingKey}-switch-target`}
            className="inline-flex items-center gap-2 cursor-pointer max-lg:min-h-11"
          >
            <Switch
              id={`${settingKey}-enabled`}
              checked={isOn}
              aria-label={`${label} On`}
              aria-describedby={describedBy}
              disabled={isDisabled}
              data-testid={`${settingKey}-switch`}
              onCheckedChange={handleToggle}
            />
            <span className="text-sm text-muted-foreground">On</span>
          </label>
        )}

        {/* Env managed badge */}
        {envManaged && (
          <Badge variant="outline" className="text-xs bg-warning/10 text-warning border-warning/30">
            Env: {envVar || `VS_CFG_${settingKey.toUpperCase()}`}
          </Badge>
        )}

        {/* Loading indicator */}
        {isPending && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>

      {/* Duration input, or "Off" when the switch is off */}
      {isOn ? (
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
          aria-describedby={describedBy}
          aria-invalid={!!error}
          className={cn(error && 'border-destructive focus-visible:ring-destructive')}
        />
      ) : (
        <p data-testid={`${settingKey}-off`} className="text-sm text-muted-foreground">
          Off
        </p>
      )}

      {/* Description text */}
      {description && !error && (
        <p id={`${settingKey}-desc`} className="text-xs text-muted-foreground">
          {description}
        </p>
      )}

      {/* Error message */}
      {error && (
        <p id={`${settingKey}-error`} className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
