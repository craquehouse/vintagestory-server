import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useSidebar } from "@/contexts/SidebarContext";
import { Sheet, SheetContent } from "@/components/ui/sheet";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isCollapsed, isMobileOpen, setMobileOpen } = useSidebar();

  return (
    <div
      className="min-h-screen bg-background"
      style={
        {
          "--sidebar-width": isCollapsed ? "64px" : "240px",
        } as React.CSSProperties
      }
    >
      {/* Mobile sidebar sheet */}
      <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <Sidebar />
        </SheetContent>
      </Sheet>

      {/* Desktop sidebar */}
      <div
        className="fixed inset-y-0 left-0 z-30 hidden transition-all duration-300 md:block"
        style={{ width: "var(--sidebar-width)" }}
      >
        <Sidebar />
      </div>

      {/* Header */}
      <Header />

      {/* Main content */}
      <main
        className="pt-12 transition-all duration-300 md:ml-[var(--sidebar-width)]"
      >
        <div className="p-4 md:p-6">{children}</div>
      </main>
    </div>
  );
}
