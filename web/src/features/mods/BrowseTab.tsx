/**
 * BrowseTab - Placeholder tab for mod discovery.
 *
 * This is a placeholder component for the Browse tab.
 * Full functionality will be implemented in Stories 10.3-10.8.
 *
 * Story 10.2: Mods Tab Restructure - AC3
 */

import { Search } from 'lucide-react';

/**
 * Browse mods tab placeholder.
 *
 * Displays a "coming soon" message until mod discovery is implemented.
 * Stories 10.3-10.8 will add:
 * - Mod search functionality
 * - Filter and sort controls
 * - Mod cards with details
 * - Pagination
 * - Install integration
 */
export function BrowseTab() {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center"
      data-testid="browse-tab-content"
    >
      <Search className="h-12 w-12 text-muted-foreground mb-4" />
      <h2 className="text-lg font-semibold">Browse Mods</h2>
      <p className="mt-2 text-muted-foreground">
        Mod discovery coming soon in Stories 10.3-10.8
      </p>
    </div>
  );
}
