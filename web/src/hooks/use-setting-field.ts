/**
 * Custom hook for managing individual setting field state.
 *
 * Provides value, error, and pending states with auto-save on blur.
 * Includes validation support and optimistic updates.
 *
 * Story 6.4: Settings UI
 */

import type { KeyboardEvent } from 'react';
import { useState, useCallback, useRef, useEffect } from 'react';
import type { SettingType } from '@/api/types';

/**
 * Union type for all possible setting values.
 */
export type SettingValue = string | number | boolean;

/**
 * Validation function type.
 * Returns null if valid, or error message string if invalid.
 */
export type Validator<T> = (value: T) => string | null;

/**
 * Built-in validators for common setting types.
 * All validators accept SettingValue to work with the generic SettingField.
 */
export const validators = {
  /**
   * Validates that a string is not empty.
   */
  required: (message = 'This field is required'): Validator<SettingValue> => (value) =>
    typeof value === 'string' && value.trim() === '' ? message : null,

  /**
   * Validates that a number is within a range.
   */
  range: (
    min: number,
    max: number,
    message?: string
  ): Validator<SettingValue> => (value) =>
    typeof value === 'number' && (value < min || value > max)
      ? message ?? `Value must be between ${min} and ${max}`
      : null,

  /**
   * Validates that a number is a positive integer.
   */
  positiveInt: (message = 'Must be a positive integer'): Validator<SettingValue> => (value) =>
    typeof value === 'number' && (!Number.isInteger(value) || value < 0) ? message : null,

  /**
   * Validates that a port number is valid.
   */
  port: (message = 'Port must be between 1 and 65535'): Validator<SettingValue> => (value) =>
    typeof value === 'number' && (!Number.isInteger(value) || value < 1 || value > 65535)
      ? message
      : null,

  /**
   * Combines multiple validators, returning first error or null.
   */
  compose: (...fns: Validator<SettingValue>[]): Validator<SettingValue> => (value) => {
    for (const fn of fns) {
      const error = fn(value);
      if (error) return error;
    }
    return null;
  },
};

/**
 * Options for the useSettingField hook.
 */
export interface UseSettingFieldOptions<T> {
  /**
   * Initial value of the field.
   */
  initialValue: T;

  /**
   * Setting key for the API update.
   */
  settingKey: string;

  /**
   * Setting type for value coercion.
   */
  settingType: SettingType;

  /**
   * Optional validation function.
   */
  validate?: Validator<T>;

  /**
   * Mutation function to save the value.
   */
  onSave: (params: { key: string; value: T }) => Promise<unknown>;

  /**
   * Whether the field is disabled (e.g., env-managed).
   */
  disabled?: boolean;
}

/**
 * Return type for the useSettingField hook.
 */
export interface UseSettingFieldReturn<T> {
  /**
   * Current value of the field.
   */
  value: T;

  /**
   * Set the field value.
   */
  setValue: (value: T) => void;

  /**
   * Current error message, or null if valid.
   */
  error: string | null;

  /**
   * Whether the field is currently saving.
   */
  isPending: boolean;

  /**
   * Whether the field value differs from initial.
   */
  isDirty: boolean;

  /**
   * Save the current value (called on blur).
   * Optionally accepts a value override for immediate saves (e.g., boolean toggles).
   */
  save: (valueOverride?: T) => Promise<void>;

  /**
   * Reset to initial value.
   */
  reset: () => void;

  /**
   * Handler for blur events (triggers save if dirty and valid).
   */
  onBlur: () => void;

  /**
   * Handler for keydown events (triggers save on Enter if dirty and valid).
   */
  onKeyDown: (e: KeyboardEvent) => void;
}

/**
 * Hook for managing individual setting field state.
 *
 * Provides value management, validation, and auto-save on blur.
 *
 * @example
 * function ServerNameField({ setting }: { setting: GameSetting }) {
 *   const { mutateAsync } = useUpdateGameSetting();
 *
 *   const field = useSettingField({
 *     initialValue: String(setting.value),
 *     settingKey: setting.key,
 *     settingType: setting.type,
 *     validate: validators.required(),
 *     onSave: mutateAsync,
 *     disabled: setting.envManaged,
 *   });
 *
 *   return (
 *     <div>
 *       <input
 *         value={field.value}
 *         onChange={(e) => field.setValue(e.target.value)}
 *         onBlur={field.onBlur}
 *         disabled={field.isPending || setting.envManaged}
 *       />
 *       {field.error && <span className="text-destructive">{field.error}</span>}
 *     </div>
 *   );
 * }
 */
export function useSettingField<T extends string | number | boolean>(
  options: UseSettingFieldOptions<T>
): UseSettingFieldReturn<T> {
  const { initialValue, settingKey, validate, onSave, disabled } = options;

  // Track the initial value so we can detect changes
  const initialRef = useRef(initialValue);

  // Update initial ref when initialValue changes (e.g., after server sync)
  useEffect(() => {
    initialRef.current = initialValue;
  }, [initialValue]);

  const [value, setValueState] = useState<T>(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  // Keep value in sync with initial when it changes externally
  useEffect(() => {
    setValueState(initialValue);
    setError(null);
  }, [initialValue]);

  const isDirty = value !== initialRef.current;

  const setValue = useCallback((newValue: T) => {
    setValueState(newValue);
    // Clear error when user starts typing
    setError(null);
  }, []);

  const save = useCallback(async (valueOverride?: T) => {
    if (disabled) return;

    // Use override if provided (for immediate saves like boolean toggles)
    const valueToSave = valueOverride !== undefined ? valueOverride : value;

    // Validate before saving
    if (validate) {
      const validationError = validate(valueToSave);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setError(null);
    setIsPending(true);

    try {
      await onSave({ key: settingKey, value: valueToSave });
      // Update the initial ref after successful save
      initialRef.current = valueToSave;
    } catch (err) {
      // Extract error message from API error
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to save setting';
      setError(message);
    } finally {
      setIsPending(false);
    }
  }, [disabled, validate, value, onSave, settingKey]);

  const reset = useCallback(() => {
    setValueState(initialRef.current);
    setError(null);
  }, []);

  const onBlur = useCallback(() => {
    // Only save if dirty, not disabled, and not already pending
    if (isDirty && !disabled && !isPending) {
      save();
    }
  }, [isDirty, disabled, isPending, save]);

  const onKeyDown = useCallback((e: KeyboardEvent) => {
    // Save on Enter key if dirty, not disabled, and not already pending
    if (e.key === 'Enter' && isDirty && !disabled && !isPending) {
      e.preventDefault();
      save();
    }
  }, [isDirty, disabled, isPending, save]);

  return {
    value,
    setValue,
    error,
    isPending,
    isDirty,
    save,
    reset,
    onBlur,
    onKeyDown,
  };
}

/**
 * Coerce a value to the appropriate type based on setting type.
 */
export function coerceSettingValue(
  value: string,
  type: SettingType
): string | number | boolean {
  switch (type) {
    case 'int':
      return parseInt(value, 10) || 0;
    case 'float':
      return parseFloat(value) || 0;
    case 'bool':
      return value === 'true' || value === '1';
    case 'string':
    default:
      return value;
  }
}
