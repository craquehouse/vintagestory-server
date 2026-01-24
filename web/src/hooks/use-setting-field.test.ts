import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useSettingField,
  validators,
  coerceSettingValue,
} from './use-setting-field';
import * as durationUtils from '@/lib/duration-utils';

describe('useSettingField', () => {
  describe('initial state', () => {
    it('initializes with the provided value', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'test value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      expect(result.current.value).toBe('test value');
      expect(result.current.error).toBeNull();
      expect(result.current.isPending).toBe(false);
      expect(result.current.isDirty).toBe(false);
    });

    it('initializes with number value', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 42420,
          settingKey: 'Port',
          settingType: 'int',
          onSave,
        })
      );

      expect(result.current.value).toBe(42420);
    });

    it('initializes with boolean value', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: true,
          settingKey: 'AllowPvP',
          settingType: 'bool',
          onSave,
        })
      );

      expect(result.current.value).toBe(true);
    });
  });

  describe('value changes', () => {
    it('updates value when setValue is called', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'old value' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.setValue('new value');
      });

      expect(result.current.value).toBe('new value');
    });

    it('marks as dirty when value differs from initial', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      expect(result.current.isDirty).toBe(false);

      act(() => {
        result.current.setValue('changed');
      });

      expect(result.current.isDirty).toBe(true);
    });

    it('clears error when setValue is called', () => {
      const onSave = vi.fn().mockRejectedValue(new Error('Save failed'));

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          validate: validators.required(),
          onSave,
        })
      );

      // Trigger validation error
      act(() => {
        result.current.setValue('');
      });

      act(() => {
        result.current.save();
      });

      // Now type something - error should clear
      act(() => {
        result.current.setValue('new value');
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('validation', () => {
    it('validates on save and shows error', async () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: '',
          settingKey: 'ServerName',
          settingType: 'string',
          validate: validators.required('Server name is required'),
          onSave,
        })
      );

      await act(async () => {
        await result.current.save();
      });

      expect(result.current.error).toBe('Server name is required');
      expect(onSave).not.toHaveBeenCalled();
    });

    it('clears error and saves when valid', async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'valid name',
          settingKey: 'ServerName',
          settingType: 'string',
          validate: validators.required(),
          onSave,
        })
      );

      await act(async () => {
        await result.current.save();
      });

      expect(result.current.error).toBeNull();
      expect(onSave).toHaveBeenCalledWith({
        key: 'ServerName',
        value: 'valid name',
      });
    });
  });

  describe('saving', () => {
    it('sets isPending during save', async () => {
      let resolvePromise: () => void;
      const savePromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      const onSave = vi.fn().mockReturnValue(savePromise);

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      expect(result.current.isPending).toBe(false);

      // Start save
      act(() => {
        result.current.save();
      });

      expect(result.current.isPending).toBe(true);

      // Complete save
      await act(async () => {
        resolvePromise!();
        await savePromise;
      });

      expect(result.current.isPending).toBe(false);
    });

    it('captures error message on save failure', async () => {
      const onSave = vi.fn().mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      await act(async () => {
        await result.current.save();
      });

      expect(result.current.error).toBe('Network error');
    });

    it('does not save when disabled', async () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
          disabled: true,
        })
      );

      await act(async () => {
        await result.current.save();
      });

      expect(onSave).not.toHaveBeenCalled();
    });

    it('uses valueOverride when provided to save', async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: false,
          settingKey: 'AllowPvP',
          settingType: 'bool',
          onSave,
        })
      );

      // Save with override value (useful for boolean toggles)
      await act(async () => {
        await result.current.save(true);
      });

      expect(onSave).toHaveBeenCalledWith({
        key: 'AllowPvP',
        value: true,
      });
    });

    it('handles non-Error objects in catch block', async () => {
      const onSave = vi.fn().mockRejectedValue('String error');

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      await act(async () => {
        await result.current.save();
      });

      expect(result.current.error).toBe('Failed to save setting');
    });
  });

  describe('onBlur', () => {
    it('saves on blur when dirty', async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      await act(async () => {
        result.current.onBlur();
      });

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({
          key: 'ServerName',
          value: 'changed',
        });
      });
    });

    it('does not save on blur when not dirty', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.onBlur();
      });

      expect(onSave).not.toHaveBeenCalled();
    });

    it('does not save on blur when disabled', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
          disabled: true,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      act(() => {
        result.current.onBlur();
      });

      expect(onSave).not.toHaveBeenCalled();
    });
  });

  describe('onKeyDown', () => {
    it('saves on Enter key when dirty', async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      const enterEvent = {
        key: 'Enter',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      await act(async () => {
        result.current.onKeyDown(enterEvent);
      });

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({
          key: 'ServerName',
          value: 'changed',
        });
      });
      expect(enterEvent.preventDefault).toHaveBeenCalled();
    });

    it('does not save on Enter when not dirty', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'value',
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      const enterEvent = {
        key: 'Enter',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(enterEvent);
      });

      expect(onSave).not.toHaveBeenCalled();
      expect(enterEvent.preventDefault).not.toHaveBeenCalled();
    });

    it('does not save on Enter when disabled', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
          disabled: true,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      const enterEvent = {
        key: 'Enter',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(enterEvent);
      });

      expect(onSave).not.toHaveBeenCalled();
      expect(enterEvent.preventDefault).not.toHaveBeenCalled();
    });

    it('does not trigger save on other keys', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      const escapeEvent = {
        key: 'Escape',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(escapeEvent);
      });

      expect(onSave).not.toHaveBeenCalled();
      expect(escapeEvent.preventDefault).not.toHaveBeenCalled();
    });

    it('shows validation error on Enter when value is invalid', async () => {
      const onSave = vi.fn().mockResolvedValue({});

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          validate: validators.required('Server name is required'),
          onSave,
        })
      );

      // Set to empty string (invalid)
      act(() => {
        result.current.setValue('');
      });

      const enterEvent = {
        key: 'Enter',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      await act(async () => {
        result.current.onKeyDown(enterEvent);
      });

      // Should show validation error, not call onSave
      expect(result.current.error).toBe('Server name is required');
      expect(onSave).not.toHaveBeenCalled();
      // preventDefault is still called because Enter was pressed while dirty
      expect(enterEvent.preventDefault).toHaveBeenCalled();
    });
  });

  describe('reset', () => {
    it('resets value to initial', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: 'original' as string,
          settingKey: 'ServerName',
          settingType: 'string',
          onSave,
        })
      );

      act(() => {
        result.current.setValue('changed');
      });

      expect(result.current.value).toBe('changed');
      expect(result.current.isDirty).toBe(true);

      act(() => {
        result.current.reset();
      });

      expect(result.current.value).toBe('original');
      expect(result.current.isDirty).toBe(false);
    });

    it('clears error on reset', () => {
      const onSave = vi.fn();

      const { result } = renderHook(() =>
        useSettingField({
          initialValue: '',
          settingKey: 'ServerName',
          settingType: 'string',
          validate: validators.required('Required'),
          onSave,
        })
      );

      // Trigger validation error
      act(() => {
        result.current.save();
      });

      expect(result.current.error).toBe('Required');

      act(() => {
        result.current.reset();
      });

      expect(result.current.error).toBeNull();
    });
  });
});

