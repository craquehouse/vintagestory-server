/**
 * InstalledTab - Tab content for managing installed mods.
 *
 * This component was extracted from ModList as part of Story 10.2.
 * It displays installed mods with management actions (enable/disable/remove).
 *
 * VSS-195: Removed ModLookupInput - mod discovery is now in BrowseTab.
 *
 * Story 10.2: Mods Tab Restructure - AC2
 */

import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';
import { Loader2, RefreshCw, ArrowUpCircle, FolderSearch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ModTable } from '@/components/ModTable';
import { UpdateAllDialog } from '@/components/UpdateAllDialog';
import { UnusedFilesNotice } from '@/components/UnusedFilesNotice';
import { InstalledModsFilterBar } from '@/components/InstalledModsFilterBar';
import {
  EMPTY_FILTERS,
  filtersFromSearchParams,
  filtersToSearchParams,
  hasFilters,
  type InstalledModsFilters,
} from '@/lib/installed-mods-filters';
import { useIsAdmin } from '@/api/hooks/use-auth-me';
import { useServerStatus } from '@/hooks/use-server-status';
import { useCheckModUpdates, useModUpdates, useMods, useRescanMods } from '@/hooks/use-mods';

/**
 * Installed mods tab content.
 *
 * Provides an interface for managing installed VintageStory mods:
 * - Enable/disable installed mods
 * - Remove installed mods
 * - Check for and apply updates (Story 14.3), or all compatible updates (Story 14.4)
 * - Rescan the mods folder and see files it does not use, Admin only (Story 24.6)
 * - Filter by name, compatibility and available update, kept in the URL (Story 24.7)
 *
 * For discovering and installing new mods, use the Browse tab.
 */
export function InstalledTab() {
  const { data: statusData } = useServerStatus();
  const isServerRunning = statusData?.data?.state === 'running';
  const { data: updatesData } = useModUpdates();
  const { mutate: checkUpdates, isPending: isChecking } = useCheckModUpdates();
  const { mutate: rescan, isPending: isRescanning } = useRescanMods();
  const { isAdmin } = useIsAdmin();
  const { data: modsData } = useMods();
  const installedCount = modsData?.data?.mods.length ?? 0;

  // Story 24.7 (Epic 24 ADR-6): the filters live in the URL. Typing replaces the history
  // entry; the select and the switch push one, so Back restores the previous filter.
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(() => filtersFromSearchParams(searchParams), [searchParams]);
  // The change is applied to the URL as it is when the update runs, not to this render's
  // `filters`, so two changes in one batch both survive (Story 24.7 review)
  const setFilters = useCallback(
    (change: Partial<InstalledModsFilters>, replace: boolean) => {
      setSearchParams(
        (current) =>
          filtersToSearchParams({ ...filtersFromSearchParams(current), ...change }, current),
        { replace }
      );
    },
    [setSearchParams]
  );
  const lastChecked = updatesData?.data?.checkedAt;
  const [updateAllOpen, setUpdateAllOpen] = useState(false);
  const offeredUpdates = (updatesData?.data?.mods ?? []).filter(
    (item) => item.status === 'update_available'
  );
  const compatibleCount = offeredUpdates.filter(
    (item) => item.offeredCompatibility === 'compatible'
  ).length;

  const handleCheck = () => {
    checkUpdates(undefined, {
      onSuccess: (response) => {
        const { check, updateCount } = response.data;
        const available =
          updateCount === 0
            ? 'All mods are up to date.'
            : `${updateCount} update${updateCount === 1 ? '' : 's'} available.`;
        if (check.failed > 0) {
          toast.warning(`Checked ${check.checked} mods; ${check.failed} could not be checked`, {
            description: `${check.failedSlugs.join(', ')}. ${available}`,
          });
        } else {
          toast.success(`Checked ${check.checked} mods`, { description: available });
        }
      },
      onError: (error) => {
        toast.error('Update check failed', { description: error.message });
      },
    });
  };

  const handleRescan = () => {
    rescan(undefined, {
      onSuccess: (response) => {
        const { added, removed, skipped, pendingRestart } = response.data;
        const summary = `${added} added, ${removed} removed, ${skipped} skipped.`;
        toast.success('Rescanned the mods folder', {
          description: pendingRestart
            ? `${summary} A server restart is required for the changes to take effect.`
            : summary,
        });
      },
      onError: (error) => {
        toast.error('Rescan failed', { description: error.message });
      },
    });
  };

  const handleToggled = (slug: string, enabled: boolean) => {
    toast.success(`${slug} ${enabled ? 'enabled' : 'disabled'}`, {
      description: isServerRunning
        ? 'A server restart is required for changes to take effect.'
        : undefined,
    });
  };

  const handleRemoved = (slug: string) => {
    toast.success(`Removed ${slug}`, {
      description: isServerRunning
        ? 'A server restart may be required for changes to take effect.'
        : undefined,
    });
  };

  return (
    <div className="space-y-4" data-testid="installed-tab-content">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Installed Mods</h2>
        {/* Story 16.5: wraps on phones instead of widening the page */}
        {/* Story 17.8: the buttons are 44px tall up to lg, like the cards */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-muted-foreground" data-testid="mod-updates-last-checked">
            {lastChecked
              ? `Last checked ${new Date(lastChecked).toLocaleString()}`
              : 'Not checked yet'}
          </span>
          {compatibleCount > 0 && (
            <Button
              size="sm"
              className="max-lg:h-11"
              onClick={() => setUpdateAllOpen(true)}
              data-testid="mod-updates-update-all"
            >
              <ArrowUpCircle className="mr-2 h-4 w-4" />
              Update all ({compatibleCount})
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="max-lg:h-11"
            onClick={handleCheck}
            disabled={isChecking}
            data-testid="mod-updates-check"
          >
            {isChecking ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Check for updates
          </Button>
          {isAdmin && (
            <Button
              variant="outline"
              size="sm"
              className="max-lg:h-11"
              onClick={handleRescan}
              disabled={isRescanning}
              title="Pick up mods copied into the mods folder by hand"
              data-testid="mods-rescan"
            >
              {isRescanning ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <FolderSearch className="mr-2 h-4 w-4" />
              )}
              Rescan
            </Button>
          )}
        </div>
      </div>
      <UnusedFilesNotice />
      {(installedCount > 0 || hasFilters(filters)) && (
        <InstalledModsFilterBar
          value={filters}
          onQueryChange={(query) => setFilters({ query }, true)}
          onCompatChange={(compat) => setFilters({ compat }, false)}
          onUpdatesChange={(updates) => setFilters({ updates }, false)}
        />
      )}
      <ModTable
        onToggled={handleToggled}
        onRemoved={handleRemoved}
        filters={filters}
        onClearFilters={() => setFilters(EMPTY_FILTERS, false)}
      />
      <UpdateAllDialog
        open={updateAllOpen}
        onOpenChange={setUpdateAllOpen}
        updates={offeredUpdates}
        gameVersion={updatesData?.data?.gameVersion ?? null}
      />
    </div>
  );
}
