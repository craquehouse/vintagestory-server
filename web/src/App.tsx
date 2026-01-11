import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { PreferencesProvider } from "@/contexts/PreferencesContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { ModsPage, InstalledTab, BrowseTab, ModDetailPage } from "@/features/mods";
import { VersionPage, SettingsPage as GameServerSettingsPage } from "@/features/game-server";
import { SettingsPage } from "@/features/settings";
import { ConsolePanel } from "@/components/ConsolePanel";

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
 * Console page showing full-width console panel.
 */
function GameServerConsolePage() {
  return (
    <div className="h-full p-4" data-testid="game-server-console-page">
      <ConsolePanel className="h-full" />
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

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              {/* Game Server nested routes */}
              <Route path="/game-server" element={<GameServerLayout />}>
                <Route index element={<Navigate to="console" replace />} />
                <Route path="version" element={<VersionPage />} />
                <Route path="settings" element={<GameServerSettingsPage />} />
                {/* Mods routes - moved from top-level /mods (Story 11.4) */}
                <Route path="mods" element={<ModsPage />}>
                  <Route index element={<Navigate to="installed" replace />} />
                  <Route path="installed" element={<InstalledTab />} />
                  <Route path="browse" element={<BrowseTab />} />
                  <Route path="browse/:slug" element={<ModDetailPage />} />
                </Route>
                <Route path="console" element={<GameServerConsolePage />} />
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
