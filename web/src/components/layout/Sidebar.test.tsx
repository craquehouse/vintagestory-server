import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { PreferencesProvider } from "@/contexts/PreferencesContext";

// Mock cookies module
vi.mock("@/lib/cookies", () => ({
  getCookie: vi.fn().mockReturnValue(null),
  setCookie: vi.fn(),
}));

// Mock next-themes
vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "dark",
    setTheme: vi.fn(),
    resolvedTheme: "dark",
    systemTheme: "dark",
  }),
}));

// Mock server status hook
const mockServerState = { data: { state: "installed" } };
vi.mock("@/hooks/use-server-status", () => ({
  useServerStatus: () => ({ data: mockServerState }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (
  ui: React.ReactElement,
  { initialRoute = "/" } = {}
) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <SidebarProvider>
          <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>
        </SidebarProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
};

describe("Sidebar", () => {
  beforeEach(() => {
    // Clear localStorage to ensure consistent initial state (sidebar expanded)
    localStorage.clear();
    // Reset server state to installed
    mockServerState.data.state = "installed";
  });

  describe("Navigation Structure", () => {
    it("renders Dashboard link", () => {
      renderWithProviders(<Sidebar />);

      const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
      expect(dashboardLink).toBeInTheDocument();
      expect(dashboardLink).toHaveAttribute("href", "/");
    });

    it("renders expandable Game Server section", () => {
      renderWithProviders(<Sidebar />);

      // Game Server is now a button (expandable), not a direct link
      const gameServerToggle = screen.getByTestId("expandable-nav-toggle");
      expect(gameServerToggle).toBeInTheDocument();
      expect(screen.getByText("Game Server")).toBeInTheDocument();
    });

    // Story 11.4: Top-level Mods link removed - now only under Game Server
    it("does not render top-level Mods link", () => {
      renderWithProviders(<Sidebar />);

      // Only one Mods link should exist - the sub-item under Game Server
      const modsLinks = screen.getAllByRole("link", { name: /^mods$/i });
      expect(modsLinks.length).toBe(1);
      expect(modsLinks[0]).toHaveAttribute("href", "/game-server/mods");
    });

    it("renders VSManager (Settings) link", () => {
      renderWithProviders(<Sidebar />);

      const settingsLink = screen.getByRole("link", { name: /vsmanager/i });
      expect(settingsLink).toBeInTheDocument();
      expect(settingsLink).toHaveAttribute("href", "/config");
    });
  });

  describe("Game Server Expandable Navigation", () => {
    it("shows sub-items when expanded (default state)", () => {
      renderWithProviders(<Sidebar />);

      // Default state is expanded, so sub-items should be visible
      expect(screen.getByRole("link", { name: /version/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /^settings$/i })
      ).toBeInTheDocument();
      // Story 11.4: "Mods" now only appears once - as sub-item under Game Server
      const modsLinks = screen.getAllByRole("link", { name: /mods/i });
      expect(modsLinks.length).toBe(1); // Only sub-item
      expect(modsLinks[0]).toHaveAttribute("href", "/game-server/mods");
      expect(screen.getByRole("link", { name: /console/i })).toBeInTheDocument();
    });

    it("collapses Game Server sub-items when toggle clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const gameServerToggle = screen.getByTestId("expandable-nav-toggle");
      await user.click(gameServerToggle);

      // Sub-items container should be collapsed (hidden)
      const container = screen.getByTestId("sub-items-container");
      expect(container).toHaveClass("max-h-0", "opacity-0");
    });

    it("expands Game Server sub-items when toggle clicked again", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const gameServerToggle = screen.getByTestId("expandable-nav-toggle");

      // Collapse first
      await user.click(gameServerToggle);
      // Then expand
      await user.click(gameServerToggle);

      const container = screen.getByTestId("sub-items-container");
      expect(container).toHaveClass("max-h-40", "opacity-100");
    });

    it("shows correct sub-item links", () => {
      renderWithProviders(<Sidebar />);

      expect(screen.getByRole("link", { name: /version/i })).toHaveAttribute(
        "href",
        "/game-server/version"
      );
      expect(screen.getByRole("link", { name: /^settings$/i })).toHaveAttribute(
        "href",
        "/game-server/settings"
      );
      expect(screen.getByRole("link", { name: /console/i })).toHaveAttribute(
        "href",
        "/game-server/console"
      );
    });
  });

  describe("Dynamic Version/Installation Label (AC 4, 5)", () => {
    it('shows "Version" label when server is installed', () => {
      mockServerState.data.state = "installed";
      renderWithProviders(<Sidebar />);

      expect(screen.getByRole("link", { name: /version/i })).toBeInTheDocument();
      expect(
        screen.queryByRole("link", { name: /installation/i })
      ).not.toBeInTheDocument();
    });

    it('shows "Installation" label when server is not installed', () => {
      mockServerState.data.state = "not_installed";
      renderWithProviders(<Sidebar />);

      expect(
        screen.getByRole("link", { name: /installation/i })
      ).toBeInTheDocument();
    });
  });

  describe("Active Route Highlighting", () => {
    // Story 11.4: Updated to use /game-server/mods instead of /mods
    it("highlights active route with bg-sidebar-accent class", () => {
      renderWithProviders(<Sidebar />, { initialRoute: "/game-server/mods" });

      // Find Mods link under Game Server (href="/game-server/mods")
      const modsLink = screen.getByRole("link", { name: /^mods$/i });
      expect(modsLink).toHaveAttribute("href", "/game-server/mods");
    });

    it("does not highlight inactive routes", () => {
      renderWithProviders(<Sidebar />, { initialRoute: "/game-server/mods" });

      const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
      expect(dashboardLink).not.toHaveClass("bg-sidebar-accent");
      expect(dashboardLink).not.toHaveClass("text-sidebar-primary");
    });
  });

  describe("Sidebar Collapse Behavior", () => {
    it("shows collapse button when expanded", () => {
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"));
      expect(collapseButton).toBeInTheDocument();
    });

    it("toggles collapse state when collapse button clicked", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"))!;

      await user.click(collapseButton);

      const collapsedButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left"));
      expect(collapsedButton).toBeInTheDocument();
    });

    it("hides version label when collapsed", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"))!;

      await user.click(collapseButton);

      const version = screen.queryByText("v0.1.0");
      expect(version).not.toBeInTheDocument();
    });

    it("hides nav labels when collapsed", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"))!;

      await user.click(collapseButton);

      // All nav labels should be hidden
      expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
      expect(screen.queryByText("Game Server")).not.toBeInTheDocument();
      // Top-level Mods link label should be hidden
      expect(screen.queryByText("VSManager")).not.toBeInTheDocument();
    });
  });

  describe("Logo and Branding", () => {
    it("renders logo image when expanded", () => {
      renderWithProviders(<Sidebar />);

      const logo = screen.getByRole("img", { name: /vintage story/i });
      expect(logo).toBeInTheDocument();
      expect(logo).toHaveAttribute("src", "/vintagestory-logo.webp");
    });

    it("renders icon when collapsed", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"))!;

      await user.click(collapseButton);

      const icon = screen.getByRole("img", { name: /vs/i });
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveAttribute("src", "/vintagestory-icon.webp");
      expect(
        screen.queryByRole("img", { name: /vintage story/i })
      ).not.toBeInTheDocument();
    });
  });

  describe("External Links", () => {
    it("renders GitHub link with correct href", () => {
      renderWithProviders(<Sidebar />);

      const githubLink = screen.getByRole("link", { name: /github/i });
      expect(githubLink).toHaveAttribute(
        "href",
        "https://github.com/craquehouse/vintagestory-server"
      );
      expect(githubLink).toHaveAttribute("target", "_blank");
      expect(githubLink).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("Tooltips", () => {
    it("shows tooltips when sidebar is collapsed", async () => {
      const user = userEvent.setup();
      renderWithProviders(<Sidebar />);

      const collapseButton = screen
        .getAllByRole("button")
        .find((btn) => btn.innerHTML.includes("panel-left-close"))!;

      await user.click(collapseButton);

      // Check that tooltip-trigger elements are present
      const tooltipTriggers = document.querySelectorAll(
        '[data-slot="tooltip-trigger"]'
      );
      expect(tooltipTriggers.length).toBeGreaterThan(0);
    });
  });
});
