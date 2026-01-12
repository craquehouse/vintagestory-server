/**
 * Console Page Component
 *
 * Story 11.5: Console Page Extraction
 *
 * Displays the game server console in a full-height layout with:
 * - Page header with title and server status badge
 * - Empty state when server is not installed
 * - ConsolePanel with maximum vertical space for terminal output
 */

import { Link } from 'react-router';
import { ServerOff, Loader2 } from 'lucide-react';
import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { Button } from '@/components/ui/button';
import { useServerStatus } from '@/hooks/use-server-status';
import { ConsolePanel } from '@/components/ConsolePanel';
import type { ServerState } from '@/api/types';

/**
 * Determines if the server is in an "installed" state (has a version installed).
 */
function isServerInstalled(state: ServerState): boolean {
  return state !== 'not_installed' && state !== 'installing';
}

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

  return (
    <div
      className="p-4 lg:p-6 h-full flex flex-col"
      data-testid="console-page"
      aria-label="Server Console"
    >
      {/* Page Header with title and status badge */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">Server Console</h1>
        {isInstalled && (
          <ServerStatusBadge state={serverState} />
        )}
      </div>

      {/* Content area */}
      {isInstalled ? (
        <ConsolePanel className="flex-1 min-h-0" />
      ) : (
        <EmptyServerState isInstalling={isInstalling} />
      )}
    </div>
  );
}

interface EmptyServerStateProps {
  isInstalling: boolean;
}

/**
 * Empty state shown when server is not installed.
 *
 * Displays a message and link to the Installation page.
 */
function EmptyServerState({ isInstalling }: EmptyServerStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center h-64 text-center"
      data-testid="console-page-empty"
    >
      {isInstalling ? (
        <>
          <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
          <p className="text-lg font-medium">Installation in Progress</p>
          <p className="text-muted-foreground mb-4">
            Console will be available once installation completes.
          </p>
          <Link to="/game-server/version">
            <Button variant="outline">View Installation Progress</Button>
          </Link>
        </>
      ) : (
        <>
          <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Server Not Installed</p>
          <p className="text-muted-foreground mb-4">
            Install a VintageStory server to access the console.
          </p>
          <Link to="/game-server/version">
            <Button variant="default">Go to Installation</Button>
          </Link>
        </>
      )}
    </div>
  );
}
