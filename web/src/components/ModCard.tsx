/**
 * ModCard - Card component for displaying a single mod in the browse grid.
 *
 * Displays: thumbnail (or placeholder), name, author, download count,
 * short description, and compatibility badge.
 *
 * Story 10.5: Enhanced with thumbnail and compatibility badge.
 */

import { Download, Users, TrendingUp, ExternalLink, Package } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { getBrowseCardCompatibility } from '@/lib/mod-compatibility';
import type { ModBrowseItem } from '@/api/types';

interface ModCardProps {
  /** Mod data to display */
  mod: ModBrowseItem;
  /** Click handler for card navigation (optional) */
  onClick?: () => void;
}

/**
 * Formats a number with K/M suffix for compact display.
 *
 * @param num - Number to format
 * @returns Formatted string (e.g., "1.2K", "3.4M")
 */
function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return String(num);
}

/**
 * Card displaying mod information in the browse grid.
 *
 * Shows thumbnail (or placeholder), name, author, download count,
 * short description, and compatibility badge.
 *
 * @example
 * <ModCard mod={modBrowseItem} />
 */
export function ModCard({ mod, onClick }: ModCardProps) {
  // For browse grid, use 'not_verified' as conservative default
  // Full compatibility check deferred to mod detail view (Story 10.6)
  const compatibilityStatus = getBrowseCardCompatibility();

  // Only apply clickable styles when onClick handler is provided
  const clickableStyles = onClick
    ? 'cursor-pointer hover:shadow-lg transition-shadow'
    : '';

  return (
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
      </CardContent>
    </Card>
  );
}

export { formatNumber };
