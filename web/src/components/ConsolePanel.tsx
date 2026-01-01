/**
 * ConsolePanel component for reusable server console display.
 *
 * Extracted from Terminal.tsx for use in split layouts.
 * Provides real-time console output and command input.
 *
 * Story 6.4: Settings UI
 */

import { useRef, useState, useCallback } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import type { Terminal as XTerminal } from '@xterm/xterm';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TerminalView } from '@/components/terminal/TerminalView';
import { ConnectionStatus } from '@/components/terminal/ConnectionStatus';
import { useConsoleWebSocket } from '@/hooks/use-console-websocket';
import { useServerStatus } from '@/hooks/use-server-status';
import { cn } from '@/lib/utils';

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
 * - Command input field for sending commands
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

  const { connectionState, sendCommand } = useConsoleWebSocket({
    onMessage: writeToTerminal,
  });

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
    if (trimmedCommand && connectionState === 'connected' && serverState === 'running') {
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

  const isConnected = connectionState === 'connected';
  const isServerRunning = serverState === 'running';
  const canSendCommands = isConnected && isServerRunning;

  // Determine input placeholder based on state
  const getPlaceholder = () => {
    if (!isConnected) return 'Disconnected';
    if (!isServerRunning) return 'Server not running';
    return 'Enter command...';
  };

  return (
    <Card
      className={cn('flex flex-col overflow-hidden', className)}
      data-testid="console-panel"
    >
      {showHeader && (
        <CardHeader className="flex-shrink-0 border-b py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">{title}</CardTitle>
            <ConnectionStatus state={connectionState} serverState={serverState} />
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
