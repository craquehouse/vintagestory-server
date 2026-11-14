/**
 * InstalledModCard - one installed mod as a card, for screens narrower than `md`
 * (Story 16.5, FR172).
 *
 * Shows what the table row shows (name, version, side, compatibility, update status
 * with the Update action, enable toggle, remove) without horizontal scrolling. ModTable
 * renders it from the same sorted rows and passes its own handlers, so both layouts
 * share the data, the mutations and the dialogs. Controls are at least 44x44px.
 */

import { SideBadge } from '@/components/SideBadge';
import { ModUpdateCell } from '@/components/ModUpdateCell';
import {
  ModCompatibility,
  ModEnableToggle,
  ModNameLink,
  ModRemoveButton,
  type ModTableRow,
} from '@/components/InstalledModParts';

interface InstalledModCardProps {
  mod: ModTableRow;
  /** Installed game version, for the update status tooltip */
  gameVersion: string | null;
  isToggling: boolean;
  isUpdating: boolean;
  onToggle: () => void;
  onUpdate: () => void;
  onRemove: () => void;
}

export function InstalledModCard({
  mod,
  gameVersion,
  isToggling,
  isUpdating,
  onToggle,
  onUpdate,
  onRemove,
}: InstalledModCardProps) {
  return (
    <li
      className="space-y-3 rounded-lg border bg-card p-3 text-card-foreground"
      aria-label={mod.name || mod.slug}
      data-testid={`installed-mod-card-${mod.slug}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 break-words">
          <ModNameLink mod={mod} />
        </div>
        {/* The label makes the whole 44px area toggle the switch */}
        <label className="flex min-h-11 min-w-11 shrink-0 cursor-pointer items-center justify-end gap-2 text-sm text-muted-foreground">
          <span>{mod.enabled ? 'Enabled' : 'Disabled'}</span>
          <ModEnableToggle mod={mod} isToggling={isToggling} onToggle={onToggle} />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">v{mod.version}</span>
        <SideBadge side={mod.side} />
      </div>

      <ModCompatibility
        slug={mod.slug}
        status={mod.compatibilityStatus}
        compatibility={mod.compatibility}
        showMessage
      />

      <div className="flex items-center justify-between gap-2 border-t pt-2">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
          <span className="text-sm font-medium">Available</span>
          <ModUpdateCell
            status={mod.updateStatus}
            gameVersion={gameVersion}
            onUpdate={onUpdate}
            isUpdating={isUpdating}
            buttonClassName="min-h-11 min-w-11"
          />
        </div>
        <ModRemoveButton mod={mod} onRemove={onRemove} className="size-11 shrink-0" />
      </div>
    </li>
  );
}
