import { useRef, useState, useCallback } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import type { Terminal as XTerminal } from '@xterm/xterm';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TerminalView } from '@/components/terminal/TerminalView';
import { ConnectionStatus } from '@/components/terminal/ConnectionStatus';
import { useConsoleWebSocket } from '@/hooks/use-console-websocket';

/**
 * Terminal page component that displays the server console.
 *
 * Features:
 * - Real-time console output via WebSocket (read-only terminal display)
 * - Separate command input field for sending commands
 * - Connection status indicator
 * - Theme-aware styling
 */
export function Terminal() {
  const terminalRef = useRef<XTerminal | null>(null);
  const messageQueueRef = useRef<string[]>([]);
  const [command, setCommand] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

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
    if (trimmedCommand && connectionState === 'connected') {
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

  return (
    <div className="flex h-full flex-col gap-4" aria-label="Terminal page">
      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0 border-b py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Server Console</CardTitle>
            <ConnectionStatus state={connectionState} />
          </div>
        </CardHeader>
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
              placeholder={isConnected ? 'Enter command...' : 'Disconnected'}
              disabled={!isConnected}
              className="flex-1 font-mono"
              aria-label="Command input"
            />
            <Button
              type="submit"
              disabled={!isConnected || !command.trim()}
              variant="default"
            >
              Send
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
