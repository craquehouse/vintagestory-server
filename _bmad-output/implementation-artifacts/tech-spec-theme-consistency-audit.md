---
title: 'Theme Consistency Audit - CSS Variables and Utility Classes'
slug: 'theme-consistency-audit'
created: '2026-01-18'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Tailwind CSS v4', 'CSS Variables', 'Catppuccin', 'React', 'TypeScript']
files_to_modify:
  # CSS - utility class definitions
  - 'web/src/styles/index.css'
  # CRITICAL - hardcoded hex values (breaks light mode)
  - 'web/src/components/CompatibilityBadge.tsx'
  - 'web/src/components/PendingRestartBanner.tsx'
  # MODERATE - hardcoded Tailwind colors
  - 'web/src/components/DiskSpaceWarningBanner.tsx'
  - 'web/src/components/terminal/ConnectionStatus.tsx'
  - 'web/src/components/VersionCard.tsx'
  - 'web/src/components/SettingField.tsx'
  - 'web/src/components/InstallConfirmDialog.tsx'
  - 'web/src/components/UninstallConfirmDialog.tsx'
  - 'web/src/components/InstallVersionDialog.tsx'
  - 'web/src/components/QuickInstallButton.tsx'
  - 'web/src/components/ModCard.tsx'
  - 'web/src/features/mods/ModDetailPage.tsx'
  # Tests to update
  - 'web/src/components/CompatibilityBadge.test.tsx'
  - 'web/src/components/DiskSpaceWarningBanner.test.tsx'
  - 'web/src/components/PendingRestartBanner.test.tsx'
code_patterns:
  - 'Semantic CSS variables: --success, --warning, --destructive, --primary, --muted'
  - 'Tailwind v4 @theme inline directive for CSS variable integration'
  - 'Dark mode via .dark class on root element'
test_patterns:
  - 'Vitest with React Testing Library'
  - 'Tests co-located with components (*.test.tsx)'
---

# Tech-Spec: Theme Consistency Audit - CSS Variables and Utility Classes

**Created:** 2026-01-18

## Overview

### Problem Statement

The web UI has inconsistent theming - **12 components** use hardcoded Tailwind colors (`green-*`, `yellow-*`, hex values) instead of the established Catppuccin-based CSS variable system. Two components use hardcoded hex values that only work in dark mode, breaking light mode entirely. This creates maintenance issues and visual inconsistencies across themes.

### Solution

1. Create reusable utility classes for common semantic patterns (badges, alerts, status indicators)
2. Refactor all 12 identified components to use CSS variables and new utility classes
3. Update associated test files to validate semantic classes instead of hardcoded values
4. Ensure all color usage goes through the semantic variable system

### Scope

**In Scope:**
- Create utility classes for success/warning/destructive/muted states (badges, banners, status indicators)
- Fix 2 CRITICAL components with hardcoded hex values (CompatibilityBadge, PendingRestartBanner)
- Fix 10 MODERATE components with hardcoded Tailwind colors
- Update 3 test files with hardcoded color assertions
- Use existing `--warning` variable (Catppuccin gold/yellow)
- Use existing `--success` variable (Catppuccin green)
- Use existing `--destructive` variable (Catppuccin red)
- Use existing `--primary` variable (Catppuccin purple)
- Use existing `--muted` variable (Catppuccin gray)

**Out of Scope:**
- Changing the Catppuccin color scheme itself
- Terminal theme modifications (already uses proper theme system)
- Chart color handling (already using CSS variables with fallbacks)
- Adding new semantic color variables (using existing ones)

## Context for Development

### Codebase Patterns

- Theming uses Catppuccin color scheme with CSS variables defined in `web/src/styles/index.css`
- Light theme (Latte) and Dark theme (Mocha) are toggled via `.dark` class on root element
- Tailwind v4 integrates CSS variables via `@theme inline` directive
- Semantic colors available: `--success`, `--warning`, `--destructive`, `--primary`, `--secondary`, `--accent`

### Files to Reference

| File | Purpose | Severity |
| ---- | ------- | -------- |
| `web/src/styles/index.css` | CSS variable definitions - add utility classes here | N/A |
| `web/src/components/CompatibilityBadge.tsx` | Hardcoded Catppuccin Mocha hex values | CRITICAL |
| `web/src/components/PendingRestartBanner.tsx` | Hardcoded `#cba6f7` hex | CRITICAL |
| `web/src/components/DiskSpaceWarningBanner.tsx` | `yellow-500` hardcoded | MODERATE |
| `web/src/components/terminal/ConnectionStatus.tsx` | 8 instances of hardcoded colors | MODERATE |
| `web/src/components/VersionCard.tsx` | `green-*`, `yellow-*` hardcoded | MODERATE |
| `web/src/components/SettingField.tsx` | `yellow-500` env badge | MODERATE |
| `web/src/components/InstallConfirmDialog.tsx` | `yellow-500` warning | MODERATE |
| `web/src/components/UninstallConfirmDialog.tsx` | `yellow-500` warning | MODERATE |
| `web/src/components/InstallVersionDialog.tsx` | `yellow-500` warning | MODERATE |
| `web/src/components/QuickInstallButton.tsx` | `yellow-500` icon | MODERATE |
| `web/src/components/ModCard.tsx` | `green-500` installed indicator | MODERATE |
| `web/src/features/mods/ModDetailPage.tsx` | `green-500` installed icon | MODERATE |

