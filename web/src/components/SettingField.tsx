/**
 * SettingField component for displaying and editing individual settings.
 *
 * Supports text, number, and boolean input variants.
 * Shows env_managed badge and disabled state when applicable.
 * Includes loading spinner during save and error display.
 *
 * Story 6.4: Settings UI
 * Story 16.8: a setting with no value (null) is an empty field; `masked` hides the
 * value (password) behind a show/hide toggle.
 * Story 17.6: a boolean with no value shows the game's default ("Enabled (default)")
 * when it is known, otherwise "Not set", never a plain "Disabled".
 */

import { useState } from 'react';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SettingType } from '@/api/types';
import { useSettingField, type Validator, coerceSettingValue } from '@/hooks/use-setting-field';

/**
 * Props for the SettingField component.
 */
export interface SettingFieldProps {
  /**
   * Setting key for display and API updates.
   */
  settingKey: string;

  /**
   * Display label for the setting.
   */
  label: string;

  /**
   * Current value of the setting; null when the setting has no value.
   */
  value: string | number | boolean | null;

  /**
   * Type of the setting (string, int, bool, float).
   */
  type: SettingType;

  /**
   * Optional validation function.
   */
  validate?: Validator<string | number | boolean>;

  /**
   * Whether the setting is managed by environment variable.
   */
  envManaged?: boolean;

  /**
   * Read-only for this key, e.g. a Monitor key (Story 23.3). Unlike envManaged, no badge.
   */
  disabled?: boolean;

  /**
   * The id of an element that says why the field is disabled, added to the control's
   * aria-describedby while disabled (Story 23.3 review: the Game Settings read-only note).
   */
  disabledReasonId?: string;

  /**
   * Environment variable name (shown in badge).
   */
  envVar?: string;

  /**
   * Optional description/help text.
   */
  description?: string;

  /**
   * Mutation function to save the value.
   */
  onSave: (params: { key: string; value: string | number | boolean }) => Promise<unknown>;

  /**
   * Mask the value (a password), with a button to show and hide it.
   */
  masked?: boolean;

