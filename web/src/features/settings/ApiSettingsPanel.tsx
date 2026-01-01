/**
 * ApiSettingsPanel component for managing API operational settings.
 *
 * Displays API settings with auto-save on blur.
 * Settings control server auto-start, environment handling, and refresh intervals.
 *
 * Story 6.4: Settings UI - AC6
 */

import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { SettingField } from '@/components/SettingField';
import { SettingGroup } from '@/components/SettingGroup';
import { Skeleton } from '@/components/ui/skeleton';
import { useApiSettings, useUpdateApiSetting } from '@/hooks/use-api-settings';
import { validators, type SettingValue } from '@/hooks/use-setting-field';

/**
 * Props for the ApiSettingsPanel component.
 */
export interface ApiSettingsPanelProps {
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Panel for managing API operational settings.
 *
 * Fetches settings from API and provides auto-save on blur.
 */
export function ApiSettingsPanel({ className }: ApiSettingsPanelProps) {
  const { data, isLoading, error } = useApiSettings();
  const updateMutation = useUpdateApiSetting();

  // Handle save with toast notification
  const handleSave = async (params: { key: string; value: SettingValue }) => {
    try {
      const result = await updateMutation.mutateAsync(params);
      toast.success(`${params.key} updated`);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update setting';
      toast.error('Update failed', { description: message });
      throw err;
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={className} data-testid="api-settings-loading">
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className} data-testid="api-settings-error">
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <div>
            <p className="font-medium text-destructive">Failed to load settings</p>
            <p className="text-sm text-muted-foreground">
              {error.message || 'Unable to load API settings'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const settings = data?.data?.settings;

  return (
    <div className={className} data-testid="api-settings-panel">
      <div className="space-y-4">
        {/* Server Behavior Settings */}
        <SettingGroup
          title="Server Behavior"
          description="Control how the API server manages the game server"
        >
          <SettingField
            settingKey="auto_start_server"
            label="Auto-Start Server"
            value={settings?.autoStartServer ?? false}
            type="bool"
            description="Automatically start the game server when the API starts"
            onSave={handleSave}
          />
        </SettingGroup>

        {/* Environment Settings */}
        <SettingGroup
          title="Environment Variables"
          description="Control how VS_CFG_* environment variables are handled"
        >
          <SettingField
            settingKey="block_env_managed_settings"
            label="Block Env-Managed Settings"
            value={settings?.blockEnvManagedSettings ?? true}
            type="bool"
            description="Prevent changes to settings managed by environment variables"
            onSave={handleSave}
          />
          <SettingField
            settingKey="enforce_env_on_restart"
            label="Enforce Env on Restart"
            value={settings?.enforceEnvOnRestart ?? true}
            type="bool"
            description="Re-apply environment variable values when the server restarts"
            onSave={handleSave}
          />
        </SettingGroup>

        {/* Refresh Intervals */}
        <SettingGroup
          title="Refresh Intervals"
          description="Configure how often data is refreshed (in seconds)"
          collapsible
        >
          <SettingField
            settingKey="mod_list_refresh_interval"
            label="Mod List Refresh"
            value={settings?.modListRefreshInterval ?? 300}
            type="int"
            description="How often to refresh the installed mods list"
            validate={validators.compose(
              validators.positiveInt('Must be a positive integer'),
              validators.range(10, 3600, 'Must be between 10 and 3600 seconds')
            )}
            onSave={handleSave}
          />
          <SettingField
            settingKey="server_versions_refresh_interval"
            label="Server Versions Refresh"
            value={settings?.serverVersionsRefreshInterval ?? 3600}
            type="int"
            description="How often to check for new game server versions"
            validate={validators.compose(
              validators.positiveInt('Must be a positive integer'),
              validators.range(60, 86400, 'Must be between 60 and 86400 seconds')
            )}
            onSave={handleSave}
          />
        </SettingGroup>
      </div>
    </div>
  );
}
