/**
 * ConsolePanel component for reusable server console display.
 *
 * Extracted from Terminal.tsx for use in split layouts.
 * Provides real-time console output and command input.
 * Also supports streaming log files from the Logs directory.
 *
 * Story 6.4: Settings UI
 * Polish: UI-005, API-006 - Log file streaming
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import type { Terminal as XTerminal } from '@xterm/xterm';
import { ChevronDown, FileText, Terminal } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TerminalView } from '@/components/terminal/TerminalView';
import { ConnectionStatus } from '@/components/terminal/ConnectionStatus';
import { useConsoleWebSocket } from '@/hooks/use-console-websocket';
import { useLogStream } from '@/hooks/use-log-stream';
import { useLogFiles } from '@/hooks/use-log-files';
import { useServerStatus } from '@/hooks/use-server-status';
import { cn } from '@/lib/utils';

/**
 * Output source type - either the live console or a log file.
 */
export type OutputSource =
  | { type: 'console' }
  | { type: 'logfile'; filename: string };

/**
 * Props for the ConsolePanel component.
 */
export interface ConsolePanelProps {
  /**
   * Optional title override.
   * @default "Server Console"
   */
  title?: string;

  /**
   * Whether to show the header.
   * @default true
   */
  showHeader?: boolean;

  /**
   * Additional CSS class names.
   */
  className?: string;
}

/**
 * Reusable console panel for displaying server output.
 *
 * Features:
 * - Real-time console output via WebSocket
 * - Log file streaming via WebSocket
 * - Source selector dropdown (Console vs Log files)
 * - Command input field for sending commands (console mode only)
 * - Connection status indicator
 * - Theme-aware styling
 *
 * @example
 * // In split layout
 * <ConsolePanel className="flex-1" />
 *
 * @example
 * // Without header for compact views
 * <ConsolePanel showHeader={false} />
 */
