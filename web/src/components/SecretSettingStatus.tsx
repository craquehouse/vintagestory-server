/**
 * SecretSettingStatus shows whether a secret setting is set, without its value.
 *
 * Story 17.5 (FR186): a key that is not Admin does not receive a secret setting's
 * value (Password), only whether it is set. This replaces the setting's field for
 * that key: there is no input and no show/hide control, so nothing here can hold
 * or reveal a value.
 */

import { cn } from '@/lib/utils';

export interface SecretSettingStatusProps {
  /** The setting key, used in the test IDs */
  settingKey: string;
  /** Display label */
  label: string;
  /** Whether the secret is set */
  configured: boolean;
  /** Additional CSS class names */
  className?: string;
}

export function SecretSettingStatus({
  settingKey,
  label,
  configured,
  className,
}: SecretSettingStatusProps) {
  return (
    <div className={cn('space-y-1', className)} data-testid={`secret-setting-${settingKey}`}>
      {/* Same label row as SettingField; a span, not a label: there is no control to label */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">{label}</span>
      </div>
      <p className="text-sm" data-testid={`secret-setting-status-${settingKey}`}>
        {configured ? 'Set' : 'Not set'}
      </p>
      <p className="text-xs text-muted-foreground">
        Only an Admin key can see or change this value.
      </p>
    </div>
  );
}
