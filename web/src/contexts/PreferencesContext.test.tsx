import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  PreferencesProvider,
  usePreferences,
  FONT_SIZE_MIN,
  FONT_SIZE_MAX,
  FONT_SIZE_DEFAULT,
} from "./PreferencesContext";
import * as cookies from "@/lib/cookies";

// Mock cookies module
vi.mock("@/lib/cookies", () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
}));

// Mock next-themes to avoid matchMedia issues
const mockSetTheme = vi.fn();
vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "system",
    setTheme: mockSetTheme,
    systemTheme: "dark",
    resolvedTheme: "dark",
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockedGetCookie = vi.mocked(cookies.getCookie);
const mockedSetCookie = vi.mocked(cookies.setCookie);

// Simple wrapper with just PreferencesProvider
function Wrapper({ children }: { children: React.ReactNode }) {
  return <PreferencesProvider>{children}</PreferencesProvider>;
}

describe("PreferencesContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCookie.mockReturnValue(null);
  });

  describe("initialization", () => {
    it("loads default preferences when no cookie exists", () => {
      mockedGetCookie.mockReturnValue(null);

      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      expect(result.current.preferences).toEqual({
        theme: "system",
        consoleFontSize: FONT_SIZE_DEFAULT,
        sidebarCollapsed: false,
      });
    });

    it("loads preferences from cookie when present", () => {
      mockedGetCookie.mockReturnValue(
        JSON.stringify({
          theme: "dark",
          consoleFontSize: 16,
          sidebarCollapsed: true,
        })
      );

      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      expect(result.current.preferences).toEqual({
        theme: "dark",
        consoleFontSize: 16,
        sidebarCollapsed: true,
      });
    });

    it("uses defaults for missing or invalid cookie values", () => {
      mockedGetCookie.mockReturnValue(
        JSON.stringify({
          theme: "invalid",
          consoleFontSize: 100, // Out of range
        })
      );

      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      expect(result.current.preferences).toEqual({
        theme: "system", // Default for invalid
        consoleFontSize: FONT_SIZE_DEFAULT, // Default for out of range
        sidebarCollapsed: false, // Default for missing
      });
    });

    it("handles corrupted cookie JSON gracefully", () => {
      mockedGetCookie.mockReturnValue("not valid json {{{");

      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      expect(result.current.preferences).toEqual({
        theme: "system",
        consoleFontSize: FONT_SIZE_DEFAULT,
        sidebarCollapsed: false,
      });
    });

    it("syncs theme with next-themes on mount", () => {
      mockedGetCookie.mockReturnValue(JSON.stringify({ theme: "dark" }));

      renderHook(() => usePreferences(), { wrapper: Wrapper });

      expect(mockSetTheme).toHaveBeenCalledWith("dark");
    });
  });

  describe("setThemePreference", () => {
    it("updates theme preference", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setThemePreference("dark");
      });

      expect(result.current.preferences.theme).toBe("dark");
    });

    it("persists theme to cookie", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setThemePreference("light");
      });

      expect(mockedSetCookie).toHaveBeenCalledWith(
        "vs_ui_prefs",
        expect.stringContaining('"theme":"light"')
      );
    });

    it("syncs theme with next-themes", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setThemePreference("light");
      });

      expect(mockSetTheme).toHaveBeenCalledWith("light");
    });
  });

  describe("setConsoleFontSize", () => {
    it("updates font size", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setConsoleFontSize(18);
      });

      expect(result.current.preferences.consoleFontSize).toBe(18);
    });

    it("clamps font size to minimum", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setConsoleFontSize(5);
      });

      expect(result.current.preferences.consoleFontSize).toBe(FONT_SIZE_MIN);
    });

    it("clamps font size to maximum", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setConsoleFontSize(50);
      });

      expect(result.current.preferences.consoleFontSize).toBe(FONT_SIZE_MAX);
    });

    it("rounds fractional font sizes", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setConsoleFontSize(15.7);
      });

      expect(result.current.preferences.consoleFontSize).toBe(16);
    });

    it("persists font size to cookie", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setConsoleFontSize(20);
      });

      expect(mockedSetCookie).toHaveBeenCalledWith(
        "vs_ui_prefs",
        expect.stringContaining('"consoleFontSize":20')
      );
    });
  });

  describe("setSidebarCollapsed", () => {
    it("updates sidebar collapsed state", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setSidebarCollapsed(true);
      });

      expect(result.current.preferences.sidebarCollapsed).toBe(true);
    });

    it("persists sidebar state to cookie", () => {
      const { result } = renderHook(() => usePreferences(), { wrapper: Wrapper });

      act(() => {
        result.current.setSidebarCollapsed(true);
      });

      expect(mockedSetCookie).toHaveBeenCalledWith(
        "vs_ui_prefs",
        expect.stringContaining('"sidebarCollapsed":true')
      );
    });
  });

  describe("usePreferences outside provider", () => {
    it("throws error when used outside PreferencesProvider", () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(() => {
        renderHook(() => usePreferences());
      }).toThrow("usePreferences must be used within a PreferencesProvider");

      consoleSpy.mockRestore();
    });
  });
});
