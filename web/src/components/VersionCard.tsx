/**
 * VersionCard - Card component for displaying a VintageStory server version.
 *
 * Displays: version number, channel badge (Stable/Unstable), file size,
 * "Latest" badge, and "Installed" indicator.
 *
 * Story 13.2: Version Card Component
 */

import { Check, HardDrive } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { VersionInfo } from '@/api/types';

interface VersionCardProps {
  /** Version data to display */
  version: VersionInfo;
  /** Currently installed version (for "Installed" badge) */
  installedVersion?: string | null;
  /** Click handler for card selection */
  onClick?: () => void;
}

/**
 * Card displaying VintageStory server version information.
 *
 * Shows version number, channel badge (Stable/Unstable), file size,
 * and status badges (Latest, Installed).
 *
 * @example
 * <VersionCard
 *   version={versionInfo}
 *   installedVersion="1.21.5"
 *   onClick={() => handleVersionSelect(versionInfo.version)}
 * />
 */
export function VersionCard({
  version,
  installedVersion,
  onClick,
}: VersionCardProps) {
  // Check if this version is currently installed
  const isInstalled = installedVersion === version.version;

  // Only apply clickable styles when onClick handler is provided
  const clickableStyles = onClick
    ? 'cursor-pointer hover:shadow-lg transition-shadow'
    : '';

  return (
    <Card
      className={`h-full ${clickableStyles}`}
      data-testid={`version-card-${version.version}`}
      onClick={onClick}
    >
      <CardContent className="pt-4">
        {/* Channel badge at top */}
        <div className="mb-3" data-testid={`version-card-channel-${version.version}`}>
          {version.channel === 'stable' ? (
            <Badge
              variant="outline"
              className="text-green-600 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800 dark:text-green-400"
            >
              Stable
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="text-yellow-600 border-yellow-200 bg-yellow-50 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-400"
            >
              Unstable
            </Badge>
          )}
        </div>

        {/* Version number - primary display */}
        <h3
          className="text-xl font-semibold mb-1"
          data-testid={`version-card-version-${version.version}`}
        >
          {version.version}
        </h3>

        {/* File size */}
        <div
          className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3"
          data-testid={`version-card-filesize-${version.version}`}
        >
          <HardDrive className="h-3.5 w-3.5" />
          <span>{version.filesize}</span>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          {version.isLatest && (
            <Badge
              variant="secondary"
              data-testid={`version-card-latest-${version.version}`}
            >
              Latest
            </Badge>
          )}

          {isInstalled && (
            <div
              className="flex items-center gap-1.5 text-sm text-green-500"
              data-testid={`version-card-installed-${version.version}`}
            >
              <Check className="h-4 w-4" />
              <span>Installed</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
