/**
 * SideBadge - Displays mod side (Client/Server/Both) as visual badges.
 *
 * VSS-qal: Replaces the ambiguous "Both" text with clear Client/Server badges.
 *
 * Visual indicators:
 * - Client: Monitor icon with "Client" label
 * - Server: Server icon with "Server" label
 * - Both: Shows both badges
 */

import { Monitor, Server } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ModSide, BrowseModSide } from '@/api/types';

interface SideBadgeProps {
  /** The side value - supports both capitalized (ModSide) and lowercase (BrowseModSide). Falls back to 'both' if null/undefined/invalid. */
  side: ModSide | BrowseModSide | null | undefined;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Valid normalized side values.
 */
const VALID_SIDES = new Set(['client', 'server', 'both']);

/**
 * Normalizes side values to lowercase for consistent comparison.
 * Returns 'both' as fallback for invalid/missing values to ensure badges render.
 */
function normalizeSide(side: ModSide | BrowseModSide | null | undefined): 'client' | 'server' | 'both' {
  if (!side) {
    return 'both'; // Fallback: show both badges if side is missing
  }
  const normalized = side.toLowerCase();
  if (VALID_SIDES.has(normalized)) {
    return normalized as 'client' | 'server' | 'both';
  }
  return 'both'; // Fallback: show both badges for unknown values
}

/**
 * Displays mod side (Client/Server) as visual badges.
 *
 * @example
 * <SideBadge side="Both" />      // Shows Client + Server badges
 * <SideBadge side="client" />    // Shows Client badge only
 * <SideBadge side="Server" />    // Shows Server badge only
 */
export function SideBadge({ side, className }: SideBadgeProps) {
  const normalizedSide = normalizeSide(side);
  const showClient = normalizedSide === 'client' || normalizedSide === 'both';
  const showServer = normalizedSide === 'server' || normalizedSide === 'both';

  return (
    <span
      className={cn('inline-flex items-center gap-1', className)}
      data-testid="side-badge"
      data-side={side}
    >
      {showClient && (
        <Badge
          variant="outline"
          className="gap-1"
          data-testid="side-badge-client"
        >
          <Monitor className="h-3 w-3" aria-hidden="true" />
          <span>Client</span>
        </Badge>
      )}
      {showServer && (
        <Badge
          variant="outline"
          className="gap-1"
          data-testid="side-badge-server"
        >
          <Server className="h-3 w-3" aria-hidden="true" />
          <span>Server</span>
        </Badge>
      )}
    </span>
  );
}
