/**
 * ModTable - Table displaying installed mods with management actions.
 *
 * Features:
 * - Displays mod name, version, compatibility status
 * - Enable/disable toggle with optimistic updates
 * - Remove button with confirmation dialog
 * - Empty state when no mods installed
 */

import { useState } from 'react';
import { Trash2, Loader2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
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
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { useMods, useEnableMod, useDisableMod, useRemoveMod } from '@/hooks/use-mods';
import type { ModInfo, CompatibilityStatus } from '@/api/types';

interface ModTableProps {
  /** Callback when a mod is successfully removed */
  onRemoved?: (slug: string) => void;
  /** Callback when a mod's enabled state changes */
  onToggled?: (slug: string, enabled: boolean) => void;
}

/**
 * Table displaying installed mods with enable/disable toggles and remove actions.
 *
 * @example
 * <ModTable
 *   onRemoved={(slug) => toast.success(`Removed ${slug}`)}
 *   onToggled={(slug, enabled) => toast.success(`${slug} ${enabled ? 'enabled' : 'disabled'}`)}
 * />
 */
export function ModTable({ onRemoved, onToggled }: ModTableProps) {
  const [modToRemove, setModToRemove] = useState<ModInfo | null>(null);

  const { data: modsData, isLoading } = useMods();
  const { mutate: enableMod, isPending: isEnabling, variables: enablingSlug } = useEnableMod();
  const { mutate: disableMod, isPending: isDisabling, variables: disablingSlug } = useDisableMod();
  const { mutate: removeModMutation, isPending: isRemoving } = useRemoveMod();

  const mods = modsData?.data?.mods ?? [];

  const handleToggle = (mod: ModInfo) => {
    if (mod.enabled) {
      disableMod(mod.slug, {
        onSuccess: () => {
          onToggled?.(mod.slug, false);
        },
      });
    } else {
      enableMod(mod.slug, {
        onSuccess: () => {
          onToggled?.(mod.slug, true);
        },
      });
    }
  };

  const handleRemoveClick = (mod: ModInfo) => {
    setModToRemove(mod);
  };

  const handleRemoveConfirm = () => {
    if (!modToRemove) return;

    removeModMutation(modToRemove.slug, {
      onSuccess: () => {
        onRemoved?.(modToRemove.slug);
        setModToRemove(null);
      },
      onError: () => {
        setModToRemove(null);
      },
    });
  };

  const handleRemoveCancel = () => {
    setModToRemove(null);
  };

  // Determine compatibility status for display
  // Since installed mods don't have full compatibility info, we show "not_verified"
  // unless we have that data from the server in the future
  const getCompatibilityStatus = (_mod: ModInfo): CompatibilityStatus => {
    // For now, installed mods show as "not_verified" since we don't have
    // real-time compatibility checking for already-installed mods
    return 'not_verified';
  };

  const isTogglingMod = (slug: string) => {
    return (
      (isEnabling && enablingSlug === slug) ||
      (isDisabling && disablingSlug === slug)
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8" data-testid="mod-table-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (mods.length === 0) {
    return (
      <div
        className="text-center py-8 text-muted-foreground"
        data-testid="mod-table-empty"
      >
        No mods installed yet
      </div>
    );
  }

  return (
    <>
      <Table data-testid="mod-table">
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Version</TableHead>
            <TableHead>Compatibility</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[80px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mods.map((mod) => (
            <TableRow key={mod.slug} data-testid={`mod-row-${mod.slug}`}>
              <TableCell>
                <div>
                  <div className="font-medium">{mod.name || mod.slug}</div>
                  {mod.name && (
                    <div className="text-sm text-muted-foreground">{mod.slug}</div>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <span className="text-muted-foreground">v{mod.version}</span>
              </TableCell>
              <TableCell>
                <CompatibilityBadge status={getCompatibilityStatus(mod)} />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={mod.enabled}
                    onCheckedChange={() => handleToggle(mod)}
                    disabled={isTogglingMod(mod.slug)}
                    data-testid={`mod-toggle-${mod.slug}`}
                    aria-label={mod.enabled ? 'Disable mod' : 'Enable mod'}
                  />
                  {isTogglingMod(mod.slug) && (
                    <Loader2
                      className="h-4 w-4 animate-spin text-muted-foreground"
                      data-testid={`mod-toggle-spinner-${mod.slug}`}
                    />
                  )}
                </div>
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveClick(mod)}
                  data-testid={`mod-remove-${mod.slug}`}
                  aria-label={`Remove ${mod.name || mod.slug}`}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Remove confirmation dialog */}
      <AlertDialog
        open={!!modToRemove}
        onOpenChange={(open) => !open && handleRemoveCancel()}
      >
        <AlertDialogContent data-testid="remove-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {modToRemove?.name || modToRemove?.slug}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the mod from your server. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={handleRemoveCancel}
              data-testid="remove-dialog-cancel"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemoveConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="remove-dialog-confirm"
            >
              {isRemoving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Removing...
                </>
              ) : (
                'Remove'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