describe('validators', () => {
  describe('required', () => {
    it('returns error for empty string', () => {
      const validate = validators.required();
      expect(validate('')).toBe('This field is required');
    });

    it('returns error for whitespace-only string', () => {
      const validate = validators.required();
      expect(validate('   ')).toBe('This field is required');
    });

    it('returns null for non-empty string', () => {
      const validate = validators.required();
      expect(validate('value')).toBeNull();
    });

    it('uses custom error message', () => {
      const validate = validators.required('Custom message');
      expect(validate('')).toBe('Custom message');
    });
  });

  describe('range', () => {
    it('returns error for value below min', () => {
      const validate = validators.range(1, 100);
      expect(validate(0)).toBe('Value must be between 1 and 100');
    });

    it('returns error for value above max', () => {
      const validate = validators.range(1, 100);
      expect(validate(101)).toBe('Value must be between 1 and 100');
    });

    it('returns null for value within range', () => {
      const validate = validators.range(1, 100);
      expect(validate(50)).toBeNull();
    });

    it('uses custom error message', () => {
      const validate = validators.range(1, 100, 'Out of range');
      expect(validate(0)).toBe('Out of range');
    });
  });

  describe('positiveInt', () => {
    it('returns error for negative number', () => {
      const validate = validators.positiveInt();
      expect(validate(-1)).toBe('Must be a positive integer');
    });

    it('returns error for float', () => {
      const validate = validators.positiveInt();
      expect(validate(1.5)).toBe('Must be a positive integer');
    });

    it('returns null for zero', () => {
      const validate = validators.positiveInt();
      expect(validate(0)).toBeNull();
    });

    it('returns null for positive integer', () => {
      const validate = validators.positiveInt();
      expect(validate(42)).toBeNull();
    });
  });

  describe('port', () => {
    it('returns error for port below 1', () => {
      const validate = validators.port();
      expect(validate(0)).toBe('Port must be between 1 and 65535');
    });

    it('returns error for port above 65535', () => {
      const validate = validators.port();
      expect(validate(65536)).toBe('Port must be between 1 and 65535');
    });

    it('returns null for valid port', () => {
      const validate = validators.port();
      expect(validate(42420)).toBeNull();
    });
  });

  describe('compose', () => {
    it('returns first error from composed validators', () => {
      const validate = validators.compose(
        validators.positiveInt(),
        validators.range(1, 100)
      );
      expect(validate(-1)).toBe('Must be a positive integer');
    });

    it('checks all validators and returns first error', () => {
      const validate = validators.compose(
        validators.positiveInt(),
        validators.range(1, 100)
      );
      expect(validate(200)).toBe('Value must be between 1 and 100');
    });

    it('returns null when all validators pass', () => {
      const validate = validators.compose(
        validators.positiveInt(),
        validators.range(1, 100)
      );
      expect(validate(50)).toBeNull();
    });
  });

  describe('duration', () => {
    it('returns error for non-string value', () => {
      const validate = validators.duration();
      expect(validate(123)).toBe('Duration must be a string');
    });

    it('returns error for invalid duration format', () => {
      const validate = validators.duration();
      const result = validate('invalid');
      // parseDuration treats 'invalid' as having an unknown unit
      expect(result).toBe('Invalid duration format: unexpected "invalid"');
    });

    it('returns specific error from parseDuration for unknown unit', () => {
      const validate = validators.duration();
      expect(validate('5xyz')).toBe('Unknown unit "xyz". Use s, m, h, or d');
    });

    it('returns specific error for duration with unexpected characters', () => {
      const validate = validators.duration();
      expect(validate('4h!!!30m')).toBe('Invalid duration format: unexpected "!!!"');
    });

    it('returns error for empty duration string', () => {
      const validate = validators.duration();
      expect(validate('')).toBe('Duration cannot be empty');
    });

    it('returns null for valid duration string', () => {
      const validate = validators.duration();
      expect(validate('4h')).toBeNull();
      expect(validate('30m')).toBeNull();
      expect(validate('1d')).toBeNull();
    });

    it('returns error when duration is below minimum', () => {
      const validate = validators.duration({ min: 3600 }); // 1 hour minimum
      expect(validate('30m')).toBe('Duration must be at least 3600 seconds');
    });

    it('uses custom minMessage when provided', () => {
      const validate = validators.duration({
        min: 3600,
        minMessage: 'Must be at least 1 hour',
      });
      expect(validate('30m')).toBe('Must be at least 1 hour');
    });

    it('returns error when duration is above maximum', () => {
      const validate = validators.duration({ max: 3600 }); // 1 hour maximum
      expect(validate('2h')).toBe('Duration must be at most 3600 seconds');
    });

    it('uses custom maxMessage when provided', () => {
      const validate = validators.duration({
        max: 3600,
        maxMessage: 'Must be at most 1 hour',
      });
      expect(validate('2h')).toBe('Must be at most 1 hour');
    });

    it('returns null when duration is within min and max range', () => {
      const validate = validators.duration({ min: 1800, max: 7200 });
      expect(validate('1h')).toBeNull(); // 3600 seconds
    });

    it('accepts duration at exact minimum', () => {
      const validate = validators.duration({ min: 3600 });
      expect(validate('1h')).toBeNull();
    });

    it('accepts duration at exact maximum', () => {
      const validate = validators.duration({ max: 3600 });
      expect(validate('1h')).toBeNull();
    });

    it('validates compound durations', () => {
      const validate = validators.duration({ min: 3600, max: 10800 });
      expect(validate('1h30m')).toBeNull(); // 5400 seconds
    });

    it('uses fallback error message when parseDuration returns no error', () => {
      // Mock parseDuration to return failure without error property
      const parseDurationSpy = vi.spyOn(durationUtils, 'parseDuration');
      parseDurationSpy.mockReturnValueOnce({
        success: false,
        seconds: 0,
        // Intentionally omit error property to test fallback
      } as any);

      const validate = validators.duration();
      expect(validate('test')).toBe('Invalid duration format');

      parseDurationSpy.mockRestore();
    });
  });
});

describe('coerceSettingValue', () => {
  it('coerces string to int', () => {
    expect(coerceSettingValue('42', 'int')).toBe(42);
  });

  it('returns 0 for invalid int', () => {
    expect(coerceSettingValue('abc', 'int')).toBe(0);
  });

  it('coerces string to float', () => {
    expect(coerceSettingValue('3.14', 'float')).toBe(3.14);
  });

  it('returns 0 for invalid float', () => {
    expect(coerceSettingValue('abc', 'float')).toBe(0);
  });

  it('coerces "true" to boolean true', () => {
    expect(coerceSettingValue('true', 'bool')).toBe(true);
  });

  it('coerces "1" to boolean true', () => {
    expect(coerceSettingValue('1', 'bool')).toBe(true);
  });

  it('coerces other strings to boolean false', () => {
    expect(coerceSettingValue('false', 'bool')).toBe(false);
    expect(coerceSettingValue('0', 'bool')).toBe(false);
    expect(coerceSettingValue('anything', 'bool')).toBe(false);
  });

  it('returns string as-is for string type', () => {
    expect(coerceSettingValue('hello', 'string')).toBe('hello');
  });
});