### Technical Decisions

- **TD-1:** Use existing `--warning` CSS variable (Catppuccin gold) instead of Tailwind's yellow-500
- **TD-2:** Use existing `--success` CSS variable (Catppuccin green) instead of Tailwind's green-*
- **TD-3:** Use existing `--destructive` CSS variable (Catppuccin red) instead of Tailwind's red-*
- **TD-4:** Use existing `--primary` CSS variable (Catppuccin purple) for accent/highlight states
- **TD-5:** Use existing `--muted` CSS variable (Catppuccin gray) for neutral/disconnected states
- **TD-6:** Create utility classes in index.css to prevent future inconsistencies and enable reuse

## Implementation Plan

### Tasks

- [x] **Task 1: Add semantic utility classes to index.css**
  - File: `web/src/styles/index.css`
  - Action: Add utility classes for badges, banners, and status indicators using CSS variables
  - Classes to add:
    - `.badge-success` - green badge for compatible/installed states
    - `.badge-warning` - yellow badge for not_verified/unstable states
    - `.badge-destructive` - red badge for incompatible/error states
    - `.badge-primary` - purple badge for primary/accent states
    - `.banner-warning` - yellow warning banner styling
    - `.banner-primary` - purple primary banner styling
    - `.status-indicator-success` - green status dot
    - `.status-indicator-warning` - yellow status dot
    - `.status-indicator-destructive` - red status dot
    - `.status-indicator-muted` - gray status dot
  - Notes: Use `@apply` with Tailwind classes that reference CSS variables (e.g., `bg-success/20 text-success border-success/30`)

- [x] **Task 2: Fix CompatibilityBadge.tsx (CRITICAL)**
  - File: `web/src/components/CompatibilityBadge.tsx`
  - Action: Replace hardcoded hex values with semantic Tailwind classes
  - Changes:
    - `bg-[#a6e3a1]/20 text-[#a6e3a1] border-[#a6e3a1]/30` → `bg-success/20 text-success border-success/30`
    - `bg-[#f9e2af]/20 text-[#f9e2af] border-[#f9e2af]/30` → `bg-warning/20 text-warning border-warning/30`
    - `bg-[#f38ba8]/20 text-[#f38ba8] border-[#f38ba8]/30` → `bg-destructive/20 text-destructive border-destructive/30`
  - Notes: Update component docstring to remove hardcoded hex references

- [x] **Task 3: Fix PendingRestartBanner.tsx (CRITICAL)**
  - File: `web/src/components/PendingRestartBanner.tsx`
  - Action: Replace hardcoded `#cba6f7` with semantic primary variable
  - Changes:
    - `bg-[#cba6f7]/20` → `bg-primary/20`
    - `text-[#cba6f7]` → `text-primary`
    - `hover:bg-[#cba6f7]/20 hover:text-[#cba6f7]` → `hover:bg-primary/20 hover:text-primary`

- [x] **Task 4: Fix DiskSpaceWarningBanner.tsx**
  - File: `web/src/components/DiskSpaceWarningBanner.tsx`
  - Action: Replace `yellow-500` with semantic warning variable
  - Changes:
    - `bg-yellow-500/20` → `bg-warning/20`
    - `text-yellow-500` → `text-warning`

- [x] **Task 5: Fix ConnectionStatus.tsx**
  - File: `web/src/components/terminal/ConnectionStatus.tsx`
  - Action: Replace all hardcoded Tailwind colors with semantic variables
  - Changes:
    - `bg-yellow-500` → `bg-warning`
    - `text-yellow-600 dark:text-yellow-400` → `text-warning`
    - `bg-green-500` → `bg-success`
    - `text-green-600 dark:text-green-400` → `text-success`
    - `bg-gray-500` → `bg-muted-foreground`
    - `text-gray-600 dark:text-gray-400` → `text-muted-foreground`
    - `bg-red-500` → `bg-destructive`
    - `text-red-600 dark:text-red-400` → `text-destructive`

