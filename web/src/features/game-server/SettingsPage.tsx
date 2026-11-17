/**
 * Settings Page Component
 *
 * Story 11.3: Settings Page Extraction
 *
 * Displays game server settings in a full-width layout with:
 * - Page header with title and server status badge
 * - Empty state when server is not installed
 * - GameConfigPanel for configured servers
 *
 * Story 17.8 (FR193): the title row and the panel share one centered 1280px width
 * (Epic 16 ADR-3), in the loading and error states too, so the title starts at the
 * panel's left edge, the status badge ends at its right edge, and the title does not
 * move when the status arrives.
 */

import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { EmptyServerState } from '@/components/EmptyServerState';
import { useServerStatus } from '@/hooks/use-server-status';
import { GameConfigPanel } from './GameConfigPanel';
import { isServerInstalled } from '@/lib/server-utils';
import { SETTINGS_CONTENT_WIDTH } from './content-width';

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
      <div className="p-4 lg:p-6 h-full overflow-auto" data-testid="settings-page-loading">
        <div className={SETTINGS_CONTENT_WIDTH} data-testid="settings-page-content">
          <h1 className="text-2xl font-bold">Game Settings</h1>
          <p className="text-muted-foreground mt-4">Loading server status...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 lg:p-6 h-full overflow-auto" data-testid="settings-page-error">
        <div className={SETTINGS_CONTENT_WIDTH} data-testid="settings-page-content">
          <h1 className="text-2xl font-bold">Game Settings</h1>
          <p className="text-destructive mt-4">Error: {error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-4 lg:p-6 h-full overflow-auto"
      data-testid="settings-page"
      aria-label="Game Settings"
    >
      <div className={SETTINGS_CONTENT_WIDTH} data-testid="settings-page-content">
        {/* Page Header with title and status badge */}
        <div className="flex items-center justify-between mb-6" data-testid="settings-page-header">
          <h1 className="text-2xl font-bold">Game Settings</h1>
          {isInstalled && <ServerStatusBadge state={serverState} />}
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
    </div>
  );
}
