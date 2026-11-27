/**
 * ModUpdateCell - "Available" column cell for the installed mods table (Story 14.3).
 *
 * Shows the offered update with an Update action, or a quiet status label
 * ("Up to date", "No compatible update", "Not checked yet", "Unknown") with the reason
 * as a tooltip. Story 17.4: a mod with no stored update data (`not_checked`) says
 * "Not checked yet" rather than "Unknown".
 * Story 18.4: the Update button wraps under the version when the column is narrow.
 * Story 24.4: a mod the mod database does not know (`not_in_database`) is a "Local mod".
 * Story 28.1: an uploaded or linked mod (`manual_install`) says where it came from.
 */

import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ModSource, ModUpdateStatus, ModUpdateUnknownReason } from '@/api/types';

const UNKNOWN_REASONS: Record<ModUpdateUnknownReason, string> = {
  not_checked: 'Use "Check for updates" to look it up now.',
  not_in_database:
    'Not in the mod database: it has no mod database page and gets no update offers.',
  manual_install: 'Not from the mod database: it gets no update offers.',
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
  /** Extra classes for the Update button, e.g. a larger touch size on the cards (Story 16.5) */
  buttonClassName?: string;
  /** Story 28.1: where the mod came from, to label an uploaded or linked mod */
  source?: ModSource;
  /** Story 28.1: the link a `url` mod came from */
  sourceUrl?: string | null;
}

/** The host of a link, or null when it does not parse. */
function linkHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).host || null;
  } catch {
    return null;
  }
}

/** Story 28.1: the label and tooltip of an uploaded or linked mod. */
function manualInstallLabel(
  source: ModSource | undefined,
  sourceUrl: string | null | undefined
): { label: string; title: string } {
  if (source === 'url') {
    const host = linkHost(sourceUrl);
    return {
      label: 'Installed from a link',
      title: `Installed from ${host ?? 'a link'}; not from the mod database, so it gets no update offers.`,
    };
  }
  return {
    label: 'Uploaded file',
    title: 'Uploaded file; not from the mod database, so it gets no update offers.',
  };
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

export function ModUpdateCell({
  status,
  gameVersion,
  onUpdate,
  isUpdating,
  buttonClassName,
  source,
  sourceUrl,
}: ModUpdateCellProps) {
  const slug = status?.slug ?? 'none';

  switch (status?.status) {
    case 'update_available':
      return (
        <div
          className="flex flex-wrap items-center gap-x-2 gap-y-1"
          data-testid={`mod-update-${slug}`}
        >
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
              className={buttonClassName}
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
      if (status.reason === 'manual_install') {
        const { label, title } = manualInstallLabel(source, sourceUrl);
        return (
          <StatusLabel
            label={label}
            title={withError(title, status)}
            testId={`mod-update-${slug}`}
          />
        );
      }
      return (
        <StatusLabel
          label={
            status.reason === 'not_checked'
              ? 'Not checked yet'
              : status.reason === 'not_in_database'
                ? 'Local mod'
                : 'Unknown'
          }
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
