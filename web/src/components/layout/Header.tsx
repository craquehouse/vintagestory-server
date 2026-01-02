import { Moon, Sun, Menu } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import { Button } from "@/components/ui/button";
import { useSidebar } from "@/contexts/SidebarContext";
import { usePreferences } from "@/contexts/PreferencesContext";
import { PendingRestartBanner } from "@/components/PendingRestartBanner";

export function Header() {
  const { resolvedTheme } = useTheme();
  const { setThemePreference } = usePreferences();
  const { setMobileOpen } = useSidebar();

  return (
    <header className="fixed top-0 right-0 left-0 z-40 h-12 border-b border-border bg-background md:left-[var(--sidebar-width)]">
      <div className="flex h-full items-center justify-between px-4">
        {/* Left: Mobile menu button + Server name */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon-sm"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <span className="font-semibold">VintageStory Server</span>
            <span className="hidden text-sm text-muted-foreground sm:inline">
              (placeholder)
            </span>
          </div>
        </div>

        {/* Center: Pending restart indicator */}
        <div className="flex items-center">
          <PendingRestartBanner />
        </div>

        {/* Right: Theme toggle */}
        <div className="flex items-center">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setThemePreference(resolvedTheme === "dark" ? "light" : "dark")}
            aria-label="Toggle theme"
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
        </div>
      </div>
    </header>
  );
}
