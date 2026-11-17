/**
 * ModsPage - Tab container for mod management with URL-synced navigation.
 *
 * Features:
 * - Two tabs: Installed (existing mod management) and Browse (discovery)
 * - URL reflects active tab for bookmarkability
 * - Browser history navigation works correctly
 *
 * Story 10.2: Mods Tab Restructure - AC1, AC4
 * Story 16.1: The Browse tab returns to the last browse state
 * Story 17.7: Browse is the active tab on a mod detail page, and Installed opens the list from there;
 * a tab change adds one history entry
 */

import { useEffect, useRef } from 'react';
import { useLocation, useMatch, useNavigate, Outlet } from 'react-router';
import { Package, Search } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  BROWSE_PATH,
  MOD_DETAIL_RETURN_STATE,
  getLastBrowseSearch,
  readBrowseSearchState,
} from '@/lib/browse-search';

/**
 * Extract the active tab from the current URL path.
 * /game-server/mods/installed → "installed"
 * /game-server/mods/browse → "browse" (also with a trailing slash)
 * /game-server/mods/browse/:slug → "browse" (Story 17.7: a mod detail page)
 * /game-server/mods → "installed" (fallback)
 */
function getActiveTab(pathname: string): string {
  if (pathname === BROWSE_PATH || pathname.startsWith(`${BROWSE_PATH}/`)) return 'browse';
  return 'installed';
}

/**
 * Mods page with tabbed navigation.
 *
 * Displays two tabs:
 * - Installed: Existing mod management (ModTable)
 * - Browse: Mod discovery interface (placeholder for Stories 10.3+)
 *
 * The active tab is synced with the URL for direct linking and history navigation.
 */
export function ModsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = getActiveTab(location.pathname);
  // Story 17.7: an exact match, so the browse list with a trailing slash
  // (`/game-server/mods/browse/`, empty slug) is not a detail page
  const isDetailPage = useMatch(`${BROWSE_PATH}/:slug`) !== null;

  const openBrowse = () => {
    // Story 16.1: On a detail page opened from browse, return to the state it was
    // opened from; otherwise to the last browse state of this session, or the default.
    const openedFrom = isDetailPage ? readBrowseSearchState(location.state) : undefined;
    if (openedFrom !== undefined) {
      navigate(`${BROWSE_PATH}${openedFrom}`, { state: MOD_DETAIL_RETURN_STATE });
      return;
    }
    navigate(`${BROWSE_PATH}${getLastBrowseSearch() ?? ''}`);
  };

  // Story 17.7: Radix reports a mouse click twice in one mousedown (it focuses the
  // trigger, whose onFocus reports the value, then reports it itself), before the
  // navigation commits. Remember the tab requested since the last tab change and drop
  // the repeat, so a click adds one history entry.
  const requestedTabRef = useRef<string | null>(null);
  useEffect(() => {
    requestedTabRef.current = null;
  }, [activeTab]);

  const handleTabChange = (value: string) => {
    // Radix Tabs does not report the active value, but never push a duplicate entry
    if (value === activeTab || value === requestedTabRef.current) return;
    requestedTabRef.current = value;
    if (value === 'browse') {
      openBrowse();
      return;
    }
    navigate(`/game-server/mods/${value}`);
  };

  return (
    <div className="flex h-full flex-col gap-4" data-testid="mods-page" aria-label="Mods page">
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
          {/*
            Story 17.7: on a detail page Browse is already the active tab, so Radix never
            calls onValueChange('browse') there. The trigger is a native button, so onClick
            fires for a click and for Enter and Space; Radix's own call for the same value
            is dropped by the controlled state, so exactly one navigation happens. On the
            browse list there is no handler: the active tab stays inert.
          */}
          <TabsTrigger
            value="browse"
            data-testid="browse-tab"
            onClick={isDetailPage ? openBrowse : undefined}
          >
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
