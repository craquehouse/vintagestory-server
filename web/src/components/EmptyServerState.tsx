/**
 * Empty Server State Component
 *
 * Shared empty state shown when the server is not installed or installing.
 * Used across Console, Settings, and Mods pages to provide consistent UX.
 */

import { Link } from 'react-router';
import { ServerOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyServerStateProps {
  /** Whether the server is currently installing */
  isInstalling: boolean;
  /** Context-specific message for not installed state */
  notInstalledMessage: string;
  /** Context-specific message for installing state */
  installingMessage: string;
  /** Optional data-testid for the container */
  testId?: string;
}

/**
 * Empty state component for pages that require an installed server.
 *
 * Shows either:
 * - Installation in progress with spinner and link to view progress
 * - Server not installed with link to installation page
 */
export function EmptyServerState({
  isInstalling,
  notInstalledMessage,
  installingMessage,
  testId,
}: EmptyServerStateProps): React.ReactElement {
  if (isInstalling) {
    return (
      <div
        className="flex flex-col items-center justify-center h-64 text-center"
        data-testid={testId}
      >
        <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
        <p className="text-lg font-medium">Installation in Progress</p>
        <p className="text-muted-foreground mb-4">{installingMessage}</p>
        <Link to="/game-server/version">
          <Button variant="outline">View Installation Progress</Button>
        </Link>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col items-center justify-center h-64 text-center"
      data-testid={testId}
    >
      <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
      <p className="text-lg font-medium">Server Not Installed</p>
      <p className="text-muted-foreground mb-4">{notInstalledMessage}</p>
      <Link to="/game-server/version">
        <Button variant="default">Go to Installation</Button>
      </Link>
    </div>
  );
}
