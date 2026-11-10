/**
 * ModUpdateCell - "Available" column cell for the installed mods table (Story 14.3).
 *
 * Shows the offered update with an Update action, or a quiet status label
 * ("Up to date", "No compatible update", "Unknown") with the reason as a tooltip.
 */

import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ModUpdateStatus, ModUpdateUnknownReason } from '@/api/types';

const UNKNOWN_REASONS: Record<ModUpdateUnknownReason, string> = {
  not_checked: 'Not checked yet. Use "Check for updates".',
  not_in_database: 'Not found in the mod database.',
  installed_release_not_listed: 'The installed version is not listed in the mod database.',
  version_unparsable: 'The installed version could not be compared with newer releases.',
};

interface ModUpdateCellProps {
  /** Update status for this mod; undefined while loading or when not reported */
  status?: ModUpdateStatus;
  /** Installed game version, for the "No compatible update" tooltip */
  gameVersion?: string | null;
  /** Called when the Update action is clicked; omit to hide the action */
  onUpdate?: () => void;
  /** Whether a version change for this mod is running */
  isUpdating?: boolean;
}

function withError(text: string, status: ModUpdateStatus): string {
  return status.error ? `${text} Last check failed: ${status.error}` : text;
}

function StatusLabel({ label, title, testId }: { label: string; title?: string; testId: string }) {
  // The tooltip is not reachable by keyboard or touch; repeat it for screen readers.
  return (
    <span className="text-sm text-muted-foreground" title={title} data-testid={testId}>
      {label}
      {title && <span className="sr-only">{` ${title}`}</span>}
    </span>
  );
}

export function ModUpdateCell({ status, gameVersion, onUpdate, isUpdating }: ModUpdateCellProps) {
  const slug = status?.slug ?? 'none';

  switch (status?.status) {
    case 'update_available':
      return (
        <div className="flex items-center gap-2" data-testid={`mod-update-${slug}`}>
          <span className="text-sm">
            v{status.offeredVersion}
            {status.offeredPrerelease && (
              <span className="ml-1 text-xs text-muted-foreground">pre-release</span>
            )}
          </span>
          {onUpdate && (
            <Button
              variant="outline"
              size="sm"
              onClick={onUpdate}
              disabled={isUpdating}
              data-testid={`mod-update-button-${slug}`}
              aria-label={`Update ${status.name || slug} to v${status.offeredVersion}`}
            >
              {isUpdating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Update'}
            </Button>
          )}
        </div>
      );
    case 'up_to_date':
      return (
        <StatusLabel
          label="Up to date"
          title={status.error ? `Last check failed: ${status.error}` : undefined}
          testId={`mod-update-${slug}`}
        />
      );
    case 'blocked':
      return (
        <StatusLabel
          label="No compatible update"
          title={withError(
            gameVersion
              ? `Newer releases exist, but none is compatible with game version ${gameVersion}.`
              : 'Newer releases exist, but none is compatible with the installed game version.',
            status
          )}
          testId={`mod-update-${slug}`}
        />
      );
    case 'unknown':
      return (
        <StatusLabel
          label="Unknown"
          title={withError(
            (status.reason && UNKNOWN_REASONS[status.reason]) || 'Update status is unknown.',
            status
          )}
          testId={`mod-update-${slug}`}
        />
      );
    default:
      return <span className="text-sm text-muted-foreground">—</span>;
  }
}
