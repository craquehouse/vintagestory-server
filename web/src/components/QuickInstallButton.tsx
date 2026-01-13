/**
 * QuickInstallButton - Quick action button for installing/updating server
 *
 * Story 13.5: Quick install button component for version page.
 *
 * Shows:
 * - "Install Latest Stable ({version})" when not installed
 * - "Update to {version}" when installed with update available
 * - Hidden when up to date or no versions available
 */

import { Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useInstallServer } from '@/hooks/use-server-status';
import type { VersionInfo } from '@/api/types';

interface QuickInstallButtonProps {
  /** List of available versions */
  versions: VersionInfo[];
  /** Currently installed version (null if not installed) */
  installedVersion: string | null;
  /** Whether versions are still loading */
  isLoadingVersions: boolean;
}

/**
 * Quick install button for latest stable version.
 *
 * @example
 * <QuickInstallButton
 *   versions={versions}
 *   installedVersion={serverStatus?.version ?? null}
 *   isLoadingVersions={isLoadingVersions}
 * />
 */
export function QuickInstallButton({
  versions,
  installedVersion,
  isLoadingVersions,
}: QuickInstallButtonProps) {
  const installMutation = useInstallServer();

  // Find the latest stable version
  const latestStable = versions.find((v) => v.channel === 'stable' && v.isLatest);

  // Don't render if loading, no versions, or no latest stable
  if (isLoadingVersions || versions.length === 0 || !latestStable) {
    return null;
  }

  // Check if an update is available (installed version differs from latest stable)
  const hasUpdate = installedVersion && installedVersion !== latestStable.version;
  const showButton = !installedVersion || hasUpdate;

  // Don't render if up to date
  if (!showButton) {
    return null;
  }

  const buttonText = installedVersion
    ? `Update to ${latestStable.version}`
    : `Install Latest Stable (${latestStable.version})`;

  const handleClick = () => {
    // Use force flag when updating existing installation
    installMutation.mutate({
      version: latestStable.version,
      force: !!installedVersion,
    });
  };

  return (
    <Button
      size="lg"
      onClick={handleClick}
      disabled={installMutation.isPending}
      data-testid="quick-install-button"
      className="mb-6"
    >
      {installMutation.isPending ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Installing...
        </>
      ) : (
        <>
          <Download className="mr-2 h-4 w-4" />
          {buttonText}
        </>
      )}
    </Button>
  );
}
