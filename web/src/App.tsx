import { BrowserRouter, Routes, Route } from "react-router";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { ModList } from "@/features/mods/ModList";
import { GameServerPage } from "@/features/game-server";
import { SettingsPage } from "@/features/settings";

function App() {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/game-server" element={<GameServerPage />} />
              <Route path="/mods" element={<ModList />} />
              <Route path="/config" element={<SettingsPage />} />
            </Routes>
          </Layout>
        </BrowserRouter>
        <Toaster />
      </SidebarProvider>
    </ThemeProvider>
  );
}

export default App;
