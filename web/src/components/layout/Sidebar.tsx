import { NavLink } from "react-router";
import {
  LayoutDashboard,
  Package,
  Settings,
  Terminal,
  PanelLeftClose,
  PanelLeft,
  Github,
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

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/mods", icon: Package, label: "Mods" },
  { to: "/config", icon: Settings, label: "Config" },
  { to: "/terminal", icon: Terminal, label: "Console" },
];

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { isCollapsed, toggleCollapse } = useSidebar();

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
            isCollapsed ? "justify-center px-2" : "px-4"
          )}
        >
          {isCollapsed ? (
            <span className="text-lg font-bold text-sidebar-primary">VS</span>
          ) : (
            <span className="text-lg font-bold text-sidebar-primary">
              VS Server
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => {
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
          })}
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
