import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { PreferencesProvider } from "@/contexts/PreferencesContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { ModsPage, InstalledTab, BrowseTab, ModDetailPage } from "@/features/mods";
import { GameServerPage } from "@/features/game-server";
import { SettingsPage } from "@/features/settings";

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/game-server" element={<GameServerPage />} />
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
