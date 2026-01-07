/**
 * ModsPage - Tab container for mod management with URL-synced navigation.
 *
 * Features:
 * - Two tabs: Installed (existing mod management) and Browse (discovery)
 * - URL reflects active tab for bookmarkability
 * - Browser history navigation works correctly
 *
 * Story 10.2: Mods Tab Restructure - AC1, AC4
 */

import { useLocation, useNavigate, Outlet } from 'react-router';
import { Package, Search } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

/**
 * Extract the active tab from the current URL path.
 * /mods/installed → "installed"
 * /mods/browse → "browse"
 * /mods → "installed" (fallback)
 */
function getActiveTab(pathname: string): string {
  const segments = pathname.split('/');
  const lastSegment = segments[segments.length - 1];
  if (lastSegment === 'browse') return 'browse';
  return 'installed';
}

/**
 * Mods page with tabbed navigation.
 *
 * Displays two tabs:
 * - Installed: Existing mod management (ModLookupInput, ModTable)
 * - Browse: Mod discovery interface (placeholder for Stories 10.3+)
 *
 * The active tab is synced with the URL for direct linking and history navigation.
 */
export function ModsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = getActiveTab(location.pathname);

  const handleTabChange = (value: string) => {
    navigate(`/mods/${value}`);
  };

  return (
    <div
      className="flex h-full flex-col gap-4"
      data-testid="mods-page"
      aria-label="Mods page"
    >
      {/* Page heading */}
      <div>
        <h1 className="text-2xl font-bold">Mods</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage installed mods or discover new ones
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col">
        <TabsList>
          <TabsTrigger value="installed" data-testid="installed-tab">
            <Package className="h-4 w-4" />
            Installed
          </TabsTrigger>
          <TabsTrigger value="browse" data-testid="browse-tab">
            <Search className="h-4 w-4" />
            Browse
          </TabsTrigger>
        </TabsList>

        {/* Tab content rendered via nested route Outlet */}
        <div className="flex-1 mt-4">
          <Outlet />
        </div>
      </Tabs>
    </div>
  );
}
