import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router";
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
 * Placeholder for Game Server Mods page.
 * Story 11.4 will implement the actual content.
 */
function GameServerModsPage() {
  return (
    <div className="p-4" data-testid="game-server-mods-page">
      <h1 className="text-2xl font-bold mb-4">Server Mods</h1>
      <p className="text-muted-foreground">
        Server mod management will be implemented in Story 11.4.
      </p>
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
                <Route path="mods" element={<GameServerModsPage />} />
                <Route path="console" element={<GameServerConsolePage />} />
              </Route>
              <Route path="/mods" element={<ModsPage />}>
                <Route index element={<Navigate to="installed" replace />} />
                <Route path="installed" element={<InstalledTab />} />
                <Route path="browse" element={<BrowseTab />} />
                <Route path="browse/:slug" element={<ModDetailPage />} />
              </Route>
              <Route path="/config" element={<SettingsPage />} />
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
