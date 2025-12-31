# Story 4.4: Terminal View Component

Status: done

## Summary
Implemented web terminal component using xterm.js with Catppuccin theming and WebSocket integration.

## Components Created
- **TerminalView** - Main xterm.js wrapper with FitAddon, ResizeObserver
- **ConnectionStatus** - Status indicator with ARIA live region
- **use-console-websocket** - Hook for WebSocket connection with exponential backoff

## xterm.js Integration
```typescript
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';
```

## WebSocket Connection
- URL: `ws://host/api/v1alpha1/console/ws?api_key=${key}&history_lines=100`
- Exponential backoff: base 1s, max 30s, jitter, max 10 retries
- Connection states: connecting | connected | disconnected | forbidden

## Catppuccin Themes
- Dark: Mocha (background #1e1e2e)
- Light: Latte (background #eff1f5)
- Switches with ThemeContext

## Files Created
- web/src/lib/terminal-themes.ts
- web/src/components/terminal/TerminalView.tsx
- web/src/components/terminal/ConnectionStatus.tsx
- web/src/hooks/use-console-websocket.ts

## Post-Implementation Fixes
- E2E tests: Fixed API endpoint URLs
- pytest-asyncio: Excluded E2E from default test run
- Version aliases: Added "stable"/"unstable" support
- Sidebar: Changed "Terminal" → "Console"
