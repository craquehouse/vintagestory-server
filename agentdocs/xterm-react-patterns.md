# xterm.js + React Integration Patterns

This document contains research findings and patterns for implementing a terminal component with xterm.js in React for Epic 4.

## Required npm Packages

```bash
bun add @xterm/xterm@^5 @xterm/addon-fit@^0.10 @xterm/addon-attach@^0.11
```

| Package | Version | Purpose |
|---------|---------|---------|
| `@xterm/xterm` | ^5.x | Core terminal emulator |
| `@xterm/addon-fit` | ^0.10.x | Auto-resize terminal to container |
| `@xterm/addon-attach` | ^0.11.x | Bidirectional WebSocket I/O |

**Optional but recommended:**
- `@xterm/addon-web-links` - Clickable URLs in terminal output

**Note:** Pin to major versions to avoid breaking changes. The xterm.js 5.x series has a stable API.

## React Integration Pattern

### Basic Terminal Component with Refs

```tsx
import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';
import '@xterm/xterm/css/xterm.css';

interface TerminalViewProps {
  websocketUrl: string;
  className?: string;
}

export function TerminalView({ websocketUrl, className }: TerminalViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize terminal
    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
      convertEol: true,  // Convert \n to \r\n for proper line handling
    });
    terminalRef.current = terminal;

    // Add fit addon
    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    terminal.loadAddon(fitAddon);

    // Open terminal in container
    terminal.open(containerRef.current);
    fitAddon.fit();

    // Connect to WebSocket
    const ws = new WebSocket(websocketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      // Attach WebSocket for bidirectional I/O
      const attachAddon = new AttachAddon(ws);
      terminal.loadAddon(attachAddon);
      terminal.writeln('\x1b[32mConnected to server console\x1b[0m');
    };

    ws.onerror = () => {
      terminal.writeln('\x1b[31mConnection error\x1b[0m');
    };

    ws.onclose = (event) => {
      terminal.writeln(`\x1b[33mDisconnected (code: ${event.code})\x1b[0m`);
    };

    // Cleanup
    return () => {
      ws.close();
      terminal.dispose();
    };
  }, [websocketUrl]);

  // Handle resize
  useEffect(() => {
    if (!containerRef.current || !fitAddonRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      // Use requestAnimationFrame to debounce and ensure DOM is ready
      requestAnimationFrame(() => {
        fitAddonRef.current?.fit();
      });
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', height: '100%' }}
    />
  );
}
```

### Usage in a Page Component

```tsx
import { TerminalView } from '@/components/terminal-view';

export function ConsolePage() {
  const apiKey = localStorage.getItem('apiKey') || '';
  const wsUrl = `ws://${window.location.host}/api/v1alpha1/console?api_key=${apiKey}`;

  return (
    <div className="h-full p-4">
      <h1 className="text-xl font-bold mb-4">Server Console</h1>
      <div className="h-[calc(100vh-8rem)] bg-gray-900 rounded-lg overflow-hidden">
        <TerminalView websocketUrl={wsUrl} className="h-full" />
      </div>
    </div>
  );
}
```

## WebSocket Reconnection with Exponential Backoff

```tsx
import { useCallback, useEffect, useRef, useState } from 'react';

interface UseWebSocketReconnectOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

export function useWebSocketReconnect(
  url: string,
  options: UseWebSocketReconnectOptions = {}
) {
  const { maxRetries = 10, baseDelayMs = 1000, maxDelayMs = 30000 } = options;

  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const socket = new WebSocket(url);

    socket.onopen = () => {
      setIsConnected(true);
      setRetryCount(0);
    };

    socket.onclose = (event) => {
      setIsConnected(false);

      // Don't reconnect if closed intentionally (code 1000) or forbidden (4003)
      if (event.code === 1000 || event.code === 4003) {
        return;
      }

      // Schedule reconnect with exponential backoff + jitter
      if (retryCount < maxRetries) {
        const delay = Math.min(baseDelayMs * Math.pow(2, retryCount), maxDelayMs);
        const jitter = Math.random() * 1000;

        reconnectTimeoutRef.current = window.setTimeout(() => {
          setRetryCount((c) => c + 1);
          connect();
        }, delay + jitter);
      }
    };

    socket.onerror = () => {
      // Error will trigger onclose
    };

    setWs(socket);
  }, [url, retryCount, maxRetries, baseDelayMs, maxDelayMs]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      ws?.close(1000, 'Component unmounting');
    };
  }, [url]); // Only reconnect if URL changes

  return { ws, isConnected, retryCount, isReconnecting: retryCount > 0 };
}
```

## Theming with Catppuccin

xterm.js supports custom themes via the `theme` option. Here's how to integrate with Catppuccin Mocha (dark) and Latte (light):

### Theme Definition

```typescript
import type { ITheme } from '@xterm/xterm';

