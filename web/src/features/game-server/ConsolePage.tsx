/**
 * Console Page Component
 *
 * Story 11.5: Console Page Extraction
 *
 * Displays the game server console in a full-height layout with:
 * - Page header with title, server controls (Start/Stop/Restart), and status badge
 * - Empty state when server is not installed
 * - ConsolePanel with maximum vertical space for terminal output
 */

import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { EmptyServerState } from '@/components/EmptyServerState';
import { useServerStatus } from '@/hooks/use-server-status';
import { ConsolePanel } from '@/components/ConsolePanel';
import { ServerControls } from '@/features/dashboard/ServerControls';
import { isServerInstalled } from '@/lib/server-utils';

/**
 * Console page for the Game Server section.
 *
 * Shows the console terminal when installed, and an empty state
 * with link to installation when no server is present.
 */
export function ConsolePage() {
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
        className="p-4 lg:p-6 h-full flex flex-col"
        data-testid="console-page-loading"
      >
        <h1 className="text-2xl font-bold">Server Console</h1>
        <p className="text-muted-foreground mt-4">Loading server status...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="p-4 lg:p-6 h-full flex flex-col"
        data-testid="console-page-error"
      >
        <h1 className="text-2xl font-bold">Server Console</h1>
        <p className="text-destructive mt-4">Error: {error.message}</p>
      </div>
    );
  }

  // Height calculation: viewport - header (48px) - layout padding (32px mobile, 48px desktop)
  // Mobile: 100vh - 80px, Desktop (md+): 100vh - 96px
  return (
    <div
      className="h-[calc(100vh-80px)] md:h-[calc(100vh-96px)] flex flex-col"
      data-testid="console-page"
      aria-label="Server Console"
    >
      {/* Page Header with title, controls, and status badge */}
      <div className="flex items-center justify-between gap-4 mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">Server Console</h1>
        {isInstalled && (
          <div className="flex items-center gap-4">
            <ServerControls serverState={serverState} />
            <ServerStatusBadge state={serverState} />
          </div>
        )}
      </div>

      {/* Content area */}
      {isInstalled ? (
        <ConsolePanel className="flex-1 min-h-0" />
      ) : (
        <EmptyServerState
          isInstalling={isInstalling}
          notInstalledMessage="Install a VintageStory server to access the console."
          installingMessage="Console will be available once installation completes."
          testId="console-page-empty"
        />
      )}
    </div>
  );
}
