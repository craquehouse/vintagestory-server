/**
 * Settings Page Component
 *
 * Story 11.3: Settings Page Extraction
 *
 * Displays game server settings in a full-width layout with:
 * - Page header with title and server status badge
 * - Empty state when server is not installed
 * - GameConfigPanel for configured servers
 */

import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { EmptyServerState } from '@/components/EmptyServerState';
import { useServerStatus } from '@/hooks/use-server-status';
import { GameConfigPanel } from './GameConfigPanel';
import { isServerInstalled } from '@/lib/server-utils';

/**
 * Settings page for the Game Server section.
 *
 * Shows server settings when installed, and an empty state
 * with link to installation when no server is present.
 */
export function SettingsPage() {
  const { data: statusResponse, isLoading, error } = useServerStatus();
  const serverStatus = statusResponse?.data;
  const serverState = serverStatus?.state ?? 'not_installed';

  // Determine if server is installed (not in 'not_installed' or 'installing' state)
  const isInstalled = isServerInstalled(serverState);
  const isInstalling = serverState === 'installing';

  // Loading state
  if (isLoading) {
    return (
      <div
        className="p-4 lg:p-6 h-full overflow-auto"
        data-testid="settings-page-loading"
      >
        <h1 className="text-2xl font-bold">Game Settings</h1>
        <p className="text-muted-foreground mt-4">Loading server status...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="p-4 lg:p-6 h-full overflow-auto"
        data-testid="settings-page-error"
      >
        <h1 className="text-2xl font-bold">Game Settings</h1>
        <p className="text-destructive mt-4">Error: {error.message}</p>
      </div>
    );
  }

  return (
    <div
      className="p-4 lg:p-6 h-full overflow-auto"
      data-testid="settings-page"
      aria-label="Game Settings"
    >
      {/* Page Header with title and status badge */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Game Settings</h1>
        {isInstalled && (
          <ServerStatusBadge state={serverState} />
        )}
      </div>

      {/* Content area */}
      {isInstalled ? (
        <GameConfigPanel />
      ) : (
        <EmptyServerState
          isInstalling={isInstalling}
          notInstalledMessage="Install a VintageStory server to configure settings."
          installingMessage="Settings will be available once installation completes."
          testId="settings-page-empty"
        />
      )}
    </div>
  );
}
