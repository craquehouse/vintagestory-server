/**
 * InstallConfirmDialog - Confirmation dialog for mod installation.
 *
 * Story 10.8: Provides a confirmation step before installing mods,
 * displaying compatibility status and warnings for non-verified or
 * incompatible mods.
 *
 * Features:
 * - Shows mod name, version, and compatibility status
 * - Displays warning message for not_verified/incompatible mods
 * - Handles install with loading state
 * - Calls onSuccess/onError callbacks appropriately
 */

import { AlertTriangle, Download, Package } from 'lucide-react';
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
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { useInstallMod } from '@/hooks/use-mods';
import type { CompatibilityStatus } from '@/api/types';

/**
 * Props for the InstallConfirmDialog component.
 */
export interface InstallConfirmDialogProps {
  /** Mod to install */
  mod: {
    slug: string;
    name: string;
    version: string;
    logoUrl?: string | null;
    author?: string;
  };
  /** Compatibility status for warning display */
  compatibility: {
    status: CompatibilityStatus;
    message?: string;
  };
  /** Whether dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when install succeeds */
  onSuccess?: () => void;
  /** Callback when install fails */
  onError?: (error: Error) => void;
}

/**
 * Returns warning message based on compatibility status.
 * No warning for compatible mods.
 */
function getCompatibilityWarning(status: CompatibilityStatus): string | null {
  switch (status) {
    case 'not_verified':
      return 'This mod has not been verified for your game server version. Installation may cause issues.';
    case 'incompatible':
      return 'This mod is known to be incompatible with your game server version. Installation may break your server.';
    case 'compatible':
    default:
      return null;
  }
}

/**
 * Confirmation dialog for mod installation.
 *
 * Shows mod info, compatibility badge, and warning message if applicable.
 * Handles the actual install via useInstallMod hook.
 *
 * @example
 * <InstallConfirmDialog
 *   mod={{ slug: 'carrycapacity', name: 'Carry Capacity', version: '1.0.0' }}
 *   compatibility={{ status: 'compatible' }}
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   onSuccess={() => console.log('Installed!')}
 * />
 */
export function InstallConfirmDialog({
  mod,
  compatibility,
  open,
  onOpenChange,
  onSuccess,
  onError,
}: InstallConfirmDialogProps) {
  const { mutate: install, isPending } = useInstallMod();

  const warningMessage = getCompatibilityWarning(compatibility.status);

  const handleInstall = () => {
    install(
      { slug: mod.slug, version: mod.version },
      {
        onSuccess: () => {
          toast.success(`Installed ${mod.name}`, {
            description: `Version ${mod.version} installed successfully.`,
          });
          onOpenChange(false);
          onSuccess?.();
        },
        onError: (error) => {
          toast.error('Installation failed', {
            description: error.message,
          });
          onError?.(error);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="install-confirm-dialog">
        <DialogHeader>
          <DialogTitle>Install Mod</DialogTitle>
          <DialogDescription>
            Confirm installation of this mod to your server.
          </DialogDescription>
        </DialogHeader>

        {/* Mod info section */}
        <div className="flex items-start gap-4 py-4" data-testid="install-dialog-mod-info">
          {/* Logo/placeholder */}
          <div className="h-16 w-16 rounded-lg bg-muted flex items-center justify-center overflow-hidden flex-shrink-0">
            {mod.logoUrl ? (
              <img
                src={mod.logoUrl}
                alt={`${mod.name} logo`}
                className="h-full w-full object-cover"
                data-testid="install-dialog-logo"
              />
            ) : (
              <Package
                className="h-8 w-8 text-muted-foreground"
                data-testid="install-dialog-placeholder"
              />
            )}
          </div>

          {/* Mod details */}
          <div className="flex-1 space-y-1">
            <h3 className="font-semibold" data-testid="install-dialog-mod-name">
              {mod.name}
            </h3>
            {mod.author && (
              <p
                className="text-sm text-muted-foreground"
                data-testid="install-dialog-mod-author"
              >
                by {mod.author}
              </p>
            )}
            <p
              className="text-sm text-muted-foreground"
              data-testid="install-dialog-mod-version"
            >
              Version: {mod.version}
            </p>
          </div>
        </div>

        {/* Compatibility badge */}
        <div className="flex items-center gap-2" data-testid="install-dialog-compatibility">
          <CompatibilityBadge
            status={compatibility.status}
            message={compatibility.message}
          />
        </div>

        {/* Warning message for not_verified/incompatible */}
        {warningMessage && (
          <div
            className="flex items-start gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/20 p-3"
            data-testid="install-dialog-warning"
          >
            <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-yellow-500">{warningMessage}</p>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
            data-testid="install-dialog-cancel"
          >
            Cancel
          </Button>
          <Button
            onClick={handleInstall}
            disabled={isPending}
            className="gap-2"
            data-testid="install-dialog-confirm"
          >
            <Download className={`h-4 w-4 ${isPending ? 'animate-spin' : ''}`} />
            {isPending ? 'Installing...' : 'Install'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
