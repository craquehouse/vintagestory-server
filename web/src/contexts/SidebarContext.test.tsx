import { renderHook, act } from "@testing-library/react";
import { SidebarProvider, useSidebar } from "./SidebarContext";
import { PreferencesProvider } from "./PreferencesContext";
import * as cookies from "@/lib/cookies";

// Mock cookies module
vi.mock("@/lib/cookies", () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
}));

// Mock next-themes to avoid matchMedia issues
vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "system",
    setTheme: vi.fn(),
    systemTheme: "dark",
    resolvedTheme: "dark",
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockedGetCookie = vi.mocked(cookies.getCookie);
const mockedSetCookie = vi.mocked(cookies.setCookie);

// Wrapper with both PreferencesProvider and SidebarProvider
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <PreferencesProvider>
      <SidebarProvider>{children}</SidebarProvider>
    </PreferencesProvider>
  );
}

// Helper to create wrapper with initial cookie value
function createWrapperWithPrefs(prefsJson: string | null) {
  mockedGetCookie.mockReturnValue(prefsJson);
  return Wrapper;
}

describe("SidebarContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCookie.mockReturnValue(null);
  });

  it("initializes isCollapsed from preferences when sidebarCollapsed is true", () => {
    const wrapper = createWrapperWithPrefs(
      JSON.stringify({ sidebarCollapsed: true })
    );

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(true);
  });

  it("initializes isCollapsed to false when no preferences exist", () => {
    const wrapper = createWrapperWithPrefs(null);

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(false);
  });

  it("initializes isCollapsed to false when sidebarCollapsed is false in preferences", () => {
    const wrapper = createWrapperWithPrefs(
      JSON.stringify({ sidebarCollapsed: false })
    );

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(false);
  });

  it("initializes isMobileOpen to false by default", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it("persists isCollapsed to cookie when changed to true", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(mockedSetCookie).toHaveBeenCalledWith(
      "vs_ui_prefs",
      expect.stringContaining('"sidebarCollapsed":true')
    );
  });

  it("persists isCollapsed to cookie when changed to false", () => {
    const wrapper = createWrapperWithPrefs(
      JSON.stringify({ sidebarCollapsed: true })
    );

    const { result } = renderHook(() => useSidebar(), { wrapper });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(mockedSetCookie).toHaveBeenCalledWith(
      "vs_ui_prefs",
      expect.stringContaining('"sidebarCollapsed":false')
    );
  });

  it("toggleCollapse flips state from false to true", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isCollapsed).toBe(false);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
  });

  it("toggleCollapse flips state from true to false", () => {
    const wrapper = createWrapperWithPrefs(
      JSON.stringify({ sidebarCollapsed: true })
    );

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(true);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
  });

  it("setMobileOpen updates mobile state to true", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isMobileOpen).toBe(false);

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);
  });

  it("setMobileOpen updates mobile state to false", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);

    act(() => {
      result.current.setMobileOpen(false);
    });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it("does not persist isMobileOpen to cookie", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    // Clear any initial cookie writes
    mockedSetCookie.mockClear();

    act(() => {
      result.current.setMobileOpen(true);
    });

    // isMobileOpen change should NOT trigger cookie update
    expect(mockedSetCookie).not.toHaveBeenCalled();
  });

  it("throws error when useSidebar is used outside SidebarProvider", () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useSidebar());
    }).toThrow("useSidebar must be used within a SidebarProvider");

    consoleError.mockRestore();
  });

  it("persists isCollapsed on every state change", () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    // First toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(mockedSetCookie).toHaveBeenLastCalledWith(
      "vs_ui_prefs",
      expect.stringContaining('"sidebarCollapsed":true')
    );

    // Second toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(mockedSetCookie).toHaveBeenLastCalledWith(
      "vs_ui_prefs",
      expect.stringContaining('"sidebarCollapsed":false')
    );

    // Third toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(mockedSetCookie).toHaveBeenLastCalledWith(
      "vs_ui_prefs",
      expect.stringContaining('"sidebarCollapsed":true')
    );
  });
});