// Catppuccin Mocha (dark theme)
export const catppuccinMocha: ITheme = {
  background: '#1e1e2e',
  foreground: '#cdd6f4',
  cursor: '#f5e0dc',
  cursorAccent: '#1e1e2e',
  selectionBackground: '#585b70',
  selectionForeground: '#cdd6f4',
  black: '#45475a',
  red: '#f38ba8',
  green: '#a6e3a1',
  yellow: '#f9e2af',
  blue: '#89b4fa',
  magenta: '#f5c2e7',
  cyan: '#94e2d5',
  white: '#bac2de',
  brightBlack: '#585b70',
  brightRed: '#f38ba8',
  brightGreen: '#a6e3a1',
  brightYellow: '#f9e2af',
  brightBlue: '#89b4fa',
  brightMagenta: '#f5c2e7',
  brightCyan: '#94e2d5',
  brightWhite: '#a6adc8',
};

// Catppuccin Latte (light theme)
export const catppuccinLatte: ITheme = {
  background: '#eff1f5',
  foreground: '#4c4f69',
  cursor: '#dc8a78',
  cursorAccent: '#eff1f5',
  selectionBackground: '#acb0be',
  selectionForeground: '#4c4f69',
  black: '#5c5f77',
  red: '#d20f39',
  green: '#40a02b',
  yellow: '#df8e1d',
  blue: '#1e66f5',
  magenta: '#ea76cb',
  cyan: '#179299',
  white: '#acb0be',
  brightBlack: '#6c6f85',
  brightRed: '#d20f39',
  brightGreen: '#40a02b',
  brightYellow: '#df8e1d',
  brightBlue: '#1e66f5',
  brightMagenta: '#ea76cb',
  brightCyan: '#179299',
  brightWhite: '#bcc0cc',
};
```

### Theme-Aware Terminal Component

```tsx
import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { catppuccinMocha, catppuccinLatte } from '@/lib/terminal-themes';

interface TerminalViewProps {
  theme: 'light' | 'dark';
  // ... other props
}

export function TerminalView({ theme, ...props }: TerminalViewProps) {
  const terminalRef = useRef<Terminal | null>(null);

  // Update theme when it changes
  useEffect(() => {
    if (!terminalRef.current) return;

    const terminalTheme = theme === 'dark' ? catppuccinMocha : catppuccinLatte;
    terminalRef.current.options.theme = terminalTheme;
  }, [theme]);

  // Initial setup with theme
  useEffect(() => {
    const terminal = new Terminal({
      theme: theme === 'dark' ? catppuccinMocha : catppuccinLatte,
      // ... other options
    });
    terminalRef.current = terminal;
    // ... rest of setup
  }, []);

  // ...
}
```

### CSS Variables Integration (Alternative)

If using CSS variables for theming, you can read them:

```typescript
function getTerminalTheme(): ITheme {
  const style = getComputedStyle(document.documentElement);

  return {
    background: style.getPropertyValue('--terminal-bg').trim() || '#1e1e2e',
    foreground: style.getPropertyValue('--terminal-fg').trim() || '#cdd6f4',
    cursor: style.getPropertyValue('--terminal-cursor').trim() || '#f5e0dc',
    // ... etc
  };
}
```

## Resize Handling

### Pattern: ResizeObserver with Debouncing

```tsx
useEffect(() => {
  if (!containerRef.current || !fitAddonRef.current) return;

  const fitAddon = fitAddonRef.current;

  const resizeObserver = new ResizeObserver(() => {
    // requestAnimationFrame debounces rapid resize events
    requestAnimationFrame(() => {
      try {
        fitAddon.fit();
      } catch (e) {
        // Terminal may be disposed during resize
        console.warn('Terminal fit failed:', e);
      }
    });
  });

  resizeObserver.observe(containerRef.current);

  return () => {
    resizeObserver.disconnect();
  };
}, []);
```

### Notify Server of Size Changes

When the terminal resizes, notify the backend so it can adjust its PTY size:

```tsx
useEffect(() => {
  if (!terminalRef.current || !wsRef.current) return;

  const terminal = terminalRef.current;
  const ws = wsRef.current;

  const handleResize = () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'resize',
        cols: terminal.cols,
        rows: terminal.rows,
      }));
    }
  };

  terminal.onResize(handleResize);

  return () => {
    // Cleanup handled by terminal.dispose()
  };
}, []);
```

## Accessibility Considerations

### 1. Announce Connection Status to Screen Readers

```tsx
function TerminalStatusAnnouncer({ isConnected }: { isConnected: boolean }) {
  return (
    <div role="status" aria-live="polite" className="sr-only">
      {isConnected ? 'Connected to server console' : 'Disconnected from server console'}
    </div>
  );
}
```

### 2. Keyboard Focus Management

```tsx
// Focus terminal on mount or when activated
useEffect(() => {
  if (isActive && terminalRef.current) {
    terminalRef.current.focus();
  }
}, [isActive]);
```

### 3. xterm.js Built-in Accessibility

xterm.js has built-in screen reader support. Ensure the container has proper ARIA attributes:

```tsx
<div
  ref={containerRef}
  role="application"
  aria-label="Server console terminal"
