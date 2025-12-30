/**
 * ModList - Main page for mod management.
 *
 * Features:
 * - ModLookupInput for searching and installing new mods
 * - ModTable displaying installed mods with management actions
 * - Toast notifications for install/enable/disable/remove results
 */

import { toast } from 'sonner';
import { ModLookupInput } from '@/components/ModLookupInput';
import { ModTable } from '@/components/ModTable';

/**
 * Mod management page component.
 *
 * Provides a complete interface for managing VintageStory mods:
 * - Search for mods by slug or URL
 * - View mod details and compatibility status
 * - Install new mods
 * - Enable/disable installed mods
 * - Remove installed mods
 *
 * @example
 * <ModList />
 */
export function ModList() {
  const handleInstalled = (mod: { slug: string; version: string }) => {
    toast.success(`Installed ${mod.slug} v${mod.version}`, {
      description: 'A server restart may be required for changes to take effect.',
    });
  };

  const handleToggled = (slug: string, enabled: boolean) => {
    toast.success(`${slug} ${enabled ? 'enabled' : 'disabled'}`, {
      description: 'A server restart is required for changes to take effect.',
    });
  };

  const handleRemoved = (slug: string) => {
    toast.success(`Removed ${slug}`, {
      description: 'A server restart may be required for changes to take effect.',
    });
  };

  return (
    <div className="space-y-6" data-testid="mod-list-page">
      {/* Page heading */}
      <div>
        <h1 className="text-2xl font-bold">Mods</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search, install, and manage server mods
        </p>
      </div>

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
