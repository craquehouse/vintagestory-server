/**
 * The sidebar preference (Epic 21 ADR-14, Story 21.8).
 *
 * `auto` follows the width: collapsed below `lg` (1024px), expanded from it. `expanded` and
 * `collapsed` are choices made with the sidebar's toggle or in UI Preferences and apply at every
 * width. Pure functions: the cookie is read and written by PreferencesContext.
 */

export type SidebarPreference = 'auto' | 'expanded' | 'collapsed';

/** In the order UI Preferences shows them. */
export const SIDEBAR_PREFERENCES: readonly SidebarPreference[] = ['auto', 'expanded', 'collapsed'];

export function isSidebarPreference(value: unknown): value is SidebarPreference {
  return SIDEBAR_PREFERENCES.some((item) => item === value);
}

/**
 * The preference stored in a parsed vs_ui_prefs cookie. A valid `sidebar` wins. Otherwise the
 * key written before Story 21.8 is read once: `sidebarCollapsed: true` can only come from a
 * choice, so it is `collapsed`; `false` was written on every first render, so it is `auto`.
 */
export function readSidebarPreference(stored: Record<string, unknown>): SidebarPreference {
  const { sidebar } = stored;
  if (isSidebarPreference(sidebar)) {
    return sidebar;
  }
  return stored.sidebarCollapsed === true ? 'collapsed' : 'auto';
}

/** `auto` is collapsed below `lg` (1024px) and expanded from it; a choice applies at every width. */
export function isSidebarCollapsed(preference: SidebarPreference, isLgUp: boolean): boolean {
  if (preference === 'auto') {
    return !isLgUp;
  }
  return preference === 'collapsed';
}
