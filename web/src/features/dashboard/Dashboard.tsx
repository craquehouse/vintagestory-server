/**
 * Dashboard page showing server status and metrics.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Displays stat cards in a responsive grid layout:
 * - Server Status with controls (AC: 3)
 * - Memory Usage with API/Game breakdown (AC: 2, 4)
 * - Disk Space
 * - Uptime
 *
 * Layout (responsive breakpoints):
 * - Mobile (<sm): Single column, stacked (AC: 5)
 * - Tablet/small laptop (sm-lg): 2-column grid
 * - Desktop (lg+): 2-column grid (AC: 5)
 */

import { AlertCircle } from 'lucide-react';
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { DiskSpaceWarningBanner } from '@/components/DiskSpaceWarningBanner';
import { EmptyServerState } from '@/components/EmptyServerState';
import { StatCardErrorBoundary } from '@/components/StatCardErrorBoundary';
import { useServerStatus, useServerStateToasts } from '@/hooks/use-server-status';
import { isServerInstalled } from '@/lib/server-utils';
import { ServerStatusCard } from './ServerStatusCard';
import { MemoryCard } from './MemoryCard';
import { DiskSpaceCard } from './DiskSpaceCard';
import { UptimeCard } from './UptimeCard';

/**
 * Dashboard component displaying server metrics in a card grid.
 *
 * Shows:
 * - Empty state when server not installed
 * - Stat cards grid when server is installed
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
  const isRunning = state === 'running';

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

  // Server is installed - show stat cards grid
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Disk space warning banner - shown when space is low */}
      <DiskSpaceWarningBanner diskSpace={serverStatus?.diskSpace} />

      {/* Stat cards grid: responsive layout (AC: 1, 5)
          - Mobile (<640px): 1 column
          - Tablet/sm laptop (640px+): 2 columns */}
      <div className="grid gap-4 sm:grid-cols-2" data-testid="dashboard-stats-grid">
        {/* Server Status with controls (AC: 3) */}
        <StatCardErrorBoundary title="Server Status" testId="server-status-card">
          <ServerStatusCard
            state={state}
            version={serverStatus?.version}
          />
        </StatCardErrorBoundary>

        {/* Memory Usage with API/Game breakdown (AC: 2, 4) */}
        <StatCardErrorBoundary title="Memory Usage" testId="memory-card">
          <MemoryCard />
        </StatCardErrorBoundary>

        {/* Disk Space */}
        <StatCardErrorBoundary title="Disk Space" testId="disk-card">
          <DiskSpaceCard diskSpace={serverStatus?.diskSpace} />
        </StatCardErrorBoundary>

        {/* Uptime */}
        <StatCardErrorBoundary title="Uptime" testId="uptime-card">
          <UptimeCard
            uptimeSeconds={serverStatus?.uptimeSeconds}
            isRunning={isRunning}
          />
        </StatCardErrorBoundary>
      </div>
    </div>
  );
}
