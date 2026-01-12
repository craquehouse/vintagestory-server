import { Clock, Server as ServerIcon, AlertCircle, HardDrive } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { DiskSpaceWarningBanner } from '@/components/DiskSpaceWarningBanner';
import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { EmptyServerState } from '@/components/EmptyServerState';
import { ServerControls } from './ServerControls';
import { useServerStatus, useServerStateToasts } from '@/hooks/use-server-status';
import { isServerInstalled } from '@/lib/server-utils';

/**
 * Dashboard page showing server status and controls.
 *
 * Story 11.6: Dashboard & Navigation Cleanup
 *
 * Conditionally renders:
 * - Empty state with link to Installation page when server is not installed
 * - Installing state with spinner and link to view progress
 * - Server status card with controls when server is installed
 *
 * Uses TanStack Query with 5-second polling for auto-refresh.
 */
export function Dashboard() {
  const { data: statusResponse, isLoading, error } = useServerStatus();
  const serverStatus = statusResponse?.data;

  // Show toasts when server state transitions complete
  useServerStateToasts(serverStatus?.state);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading server status...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="size-5" />
            Error Loading Status
          </CardTitle>
          <CardDescription>{error.message}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const state = serverStatus?.state ?? 'not_installed';
  const isInstalled = isServerInstalled(state);
  const isInstalling = state === 'installing';

  // Show empty state for not_installed and installing states
  if (!isInstalled) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <EmptyServerState
          isInstalling={isInstalling}
          notInstalledMessage="Install a VintageStory server to get started."
          installingMessage="Visit the Installation page to view progress."
          testId="dashboard-empty"
        />
      </div>
    );
  }

  // Server is installed - show status and controls
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Disk space warning banner - shown when space is low */}
      <DiskSpaceWarningBanner diskSpace={serverStatus?.diskSpace} />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ServerIcon className="size-5 text-muted-foreground" />
              <CardTitle>Server Status</CardTitle>
            </div>
            <ServerStatusBadge state={state} />
          </div>
          {serverStatus?.version && (
            <CardDescription>
              Version {serverStatus.version}
            </CardDescription>
          )}
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Uptime display - only shown when running */}
          {state === 'running' && serverStatus?.uptimeSeconds != null && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="size-4" />
              <span>Uptime: {formatUptime(serverStatus.uptimeSeconds)}</span>
            </div>
          )}

          {/* Disk space display - always shown when available */}
          {serverStatus?.diskSpace && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <HardDrive className="size-4" />
              <span>
                Disk: {serverStatus.diskSpace.availableGb.toFixed(1)} GB free of {serverStatus.diskSpace.totalGb.toFixed(1)} GB ({serverStatus.diskSpace.usagePercent.toFixed(0)}% used)
              </span>
            </div>
          )}

          {/* Last exit code - shown when stopped with an exit code */}
          {state === 'installed' && serverStatus?.lastExitCode != null && (
            <div className="text-sm text-muted-foreground">
              Last exit code: {serverStatus.lastExitCode}
            </div>
          )}

          {/* Server controls */}
          <div className="pt-2">
            <ServerControls serverState={state} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Format uptime seconds into a human-readable string.
 *
 * Examples:
 * - 45 -> "45 seconds"
 * - 125 -> "2 minutes"
 * - 3665 -> "1 hour, 1 minute"
 * - 90061 -> "1 day, 1 hour"
 */
function formatUptime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} second${seconds !== 1 ? 's' : ''}`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) {
    if (remainingMinutes === 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    }
    return `${hours} hour${hours !== 1 ? 's' : ''}, ${remainingMinutes} minute${remainingMinutes !== 1 ? 's' : ''}`;
  }

  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  if (remainingHours === 0) {
    return `${days} day${days !== 1 ? 's' : ''}`;
  }
  return `${days} day${days !== 1 ? 's' : ''}, ${remainingHours} hour${remainingHours !== 1 ? 's' : ''}`;
}
