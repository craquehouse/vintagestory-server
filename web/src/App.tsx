import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, Link } from "react-router";
import { ServerOff, Loader2 } from "lucide-react";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { PreferencesProvider } from "@/contexts/PreferencesContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { ModsPage, InstalledTab, BrowseTab, ModDetailPage } from "@/features/mods";
import { VersionPage, SettingsPage as GameServerSettingsPage, ConsolePage } from "@/features/game-server";
import { SettingsPage } from "@/features/settings";
import { useServerStatus } from "@/hooks/use-server-status";
import { isServerInstalled } from "@/lib/server-utils";

/**
 * Placeholder component for Game Server sub-pages.
 * Will be replaced with actual implementations in future stories.
 */
function GameServerLayout() {
  return (
    <div className="h-full" data-testid="game-server-layout">
      <Outlet />
    </div>
  );
}


/**
 * Redirect component for legacy /mods routes.
 * Story 11.4: Redirects old /mods/* paths to /game-server/mods/*
 * Preserves the path portion after /mods (e.g., /mods/browse/slug → /game-server/mods/browse/slug)
 */
function ModsRedirect() {
  const location = useLocation();
  const newPath = location.pathname.replace(/^\/mods/, '/game-server/mods');
  return <Navigate to={newPath} replace />;
}

/**
 * Wrapper for Mods page that shows empty state when server is not installed.
 * Story 11.4: AC4 - Show message when server not installed, disable compatibility checking.
 */
function GameServerModsPage() {
  const { data: statusResponse, isLoading } = useServerStatus();
  const serverStatus = statusResponse?.data;
  const serverState = serverStatus?.state ?? 'not_installed';
  const isInstalled = isServerInstalled(serverState);
  const isInstalling = serverState === 'installing';

  // Loading state - show placeholder while checking server status
  if (isLoading) {
    return (
      <div className="p-4" data-testid="mods-page-loading">
        <h1 className="text-2xl font-bold">Mods</h1>
        <p className="text-muted-foreground mt-4">Loading server status...</p>
      </div>
    );
  }

  // Server not installed - show empty state
  if (!isInstalled) {
    return (
      <div className="p-4" data-testid="mods-page-empty">
        <h1 className="text-2xl font-bold mb-6">Mods</h1>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          {isInstalling ? (
            <>
              <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
              <p className="text-lg font-medium">Installation in Progress</p>
              <p className="text-muted-foreground mb-4">
                Mod management will be available once installation completes.
              </p>
              <Link to="/game-server/version">
                <Button variant="outline">View Installation Progress</Button>
              </Link>
            </>
          ) : (
            <>
              <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">Server Not Installed</p>
              <p className="text-muted-foreground mb-4">
                Install a VintageStory server to manage mods.
                Compatibility checking requires a server version to compare against.
              </p>
              <Link to="/game-server/version">
                <Button variant="default">Go to Installation</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    );
  }

  // Server installed - show ModsPage with nested routes
  return <ModsPage />;
}

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              {/* Game Server nested routes - Story 11.6: Default to /version (Installation page) */}
              <Route path="/game-server" element={<GameServerLayout />}>
                <Route index element={<Navigate to="version" replace />} />
                <Route path="version" element={<VersionPage />} />
                <Route path="settings" element={<GameServerSettingsPage />} />
                {/* Mods routes - moved from top-level /mods (Story 11.4) */}
                {/* GameServerModsPage checks server status and shows empty state if not installed */}
                <Route path="mods" element={<GameServerModsPage />}>
                  <Route index element={<Navigate to="installed" replace />} />
                  <Route path="installed" element={<InstalledTab />} />
                  <Route path="browse" element={<BrowseTab />} />
                  <Route path="browse/:slug" element={<ModDetailPage />} />
                </Route>
                <Route path="console" element={<ConsolePage />} />
              </Route>
              <Route path="/config" element={<SettingsPage />} />
              {/* Story 11.4: Redirect legacy /mods/* routes to /game-server/mods/* */}
              <Route path="/mods/*" element={<ModsRedirect />} />
            </Routes>
          </Layout>
        </BrowserRouter>
        <Toaster />
        </SidebarProvider>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

export default App;
