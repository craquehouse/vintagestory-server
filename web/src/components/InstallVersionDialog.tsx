/**
 * InstallVersionDialog - Confirmation dialog for server version installation.
 *
 * Story 13.4: Provides a confirmation step before installing, upgrading,
 * reinstalling, or downgrading the VintageStory server version.
 *
 * Features:
 * - Shows version info and action type (install/upgrade/reinstall/downgrade)
 * - Displays version comparison (current → new) when server is installed
 * - Shows server-running warning when server is running
 * - Shows downgrade warning with confirmation checkbox
 * - Displays installation progress when installing
 */

import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Download, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useInstallServer, useInstallStatus } from '@/hooks/use-server-status';
import type { VersionInfo, ServerState, InstallStatus } from '@/api/types';

/**
 * Props for the InstallVersionDialog component.
 */
export interface InstallVersionDialogProps {
  /** Version to install */
  version: VersionInfo;
  /** Currently installed version (null if not installed) */
  installedVersion: string | null;
  /** Current server state */
  serverState: ServerState;
  /** Dialog open state */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when install succeeds */
  onSuccess?: () => void;
}

/**
 * Action type for version installation.
 */
export type ActionType = 'install' | 'upgrade' | 'reinstall' | 'downgrade';

/**
 * Determines the action type based on target and installed versions.
 *
 * @param targetVersion - Version to install
 * @param installedVersion - Currently installed version (null if not installed)
 * @returns The action type
 */
export function getActionType(
  targetVersion: string,
  installedVersion: string | null
): ActionType {
  if (!installedVersion) return 'install';
  if (targetVersion === installedVersion) return 'reinstall';
  // Simple string comparison works for VintageStory versions
  // because they follow semantic-like patterns (e.g., "1.21.6", "1.20.0-pre.1")
  return targetVersion > installedVersion ? 'upgrade' : 'downgrade';
}

/**
 * Returns display info for each action type.
 */
function getActionDisplay(actionType: ActionType): {
  title: string;
  buttonText: string;
  buttonVariant: 'default' | 'outline' | 'destructive';
} {
  switch (actionType) {
    case 'install':
      return {
        title: 'Install Server Version',
        buttonText: 'Install',
        buttonVariant: 'default',
      };
    case 'upgrade':
      return {
        title: 'Upgrade Server Version',
        buttonText: 'Upgrade',
        buttonVariant: 'default',
      };
    case 'reinstall':
      return {
        title: 'Reinstall Server Version',
        buttonText: 'Reinstall',
        buttonVariant: 'outline',
      };
    case 'downgrade':
      return {
        title: 'Downgrade Server Version',
        buttonText: 'Downgrade',
        buttonVariant: 'destructive',
      };
  }
}

/**
 * Installation progress display component.
 */
function InstallProgress({ status }: { status: InstallStatus }) {
  return (
    <div
      className="space-y-3"
      role="status"
      aria-label="Installation progress"
      data-testid="install-progress"
    >
      <div className="flex items-center justify-between text-sm">
        <span className="capitalize text-muted-foreground">
          {status.state.replace(/_/g, ' ')}
        </span>
        <span className="font-medium">{status.progress}%</span>
      </div>
      <Progress value={status.progress} />
      {status.message && (
        <p className="text-xs text-muted-foreground">{status.message}</p>
      )}
    </div>
  );
}

/**
 * Confirmation dialog for version installation.
 *
 * Shows version info, warnings, and handles the install via useInstallServer hook.
 *
 * @example
 * <InstallVersionDialog
 *   version={selectedVersion}
 *   installedVersion={serverStatus?.version ?? null}
 *   serverState={serverState}
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   onSuccess={() => console.log('Installed!')}
 * />
 */
