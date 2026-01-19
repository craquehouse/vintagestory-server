/**
 * UninstallConfirmDialog - Confirmation dialog for server uninstallation.
 *
 * Story 13.7: Provides a confirmation step before uninstalling the
 * VintageStory server, with appropriate warnings about running server
 * and reassurance about data preservation.
 *
 * Features:
 * - Shows preservation message (config, mods, worlds preserved)
 * - Shows server-running warning when server is running
 * - Destructive action styling for Remove button
 */

import { AlertTriangle, Info, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { ServerState } from '@/api/types';

/**
 * Props for the UninstallConfirmDialog component.
 */
export interface UninstallConfirmDialogProps {
  /** Current server state */
  serverState: ServerState;
  /** Dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when user confirms uninstall */
  onConfirm: () => void;
  /** Whether the uninstall operation is in progress */
  isPending?: boolean;
}

/**
 * Confirmation dialog for server uninstallation.
 *
 * Shows preservation message and server-running warning when applicable.
 *
 * @example
 * <UninstallConfirmDialog
 *   serverState={serverState}
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   onConfirm={handleUninstall}
 *   isPending={mutation.isPending}
 * />
 */
export function UninstallConfirmDialog({
  serverState,
  open,
  onOpenChange,
  onConfirm,
  isPending = false,
}: UninstallConfirmDialogProps) {
  const isServerRunning = serverState === 'running';

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="uninstall-confirm-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="dialog-title">
            Remove Server Installation
          </AlertDialogTitle>
          <AlertDialogDescription>
            This will remove the VintageStory server binaries from the system.
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* Preservation note - always shown */}
        <div
          className="flex items-start gap-2 rounded-md bg-muted/50 border border-muted p-3"
          data-testid="preservation-message"
        >
          <Info className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
          <p className="text-sm text-muted-foreground">
            Your configuration files, mods, and world saves will be preserved.
          </p>
        </div>

        {/* Server running warning - conditional */}
        {isServerRunning && (
          <div
            className="flex items-start gap-2 rounded-md bg-warning/10 border border-warning/20 p-3"
            data-testid="server-running-warning"
          >
            <AlertTriangle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
            <p className="text-sm text-warning">
              The server is currently running and will be stopped first.
            </p>
          </div>
        )}

        <AlertDialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
            data-testid="cancel-button"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending}
            className="gap-2"
            data-testid="confirm-button"
          >
            <Trash2 className={`h-4 w-4 ${isPending ? 'animate-spin' : ''}`} />
            {isPending ? 'Removing...' : 'Remove Server'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