- [x] **Task 6: Fix VersionCard.tsx**
  - File: `web/src/components/VersionCard.tsx`
  - Action: Replace channel badge colors and installed indicator
  - Changes:
    - Stable channel: `text-green-600 border-green-200 bg-green-50 dark:bg-green-950 dark:border-green-800 dark:text-green-400` → `text-success border-success/30 bg-success/10`
    - Unstable channel: `text-yellow-600 border-yellow-200 bg-yellow-50 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-400` → `text-warning border-warning/30 bg-warning/10`
    - Installed indicator: `text-green-500` → `text-success`

- [x] **Task 7: Fix warning dialogs (InstallConfirmDialog, UninstallConfirmDialog, InstallVersionDialog)**
  - Files:
    - `web/src/components/InstallConfirmDialog.tsx`
    - `web/src/components/UninstallConfirmDialog.tsx`
    - `web/src/components/InstallVersionDialog.tsx`
  - Action: Replace `yellow-500` with semantic warning variable in warning message sections
  - Changes:
    - `bg-yellow-500/10` → `bg-warning/10`
    - `border-yellow-500/20` → `border-warning/20`
    - `text-yellow-500` → `text-warning`

- [x] **Task 8: Fix remaining components (SettingField, QuickInstallButton, ModCard, ModDetailPage)**
  - Files:
    - `web/src/components/SettingField.tsx` - env badge
    - `web/src/components/QuickInstallButton.tsx` - warning icon
    - `web/src/components/ModCard.tsx` - installed indicator
    - `web/src/features/mods/ModDetailPage.tsx` - installed icon
  - Action: Replace remaining hardcoded colors
  - Changes:
    - SettingField: `bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/30` → `bg-warning/10 text-warning border-warning/30`
    - QuickInstallButton: `text-yellow-500` → `text-warning`
    - ModCard: `text-green-500` → `text-success`
    - ModDetailPage: `text-green-500` → `text-success`

- [x] **Task 9: Update test files**
  - Files:
    - `web/src/components/CompatibilityBadge.test.tsx`
    - `web/src/components/DiskSpaceWarningBanner.test.tsx`
    - `web/src/components/PendingRestartBanner.test.tsx`
  - Action: Update test assertions to check for semantic classes instead of hardcoded hex/color values
  - Notes: Tests should verify semantic class names, not specific color codes

- [x] **Task 10: Run tests and visual verification**
  - Action: Verify all changes work correctly
  - Steps:
    1. Run `just test-web` to verify no test regressions
    2. Run `just docker restart` for visual verification
    3. Test both light and dark themes
    4. Verify all 12 components render correctly

### Acceptance Criteria

- [x] **AC 1:** Given the utility classes are added to index.css, when a developer uses `.badge-success`, `.badge-warning`, `.badge-destructive`, or `.banner-warning`, then the styles automatically adapt to light/dark themes using CSS variables.

- [x] **AC 2:** Given CompatibilityBadge renders in light mode, when the status is "compatible", then the badge displays using the Catppuccin Latte green (`#40a02b`) instead of Mocha green (`#a6e3a1`).

- [x] **AC 3:** Given PendingRestartBanner renders in light mode, when the banner is visible, then it displays using the Catppuccin Latte purple (`#8839ef`) instead of Mocha purple (`#cba6f7`).

- [x] **AC 4:** Given ConnectionStatus displays "Connected" state, when the theme is toggled between light and dark, then the green indicator color changes appropriately (Latte: `#40a02b`, Mocha: `#a6e3a1`).

- [x] **AC 5:** Given all warning banners (DiskSpaceWarning, InstallConfirm, UninstallConfirm, InstallVersion), when displayed in light mode, then they use the Catppuccin Latte yellow (`#df8e1d`) instead of Tailwind's yellow-500.

- [x] **AC 6:** Given the codebase is searched for hardcoded color patterns, when running `grep -r "yellow-500\|green-500\|red-500\|#[a-f0-9]{6}" web/src/components`, then no matches are found in the 12 fixed component files.

- [x] **AC 7:** Given `just test-web` is executed, when all tests complete, then there are no test failures related to the theme changes.

- [x] **AC 8:** Given the web UI is viewed in Docker (`just docker restart`), when toggling between light and dark themes, then all 12 modified components display correct themed colors without any hardcoded values visible.

## Additional Context

### Dependencies

None - purely CSS/styling changes

### Testing Strategy

- Run `just test-web` to verify no regressions
- Update test assertions to check for semantic classes instead of hardcoded colors
- Visual inspection in both light and dark themes via `just docker restart`
- Verify all 12 components render correctly after refactor
- Check that new utility classes work as expected

### Notes

- Bead reference: VSS-9vz
- Branch: `bead_VSS-9vz_ui/theme-consistency-audit`
- Baseline commit: `995aba1da563c38175bf6baa3982cf106a5994b3`
- The existing `@theme inline` block in index.css already maps CSS variables to Tailwind color tokens, so classes like `bg-success`, `text-warning`, etc. should work out of the box
