/**
 * GameConfigPanel component for managing game server settings.
 *
 * Displays game settings organized into groups with validation.
 * Handles loading, error states, and auto-save on blur.
 *
 * Story 6.4: Settings UI
 */

import { AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { SettingField } from '@/components/SettingField';
import { SettingGroup } from '@/components/SettingGroup';
import { Skeleton } from '@/components/ui/skeleton';
import { useGameConfig, useUpdateGameSetting } from '@/hooks/use-game-config';
import { validators } from '@/hooks/use-setting-field';
import type { GameSetting, SettingType } from '@/api/types';

/**
 * Setting definition with display metadata.
 */
interface SettingDefinition {
  key: string;
  label: string;
  description?: string;
  validate?: ReturnType<typeof validators.compose>;
}

/**
 * Server Info settings - basic server identification.
 */
const SERVER_INFO_SETTINGS: SettingDefinition[] = [
  {
    key: 'ServerName',
    label: 'Server Name',
    description: 'The name shown in the server browser',
    validate: validators.required('Server name is required'),
  },
  {
    key: 'ServerDescription',
    label: 'Description',
    description: 'A brief description of your server',
  },
  {
    key: 'WelcomeMessage',
    label: 'Welcome Message',
    description: 'Message shown when players join (MOTD)',
  },
  {
    key: 'Password',
    label: 'Password',
    description: 'Leave empty for no password protection',
  },
];

/**
 * Player settings - player-related configuration.
 */
const PLAYER_SETTINGS: SettingDefinition[] = [
  {
    key: 'MaxClients',
    label: 'Max Players',
    description: 'Maximum number of simultaneous players',
    validate: validators.compose(
      validators.positiveInt('Must be a positive integer'),
      validators.range(1, 128, 'Must be between 1 and 128')
    ),
  },
  {
    key: 'AllowPvP',
    label: 'Allow PvP',
    description: 'Allow players to attack each other',
  },
];

/**
 * World settings - gameplay mechanics.
 */
const WORLD_SETTINGS: SettingDefinition[] = [
  {
    key: 'MaxChunkRadius',
    label: 'Max Chunk Radius',
    description: 'Maximum view distance (affects performance)',
    validate: validators.compose(
      validators.positiveInt('Must be a positive integer'),
      validators.range(1, 32, 'Must be between 1 and 32')
    ),
  },
  {
    key: 'AllowFireSpread',
    label: 'Allow Fire Spread',
    description: 'Whether fire can spread to nearby blocks',
  },
  {
    key: 'AllowFallingBlocks',
    label: 'Allow Falling Blocks',
    description: 'Whether blocks can fall (gravel, sand, etc.)',
  },
  {
    key: 'EntitySpawning',
    label: 'Entity Spawning',
    description: 'Whether creatures can spawn naturally',
  },
  {
    key: 'PassTimeWhenEmpty',
    label: 'Pass Time When Empty',
    description: 'Continue time progression when no players online',
  },
];

/**
 * Network settings - connection and visibility.
 */
const NETWORK_SETTINGS: SettingDefinition[] = [
  {
    key: 'Port',
    label: 'Port',
    description: 'Server port (requires restart)',
    validate: validators.port('Port must be between 1 and 65535'),
  },
  {
    key: 'Ip',
    label: 'IP Address',
    description: 'IP to bind to (requires restart)',
  },
  {
    key: 'AdvertiseServer',
    label: 'Advertise Server',
    description: 'Show server in public server list',
  },
  {
    key: 'Upnp',
    label: 'UPnP',
    description: 'Enable automatic port forwarding',
  },
];

/**
 * Props for the GameConfigPanel component.
 */
export interface GameConfigPanelProps {
  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Panel for managing game server settings.
 *
 * Fetches settings from API, organizes them into groups,
 * and provides auto-save on blur with validation.
 */
export function GameConfigPanel({ className }: GameConfigPanelProps) {
  const { data, isLoading, error } = useGameConfig();
  const updateMutation = useUpdateGameSetting();

  // Handle save with toast notification
  const handleSave = async (params: { key: string; value: string | number | boolean }) => {
    try {
      const result = await updateMutation.mutateAsync(params);
      // Show success toast
      toast.success(`${params.key} updated`, {
        description: result.data.method === 'console_command'
          ? 'Applied via console command'
          : 'Saved to config file',
      });
      return result;
    } catch (err) {
      // Show error toast
      const message = err instanceof Error ? err.message : 'Failed to update setting';
      toast.error('Update failed', { description: message });
      throw err;
    }
  };

  // Loading state with skeletons
  if (isLoading) {
    return (
      <div className={className} data-testid="game-config-loading">
        <div className="space-y-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className} data-testid="game-config-error">
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <div>
            <p className="font-medium text-destructive">Failed to load settings</p>
            <p className="text-sm text-muted-foreground">
              {error.message || 'Unable to load game configuration'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Get setting value from API response
  const getSetting = (key: string): GameSetting | undefined => {
    return data?.data?.settings.find((s) => s.key === key);
  };

  // Render a setting field
  const renderSetting = (def: SettingDefinition) => {
    const setting = getSetting(def.key);

    // Skip if setting not available from API
    if (!setting) {
      return null;
    }

    return (
      <SettingField
        key={def.key}
        settingKey={def.key}
        label={def.label}
        value={setting.value}
        type={setting.type as SettingType}
        validate={def.validate}
        envManaged={setting.envManaged}
        description={def.description}
        onSave={handleSave}
      />
    );
  };

  // Render a setting group with available settings
  const renderGroup = (
    title: string,
    description: string,
    definitions: SettingDefinition[],
    collapsible = false
  ) => {
    // Filter to only include settings that exist in API response
    const availableSettings = definitions.filter((def) => getSetting(def.key));

    // Skip group if no settings available
    if (availableSettings.length === 0) {
      return null;
    }

    return (
      <SettingGroup
        title={title}
        description={description}
        collapsible={collapsible}
      >
        {availableSettings.map(renderSetting)}
      </SettingGroup>
    );
  };

  return (
    <div className={className} data-testid="game-config-panel">
      <div className="space-y-4">
        {renderGroup(
          'Server Info',
          'Basic server identification',
          SERVER_INFO_SETTINGS
        )}
        {renderGroup(
          'Player Settings',
          'Player-related configuration',
          PLAYER_SETTINGS
        )}
        {renderGroup(
          'World Settings',
          'Gameplay mechanics',
          WORLD_SETTINGS,
          true // collapsible
        )}
        {renderGroup(
          'Network',
          'Connection and visibility',
          NETWORK_SETTINGS,
          true // collapsible
        )}
      </div>
    </div>
  );
}