export function ConsolePanel({
  title = 'Server Console',
  showHeader = true,
  className,
}: ConsolePanelProps) {
  const terminalRef = useRef<XTerminal | null>(null);
  const messageQueueRef = useRef<string[]>([]);
  const [command, setCommand] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<OutputSource>({ type: 'console' });
  const prevSourceRef = useRef<OutputSource>(source);

  // Fetch available log files
  const { data: logFilesResponse } = useLogFiles();
  const logFiles = logFilesResponse?.data?.files ?? [];

  // Get server status for connection indicator
  const { data: statusResponse } = useServerStatus();
  const serverState = statusResponse?.data?.state;

  // Write a message to terminal, or queue if terminal not ready
  const writeToTerminal = useCallback((data: string) => {
    if (terminalRef.current) {
      terminalRef.current.writeln(data);
    } else {
      // Queue messages that arrive before terminal is ready
      messageQueueRef.current.push(data);
    }
  }, []);

  // Console WebSocket - only active when source is console
  const { connectionState: consoleConnectionState, sendCommand } =
    useConsoleWebSocket({
      onMessage: source.type === 'console' ? writeToTerminal : undefined,
    });

  // Log file WebSocket - only active when source is a log file
  const { connectionState: logConnectionState } = useLogStream({
    filename: source.type === 'logfile' ? source.filename : '',
    enabled: source.type === 'logfile',
    onMessage: writeToTerminal,
  });

  // Get the effective connection state based on current source
  const connectionState =
    source.type === 'console' ? consoleConnectionState : logConnectionState;

  // Clear terminal when source changes
  useEffect(() => {
    if (
      prevSourceRef.current.type !== source.type ||
      (prevSourceRef.current.type === 'logfile' &&
        source.type === 'logfile' &&
        prevSourceRef.current.filename !== source.filename)
    ) {
      if (terminalRef.current) {
        terminalRef.current.clear();
      }
      messageQueueRef.current = [];
      prevSourceRef.current = source;
    }
  }, [source]);

  // Handle terminal ready - flush any queued messages
  const handleTerminalReady = useCallback((terminal: XTerminal) => {
    terminalRef.current = terminal;

    // Flush queued messages
    if (messageQueueRef.current.length > 0) {
      for (const msg of messageQueueRef.current) {
        terminal.writeln(msg);
      }
      messageQueueRef.current = [];
    }
  }, []);

  // Handle terminal cleanup
  const handleTerminalDispose = useCallback(() => {
    terminalRef.current = null;
  }, []);

  // Handle command submission
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmedCommand = command.trim();
    if (
      trimmedCommand &&
      source.type === 'console' &&
      consoleConnectionState === 'connected' &&
      serverState === 'running'
    ) {
      sendCommand(trimmedCommand);
      setCommand('');
    }
  };

  // Handle Enter key in input
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isConsoleMode = source.type === 'console';
  const isConnected = connectionState === 'connected';
  const isServerRunning = serverState === 'running';
  const canSendCommands = isConsoleMode && isConnected && isServerRunning;

  // Determine input placeholder based on state
  const getPlaceholder = () => {
    if (!isConsoleMode) return 'Viewing log file (read-only)';
    if (!isConnected) return 'Disconnected';
    if (!isServerRunning) return 'Server not running';
    return 'Enter command...';
  };

  // Get display name for current source
  const getSourceLabel = () => {
    if (source.type === 'console') return 'Console';
    return source.filename;
  };

  // Map log connection state to console connection state for ConnectionStatus
  const getDisplayConnectionState = (): 'connecting' | 'connected' | 'disconnected' | 'forbidden' => {
    if (source.type === 'console') return consoleConnectionState;
    // Map log-specific states to compatible states
    const state = logConnectionState;
    if (state === 'not_found' || state === 'invalid') return 'disconnected';
    return state;
  };

  return (
    <Card
      className={cn('flex flex-col overflow-hidden', className)}
      data-testid="console-panel"
    >
      {showHeader && (
        <CardHeader className="flex-shrink-0 border-b py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{title}</CardTitle>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 gap-1 text-xs"
                    data-testid="source-selector"
                  >
                    {source.type === 'console' ? (
                      <Terminal className="h-3 w-3" />
                    ) : (
                      <FileText className="h-3 w-3" />
                    )}
                    {getSourceLabel()}
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuLabel>Output Source</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setSource({ type: 'console' })}
                    className={cn(source.type === 'console' && 'bg-accent')}
                  >
                    <Terminal className="mr-2 h-4 w-4" />
                    Live Console
                  </DropdownMenuItem>
                  {logFiles.length > 0 && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuLabel className="text-xs text-muted-foreground">
                        Log Files
                      </DropdownMenuLabel>
                      {logFiles.map((file) => (
                        <DropdownMenuItem
                          key={file.name}
                          onClick={() =>
                            setSource({ type: 'logfile', filename: file.name })
                          }
                          className={cn(
                            source.type === 'logfile' &&
                              source.filename === file.name &&
                              'bg-accent'
                          )}
                        >
                          <FileText className="mr-2 h-4 w-4" />
                          <span className="truncate">{file.name}</span>
                        </DropdownMenuItem>
                      ))}
                    </>
                  )}
                  {logFiles.length === 0 && (
                    <DropdownMenuItem disabled>
                      <span className="text-muted-foreground text-xs">
                        No log files available
                      </span>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <ConnectionStatus
              state={getDisplayConnectionState()}
              serverState={serverState}
            />
          </div>
        </CardHeader>
      )}
      <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
        <div className="flex-1 overflow-hidden">
          <TerminalView
            onReady={handleTerminalReady}
            onDispose={handleTerminalDispose}
            className="h-full w-full"
          />
        </div>
        <form
          onSubmit={handleSubmit}
          className="flex gap-2 border-t bg-muted/50 p-3"
        >
          <Input
            ref={inputRef}
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={getPlaceholder()}
            disabled={!canSendCommands}
            className="flex-1 font-mono"
            aria-label="Command input"
          />
          <Button
            type="submit"
            disabled={!canSendCommands || !command.trim()}
            variant="default"
          >
            Send
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
