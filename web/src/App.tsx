import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { PreferencesProvider } from "@/contexts/PreferencesContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { EmptyServerState } from "@/components/EmptyServerState";
import { useServerStatus } from "@/hooks/use-server-status";
import { isServerInstalled } from "@/lib/server-utils";

// Each page loads on demand, so a first visit doesn't download every page's dependencies.
// The mods views share one chunk so switching between their tabs doesn't show a fallback.
const loadMods = () => import("@/features/mods");
const ModsPage = lazy(() => loadMods().then((m) => ({ default: m.ModsPage })));
const InstalledTab = lazy(() => loadMods().then((m) => ({ default: m.InstalledTab })));
const BrowseTab = lazy(() => loadMods().then((m) => ({ default: m.BrowseTab })));
const ModDetailPage = lazy(() => loadMods().then((m) => ({ default: m.ModDetailPage })));
const Dashboard = lazy(() =>
  import("@/features/dashboard/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const VersionPage = lazy(() =>
  import("@/features/game-server/VersionPage").then((m) => ({ default: m.VersionPage })),
);
const GameServerSettingsPage = lazy(() =>
  import("@/features/game-server/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);
const ConsolePage = lazy(() =>
  import("@/features/game-server/ConsolePage").then((m) => ({ default: m.ConsolePage })),
);
const SettingsPage = lazy(() =>
  import("@/features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

function PageLoading() {
  return (
    <p className="p-4 text-muted-foreground" role="status" data-testid="page-loading">
      Loading...
    </p>
  );
}

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

  if (isLoading) {
    return (
      <div className="p-4" data-testid="mods-page-loading">
        <h1 className="text-2xl font-bold">Mods</h1>
        <p className="text-muted-foreground mt-4">Loading server status...</p>
      </div>
    );
  }

  if (!isInstalled) {
    return (
      <div className="p-4" data-testid="mods-page-empty">
        <h1 className="text-2xl font-bold mb-6">Mods</h1>
        <EmptyServerState
          isInstalling={isInstalling}
          notInstalledMessage="Install a VintageStory server to manage mods. Compatibility checking requires a server version to compare against."
          installingMessage="Mod management will be available once installation completes."
        />
      </div>
    );
  }

  return <ModsPage />;
}

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Suspense fallback={<PageLoading />}>
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
            </Suspense>
          </Layout>
        </BrowserRouter>
        <Toaster />
        </SidebarProvider>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

export default App;
