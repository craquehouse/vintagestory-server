import { BrowserRouter, Routes, Route } from "react-router";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "@/components/layout/Layout";
import { Dashboard } from "@/features/dashboard/Dashboard";
import { ModList } from "@/features/mods/ModList";
import { ConfigEditor } from "@/features/config/ConfigEditor";
import { Terminal } from "@/features/terminal/Terminal";

function App() {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/mods" element={<ModList />} />
              <Route path="/config" element={<ConfigEditor />} />
              <Route path="/terminal" element={<Terminal />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </SidebarProvider>
    </ThemeProvider>
  );
}

export default App;
