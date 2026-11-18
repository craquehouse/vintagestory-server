import type { ReactNode } from 'react';
import { matchPath, useLocation } from 'react-router';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useSidebar } from '@/contexts/SidebarContext';
import { Sheet, SheetContent, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { useRefreshModDataOnGameVersionChange } from '@/hooks/use-server-status';
import { FULL_WIDTH_ROUTES, PAGE_CONTENT_WIDTH } from './content-width';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isCollapsed, isMobileOpen, setMobileOpen } = useSidebar();
  // Story 21.4: mod data follows the installed game version
  useRefreshModDataOnGameVersionChange();
  // Story 21.8 (ADR-15): every page but the console is at most 1280px wide, centered
  const { pathname } = useLocation();
  const fullWidth = FULL_WIDTH_ROUTES.some((path) => matchPath(path, pathname) !== null);

  return (
    <div
      className="min-h-screen bg-background"
      style={
        {
          '--sidebar-width': isCollapsed ? '64px' : '160px',
        } as React.CSSProperties
      }
    >
      {/* Mobile sidebar sheet */}
      <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">Navigation menu</SheetTitle>
          <SheetDescription className="sr-only">
            Main navigation links for the application
          </SheetDescription>
          <Sidebar inSheet />
        </SheetContent>
      </Sheet>

      {/* Desktop sidebar */}
      <div
        className="fixed inset-y-0 left-0 z-30 hidden transition-all duration-300 md:block"
        data-testid="desktop-sidebar"
        style={{ width: 'var(--sidebar-width)' }}
      >
        <Sidebar />
      </div>

      {/* Header */}
      <Header />

      {/* Main content */}
      <main className="pt-12 transition-all duration-300 md:ml-[var(--sidebar-width)]">
        <div className="p-4 md:p-6">
          <div className={fullWidth ? undefined : PAGE_CONTENT_WIDTH} data-testid="page-content">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
