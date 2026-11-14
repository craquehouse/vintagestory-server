/**
 * InstalledModParts - content shared by the installed mods table and its phone cards
 * (Story 16.5).
 *
 * ModTable's columns and InstalledModCard render the same parts, so both layouts show
 * the same information with the same test IDs and accessible names. Only one layout is
 * mounted at a time (ModTable switches with useMediaQuery).
 */

import { ExternalLink, Loader2, Trash2 } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import type {
  CompatibilityStatus,
  ModCompatibility as ModCompatibilityInfo,
  ModInfo,
  ModUpdateStatus,
} from '@/api/types';

/** Installed mod with compatibility and update data, as the table and cards render it. */
export interface ModTableRow extends ModInfo {
  compatibilityStatus: CompatibilityStatus;
  /** Story 16.3: message and latest supported game version for the installed release */
  compatibility?: ModCompatibilityInfo;
  /** Story 14.3: update status from GET /mods/updates */
  updateStatus?: ModUpdateStatus;
}

function modDatabaseUrl(mod: ModInfo): string {
  return mod.assetId > 0
    ? `https://mods.vintagestory.at/show/mod/${mod.assetId}`
    : `https://mods.vintagestory.at/${mod.slug}`;
}

/** Mod name linking to its mod database page, with the slug under it when a name exists. */
export function ModNameLink({ mod }: { mod: ModInfo }) {
  return (
    <div>
      <div className="font-medium">
        <a
          href={modDatabaseUrl(mod)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 hover:underline"
          data-testid={`mod-link-${mod.slug}`}
        >
          {mod.name || mod.slug}
          <ExternalLink className="h-3 w-3 text-muted-foreground" />
        </a>
      </div>
      {mod.name && <div className="text-sm text-muted-foreground">{mod.slug}</div>}
    </div>
  );
}

interface ModCompatibilityProps {
  slug: string;
  status: CompatibilityStatus;
  compatibility?: ModCompatibilityInfo;
  /**
   * Show the compatibility message as text for unverified and incompatible mods.
   * The badge tooltip cannot be reached by touch, so the phone cards turn this on.
   */
  showMessage?: boolean;
}

/**
 * Compatibility badge (message as tooltip) and, for unverified and incompatible mods,
 * the most recent supported game version (Story 16.3, Epic 16 ADR-2 decision 5).
 */
export function ModCompatibility({ slug, status, compatibility, showMessage }: ModCompatibilityProps) {
  const isFlagged = status !== 'compatible';
  const latestSupported = isFlagged ? compatibility?.latestSupportedGameVersion : null;
  const message = showMessage && isFlagged ? compatibility?.message : null;
  const badgeRow = (
    <div className="flex flex-wrap items-center gap-2">
      <CompatibilityBadge status={status} message={compatibility?.message} />
      {latestSupported && (
        <span
          className="text-xs text-muted-foreground whitespace-nowrap"
          data-testid={`mod-latest-supported-${slug}`}
        >
          Supports up to {latestSupported}
        </span>
      )}
    </div>
  );

  if (!message) return badgeRow;

  return (
    <div className="space-y-1">
      {badgeRow}
      <p
        className="text-xs text-muted-foreground break-words"
        data-testid={`mod-compatibility-message-${slug}`}
      >
        {message}
      </p>
    </div>
  );
}

interface ModEnableToggleProps {
  mod: ModInfo;
  isToggling: boolean;
  onToggle: () => void;
}

/** Enable/disable switch with a spinner while the change is running. */
export function ModEnableToggle({ mod, isToggling, onToggle }: ModEnableToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <Switch
        checked={mod.enabled}
        onCheckedChange={onToggle}
        disabled={isToggling}
        data-testid={`mod-toggle-${mod.slug}`}
        aria-label={mod.enabled ? 'Disable mod' : 'Enable mod'}
      />
      {isToggling && (
        <Loader2
          className="h-4 w-4 animate-spin text-muted-foreground"
          data-testid={`mod-toggle-spinner-${mod.slug}`}
        />
      )}
    </div>
  );
}

interface ModRemoveButtonProps {
  mod: ModInfo;
  onRemove: () => void;
  /** Extra classes, e.g. a larger touch size on the cards */
  className?: string;
}

/** Icon button that asks to remove the mod (the confirmation dialog lives in ModTable). */
export function ModRemoveButton({ mod, onRemove, className }: ModRemoveButtonProps) {
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={onRemove}
      className={className}
      data-testid={`mod-remove-${mod.slug}`}
      aria-label={`Remove ${mod.name || mod.slug}`}
    >
      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
    </Button>
  );
}
