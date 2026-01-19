/**
 * ModLookupInput - Search input for looking up mods from the VintageStory mod database.
 *
 * Features:
 * - Accepts mod slugs or full URLs (smart parsing)
 * - Debounced lookup (300ms) to avoid excessive API calls
 * - Preview card with mod details when found
 * - Install button with loading state
 * - Confirmation dialog for incompatible mods
 */

import { useState } from 'react';
import { Loader2, Download, AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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
import { useDebounce } from '@/hooks/use-debounce';
import { useLookupMod, useInstallMod } from '@/hooks/use-mods';
import { extractSlug } from '@/lib/mod-utils';

interface ModLookupInputProps {
  /** Callback when a mod is successfully installed */
  onInstalled?: (mod: { slug: string; version: string }) => void;
}

/**
 * Search input with mod lookup and install functionality.
 *
 * @example
 * <ModLookupInput onInstalled={(mod) => toast.success(`Installed ${mod.slug}`)} />
 */
export function ModLookupInput({ onInstalled }: ModLookupInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  // Debounce the input value for API lookup
  const debouncedInput = useDebounce(inputValue, 300);
  const slug = extractSlug(debouncedInput);

  // Query for mod lookup
  const {
    data: lookupData,
    isLoading: isLookingUp,
    error: lookupError,
  } = useLookupMod(slug);

  // Mutation for installing
  const { mutate: installMod, isPending: isInstalling } = useInstallMod();

  const modData = lookupData?.data;
  const isIncompatible = modData?.compatibility.status === 'incompatible';

  const handleInstall = () => {
    if (!modData) return;

    // For incompatible mods, show confirmation dialog
    if (isIncompatible) {
      setShowConfirmDialog(true);
      return;
    }

    performInstall();
  };

  const performInstall = () => {
    if (!modData) return;

    installMod(
      { slug: modData.slug },
      {
        onSuccess: (response) => {
          // Clear the input after successful install
          setInputValue('');
          setShowConfirmDialog(false);
          onInstalled?.({
            slug: response.data.slug,
            version: response.data.version,
          });
        },
      }
    );
  };

  const handleDialogConfirm = () => {
    performInstall();
  };

  const handleDialogCancel = () => {
    setShowConfirmDialog(false);
  };

  // Determine what to show in the preview area
  const showPreview = slug && (modData || isLookingUp || lookupError);
  const showError = lookupError && !isLookingUp;

  return (
    <div className="space-y-4" data-testid="mod-lookup-input">
      {/* Search input */}
      <div className="relative">
        <Input
          type="text"
          placeholder="Enter mod slug or paste URL"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="pr-10"
          data-testid="mod-search-input"
        />
        {isLookingUp && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <Loader2
              className="h-4 w-4 animate-spin text-muted-foreground"
              data-testid="lookup-spinner"
            />
          </div>
        )}
      </div>

      {/* Preview card */}
      {showPreview && (
        <Card data-testid="mod-preview-card">
          {showError ? (
            <CardContent className="pt-6">
              <div
                className="text-sm text-destructive"
                data-testid="lookup-error"
              >
                Mod not found. Check the slug and try again.
              </div>
            </CardContent>
          ) : modData ? (
            <>
              <CardHeader className="pb-2">
                <div className="flex items-start gap-3">
                  {modData.logoUrl && (
                    <img
                      src={modData.logoUrl}
                      alt={`${modData.name} logo`}
                      className="h-16 w-16 rounded-md object-cover flex-shrink-0"
                      data-testid="mod-logo"
                    />
                  )}
                  <div className="flex items-start justify-between gap-4 flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="truncate">{modData.name}</CardTitle>
                      <CardDescription className="mt-1">
                        by {modData.author}
                      </CardDescription>
                    </div>
                    <CompatibilityBadge
                      status={modData.compatibility.status}
                      message={modData.compatibility.message}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Description */}
                {modData.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {modData.description}
                  </p>
                )}

                {/* Metadata row */}
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>v{modData.latestVersion}</span>
                  <span className="capitalize">
                    {modData.side.toLowerCase()}
                  </span>
                  <span>{modData.downloads.toLocaleString()} downloads</span>
                </div>

                {/* Install button */}
                <Button
                  onClick={handleInstall}
                  disabled={isInstalling}
                  className="w-full"
                  data-testid="install-button"
                >
                  {isInstalling ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Installing...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Install
                    </>
                  )}
                </Button>
              </CardContent>
            </>
          ) : null}
        </Card>
      )}

      {/* Incompatible mod confirmation dialog */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent data-testid="incompatible-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Install Incompatible Mod?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {modData?.compatibility.message ||
                'This mod may not be compatible with your server version.'}
              <br />
              <br />
              Installing an incompatible mod may cause issues or prevent the
              server from starting.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={handleDialogCancel}
              data-testid="dialog-cancel"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDialogConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="dialog-confirm"
            >
              {isInstalling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Installing...
                </>
              ) : (
                'Install Anyway'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
