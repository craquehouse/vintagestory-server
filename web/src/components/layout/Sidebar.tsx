import { NavLink } from "react-router";
import {
  LayoutDashboard,
  Package,
  Settings,
  Terminal,
  PanelLeftClose,
  PanelLeft,
  Github,
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
import { ExpandableNavItem, type SubNavItem } from "./ExpandableNavItem";

/** Top-level navigation items (non-expandable) */
const topNavItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
];

/** Bottom navigation items (non-expandable) */
const bottomNavItems = [
  { to: "/mods", icon: Package, label: "Mods" },
  { to: "/config", icon: Settings, label: "VSManager" },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { isCollapsed, toggleCollapse } = useSidebar();
  const { preferences, setGameServerNavExpanded } = usePreferences();
  const { data: statusResponse } = useServerStatus();

  // Derive dynamic label for Version/Installation based on server state
  const serverState = statusResponse?.data?.state;
  const versionLabel = serverState === "not_installed" ? "Installation" : "Version";

  // Build game server sub-items with dynamic label
  const gameServerSubItems: SubNavItem[] = [
    { to: "/game-server/version", icon: HardDrive, label: versionLabel },
    { to: "/game-server/settings", icon: Settings2, label: "Settings" },
    { to: "/game-server/mods", icon: Package, label: "Mods" },
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
              <Github className="h-4 w-4" />
            </a>
            {!isCollapsed && <span>v0.1.0</span>}
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