/>
```

## Error States and UI Feedback

```tsx
type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error' | 'forbidden';

function ConnectionStatusBadge({ state }: { state: ConnectionState }) {
  const statusConfig = {
    connecting: { label: 'Connecting...', className: 'bg-yellow-500' },
    connected: { label: 'Connected', className: 'bg-green-500' },
    disconnected: { label: 'Disconnected', className: 'bg-gray-500' },
    error: { label: 'Connection Error', className: 'bg-red-500' },
    forbidden: { label: 'Access Denied', className: 'bg-red-500' },
  };

  const config = statusConfig[state];

  return (
    <span className={`px-2 py-1 rounded text-white text-sm ${config.className}`}>
      {config.label}
    </span>
  );
}
```

## Complete Terminal Component Example

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';
import '@xterm/xterm/css/xterm.css';

import { catppuccinMocha, catppuccinLatte } from '@/lib/terminal-themes';

interface ConsoleTerminalProps {
  apiKey: string;
  theme?: 'light' | 'dark';
}

export function ConsoleTerminal({ apiKey, theme = 'dark' }: ConsoleTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const [connectionState, setConnectionState] = useState<
    'connecting' | 'connected' | 'disconnected' | 'forbidden'
  >('connecting');
  const [retryCount, setRetryCount] = useState(0);

  const maxRetries = 10;

  // Initialize terminal
  useEffect(() => {
    if (!containerRef.current) return;

    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
      convertEol: true,
      theme: theme === 'dark' ? catppuccinMocha : catppuccinLatte,
    });
    terminalRef.current = terminal;

    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    terminal.loadAddon(fitAddon);

    terminal.open(containerRef.current);
    fitAddon.fit();

    return () => {
      terminal.dispose();
    };
  }, [theme]);

  // Handle theme changes
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.options.theme =
        theme === 'dark' ? catppuccinMocha : catppuccinLatte;
    }
  }, [theme]);

  // WebSocket connection with reconnection
  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/api/v1alpha1/console?api_key=${apiKey}`
      );
      wsRef.current = ws;
      setConnectionState('connecting');

      ws.onopen = () => {
        setConnectionState('connected');
        setRetryCount(0);

        if (terminalRef.current) {
          const attachAddon = new AttachAddon(ws);
          terminalRef.current.loadAddon(attachAddon);
          terminalRef.current.writeln('\x1b[32m--- Connected to server console ---\x1b[0m');
        }
      };

      ws.onclose = (event) => {
        if (event.code === 4003) {
          setConnectionState('forbidden');
          terminalRef.current?.writeln('\x1b[31m--- Access denied ---\x1b[0m');
          return;
        }

        setConnectionState('disconnected');
        terminalRef.current?.writeln('\x1b[33m--- Disconnected ---\x1b[0m');

        // Reconnect with exponential backoff
        if (event.code !== 1000 && retryCount < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
          const jitter = Math.random() * 1000;

          terminalRef.current?.writeln(
            `\x1b[33mReconnecting in ${Math.round((delay + jitter) / 1000)}s...\x1b[0m`
          );

          reconnectTimeoutRef.current = window.setTimeout(() => {
            setRetryCount((c) => c + 1);
            connect();
          }, delay + jitter);
        }
      };

      ws.onerror = () => {
        // Error triggers onclose
      };
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close(1000);
    };
  }, [apiKey, retryCount]);

  // Resize handling
  useEffect(() => {
    if (!containerRef.current || !fitAddonRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        fitAddonRef.current?.fit();
      });
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm text-gray-300">Server Console</span>
        <ConnectionStatus state={connectionState} />
      </div>
      <div
        ref={containerRef}
        className="flex-1"
        role="application"
        aria-label="Server console terminal"
      />
    </div>
  );
}

function ConnectionStatus({
  state,
}: {
  state: 'connecting' | 'connected' | 'disconnected' | 'forbidden';
}) {
  const config = {
    connecting: { color: 'bg-yellow-500', label: 'Connecting...' },
    connected: { color: 'bg-green-500', label: 'Connected' },
    disconnected: { color: 'bg-gray-500', label: 'Disconnected' },
    forbidden: { color: 'bg-red-500', label: 'Access Denied' },
  }[state];

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${config.color}`} />
      <span className="text-xs text-gray-400">{config.label}</span>
    </div>
  );
}
```

## References

- [xterm.js Documentation](https://xtermjs.org/)
- [xterm.js GitHub](https://github.com/xtermjs/xterm.js)
- [@xterm/addon-fit](https://github.com/xtermjs/xterm.js/tree/master/addons/addon-fit)
- [@xterm/addon-attach](https://github.com/xtermjs/xterm.js/tree/master/addons/addon-attach)
- [Catppuccin Color Palette](https://catppuccin.com/)
- Project Architecture: `_bmad-output/planning-artifacts/architecture.md`
- WebSocket Backend: `agentdocs/fastapi-websocket-patterns.md`
