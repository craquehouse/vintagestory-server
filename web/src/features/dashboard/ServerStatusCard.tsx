/**
 * ServerStatusCard component for displaying server state and controls.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Shows server status badge with Start/Stop/Restart controls (AC: 3).
 * Integrates with existing ServerControls component.
 */

import { Server } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { ServerControls } from './ServerControls';
import type { ServerState } from '@/api/types';

export interface ServerStatusCardProps {
  /** Current server state */
  state: ServerState;
  /** Server version (if installed) */
  version?: string | null;
  /** Whether the data is loading */
  isLoading?: boolean;
}

/**
 * ServerStatusCard displays server status and controls.
 *
 * Uses existing ServerStatusBadge and ServerControls components.
 * Provides Start/Stop/Restart buttons (AC: 3).
 */
export function ServerStatusCard({ state, version, isLoading }: ServerStatusCardProps) {
  // Loading state
  if (isLoading) {
    return (
      <Card className="min-h-[140px]" data-testid="server-status-card">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <Server className="size-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle className="text-base font-medium">Server Status</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="min-h-[140px]" data-testid="server-status-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Server className="size-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle className="text-base font-medium">Server Status</CardTitle>
          </div>
          <ServerStatusBadge state={state} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {version && (
          <div className="text-sm text-muted-foreground" data-testid="server-status-card-version">
            Version {version}
          </div>
        )}
        <div data-testid="server-status-card-controls">
          <ServerControls serverState={state} />
        </div>
      </CardContent>
    </Card>
  );
}
