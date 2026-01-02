/**
 * SidebarContext - Manages sidebar collapsed state and mobile visibility.
 *
 * Integrates with PreferencesContext for persistent storage of collapsed state.
 * Mobile open state is transient (not persisted).
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { usePreferences } from "@/contexts/PreferencesContext";

interface SidebarContextType {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  toggleCollapse: () => void;
  setMobileOpen: (open: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

interface SidebarProviderProps {
  children: ReactNode;
}

export function SidebarProvider({ children }: SidebarProviderProps) {
  const { preferences, setSidebarCollapsed } = usePreferences();
  const [isMobileOpen, setMobileOpen] = useState(false);

  const toggleCollapse = useCallback(() => {
    setSidebarCollapsed(!preferences.sidebarCollapsed);
  }, [preferences.sidebarCollapsed, setSidebarCollapsed]);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed: preferences.sidebarCollapsed,
        isMobileOpen,
        toggleCollapse,
        setMobileOpen,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}
