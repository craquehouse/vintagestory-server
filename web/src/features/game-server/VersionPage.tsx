/**
 * Version/Installation Page Component
 *
 * Story 11.2: Dedicated page for server version management.
 * Story 13.3: Added browsable version list with channel filter.
 *
 * Displays different content based on server state:
 * - not_installed: Shows ServerInstallCard for installation
 * - installing: Shows ServerInstallCard with installation progress
 * - installed/running/etc: Shows current version with status + Available Versions list
 */

import { useState } from 'react';
import { ServerInstallCard } from '@/components/ServerInstallCard';
import { ServerStatusBadge } from '@/components/ServerStatusBadge';
import { ChannelFilter, type ChannelFilterValue } from '@/components/ChannelFilter';
import { VersionGrid } from '@/components/VersionGrid';
import { useServerStatus, useInstallStatus } from '@/hooks/use-server-status';
import { useVersions } from '@/hooks/use-versions';
import { isServerInstalled } from '@/lib/server-utils';
import type { ServerState } from '@/api/types';

/**
 * Version/Installation page for the Game Server section.
 *
 * Shows installation interface when no server is installed,
 * and version information when server is installed.
 */
export function VersionPage() {
  const { data: statusResponse, isLoading, error } = useServerStatus();
  const serverStatus = statusResponse?.data;
  const serverState = serverStatus?.state ?? 'not_installed';

  const isInstalling = serverState === 'installing';
  const { data: installStatusResponse } = useInstallStatus(isInstalling);
  const installStatus = installStatusResponse?.data;

  // Determine if server is installed (not in 'not_installed' or 'installing' state)
  const isInstalled = isServerInstalled(serverState);

  // Channel filter state for version list (Story 13.3)
  const [channel, setChannel] = useState<ChannelFilterValue>(undefined);

  // Fetch available versions (only when installed - Story 13.3)
  const { data: versionsResponse, isLoading: isLoadingVersions } = useVersions({
    channel,
    enabled: isInstalled,
  });
  const versions = versionsResponse?.data?.versions ?? [];

  // Handler for version card clicks - prep for Story 13.4
  const handleVersionClick = (version: string) => {
    // Story 13.4 will add install/upgrade dialog
    console.log('Version clicked:', version);
  };

  // Dynamic page title based on state
  const pageTitle = isInstalled ? 'Server Version' : 'Server Installation';

  if (isLoading) {
    return (
      <div className="p-4" data-testid="version-page-loading">
        <h1 className="text-2xl font-bold mb-4">{pageTitle}</h1>
        <p className="text-muted-foreground">Loading server status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4" data-testid="version-page-error">
        <h1 className="text-2xl font-bold mb-4">{pageTitle}</h1>
        <p className="text-destructive">Error: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="p-4" data-testid="version-page">
      <h1 className="text-2xl font-bold mb-4" data-testid="version-page-title">
        {pageTitle}
      </h1>

      {isInstalled ? (
        <>
          <InstalledVersionCard
            version={serverStatus?.version ?? 'Unknown'}
            state={serverState}
            availableStableVersion={serverStatus?.availableStableVersion ?? null}
          />

          {/* Available Versions Section - Story 13.3 */}
          <div className="mt-8" data-testid="available-versions-section">
            <h2 className="text-xl font-semibold mb-4">Available Versions</h2>
            <div className="mb-4">
              <ChannelFilter value={channel} onChange={setChannel} />
            </div>
            <VersionGrid
              versions={versions}
              isLoading={isLoadingVersions}
              installedVersion={serverStatus?.version}
              onVersionClick={handleVersionClick}
            />
          </div>
        </>
      ) : (
        <ServerInstallCard
          isInstalling={isInstalling}
          installStatus={installStatus}
        />
      )}
    </div>
  );
}

interface InstalledVersionCardProps {
  version: string;
  state: ServerState;
  availableStableVersion: string | null;
}

/**
 * Card displaying the installed server version and status.
 *
 * Shows:
 * - Current installed version prominently
 * - Server state badge (running/stopped)
 * - Update available indicator when newer version exists
 */
function InstalledVersionCard({
  version,
  state,
  availableStableVersion,
}: InstalledVersionCardProps) {
  // Check if an update is available
  const hasUpdate =
    version &&
    availableStableVersion &&
    version !== availableStableVersion;

  return (
    <div
      className="space-y-4"
      data-testid="installed-version-card"
    >
      {/* Update Available Banner */}
      {hasUpdate && (
        <UpdateAvailableBanner newVersion={availableStableVersion} />
      )}

      {/* Version and Status */}
      <div className="flex items-center gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Installed Version</p>
          <p className="text-3xl font-bold" data-testid="installed-version">
            {version}
          </p>
        </div>
        <ServerStatusBadge state={state} />
      </div>
    </div>
  );
}

interface UpdateAvailableBannerProps {
  newVersion: string;
}

/**
 * Banner indicating a newer version is available.
 */
function UpdateAvailableBanner({ newVersion }: UpdateAvailableBannerProps) {
  return (
    <div
      className="rounded-lg border border-primary/20 bg-primary/10 p-4"
      role="alert"
      data-testid="update-available-banner"
    >
      <p className="text-sm font-medium text-primary">
        Update Available: {newVersion}
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        A newer version of VintageStory server is available.
      </p>
    </div>
  );
}
