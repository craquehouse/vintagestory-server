import { describe, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useSettingField,
  validators,
  coerceSettingValue,
} from './use-setting-field';

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