export function InstallVersionDialog({
  version,
  installedVersion,
  serverState,
  open,
  onOpenChange,
  onSuccess,
}: InstallVersionDialogProps) {
  const [downgradeConfirmed, setDowngradeConfirmed] = useState(false);

  const installMutation = useInstallServer();
  const isInstalling = serverState === 'installing';
  const { data: installStatusResponse } = useInstallStatus(isInstalling);
  const installStatus = installStatusResponse?.data;

  const actionType = getActionType(version.version, installedVersion);
  const { title, buttonText, buttonVariant } = getActionDisplay(actionType);

  const isServerRunning = serverState === 'running';
  const isDowngrade = actionType === 'downgrade';

  // Track previous server state to detect installation completion
  const prevServerStateRef = useRef<ServerState | undefined>(undefined);

  // Auto-close dialog when installation completes (installing → installed)
  useEffect(() => {
    const prevState = prevServerStateRef.current;
    if (prevState === 'installing' && serverState === 'installed' && open) {
      onOpenChange(false);
    }
    prevServerStateRef.current = serverState;
  }, [serverState, open, onOpenChange]);

  // Button disabled if:
  // - Mutation is pending
  // - Installation is in progress
  // - Downgrade not confirmed
  const isInstallDisabled =
    installMutation.isPending ||
    isInstalling ||
    (isDowngrade && !downgradeConfirmed);

  const handleInstall = () => {
    const needsForce = actionType !== 'install';
    installMutation.mutate(
      { version: version.version, force: needsForce },
      {
        onSuccess: () => {
          toast.success(
            actionType === 'install'
              ? `Installing version ${version.version}`
              : `Updating to version ${version.version}`,
            {
              description: 'Server installation started.',
            }
          );
          // Don't close dialog immediately - show progress
          // Dialog will be closed when user dismisses or installation completes
          onSuccess?.();
        },
        onError: (error) => {
          toast.error('Installation failed', {
            description: error.message,
          });
        },
      }
    );
  };

  // Reset downgrade confirmation when dialog closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setDowngradeConfirmed(false);
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent data-testid="install-version-dialog">
        <DialogHeader>
          <DialogTitle data-testid="dialog-title">{title}</DialogTitle>
          <DialogDescription>
            {isInstalling
              ? 'Installation in progress...'
              : 'Confirm the server version change.'}
          </DialogDescription>
        </DialogHeader>

        {isInstalling && installStatus ? (
          <InstallProgress status={installStatus} />
        ) : (
          <>
            {/* Version Comparison Section */}
            <div
              className="py-4 space-y-3"
              data-testid="version-comparison-section"
            >
              {installedVersion ? (
                <div className="flex items-center gap-2" data-testid="version-comparison">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Current</p>
                    <p className="text-lg font-semibold" data-testid="current-version">
                      {installedVersion}
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">New</p>
                    <p className="text-lg font-semibold" data-testid="new-version">
                      {version.version}
                    </p>
                  </div>
                </div>
              ) : (
                <div data-testid="single-version">
                  <p className="text-sm text-muted-foreground">Version</p>
                  <p className="text-2xl font-bold" data-testid="target-version">
                    {version.version}
                  </p>
                </div>
              )}

              {/* Version Details */}
              <div className="text-sm text-muted-foreground space-y-1" data-testid="version-details">
                <p>
                  <span className="font-medium">Channel:</span>{' '}
                  <span className="capitalize">{version.channel}</span>
                </p>
                <p>
                  <span className="font-medium">File Size:</span> {version.filesize}
                </p>
              </div>
            </div>

            {/* Server Running Warning */}
            {isServerRunning && (
              <div
                className="flex items-start gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/20 p-3"
                data-testid="server-running-warning"
              >
                <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-yellow-500">
                  The server is currently running and will be stopped during installation.
                </p>
              </div>
            )}

            {/* Downgrade Warning */}
            {isDowngrade && (
              <div
                className="space-y-3 rounded-md bg-destructive/10 border border-destructive/20 p-3"
                data-testid="downgrade-warning"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-destructive">
                      Warning: Downgrading Server Version
                    </p>
                    <p className="text-sm text-destructive/80">
                      Downgrading may cause world corruption or data loss. Make sure you
                      have backups before proceeding.
                    </p>
                  </div>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={downgradeConfirmed}
                    onChange={(e) => setDowngradeConfirmed(e.target.checked)}
                    className="h-4 w-4 rounded border-destructive/50 text-destructive focus:ring-destructive"
                    data-testid="downgrade-checkbox"
                  />
                  <span className="text-sm text-destructive">
                    I understand the risks of downgrading
                  </span>
                </label>
              </div>
            )}
          </>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={installMutation.isPending}
            data-testid="cancel-button"
          >
            {isInstalling ? 'Close' : 'Cancel'}
          </Button>
          {!isInstalling && (
            <Button
              variant={buttonVariant}
              onClick={handleInstall}
              disabled={isInstallDisabled}
              className="gap-2"
              data-testid="confirm-button"
            >
              <Download
                className={`h-4 w-4 ${installMutation.isPending ? 'animate-spin' : ''}`}
              />
              {installMutation.isPending ? 'Starting...' : buttonText}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
