/**
 * ModCard - Card component for displaying a single mod in the browse grid.
 *
 * Displays: thumbnail (or placeholder), name, author, download count,
 * short description, and compatibility badge.
 *
 * Story 10.5: Enhanced with thumbnail and compatibility badge.
 * Story 10.8: Added install button with confirmation dialog.
 */

import { useState } from 'react';
import { Download, Users, TrendingUp, ExternalLink, Package, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { InstallConfirmDialog } from '@/components/InstallConfirmDialog';
import { getBrowseCardCompatibility } from '@/lib/mod-compatibility';
import { formatNumber } from '@/lib/utils';
import type { ModBrowseItem } from '@/api/types';

interface ModCardProps {
  /** Mod data to display */
  mod: ModBrowseItem;
  /** Click handler for card navigation (optional) */
  onClick?: () => void;
  /** Set of installed mod slugs (optional, used for install button) */
  installedSlugs?: Set<string>;
}

/**
 * Version string used when installing from browse cards (latest available).
 */
const LATEST_VERSION = 'latest';

/**
 * Card displaying mod information in the browse grid.
 *
 * Shows thumbnail (or placeholder), name, author, download count,
 * short description, and compatibility badge.
 *
 * @example
 * <ModCard mod={modBrowseItem} />
 */
export function ModCard({ mod, onClick, installedSlugs }: ModCardProps) {
  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);

  // For browse grid, use 'not_verified' as conservative default
  // Full compatibility check deferred to mod detail view (Story 10.6)
  const compatibilityStatus = getBrowseCardCompatibility();

  // Check if this mod is already installed
  const isInstalled = installedSlugs?.has(mod.slug) ?? false;

  // Only apply clickable styles when onClick handler is provided
  const clickableStyles = onClick
    ? 'cursor-pointer hover:shadow-lg transition-shadow'
    : '';

  // Handle install button click - stop propagation to prevent card click
  const handleInstallClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsInstallDialogOpen(true);
  };

  return (
    <>
    <Card
      className={`h-full ${clickableStyles}`}
      data-testid={`mod-card-${mod.slug}`}
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div
        className="relative aspect-video overflow-hidden rounded-t-lg bg-muted"
        data-testid={`mod-card-thumbnail-${mod.slug}`}
      >
        {mod.logoUrl ? (
          <img
            src={mod.logoUrl}
            alt={`${mod.name} thumbnail`}
            className="h-full w-full object-cover"
            data-testid={`mod-card-logo-${mod.slug}`}
          />
        ) : (
          <div
            className="flex h-full items-center justify-center"
            data-testid={`mod-card-placeholder-${mod.slug}`}
          >
            <Package className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">
            <a
              href={`https://mods.vintagestory.at/${mod.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:underline"
              data-testid={`mod-card-link-${mod.slug}`}
              onClick={(e) => e.stopPropagation()}
            >
              {mod.name}
              <ExternalLink className="h-3 w-3 text-muted-foreground" />
            </a>
          </CardTitle>
          <CompatibilityBadge status={compatibilityStatus} />
        </div>
        <p className="text-sm text-muted-foreground" data-testid={`mod-card-author-${mod.slug}`}>
          by {mod.author}
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        {mod.summary && (
          <p
            className="text-sm text-muted-foreground line-clamp-2 mb-3"
            data-testid={`mod-card-summary-${mod.slug}`}
          >
            {mod.summary}
          </p>
        )}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span
            className="inline-flex items-center gap-1"
            title="Downloads"
            data-testid={`mod-card-downloads-${mod.slug}`}
          >
            <Download className="h-3.5 w-3.5" />
            {formatNumber(mod.downloads)}
          </span>
          <span
            className="inline-flex items-center gap-1"
            title="Followers"
            data-testid={`mod-card-follows-${mod.slug}`}
          >
            <Users className="h-3.5 w-3.5" />
            {formatNumber(mod.follows)}
          </span>
          <span
            className="inline-flex items-center gap-1"
            title="Trending"
            data-testid={`mod-card-trending-${mod.slug}`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            {formatNumber(mod.trendingPoints)}
          </span>
        </div>

        {/* Install button or Installed indicator (Story 10.8) */}
        {installedSlugs !== undefined && (
          <div className="mt-3 pt-3 border-t">
            {isInstalled ? (
              <div
                className="flex items-center gap-1.5 text-sm text-green-500"
                data-testid={`mod-card-installed-${mod.slug}`}
              >
                <Check className="h-4 w-4" />
                <span>Installed</span>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={handleInstallClick}
                data-testid={`mod-card-install-${mod.slug}`}
              >
                <Download className="h-4 w-4 mr-1.5" />
                Install
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>

    {/* Install confirmation dialog */}
    <InstallConfirmDialog
      mod={{
        slug: mod.slug,
        name: mod.name,
        version: LATEST_VERSION,
        logoUrl: mod.logoUrl,
        author: mod.author,
      }}
      compatibility={{
        status: compatibilityStatus,
      }}
      open={isInstallDialogOpen}
      onOpenChange={setIsInstallDialogOpen}
    />
    </>
  );
}
