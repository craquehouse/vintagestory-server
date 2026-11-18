/**
 * SidebarContext - Manages sidebar collapsed state and mobile visibility.
 *
 * Story 21.8 (ADR-14): `isCollapsed` comes from the stored sidebar preference and the width.
 * With `auto` the sidebar is collapsed below `lg` (1024px) and follows resizes; the toggle
 * stores the opposite of what is shown (`expanded` or `collapsed`), which then applies at every
 * width. The preference is persisted by PreferencesContext; mobile open state is transient.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { usePreferences } from '@/contexts/PreferencesContext';
import { LG_UP_QUERY, useMediaQuery } from '@/hooks/use-media-query';
import { isSidebarCollapsed } from '@/lib/sidebar-preference';

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
  const { preferences, setSidebarPreference } = usePreferences();
  const [isMobileOpen, setMobileOpen] = useState(false);
  const isLgUp = useMediaQuery(LG_UP_QUERY);
  const isCollapsed = isSidebarCollapsed(preferences.sidebar, isLgUp);

  const toggleCollapse = useCallback(() => {
    setSidebarPreference(isCollapsed ? 'expanded' : 'collapsed');
  }, [isCollapsed, setSidebarPreference]);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed,
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
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}
