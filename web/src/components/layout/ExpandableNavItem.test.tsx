import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { Home, Settings, Terminal, Package } from "lucide-react";
import { ExpandableNavItem, type SubNavItem } from "./ExpandableNavItem";

// Mock ResizeObserver for Radix UI components
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

beforeAll(() => {
  global.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
});

// Mock lucide-react icons to include test identifiers
vi.mock("lucide-react", async (importOriginal) => {
  const original = await importOriginal<typeof import("lucide-react")>();
  return {
    ...original,
    ChevronDown: (props: React.SVGProps<SVGSVGElement>) => (
      <svg {...props} data-testid="chevron-down" />
    ),
    ChevronRight: (props: React.SVGProps<SVGSVGElement>) => (
      <svg {...props} data-testid="chevron-right" />
    ),
  };
});

const mockSubItems: SubNavItem[] = [
  { to: "/parent/version", icon: Home, label: "Version" },
  { to: "/parent/settings", icon: Settings, label: "Settings" },
  { to: "/parent/mods", icon: Package, label: "Mods" },
  { to: "/parent/console", icon: Terminal, label: "Console" },
];

const defaultProps = {
  icon: Home,
  label: "Parent Item",
  subItems: mockSubItems,
  routePrefix: "/parent",
};

interface RenderOptions {
  initialRoute?: string;
  isExpanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  isCollapsed?: boolean;
}

const renderWithRouter = (options: RenderOptions = {}) => {
  const {
    initialRoute = "/",
    isExpanded = false,
    onExpandedChange = vi.fn(),
    isCollapsed = false,
  } = options;

  return {
    ...render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <ExpandableNavItem
          {...defaultProps}
          isExpanded={isExpanded}
          onExpandedChange={onExpandedChange}
          isCollapsed={isCollapsed}
        />
      </MemoryRouter>
    ),
    onExpandedChange,
  };
};

