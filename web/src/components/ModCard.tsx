/**
 * ModCard - Card component for displaying a single mod in the browse grid.
 *
 * Displays: thumbnail (or placeholder), name, author, download count,
 * and short description.
 *
 * Story 10.5: Enhanced with thumbnail.
 * Story 10.8: Added install button with confirmation dialog.
 */

import { useState, useEffect } from 'react';
import { Download, Users, TrendingUp, ExternalLink, Package, Check, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { InstallConfirmDialog } from '@/components/InstallConfirmDialog';
import { useModDetail } from '@/hooks/use-mod-detail';
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
 * and short description.
 *
 * @example
 * <ModCard mod={modBrowseItem} />
 */
export function ModCard({ mod, onClick, installedSlugs }: ModCardProps) {
  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);
  const [shouldFetchDetails, setShouldFetchDetails] = useState(false);

  // Check if this mod is already installed
  const isInstalled = installedSlugs?.has(mod.slug) ?? false;

  // Only apply clickable styles when onClick handler is provided
  const clickableStyles = onClick
    ? 'cursor-pointer hover:shadow-lg transition-shadow'
    : '';

  // Lazy-load mod details when Install button is clicked
  const { data: modDetails, isLoading: isLoadingDetails, isError } = useModDetail(
    shouldFetchDetails ? mod.slug : ''
  );

  // Handle install button click - fetch details first, then open dialog
  const handleInstallClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShouldFetchDetails(true);
  };

  // Open dialog once details are loaded or fetch fails
  useEffect(() => {
    if (shouldFetchDetails && !isLoadingDetails && (modDetails || isError)) {
      setIsInstallDialogOpen(true);
      // Note: Don't reset shouldFetchDetails here - it keeps the query enabled
      // so modDetails stays available. Reset when dialog closes instead.
    }
  }, [shouldFetchDetails, modDetails, isLoadingDetails, isError]);

  // Reset fetch state when dialog closes (keeps query enabled while dialog is open)
  const handleDialogOpenChange = (open: boolean) => {
    setIsInstallDialogOpen(open);
    if (!open) {
      setShouldFetchDetails(false);
    }
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
            <span className="inline-flex items-center gap-1">
              <span
                className={`hover:underline${onClick ? ' cursor-pointer' : ''}`}
                data-testid={`mod-card-name-${mod.slug}`}
                {...(onClick && {
                  role: 'button',
                  tabIndex: 0,
                  onKeyDown: (e: React.KeyboardEvent) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onClick();
                    }
                  },
                })}
              >
                {mod.name}
              </span>
              <a
                href={`https://mods.vintagestory.at/show/mod/${mod.assetId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-ring rounded"
                onClick={(e) => e.stopPropagation()}
                data-testid={`mod-card-link-${mod.slug}`}
                title="Open on ModDB"
                aria-label={`Open ${mod.name} on ModDB (opens in new tab)`}
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            </span>
          </CardTitle>
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
                className="flex items-center gap-1.5 text-sm text-success"
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
                disabled={isLoadingDetails}
                data-testid={`mod-card-install-${mod.slug}`}
              >
                {isLoadingDetails ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-1.5" />
                    Install
                  </>
                )}
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
        version: modDetails?.data?.latestVersion ?? LATEST_VERSION,
        logoUrl: mod.logoUrl,
        author: mod.author,
      }}
      compatibility={{
        status: modDetails?.data?.compatibility?.status ?? 'not_verified',
        message: modDetails?.data?.compatibility?.message,
      }}
      open={isInstallDialogOpen}
      onOpenChange={handleDialogOpenChange}
    />
    </>
  );
}
