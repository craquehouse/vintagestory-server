import { NavLink } from "react-router";
import {
  LayoutDashboard,
  Package,
  Settings,
  Terminal,
  PanelLeftClose,
  PanelLeft,
  Server,
  HardDrive,
  Settings2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSidebar } from "@/contexts/SidebarContext";
import { usePreferences } from "@/contexts/PreferencesContext";
import { useServerStatus } from "@/hooks/use-server-status";
import { useModUpdates } from "@/hooks/use-mods";
import { ExpandableNavItem, type SubNavItem } from "./ExpandableNavItem";

/** Top-level navigation items (non-expandable) */
const topNavItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
];

/** Bottom navigation items (non-expandable) */
// Story 11.4: Removed top-level Mods - now under Game Server > Mods
const bottomNavItems = [
  { to: "/config", icon: Settings, label: "VSManager" },
];

/** GitHub mark, inlined because lucide-react no longer ships brand icons */
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { isCollapsed, toggleCollapse } = useSidebar();
  const { preferences, setGameServerNavExpanded } = usePreferences();
  const { data: statusResponse } = useServerStatus();
  // Story 14.5: count of mods with an update available, shown on the Mods item
  const { data: updatesResponse } = useModUpdates();
  const updateCount = updatesResponse?.data?.updateCount ?? 0;

  // Derive dynamic label for Version/Installation based on server state
  const serverState = statusResponse?.data?.state;
  const versionLabel = serverState === "not_installed" ? "Installation" : "Version";

  // Build game server sub-items with dynamic label
  const gameServerSubItems: SubNavItem[] = [
    { to: "/game-server/version", icon: HardDrive, label: versionLabel },
    { to: "/game-server/settings", icon: Settings2, label: "Settings" },
    {
      to: "/game-server/mods",
      icon: Package,
      label: "Mods",
      badge: updateCount,
      badgeLabel: `${updateCount} mod ${updateCount === 1 ? "update" : "updates"} available`,
    },
    { to: "/game-server/console", icon: Terminal, label: "Console" },
  ];

  // Render a standard nav item (non-expandable)
  const renderNavItem = (item: { to: string; icon: typeof LayoutDashboard; label: string }) => {
    const navButton = (
      <Button
        key={item.to}
        variant="ghost"
        size={isCollapsed ? "icon-sm" : "sm"}
        asChild
        className={cn(
          "w-full",
          isCollapsed ? "justify-center" : "justify-start"
        )}
      >
        <NavLink
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            cn(
              "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              isActive && "bg-sidebar-accent text-sidebar-primary"
            )
          }
        >
          <item.icon className="h-5 w-5 shrink-0" />
          {!isCollapsed && <span>{item.label}</span>}
        </NavLink>
      </Button>
    );

    if (isCollapsed) {
      return (
        <Tooltip key={item.to}>
          <TooltipTrigger asChild>{navButton}</TooltipTrigger>
          <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
      );
    }

    return navButton;
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex h-full flex-col border-r border-sidebar-border bg-sidebar",
          className
        )}
      >
        {/* Logo/Title */}
        <div
          className={cn(
            "flex h-12 items-center border-b border-sidebar-border",
            isCollapsed ? "justify-center px-2" : "px-3"
          )}
        >
          {isCollapsed ? (
            <img
              src="/vintagestory-icon.webp"
              srcSet="/vintagestory-icon.webp 1x, /vintagestory-icon@2x.webp 2x"
              alt="VS"
              className="h-6 w-6"
            />
          ) : (
            <img
              src="/vintagestory-logo.webp"
              srcSet="/vintagestory-logo.webp 1x, /vintagestory-logo@2x.webp 2x"
              alt="Vintage Story"
              className="h-6 w-auto"
            />
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {/* Dashboard */}
          {topNavItems.map(renderNavItem)}

          {/* Game Server (expandable) */}
          <ExpandableNavItem
            icon={Server}
            label="Game Server"
            subItems={gameServerSubItems}
            isExpanded={preferences.gameServerNavExpanded}
            onExpandedChange={setGameServerNavExpanded}
            isCollapsed={isCollapsed}
            routePrefix="/game-server"
          />

          {/* Other nav items */}
          {bottomNavItems.map(renderNavItem)}
        </nav>

        <Separator className="bg-sidebar-border" />

        {/* Footer */}
        <div className="p-2">
          {/* Collapse toggle */}
          <Button
            variant="ghost"
            size={isCollapsed ? "icon-sm" : "sm"}
            onClick={toggleCollapse}
            className={cn(
              "w-full text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              isCollapsed ? "justify-center" : "justify-start"
            )}
          >
            {isCollapsed ? (
              <PanelLeft className="h-5 w-5" />
            ) : (
              <>
                <PanelLeftClose className="h-5 w-5" />
                <span className="ml-2">Collapse</span>
              </>
            )}
          </Button>

          {/* GitHub link + version */}
          <div
            className={cn(
              "mt-2 flex items-center text-xs text-muted-foreground",
              isCollapsed ? "justify-center" : "justify-between px-3"
            )}
          >
            <a
              href="https://github.com/craquehouse/vintagestory-server"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-sidebar-foreground"
              aria-label="GitHub"
            >
              <GithubIcon className="h-4 w-4" />
            </a>
            {!isCollapsed && <span>v0.1.0</span>}
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
