/**
 * QuickInstallButton - Quick action button for installing/updating server
 *
 * Story 13.5: Quick install button component for version page.
 *
 * Shows:
 * - "Install Latest Stable ({version})" when not installed
 * - "Update to {version}" when installed with update available
 * - Hidden when up to date or no versions available
 *
 * When server is running, shows confirmation dialog before proceeding.
 */

import { useState } from 'react';
import { Download, Loader2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
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
import { useInstallServer } from '@/hooks/use-server-status';
import type { VersionInfo, ServerState } from '@/api/types';

interface QuickInstallButtonProps {
  /** List of available versions */
  versions: VersionInfo[];
  /** Currently installed version (null if not installed) */
  installedVersion: string | null;
  /** Whether versions are still loading */
  isLoadingVersions: boolean;
  /** Current server state (for running server warning) */
  serverState?: ServerState;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Quick install button for latest stable version.
 *
 * @example
 * <QuickInstallButton
 *   versions={versions}
 *   installedVersion={serverStatus?.version ?? null}
 *   isLoadingVersions={isLoadingVersions}
 *   serverState={serverState}
 * />
 */
export function QuickInstallButton({
  versions,
  installedVersion,
  isLoadingVersions,
  serverState,
  className,
}: QuickInstallButtonProps) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const installMutation = useInstallServer();

  const latestStable = versions.find((v) => v.channel === 'stable' && v.isLatest);

  // Don't render if loading, no versions, no latest stable, or already up to date
  if (isLoadingVersions || !latestStable || installedVersion === latestStable.version) {
    return null;
  }

  const targetVersion = latestStable.version;
  const isServerRunning = serverState === 'running';
  const isInstalling = serverState === 'installing';
  const buttonText = installedVersion
    ? `Update to ${targetVersion}`
    : `Install Latest Stable (${targetVersion})`;

  function performInstall(): void {
    installMutation.mutate(
      {
        version: targetVersion,
        force: !!installedVersion,
      },
      {
        onSuccess: () => {
          toast.success(`Installing version ${targetVersion}`, {
            description: 'Server installation started.',
          });
        },
        onError: (error) => {
          toast.error('Installation failed', {
            description: error.message,
          });
        },
      }
    );
  }

  function handleClick(): void {
    if (isServerRunning) {
      setShowConfirmDialog(true);
    } else {
      performInstall();
    }
  }

  function handleConfirm(): void {
    setShowConfirmDialog(false);
    performInstall();
  }

  return (
    <>
      <Button
        size="lg"
        onClick={handleClick}
        disabled={installMutation.isPending || isInstalling || showConfirmDialog}
        data-testid="quick-install-button"
        className={cn('mb-6', className)}
      >
        {installMutation.isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Installing...
          </>
        ) : (
          <>
            <Download className="mr-2 h-4 w-4" />
            {buttonText}
          </>
        )}
      </Button>

      {/* Confirmation dialog when server is running */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent data-testid="quick-install-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Server Currently Running
            </AlertDialogTitle>
            <AlertDialogDescription>
              The server is currently running and will be stopped to install version{' '}
              <span className="font-semibold">{targetVersion}</span>. Any connected
              players will be disconnected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="confirm-dialog-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} data-testid="confirm-dialog-proceed">
              Stop Server &amp; Update
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
