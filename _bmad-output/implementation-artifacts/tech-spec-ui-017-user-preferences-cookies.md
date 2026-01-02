# Tech Spec: UI-017 User Preferences Cookie Persistence

## Overview

Store user preferences (theme override, console font size, sidebar state) in cookies instead of localStorage for consistent cross-session persistence.

**Backlog Item:** UI-017
**Effort:** M (1-4 hours)
**Priority:** low

---

## Current State

| Preference | Current Storage | Location |
|------------|-----------------|----------|
| Theme | localStorage (via next-themes) | `ThemeContext.tsx` |
| Sidebar collapsed | localStorage | `SidebarContext.tsx` |
| Console font size | Hardcoded (14px) | `TerminalView.tsx:76` |

**Problems:**
1. localStorage is origin-bound but not portable across subdomains
2. No unified preferences system - each setting manages its own storage
3. Console font size is not configurable at all

---

## Solution Design

### Architecture

Create a unified `PreferencesContext` that:
1. Stores all UI preferences in a single cookie as JSON
2. Provides typed access to each preference
3. Syncs with `next-themes` for theme persistence
4. Exposes console font size to `TerminalView`

```
┌─────────────────────────────────────────────┐
│          PreferencesProvider                │
│  Cookie: vs_prefs = {                       │
│    theme: "dark" | "light" | "system",      │
│    consoleFontSize: 14,                     │
│    sidebarCollapsed: false                  │
│  }                                          │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    v          v          v
ThemeProvider  Sidebar   TerminalView
(synced)       (reads)   (reads fontSize)
```

### Cookie Design

**Name:** `vs_ui_prefs`
**Value:** JSON-encoded preferences object
**Max-Age:** 1 year (31536000 seconds)
**Path:** `/`
**SameSite:** `Lax`

```typescript
interface UserPreferences {
  theme: "light" | "dark" | "system";
  consoleFontSize: number; // 10-24, default 14
  sidebarCollapsed: boolean;
}
```

---

## Tasks

### Task 1: Create cookie utility functions

**File:** `web/src/lib/cookies.ts`

```typescript
export function getCookie(name: string): string | null;
export function setCookie(name: string, value: string, maxAge?: number): void;
export function deleteCookie(name: string): void;
```

Simple wrappers around `document.cookie` with proper encoding.

**Tests:** Unit tests for get/set/delete with various values.

---

### Task 2: Create PreferencesContext

**File:** `web/src/contexts/PreferencesContext.tsx`

```typescript
interface UserPreferences {
  theme: "light" | "dark" | "system";
  consoleFontSize: number;
  sidebarCollapsed: boolean;
}

interface PreferencesContextType {
  preferences: UserPreferences;
  setTheme: (theme: UserPreferences["theme"]) => void;
  setConsoleFontSize: (size: number) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}
```

**Behavior:**
- Initialize from cookie on mount (with defaults if missing)
- Persist to cookie on any change
- Sync theme changes with `next-themes` via `useTheme().setTheme()`

**Tests:** Context provider tests - initialization, updates, cookie sync.

---

### Task 3: Integrate PreferencesContext into app

**Files to modify:**
- `web/src/App.tsx` - Add `PreferencesProvider` to provider tree
- `web/src/contexts/SidebarContext.tsx` - Read/write via PreferencesContext
- `web/src/components/layout/Header.tsx` - Use PreferencesContext for theme toggle

**Migration:**
- SidebarContext reads initial state from PreferencesContext instead of localStorage
- SidebarContext writes to PreferencesContext instead of localStorage
- Theme toggle uses PreferencesContext which syncs to next-themes

**Tests:** Integration tests verifying provider tree works correctly.

---

### Task 4: Wire console font size to TerminalView

**Files to modify:**
- `web/src/components/terminal/TerminalView.tsx`

**Changes:**
- Accept optional `fontSize` prop (defaults to 14)
- Use `terminal.options.fontSize` to update dynamically

```typescript
export interface TerminalViewProps {
  fontSize?: number;  // Add this
  // ... existing props
}
```

**Consumer update:**
- `ConsolePanel.tsx` or parent passes fontSize from PreferencesContext

**Tests:** TerminalView tests with different font sizes.

---

### Task 5: Add UI Preferences tab to Settings page

**Files to modify:**
- `web/src/features/settings/SettingsPage.tsx` - Add "UI Preferences" tab

**New file:**
- `web/src/features/settings/UIPreferencesPanel.tsx`

**UI Components:**
1. **Theme selector** - Radio group: System, Light, Dark
2. **Console font size** - Slider or number input (10-24px)
3. **Sidebar default** - Checkbox for "Start with sidebar collapsed"

Use existing `SettingGroup` and `SettingField` components.

**Tests:** Component tests for preference controls.

---

## Acceptance Criteria

- [ ] User preferences persist across browser sessions via cookie
- [ ] Theme selection (system/light/dark) is stored in cookie
- [ ] Console font size is configurable (10-24px range)
- [ ] Sidebar collapsed state is stored in cookie
- [ ] Settings page has "UI Preferences" tab with controls
- [ ] All existing tests pass
- [ ] New functionality has test coverage

---

## Files Summary

**New files:**
- `web/src/lib/cookies.ts`
- `web/src/contexts/PreferencesContext.tsx`
- `web/src/features/settings/UIPreferencesPanel.tsx`

**Modified files:**
- `web/src/App.tsx`
- `web/src/contexts/SidebarContext.tsx`
- `web/src/components/layout/Header.tsx`
- `web/src/components/terminal/TerminalView.tsx`
- `web/src/features/settings/SettingsPage.tsx`

---

## Out of Scope

- Server-side preference storage (API backend)
- Preference sync across devices
- Import/export preferences
- Console font family selection (UI-016 separate backlog item)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cookie size limit (4KB) | JSON is small; current prefs < 100 bytes |
| SSR hydration mismatch | Check `typeof window !== "undefined"` |
| next-themes conflict | Sync, don't replace - PreferencesContext calls setTheme |
