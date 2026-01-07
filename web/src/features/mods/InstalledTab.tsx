/**
 * InstalledTab - Tab content for managing installed mods.
 *
 * This component was extracted from ModList as part of Story 10.2.
 * It contains the existing mod management functionality:
 * - ModLookupInput for searching and installing new mods
 * - ModTable displaying installed mods with management actions
 * - Toast notifications for install/enable/disable/remove results
 *
 * Story 10.2: Mods Tab Restructure - AC2
 */

import { toast } from 'sonner';
import { ModLookupInput } from '@/components/ModLookupInput';
import { ModTable } from '@/components/ModTable';
import { useServerStatus } from '@/hooks/use-server-status';

/**
 * Installed mods tab content.
 *
 * Provides a complete interface for managing VintageStory mods:
 * - Search for mods by slug or URL
 * - View mod details and compatibility status
 * - Install new mods
 * - Enable/disable installed mods
 * - Remove installed mods
 */
export function InstalledTab() {
  const { data: statusData } = useServerStatus();
  const isServerRunning = statusData?.data?.state === 'running';

  const handleInstalled = (mod: { slug: string; version: string }) => {
    toast.success(`Installed ${mod.slug} v${mod.version}`, {
      description: isServerRunning
        ? 'A server restart may be required for changes to take effect.'
        : undefined,
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
    <div className="space-y-6" data-testid="installed-tab-content">
      {/* Mod lookup and install */}
      <div className="max-w-xl">
        <ModLookupInput onInstalled={handleInstalled} />
      </div>

      {/* Installed mods table */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Installed Mods</h2>
        <ModTable onToggled={handleToggled} onRemoved={handleRemoved} />
      </div>
    </div>
  );
}
