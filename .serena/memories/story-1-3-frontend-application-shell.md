# Story 1.3: Frontend Application Shell

Status: done

## Summary
Created web UI shell with Catppuccin theming, responsive sidebar navigation, and React Router routing.

## Key Components
- **Layout**: Header (48px) + Sidebar (240px/64px collapsed) + Main content
- **Theme**: Catppuccin Mocha (dark) / Latte (light) with localStorage persistence
- **Navigation**: Dashboard, Mods, Config, Terminal with active highlighting

## Routes
- `/` - Dashboard
- `/mods` - ModList
- `/config` - ConfigEditor
- `/terminal` - Terminal

## Dependencies Added
- react-router v7.11.0
- @tanstack/react-query v5.90.12
- shadcn/ui: separator, tooltip, sheet, dropdown-menu, switch, avatar

## Files Created
- web/src/styles/themes/{mocha.json, latte.json}
- web/src/contexts/{ThemeContext.tsx, SidebarContext.tsx}
- web/src/hooks/use-theme.ts
- web/src/components/layout/{Header.tsx, Sidebar.tsx, Layout.tsx}
- web/src/features/{dashboard/Dashboard.tsx, mods/ModList.tsx, config/ConfigEditor.tsx, terminal/Terminal.tsx}

## Tests
67 tests passing - covers theming, sidebar, layout, navigation