  /**
   * The game's value for a setting with no value (Story 17.6). Used only for
   * `type === 'bool'` with `value === null`; absent when the default is unknown.
   */
  gameDefault?: boolean;

  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Renders a setting field with appropriate input type.
 *
 * @example
 * <SettingField
 *   settingKey="ServerName"
 *   label="Server Name"
 *   value="My Server"
 *   type="string"
 *   validate={validators.required()}
 *   onSave={updateGameSetting}
 * />
 */
export function SettingField({
  settingKey,
  label,
  value,
  type,
  validate,
  envManaged = false,
  disabled = false,
  disabledReasonId,
  envVar,
  description,
  onSave,
  masked = false,
  gameDefault,
  className,
}: SettingFieldProps) {
  // Coerce value to appropriate type and use as initial.
  // Story 16.8: no value (null) is an empty field, so it never shows or saves "null".
  // Story 17.6: a boolean with no value starts at the game's default when it is known.
  const initialValue =
    type === 'bool' ? (value === null ? (gameDefault ?? false) : Boolean(value)) : (value ?? '');
  const [isRevealed, setIsRevealed] = useState(false);

  // Use the setting field hook for state management
  const field = useSettingField({
    initialValue: initialValue as string | number | boolean,
    settingKey,
    settingType: type,
    validate,
    onSave,
    disabled: envManaged || disabled,
    // Story 17.6 review: a switch that failed to save goes back to the stored state
    // (for a setting with no value, the default or "Not set"); typed text is kept
    revertOnError: type === 'bool',
  });

  const isDisabled = envManaged || disabled || field.isPending;
  const isNumber = type === 'int' || type === 'float';

  // Story 17.6: a boolean with no value whose switch has not been moved from the
  // position it started in. Once switched, the label is the plain switch state (the
  // optimistic cache write then gives the setting its value); a failed save puts the
  // switch back (revertOnError), so the label returns to the default or "Not set".
  const isUnset = type === 'bool' && value === null && field.value === initialValue;
  const boolStateLabel = !isUnset
    ? Boolean(field.value)
      ? 'Enabled'
      : 'Disabled'
    : gameDefault === undefined
      ? 'Not set'
      : `${gameDefault ? 'Enabled' : 'Disabled'} (default)`;

  // Story 23.3 review: a disabled control also names the note that says why
  const withReason = (ids: string | undefined) =>
    [ids, disabled ? disabledReasonId : undefined].filter(Boolean).join(' ') || undefined;

  // Props shared by the plain and masked text inputs, so the two cannot drift apart
  const sharedInputProps = {
    id: settingKey,
    value: String(field.value),
    onBlur: field.onBlur,
    onKeyDown: field.onKeyDown,
    disabled: isDisabled,
    'aria-describedby': withReason(
      field.error ? `${settingKey}-error` : description ? `${settingKey}-desc` : undefined
    ),
    'aria-invalid': !!field.error,
  };
  const errorInputClass = field.error && 'border-destructive focus-visible:ring-destructive';

  return (
    <div className={cn('space-y-1', className)}>
      {/* Label and badges row */}
      <div className="flex items-center gap-2">
        <label htmlFor={settingKey} className="text-sm font-medium text-foreground">
          {label}
        </label>

        {/* Env managed badge */}
        {envManaged && (
          <Badge variant="outline" className="text-xs bg-warning/10 text-warning border-warning/30">
            Env: {envVar || `VS_CFG_${settingKey.toUpperCase()}`}
          </Badge>
        )}

        {/* Loading indicator */}
        {field.isPending && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
      </div>

      {/* Input field based on type */}
      {type === 'bool' ? (
        <div className="flex items-center gap-2">
          <Switch
            id={settingKey}
            checked={Boolean(field.value)}
            onCheckedChange={(checked) => {
              field.setValue(checked);
              // For boolean, save immediately on change (no blur needed)
              // Use save() with value override for proper validation/error handling
              field.save(checked);
            }}
            disabled={isDisabled}
            // Story 17.6 review: the state ("Enabled (default)", "Not set") is announced
            // with the switch, before the description
            aria-describedby={withReason(
              description ? `${settingKey}-state ${settingKey}-desc` : `${settingKey}-state`
            )}
          />
          <span
            id={`${settingKey}-state`}
            className="text-sm text-muted-foreground"
            data-testid={`setting-state-${settingKey}`}
          >
            {boolStateLabel}
          </span>
        </div>
      ) : masked ? (
        <div className="relative">
          <Input
            {...sharedInputProps}
            type={isRevealed ? 'text' : 'password'}
            // Keep browsers from filling a saved login in, which would then be saved on blur
            autoComplete="new-password"
            onChange={(e) => field.setValue(e.target.value)}
            className={cn('pr-9', errorInputClass)}
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0"
            onClick={() => setIsRevealed((revealed) => !revealed)}
            disabled={isDisabled}
            aria-label={isRevealed ? 'Hide password' : 'Show password'}
            aria-pressed={isRevealed}
            aria-controls={settingKey}
          >
            {isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
        </div>
      ) : (
        <Input
          {...sharedInputProps}
          type={isNumber ? 'number' : 'text'}
          onChange={(e) => {
            const newValue = isNumber ? coerceSettingValue(e.target.value, type) : e.target.value;
            field.setValue(newValue as string | number);
          }}
          className={cn(
            // Numbers (ports, counts) keep a narrow box at every width (Epic 16 ADR-3)
            isNumber && 'max-w-xs',
            errorInputClass
          )}
        />
      )}

      {/* Description text */}
      {description && !field.error && (
        <p id={`${settingKey}-desc`} className="text-xs text-muted-foreground">
          {description}
        </p>
      )}

      {/* Error message */}
      {field.error && (
        <p id={`${settingKey}-error`} className="text-xs text-destructive" role="alert">
          {field.error}
        </p>
      )}
    </div>
  );
}
