/**
 * Custom hook for managing individual setting field state.
 *
 * Provides value, error, and pending states with auto-save on blur.
 * Includes validation support and optimistic updates.
 *
 * Story 6.4: Settings UI
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { SettingType } from '@/api/types';

/**
 * Validation function type.
 * Returns null if valid, or error message string if invalid.
 */
export type Validator<T> = (value: T) => string | null;

/**
 * Built-in validators for common setting types.
 */
export const validators = {
  /**
   * Validates that a string is not empty.
   */
  required: (message = 'This field is required'): Validator<string> => (value) =>
    value.trim() === '' ? message : null,

  /**
   * Validates that a number is within a range.
   */
  range: (
    min: number,
    max: number,
    message?: string
  ): Validator<number> => (value) =>
    value < min || value > max
      ? message ?? `Value must be between ${min} and ${max}`
      : null,

  /**
   * Validates that a number is a positive integer.
   */
  positiveInt: (message = 'Must be a positive integer'): Validator<number> => (value) =>
    !Number.isInteger(value) || value < 0 ? message : null,

  /**
   * Validates that a port number is valid.
   */
  port: (message = 'Port must be between 1 and 65535'): Validator<number> => (value) =>
    !Number.isInteger(value) || value < 1 || value > 65535 ? message : null,

  /**
   * Combines multiple validators, returning first error or null.
   */
  compose: <T>(...fns: Validator<T>[]): Validator<T> => (value) => {
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
   */
  save: () => Promise<void>;

  /**
   * Reset to initial value.
   */
  reset: () => void;

  /**
   * Handler for blur events (triggers save if dirty and valid).
   */
  onBlur: () => void;
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
 *       {field.error && <span className="text-red-500">{field.error}</span>}
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

  const save = useCallback(async () => {
    if (disabled) return;

    // Validate before saving
    if (validate) {
      const validationError = validate(value);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setError(null);
    setIsPending(true);

    try {
      await onSave({ key: settingKey, value });
      // Update the initial ref after successful save
      initialRef.current = value;
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

  return {
    value,
    setValue,
    error,
    isPending,
    isDirty,
    save,
    reset,
    onBlur,
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
