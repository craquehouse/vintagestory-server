/**
 * VersionCard - Card component for displaying a VintageStory server version.
 *
 * Displays: version number, channel badge (Stable/Unstable), file size,
 * "Latest" badge, and "Installed" indicator.
 */

import { Check, HardDrive } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { VersionInfo, VersionChannel } from '@/api/types';

interface VersionCardProps {
  version: VersionInfo;
  installedVersion?: string | null;
  onClick?: () => void;
}

const channelStyles: Record<VersionChannel, { label: string; className: string }> = {
  stable: {
    label: 'Stable',
    className: 'text-green-600 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800 dark:text-green-400',
  },
  unstable: {
    label: 'Unstable',
    className: 'text-yellow-600 border-yellow-200 bg-yellow-50 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-400',
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
  onClick,
}: VersionCardProps) {
  const isInstalled = installedVersion === version.version;
  const channel = channelStyles[version.channel];

  return (
    <Card
      className={cn('h-full', onClick && 'cursor-pointer hover:shadow-lg transition-shadow')}
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
          {version.version}
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
