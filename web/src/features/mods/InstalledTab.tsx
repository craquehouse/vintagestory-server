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

import { toast } from 'sonner';
import { ModTable } from '@/components/ModTable';
import { useServerStatus } from '@/hooks/use-server-status';

/**
 * Installed mods tab content.
 *
 * Provides an interface for managing installed VintageStory mods:
 * - Enable/disable installed mods
 * - Remove installed mods
 *
 * For discovering and installing new mods, use the Browse tab.
 */
export function InstalledTab() {
  const { data: statusData } = useServerStatus();
  const isServerRunning = statusData?.data?.state === 'running';

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
      <h2 className="text-lg font-semibold">Installed Mods</h2>
      <ModTable onToggled={handleToggled} onRemoved={handleRemoved} />
    </div>
  );
}
