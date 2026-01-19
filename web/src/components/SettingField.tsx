/**
 * SettingField component for displaying and editing individual settings.
 *
 * Supports text, number, and boolean input variants.
 * Shows env_managed badge and disabled state when applicable.
 * Includes loading spinner during save and error display.
 *
 * Story 6.4: Settings UI
 */

import { Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SettingType } from '@/api/types';
import {
  useSettingField,
  type Validator,
  coerceSettingValue,
} from '@/hooks/use-setting-field';

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
   * Current value of the setting.
   */
  value: string | number | boolean;

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
  envVar,
  description,
  onSave,
  className,
}: SettingFieldProps) {
  // Coerce value to appropriate type and use as initial
  const initialValue = type === 'bool' ? Boolean(value) : value;

  // Use the setting field hook for state management
  const field = useSettingField({
    initialValue: initialValue as string | number | boolean,
    settingKey,
    settingType: type,
    validate,
    onSave,
    disabled: envManaged,
  });

  const isDisabled = envManaged || field.isPending;

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
        {field.isPending && (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        )}
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
            aria-describedby={description ? `${settingKey}-desc` : undefined}
          />
          <span className="text-sm text-muted-foreground">
            {Boolean(field.value) ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      ) : (
        <Input
          id={settingKey}
          type={type === 'int' || type === 'float' ? 'number' : 'text'}
          value={String(field.value)}
          onChange={(e) => {
            const newValue =
              type === 'int' || type === 'float'
                ? coerceSettingValue(e.target.value, type)
                : e.target.value;
            field.setValue(newValue as string | number);
          }}
          onBlur={field.onBlur}
          onKeyDown={field.onKeyDown}
          disabled={isDisabled}
          aria-describedby={
            field.error ? `${settingKey}-error` : description ? `${settingKey}-desc` : undefined
          }
          aria-invalid={!!field.error}
          className={cn(
            field.error && 'border-destructive focus-visible:ring-destructive'
          )}
        />
      )}

      {/* Description text */}
      {description && !field.error && (
        <p
          id={`${settingKey}-desc`}
          className="text-xs text-muted-foreground"
        >
          {description}
        </p>
      )}

      {/* Error message */}
      {field.error && (
        <p
          id={`${settingKey}-error`}
          className="text-xs text-destructive"
          role="alert"
        >
          {field.error}
        </p>
      )}
    </div>
  );
}
