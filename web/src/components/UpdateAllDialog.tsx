/**
 * UpdateAllDialog - Confirm and report applying every compatible update (Story 14.4).
 *
 * Confirm step: lists the mods that will update (installed → offered) and those skipped
 * because their offered update is not verified. After confirming, the dialog shows each
 * mod's outcome and, once, whether a server restart is required (UX: Update All Flow).
 */

import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useApplyAllModUpdates } from '@/hooks/use-mods';
import type { ModUpdateAllItem, ModUpdateStatus } from '@/api/types';

const RESTART_REQUIRED = 'A server restart is required for changes to take effect.';

const REASON_LABELS: Record<string, string> = {
  not_verified: 'not verified',
  incompatible: 'incompatible',
  prerelease: 'pre-release',
  older: 'older release',
};

interface UpdateAllDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Update status items with an offered update */
  updates: ModUpdateStatus[];
  /** Installed game version, for the skipped list */
  gameVersion: string | null;
}

function outcomeText(item: ModUpdateAllItem): string {
  switch (item.outcome) {
    case 'updated':
      return 'Updated';
    case 'skipped': {
      const reasons = item.reasons.map((reason) => REASON_LABELS[reason] ?? reason);
      return reasons.length > 0 ? `Skipped: ${reasons.join(', ')}` : 'Skipped';
    }
    case 'failed':
      return item.error ? `Failed: ${item.error}` : 'Failed';
  }
}

export function UpdateAllDialog({ open, onOpenChange, updates, gameVersion }: UpdateAllDialogProps) {
  const { mutate, isPending, data, reset } = useApplyAllModUpdates();
  const summary = data?.data;

  const toUpdate = updates.filter((item) => item.offeredCompatibility === 'compatible');
  const notVerified = updates.filter((item) => item.offeredCompatibility !== 'compatible');

  const handleOpenChange = (next: boolean) => {
    if (!next && isPending) return;
    if (!next) reset();
    onOpenChange(next);
  };

  const handleConfirm = () => {
    mutate(undefined, {
      onError: (error) => {
        toast.error('Update all failed', { description: error.message });
        reset();
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent data-testid="update-all-dialog">
        {summary ? (
          <>
            <DialogHeader>
              <DialogTitle>Update all finished</DialogTitle>
              <DialogDescription data-testid="update-all-counts">
                {summary.updated} updated, {summary.skipped} skipped, {summary.failed} failed
              </DialogDescription>
            </DialogHeader>
            <ul className="space-y-2 text-sm" data-testid="update-all-results">
              {summary.results.map((item) => (
                <li key={item.slug} data-outcome={item.outcome}>
                  <span className="font-medium">{item.name || item.slug}</span>{' '}
                  <span className="text-muted-foreground">
                    v{item.fromVersion} → v{item.toVersion}
                  </span>
                  <div
                    className={
                      item.outcome === 'failed' ? 'text-destructive' : 'text-muted-foreground'
                    }
                  >
                    {outcomeText(item)}
                  </div>
                </li>
              ))}
            </ul>
            {summary.pendingRestart && (
              <p className="text-sm" data-testid="update-all-restart">
                {RESTART_REQUIRED}
              </p>
            )}
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)} data-testid="update-all-close">
                Close
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Update all mods?</DialogTitle>
              <DialogDescription>
                Mods update one at a time. A mod that fails does not stop the others.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 text-sm">
              <section>
                <h3 className="font-medium">Will update</h3>
                <ul className="mt-1 space-y-1" data-testid="update-all-planned">
                  {toUpdate.map((item) => (
                    <li key={item.slug}>
                      {item.name || item.slug}{' '}
                      <span className="text-muted-foreground">
                        v{item.installedVersion} → v{item.offeredVersion}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
              {notVerified.length > 0 && (
                <section>
                  <h3 className="font-medium">
                    Skipped: not verified for{' '}
                    {gameVersion ? `game version ${gameVersion}` : 'the installed game version'}
                  </h3>
                  <p className="text-muted-foreground">Review these individually.</p>
                  <ul className="mt-1 space-y-1" data-testid="update-all-skipped">
                    {notVerified.map((item) => (
                      <li key={item.slug}>
                        {item.name || item.slug}{' '}
                        <span className="text-muted-foreground">
                          v{item.installedVersion} → v{item.offeredVersion}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isPending}
                data-testid="update-all-cancel"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={isPending || toUpdate.length === 0}
                data-testid="update-all-confirm"
              >
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Update {toUpdate.length} {toUpdate.length === 1 ? 'mod' : 'mods'}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
