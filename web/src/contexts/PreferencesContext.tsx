/**
 * PreferencesContext - Unified user preferences management.
 *
 * Stores UI preferences in a cookie for cross-session persistence.
 * Syncs theme preference with next-themes for proper theme handling.
 *
 * Story: UI-017 - User preferences cookie persistence
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useTheme } from "next-themes";
import { getCookie, setCookie } from "@/lib/cookies";

/** Theme preference options */
export type ThemePreference = "light" | "dark" | "system";

/** User preferences stored in cookie */
export interface UserPreferences {
  theme: ThemePreference;
  consoleFontSize: number;
  sidebarCollapsed: boolean;
  gameServerNavExpanded: boolean;
}

/** Default preferences for new users */
const DEFAULT_PREFERENCES: UserPreferences = {
  theme: "system",
  consoleFontSize: 14,
  sidebarCollapsed: false,
  gameServerNavExpanded: true,
};

/** Cookie name for preferences storage */
const PREFS_COOKIE_NAME = "vs_ui_prefs";

/** Console font size constraints */
export const FONT_SIZE_MIN = 10;
export const FONT_SIZE_MAX = 24;
export const FONT_SIZE_DEFAULT = 14;

/** Context interface */
interface PreferencesContextType {
  preferences: UserPreferences;
  setThemePreference: (theme: ThemePreference) => void;
  setConsoleFontSize: (size: number) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setGameServerNavExpanded: (expanded: boolean) => void;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(
  undefined
);

interface PreferencesProviderProps {
  children: ReactNode;
}

/**
 * Load preferences from cookie, merging with defaults.
 */
function loadPreferences(): UserPreferences {
  const cookieValue = getCookie(PREFS_COOKIE_NAME);
  if (!cookieValue) {
    return { ...DEFAULT_PREFERENCES };
  }

  try {
    const parsed = JSON.parse(cookieValue) as Partial<UserPreferences>;
    return {
      theme: isValidTheme(parsed.theme) ? parsed.theme : DEFAULT_PREFERENCES.theme,
      consoleFontSize: isValidFontSize(parsed.consoleFontSize)
        ? parsed.consoleFontSize
        : DEFAULT_PREFERENCES.consoleFontSize,
      sidebarCollapsed:
        typeof parsed.sidebarCollapsed === "boolean"
          ? parsed.sidebarCollapsed
          : DEFAULT_PREFERENCES.sidebarCollapsed,
      gameServerNavExpanded:
        typeof parsed.gameServerNavExpanded === "boolean"
          ? parsed.gameServerNavExpanded
          : DEFAULT_PREFERENCES.gameServerNavExpanded,
    };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

/**
 * Validate theme preference value.
 */
function isValidTheme(theme: unknown): theme is ThemePreference {
  return theme === "light" || theme === "dark" || theme === "system";
}

/**
 * Validate font size value.
 */
function isValidFontSize(size: unknown): size is number {
  return (
    typeof size === "number" &&
    size >= FONT_SIZE_MIN &&
    size <= FONT_SIZE_MAX &&
    Number.isInteger(size)
  );
}

/**
 * Clamp font size to valid range.
 */
function clampFontSize(size: number): number {
  return Math.max(FONT_SIZE_MIN, Math.min(FONT_SIZE_MAX, Math.round(size)));
}

/**
 * Preferences provider that persists user preferences to a cookie.
 *
 * Must be rendered inside ThemeProvider to sync theme preferences.
 */
export function PreferencesProvider({ children }: PreferencesProviderProps) {
  const { setTheme: setNextTheme } = useTheme();
  const [preferences, setPreferences] = useState<UserPreferences>(loadPreferences);

  // Persist preferences to cookie whenever they change
  useEffect(() => {
    setCookie(PREFS_COOKIE_NAME, JSON.stringify(preferences));
  }, [preferences]);

  // Sync theme preference with next-themes on mount and changes
  useEffect(() => {
    setNextTheme(preferences.theme);
  }, [preferences.theme, setNextTheme]);

  const setThemePreference = useCallback((theme: ThemePreference) => {
    setPreferences((prev) => ({ ...prev, theme }));
  }, []);

  const setConsoleFontSize = useCallback((size: number) => {
    const clampedSize = clampFontSize(size);
    setPreferences((prev) => ({ ...prev, consoleFontSize: clampedSize }));
  }, []);

  const setSidebarCollapsed = useCallback((collapsed: boolean) => {
    setPreferences((prev) => ({ ...prev, sidebarCollapsed: collapsed }));
  }, []);

  const setGameServerNavExpanded = useCallback((expanded: boolean) => {
    setPreferences((prev) => ({ ...prev, gameServerNavExpanded: expanded }));
  }, []);

  return (
    <PreferencesContext.Provider
      value={{
        preferences,
        setThemePreference,
        setConsoleFontSize,
        setSidebarCollapsed,
        setGameServerNavExpanded,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
}

/**
 * Hook to access user preferences.
 *
 * @throws Error if used outside PreferencesProvider
 */
export function usePreferences(): PreferencesContextType {
  const context = useContext(PreferencesContext);
  if (context === undefined) {
    throw new Error("usePreferences must be used within a PreferencesProvider");
  }
  return context;
}
