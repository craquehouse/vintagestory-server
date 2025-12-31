# Story 3.4: Dashboard with Server Controls UI

Status: done

## Summary
Created web dashboard with server status display and control buttons.

## Components Created
- **ServerStatusBadge** - Shows state with color/icon (green=running, red=stopped, yellow=transitional)
- **ServerInstallCard** - Version input + install button + progress indicator
- **ServerControls** - Start/Stop/Restart buttons with loading states
- **Dashboard** - Integrates all components conditionally

## Conditional Rendering
- `not_installed` or `installing` → ServerInstallCard
- Otherwise → ServerStatusBadge + version + uptime + ServerControls

## API Hooks Created (`use-server-status.ts`)
- `useServerStatus()` - Polls every 5s
- `useInstallStatus()` - Polls every 1s during install
- `useStartServer()`, `useStopServer()`, `useRestartServer()` - Mutations
- `useInstallServer()` - Install mutation

## Toast Notifications
Uses sonner for success/failure messages on all actions.

## Files Created
- web/src/components/ServerStatusBadge.tsx
- web/src/components/ServerInstallCard.tsx
- web/src/features/dashboard/ServerControls.tsx
- web/src/api/server.ts
- web/src/hooks/use-server-status.ts

## Tests
64 new tests (176 total web tests)