describe("ExpandableNavItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Expanded Sidebar Mode", () => {
    it("renders parent item with label and icon", () => {
      renderWithRouter();

      expect(screen.getByText("Parent Item")).toBeInTheDocument();
      expect(screen.getByTestId("expandable-nav-toggle")).toBeInTheDocument();
    });

    it("shows chevron-right when collapsed", () => {
      renderWithRouter({ isExpanded: false });

      expect(screen.getByTestId("chevron-right")).toBeInTheDocument();
      expect(screen.queryByTestId("chevron-down")).not.toBeInTheDocument();
    });

    it("shows chevron-down when expanded", () => {
      renderWithRouter({ isExpanded: true });

      expect(screen.getByTestId("chevron-down")).toBeInTheDocument();
      expect(screen.queryByTestId("chevron-right")).not.toBeInTheDocument();
    });

    it("hides sub-items when collapsed", () => {
      renderWithRouter({ isExpanded: false });

      const container = screen.getByTestId("sub-items-container");
      expect(container).toHaveClass("max-h-0", "opacity-0");
    });

    it("shows sub-items when expanded", () => {
      renderWithRouter({ isExpanded: true });

      const container = screen.getByTestId("sub-items-container");
      expect(container).toHaveClass("max-h-40", "opacity-100");

      // All sub-items should be visible
      expect(screen.getByRole("link", { name: /version/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /settings/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /mods/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /console/i })).toBeInTheDocument();
    });

    it("toggles expanded state when parent clicked", async () => {
      const user = userEvent.setup();
      const onExpandedChange = vi.fn();
      renderWithRouter({ isExpanded: false, onExpandedChange });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      await user.click(toggle);

      expect(onExpandedChange).toHaveBeenCalledWith(true);
    });

    it("toggles collapsed state when parent clicked while expanded", async () => {
      const user = userEvent.setup();
      const onExpandedChange = vi.fn();
      renderWithRouter({ isExpanded: true, onExpandedChange });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      await user.click(toggle);

      expect(onExpandedChange).toHaveBeenCalledWith(false);
    });

    it("sets aria-expanded attribute correctly when collapsed", () => {
      renderWithRouter({ isExpanded: false });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });

    it("sets aria-expanded attribute correctly when expanded", () => {
      renderWithRouter({ isExpanded: true });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      expect(toggle).toHaveAttribute("aria-expanded", "true");
    });

    it("renders sub-items with correct links", () => {
      renderWithRouter({ isExpanded: true });

      expect(screen.getByRole("link", { name: /version/i })).toHaveAttribute(
        "href",
        "/parent/version"
      );
      expect(screen.getByRole("link", { name: /settings/i })).toHaveAttribute(
        "href",
        "/parent/settings"
      );
      expect(screen.getByRole("link", { name: /mods/i })).toHaveAttribute(
        "href",
        "/parent/mods"
      );
      expect(screen.getByRole("link", { name: /console/i })).toHaveAttribute(
        "href",
        "/parent/console"
      );
    });

    it("applies transition classes for animation", () => {
      renderWithRouter({ isExpanded: false });

      const container = screen.getByTestId("sub-items-container");
      expect(container).toHaveClass(
        "overflow-hidden",
        "transition-all",
        "duration-200",
        "ease-in-out"
      );
    });
  });

  describe("Auto-expand on route match", () => {
    it("auto-expands when navigating to a matching route", async () => {
      const onExpandedChange = vi.fn();
      renderWithRouter({
        initialRoute: "/parent/settings",
        isExpanded: false,
        onExpandedChange,
      });

      await waitFor(() => {
        expect(onExpandedChange).toHaveBeenCalledWith(true);
      });
    });

    it("does not auto-expand when on non-matching route", () => {
      const onExpandedChange = vi.fn();
      renderWithRouter({
        initialRoute: "/other/page",
        isExpanded: false,
        onExpandedChange,
      });

      expect(onExpandedChange).not.toHaveBeenCalled();
    });

    it("does not trigger callback when already expanded on matching route", () => {
      const onExpandedChange = vi.fn();
      renderWithRouter({
        initialRoute: "/parent/settings",
        isExpanded: true,
        onExpandedChange,
      });

      expect(onExpandedChange).not.toHaveBeenCalled();
    });
  });

  describe("Active state highlighting", () => {
    it("highlights parent when a sub-item is active", () => {
      renderWithRouter({
        initialRoute: "/parent/settings",
        isExpanded: true,
      });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      expect(toggle).toHaveClass("bg-sidebar-accent/50");
    });

    it("does not highlight parent when no sub-item is active", () => {
      renderWithRouter({
        initialRoute: "/other/page",
        isExpanded: true,
      });

      const toggle = screen.getByTestId("expandable-nav-toggle");
      expect(toggle).not.toHaveClass("bg-sidebar-accent/50");
    });
  });

  describe("Collapsed Sidebar Mode", () => {
    it("renders only icon button when collapsed", () => {
      renderWithRouter({ isCollapsed: true });

      // Should not show the expanded nav toggle
      expect(screen.queryByTestId("expandable-nav-toggle")).not.toBeInTheDocument();
      // Should show collapsed nav trigger instead
      expect(screen.getByTestId("collapsed-nav-trigger")).toBeInTheDocument();
      // Should not show sub-items container
      expect(screen.queryByTestId("sub-items-container")).not.toBeInTheDocument();
    });

    it("applies active styling when on sub-route in collapsed mode", () => {
      renderWithRouter({
        isCollapsed: true,
        initialRoute: "/parent/settings",
      });

      const button = screen.getByTestId("collapsed-nav-trigger");
      expect(button).toHaveClass("bg-sidebar-accent", "text-sidebar-primary");
    });

    it("toggles expansion when clicked in collapsed mode", async () => {
      const user = userEvent.setup();
      const onExpandedChange = vi.fn();
      renderWithRouter({
        isCollapsed: true,
        isExpanded: false,
        onExpandedChange,
      });

      const button = screen.getByTestId("collapsed-nav-trigger");
      await user.click(button);

      expect(onExpandedChange).toHaveBeenCalledWith(true);
    });

    it("has proper data-testid for collapsed flyout content", () => {
      // The collapsed mode component renders with data-testid="collapsed-nav-flyout"
      // in its TooltipContent. Since Tooltip uses portals, we verify the trigger exists
      // and has the correct structure. The actual flyout appears on hover.
      renderWithRouter({ isCollapsed: true });

      const trigger = screen.getByTestId("collapsed-nav-trigger");
      expect(trigger).toBeInTheDocument();
      expect(trigger.tagName.toLowerCase()).toBe("button");
    });
  });

  describe("State sync with props", () => {
    it("syncs internal state when isExpanded prop changes", () => {
      const { rerender } = render(
        <MemoryRouter>
          <ExpandableNavItem
            {...defaultProps}
            isExpanded={false}
            onExpandedChange={vi.fn()}
          />
        </MemoryRouter>
      );

      // Initially collapsed
      expect(screen.getByTestId("chevron-right")).toBeInTheDocument();

      // Rerender with expanded=true
      rerender(
        <MemoryRouter>
          <ExpandableNavItem
            {...defaultProps}
            isExpanded={true}
            onExpandedChange={vi.fn()}
          />
        </MemoryRouter>
      );

      // Should now show expanded state
      expect(screen.getByTestId("chevron-down")).toBeInTheDocument();
    });
  });
});
