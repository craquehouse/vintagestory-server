/**
 * ExpandableNavItem - A navigation item that can expand to show nested sub-items.
 *
 * Used for hierarchical navigation in the sidebar, such as Game Server section
 * with sub-pages (Version, Settings, Mods, Console).
 *
 * Story: 11-1-sub-navigation-infrastructure
 */

import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router";
import { ChevronDown, ChevronRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** Sub-navigation item definition */
export interface SubNavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  /** Count shown as a pill when greater than 0 (Story 14.5: mod updates) */
  badge?: number;
  /** Screen reader text for the badge, e.g. "2 mod updates available" */
  badgeLabel?: string;
}

function badgeText(item: SubNavItem): string {
  return item.badgeLabel ?? `${item.label}: ${item.badge}`;
}

/** Count pill; the number is visual, the label is read by screen readers. */
function CountBadge({ count, label, testId }: { count: number; label: string; testId: string }) {
  return (
    <span
      className="ml-auto rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-semibold leading-none text-primary-foreground"
      data-testid={testId}
    >
      <span aria-hidden="true">{count}</span>
      <span className="sr-only">{`, ${label}`}</span>
    </span>
  );
}

/** Dot for icon-only (collapsed sidebar) items. */
function CountDot({ label, testId }: { label: string; testId: string }) {
  return (
    <span
      className="absolute right-1 top-1 h-2 w-2 rounded-full bg-primary"
      data-testid={testId}
    >
      <span className="sr-only">{label}</span>
    </span>
  );
}

interface ExpandableNavItemProps {
  /** Icon to display for the parent item */
  icon: LucideIcon;
  /** Label for the parent item */
  label: string;
  /** Nested navigation items */
  subItems: SubNavItem[];
  /** Whether the item is expanded */
  isExpanded: boolean;
  /** Callback when expanded state changes */
  onExpandedChange: (expanded: boolean) => void;
  /** Whether the sidebar is collapsed (icon-only mode) */
  isCollapsed?: boolean;
  /** Route prefix for auto-expansion (e.g., "/game-server") */
  routePrefix: string;
}

/**
 * ExpandableNavItem component that toggles open/closed to reveal sub-navigation items.
 * Supports both expanded sidebar (inline sub-items) and collapsed sidebar (flyout menu).
 */
export function ExpandableNavItem({
  icon: Icon,
  label,
  subItems,
  isExpanded,
  onExpandedChange,
  isCollapsed = false,
  routePrefix,
}: ExpandableNavItemProps) {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(isExpanded);

  // Sync internal state with prop
  useEffect(() => {
    setIsOpen(isExpanded);
  }, [isExpanded]);

  // Auto-expand when navigating to a matching route
  useEffect(() => {
    const isOnSubRoute = location.pathname.startsWith(routePrefix);
    if (isOnSubRoute && !isOpen) {
      setIsOpen(true);
      onExpandedChange(true);
    }
  }, [location.pathname, routePrefix, isOpen, onExpandedChange]);

  const handleToggle = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    onExpandedChange(newState);
  };

  // Story 14.5: badges on sub-items; the parent shows their total while closed
  const badgedItems = subItems.filter((item) => (item.badge ?? 0) > 0);
  const badgeTotal = badgedItems.reduce((sum, item) => sum + (item.badge ?? 0), 0);
  const parentBadgeLabel = badgedItems.map(badgeText).join(", ");

  // Check if any sub-item is currently active
  const isAnySubItemActive = subItems.some(
    (item) =>
      location.pathname === item.to ||
      location.pathname.startsWith(item.to + "/")
  );

  // Collapsed sidebar mode - render icon-only with expandable sub-items below
  if (isCollapsed) {
    return (
      <div className="space-y-1">
        {/* Parent item with tooltip for label */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(
                "relative w-full justify-center",
                "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                isAnySubItemActive && "bg-sidebar-accent/50"
              )}
              onClick={handleToggle}
              aria-expanded={isOpen}
              data-testid="collapsed-nav-trigger"
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!isOpen && badgeTotal > 0 && (
                <CountDot label={parentBadgeLabel} testId="nav-parent-badge" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {!isOpen && badgeTotal > 0 ? `${label} (${badgeTotal})` : label}
          </TooltipContent>
        </Tooltip>

        {/* Sub-items expanded below (icons only with tooltips) */}
        <div
          className={cn(
            "overflow-hidden transition-all duration-200 ease-in-out space-y-1",
            isOpen ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
          )}
          data-testid="collapsed-sub-items-container"
        >
          {subItems.map((item) => (
            <Tooltip key={item.to}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  asChild
                  className="relative w-full justify-center"
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
                    <item.icon className="h-4 w-4 shrink-0" />
                    {(item.badge ?? 0) > 0 && (
                      <CountDot label={badgeText(item)} testId={`nav-badge-${item.label}`} />
                    )}
                  </NavLink>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                {(item.badge ?? 0) > 0 ? `${item.label} (${item.badge})` : item.label}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>
    );
  }

  // Expanded sidebar mode - render expandable section
  return (
    <div className="space-y-1">
      {/* Parent item with expand/collapse toggle */}
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          "w-full justify-start",
          "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          isAnySubItemActive && "bg-sidebar-accent/50"
        )}
        onClick={handleToggle}
        aria-expanded={isOpen}
        data-testid="expandable-nav-toggle"
      >
        <Icon className="h-5 w-5 shrink-0" />
        <span className="flex-1 text-left">{label}</span>
        {!isOpen && badgeTotal > 0 && (
          <CountBadge count={badgeTotal} label={parentBadgeLabel} testId="nav-parent-badge" />
        )}
        {isOpen ? (
          <ChevronDown className="h-4 w-4 shrink-0" data-testid="chevron-down" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" data-testid="chevron-right" />
        )}
      </Button>

      {/* Sub-items with smooth animation */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          isOpen ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
        )}
        data-testid="sub-items-container"
      >
        <div className="ml-4 space-y-1 border-l border-sidebar-border pl-2">
          {subItems.map((item) => (
            <Button
              key={item.to}
              variant="ghost"
              size="sm"
              asChild
              className="w-full justify-start"
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
                <item.icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
                {(item.badge ?? 0) > 0 && (
                  <CountBadge
                    count={item.badge ?? 0}
                    label={badgeText(item)}
                    testId={`nav-badge-${item.label}`}
                  />
                )}
              </NavLink>
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
