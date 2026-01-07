/**
 * ModCard - Card component for displaying a single mod in the browse grid.
 *
 * This is a placeholder implementation for Story 10.3.
 * The full card design will be implemented in Story 10.5.
 */

import { Download, Users, TrendingUp, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ModBrowseItem } from '@/api/types';

interface ModCardProps {
  /** Mod data to display */
  mod: ModBrowseItem;
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
 * Card displaying basic mod information in the browse grid.
 *
 * Placeholder for Story 10.3 - full implementation in Story 10.5.
 *
 * @example
 * <ModCard mod={modBrowseItem} />
 */
export function ModCard({ mod }: ModCardProps) {
  return (
    <Card className="h-full" data-testid={`mod-card-${mod.slug}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          <a
            href={`https://mods.vintagestory.at/${mod.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 hover:underline"
            data-testid={`mod-card-link-${mod.slug}`}
          >
            {mod.name}
            <ExternalLink className="h-3 w-3 text-muted-foreground" />
          </a>
        </CardTitle>
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

/**
 * Export formatNumber for testing.
 */
export { formatNumber };
