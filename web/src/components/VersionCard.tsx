/**
 * VersionCard - Card component for displaying a VintageStory server version.
 *
 * Displays: version number, channel badge (Stable/Unstable), file size,
 * "Latest" badge, and "Installed" indicator.
 */

import { Check, ExternalLink, HardDrive } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { VersionInfo, VersionChannel } from '@/api/types';

interface VersionCardProps {
  version: VersionInfo;
  installedVersion?: string | null;
  /** Story 13.5: Whether this version is newer than installed */
  isNewer?: boolean;
  onClick?: () => void;
}

const channelStyles: Record<VersionChannel, { label: string; className: string }> = {
  stable: {
    label: 'Stable',
    className: 'text-success border-success/30 bg-success/10',
  },
  unstable: {
    label: 'Unstable',
    className: 'text-warning border-warning/30 bg-warning/10',
  },
};

/**
 * Card displaying VintageStory server version information.
 *
 * Shows version number, channel badge (Stable/Unstable), file size,
 * and status badges (Latest, Installed).
 */
export function VersionCard({
  version,
  installedVersion,
  isNewer,
  onClick,
}: VersionCardProps) {
  const isInstalled = installedVersion === version.version;
  const channel = channelStyles[version.channel];

  return (
    <Card
      className={cn(
        'h-full',
        onClick && 'cursor-pointer hover:shadow-lg transition-shadow',
        // Story 13.5: Highlight newer versions with ring styling
        isNewer && 'ring-2 ring-primary ring-offset-2'
      )}
      data-testid={`version-card-${version.version}`}
      onClick={onClick}
    >
      <CardContent className="pt-4">
        <div className="mb-3" data-testid={`version-card-channel-${version.version}`}>
          <Badge variant="outline" className={channel.className}>
            {channel.label}
          </Badge>
        </div>

        <h3
          className="text-xl font-semibold mb-1"
          data-testid={`version-card-version-${version.version}`}
        >
          <span className="inline-flex items-center gap-1.5">
            {version.version}
            <a
              href={`https://wiki.vintagestory.at/${version.version}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-ring rounded"
              onClick={(e) => e.stopPropagation()}
              data-testid={`version-card-changelog-${version.version}`}
              title="View changelog"
              aria-label={`View changelog for version ${version.version} (opens in new tab)`}
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </span>
        </h3>

        <div
          className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3"
          data-testid={`version-card-filesize-${version.version}`}
        >
          <HardDrive className="h-3.5 w-3.5" />
          <span>{version.filesize}</span>
        </div>

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
              className="flex items-center gap-1.5 text-sm text-success"
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
