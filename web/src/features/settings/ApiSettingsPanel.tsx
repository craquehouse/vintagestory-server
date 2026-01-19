/**
 * ApiSettingsPanel component for managing API operational settings.
 *
 * Displays API settings with auto-save on blur.
 * Settings control server auto-start, environment handling, and refresh intervals.
 *
 * Story 6.4: Settings UI - AC6
 * VSS-c9o: Debug logging toggle
 */

import { AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { SettingField } from '@/components/SettingField';
import { SettingGroup } from '@/components/SettingGroup';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useApiSettings, useUpdateApiSetting } from '@/hooks/use-api-settings';
import { useDebugStatus, useToggleDebug } from '@/hooks/use-debug';
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
  const { data: debugData, isLoading: isDebugLoading, error: debugError } = useDebugStatus();
  const toggleDebug = useToggleDebug();

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

  // Handle debug toggle with toast notification
  const handleDebugToggle = async (enabled: boolean) => {
    try {
      const result = await toggleDebug.mutateAsync({ enabled });
      if (result.data?.changed) {
        toast.success(`Debug logging ${enabled ? 'enabled' : 'disabled'}`);
      } else {
        toast.info(`Debug logging was already ${enabled ? 'enabled' : 'disabled'}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to toggle debug logging';
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

        {/* Debug Logging (VSS-c9o) */}
        <SettingGroup
          title="Debug Logging"
          description="Enable verbose logging for troubleshooting"
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <label
                htmlFor="debug_logging"
                className="text-sm font-medium text-foreground"
              >
                Enable
              </label>
              {toggleDebug.isPending && (
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              )}
            </div>
            {debugError ? (
              <p className="text-xs text-destructive">
                Unable to load debug status
              </p>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  {isDebugLoading ? (
                    <Skeleton className="h-5 w-9" />
                  ) : (
                    <Switch
                      id="debug_logging"
                      checked={debugData?.data?.debugEnabled ?? false}
                      onCheckedChange={handleDebugToggle}
                      disabled={toggleDebug.isPending}
                      data-testid="debug-logging-toggle"
                      aria-describedby="debug_logging-desc"
                    />
                  )}
                  <span className="text-sm text-muted-foreground">
                    {debugData?.data?.debugEnabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <p
                  id="debug_logging-desc"
                  className="text-xs text-muted-foreground"
                >
                  Enable DEBUG-level logging at runtime without server restart
                </p>
              </>
            )}
          </div>
        </SettingGroup>
      </div>
    </div>
  );
}
