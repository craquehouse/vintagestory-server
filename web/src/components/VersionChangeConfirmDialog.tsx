/**
 * VersionChangeConfirmDialog - Warning before a risky update or version switch (Story 14.3).
 *
 * Lists each reason the API gave (not verified, incompatible, pre-release, older),
 * with "Cancel" as the secondary action and "Update anyway" / "Switch anyway" as the
 * primary (UX spec: Compatibility Warnings).
 */

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { VersionChangeReason } from '@/api/types';
import type { VersionChangeConfirmation } from '@/hooks/use-version-change-flow';

interface VersionChangeConfirmDialogProps {
  /** The held change; the dialog is open while this is set */
  confirmation: VersionChangeConfirmation | null;
  /** Installed game version, for the compatibility reasons */
  gameVersion: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

function reasonText(
  reason: VersionChangeReason,
  confirmation: VersionChangeConfirmation,
  gameVersion: string | null
): string {
  const game = gameVersion ? `game version ${gameVersion}` : 'the installed game version';
  switch (reason) {
    case 'not_verified':
      return `Not verified for ${game}. It may still work.`;
    case 'incompatible':
      return `Not tagged for ${game}. It may not load.`;
    case 'prerelease':
      return `v${confirmation.version} is a pre-release; the installed version is a stable release.`;
    case 'older':
      return `v${confirmation.version} is older than the installed v${confirmation.installedVersion}. Worlds saved with a newer version may not load correctly.`;
  }
}

export function VersionChangeConfirmDialog({
  confirmation,
  gameVersion,
  onConfirm,
  onCancel,
}: VersionChangeConfirmDialogProps) {
  const verb = confirmation?.kind === 'switch' ? 'Switch' : 'Update';

  return (
    <AlertDialog open={!!confirmation} onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent data-testid="version-change-dialog">
        {confirmation && (
          <>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {verb} {confirmation.name} to v{confirmation.version}?
              </AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div>
                  {confirmation.reasons.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5" data-testid="version-change-reasons">
                      {confirmation.reasons.map((reason) => (
                        <li key={reason} data-reason={reason}>
                          {reasonText(reason, confirmation, gameVersion)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>This change needs confirmation.</p>
                  )}
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={onCancel} data-testid="version-change-cancel">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction onClick={onConfirm} data-testid="version-change-confirm">
                {verb} anyway
              </AlertDialogAction>
            </AlertDialogFooter>
          </>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
