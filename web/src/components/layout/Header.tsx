import { Moon, Sun, Menu } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { useSidebar } from "@/contexts/SidebarContext";
import { PendingRestartBanner } from "@/components/PendingRestartBanner";
import { useGameSetting } from "@/hooks/use-game-config";

/** Default server name shown when game config is not available */
export const DEFAULT_SERVER_NAME = "VintageStory Server";

export function Header() {
  const { theme, setTheme } = useTheme();
  const { setMobileOpen } = useSidebar();
  const serverNameSetting = useGameSetting("ServerName");
  const serverName =
    typeof serverNameSetting?.value === "string" && serverNameSetting.value
      ? serverNameSetting.value
      : DEFAULT_SERVER_NAME;

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
          <span className="font-semibold">{serverName}</span>
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
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
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
