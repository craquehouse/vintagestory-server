import { useEffect, useRef, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

import { cn } from '@/lib/utils';
import { getTerminalTheme } from '@/lib/terminal-themes';
import { useTheme } from '@/hooks/use-theme';
import { usePreferences, FONT_SIZE_DEFAULT } from '@/contexts/PreferencesContext';

export interface TerminalViewProps {
  /** Callback when terminal is initialized and ready */
  onReady?: (terminal: Terminal) => void;
  /** Callback when terminal is disposed */
  onDispose?: () => void;
  /** Additional CSS classes for the container */
  className?: string;
  /** Override font size from preferences (optional, defaults to user preference) */
  fontSize?: number;
}

/**
 * Terminal component using xterm.js with Catppuccin theming.
 *
 * This component initializes and manages an xterm.js terminal instance
 * with automatic resize handling and theme synchronization.
 *
 * @example
 * ```tsx
 * <TerminalView
 *   onReady={(terminal) => console.log('Terminal ready', terminal)}
 *   className="h-full"
 * />
 * ```
 */
export function TerminalView({
  onReady,
  onDispose,
  className,
  fontSize: fontSizeProp,
}: TerminalViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const isInitializedRef = useRef(false);

  // Store callbacks in refs to avoid recreating terminal when callbacks change
  const onReadyRef = useRef(onReady);
  const onDisposeRef = useRef(onDispose);
  onReadyRef.current = onReady;
  onDisposeRef.current = onDispose;

  const { resolvedTheme } = useTheme();
  const themeMode = resolvedTheme === 'dark' ? 'dark' : 'light';

  // Get font size from preferences, with prop override
  const { preferences } = usePreferences();
  const fontSize = fontSizeProp ?? preferences.consoleFontSize ?? FONT_SIZE_DEFAULT;

  // Update theme when it changes
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.options.theme = getTerminalTheme(themeMode);
    }
  }, [themeMode]);

  // Update font size when it changes
  useEffect(() => {
    if (terminalRef.current && fitAddonRef.current) {
      terminalRef.current.options.fontSize = fontSize;
      // Re-fit terminal after font size change
      try {
        fitAddonRef.current.fit();
      } catch {
        // Terminal may be disposed
      }
    }
  }, [fontSize]);

  // Fit terminal to container - memoized for use in effects
  const fit = useCallback(() => {
    if (fitAddonRef.current) {
      try {
        fitAddonRef.current.fit();
      } catch {
        // Terminal may be disposed during resize
      }
    }
  }, []);

  // Initialize terminal - only runs once on mount
  useEffect(() => {
    if (!containerRef.current || isInitializedRef.current) return;

    const terminal = new Terminal({
      cursorBlink: true,
      fontSize,
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
      convertEol: true,
      theme: getTerminalTheme(themeMode),
    });

    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);

    terminal.open(containerRef.current);
    fitAddon.fit();

    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;
    isInitializedRef.current = true;

    onReadyRef.current?.(terminal);

    return () => {
      isInitializedRef.current = false;
      terminal.dispose();
      terminalRef.current = null;
      fitAddonRef.current = null;
      onDisposeRef.current?.();
    };
    // Only depend on themeMode for initial theme - callbacks are in refs
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle resize with ResizeObserver
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;

    const resizeObserver = new ResizeObserver(() => {
      // Use requestAnimationFrame to debounce and ensure DOM is ready
      requestAnimationFrame(fit);
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
    };
  }, [fit]);

  return (
    <div
      ref={containerRef}
      className={cn('min-h-0 min-w-0', className)}
      role="application"
      aria-label="Server console terminal"
    />
  );
}
