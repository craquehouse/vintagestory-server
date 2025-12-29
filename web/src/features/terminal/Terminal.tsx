import { useCallback, useRef } from 'react';
import type { Terminal as XTerminal, IDisposable } from '@xterm/xterm';
import { AttachAddon } from '@xterm/addon-attach';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TerminalView } from '@/components/terminal/TerminalView';
import { ConnectionStatus } from '@/components/terminal/ConnectionStatus';
import { useConsoleWebSocket } from '@/hooks/use-console-websocket';

/**
 * Terminal page component that displays the server console.
 *
 * Features:
 * - Real-time console output via WebSocket
 * - Command input through the terminal
 * - Connection status indicator
 * - Theme-aware styling
 */
export function Terminal() {
  const terminalRef = useRef<XTerminal | null>(null);
  const attachAddonRef = useRef<AttachAddon | null>(null);
  const inputBufferRef = useRef<string>('');
  const dataListenerRef = useRef<IDisposable | null>(null);

  // Handle WebSocket connection opened
  const handleOpen = useCallback((ws: WebSocket) => {
    if (terminalRef.current) {
      // Attach WebSocket for receiving console output only (bidirectional: false)
      // Commands are sent via JSON format, not raw terminal input
      const attachAddon = new AttachAddon(ws, { bidirectional: false });
      attachAddonRef.current = attachAddon;
      terminalRef.current.loadAddon(attachAddon);
    }
  }, []);

  // Handle terminal ready - set up input handler
  const handleTerminalReady = useCallback((terminal: XTerminal) => {
    terminalRef.current = terminal;
    inputBufferRef.current = '';
  }, []);

  // Handle terminal cleanup
  const handleTerminalDispose = useCallback(() => {
    if (dataListenerRef.current) {
      dataListenerRef.current.dispose();
      dataListenerRef.current = null;
    }
    terminalRef.current = null;
    attachAddonRef.current = null;
    inputBufferRef.current = '';
  }, []);

  const { connectionState, sendCommand } = useConsoleWebSocket({
    onOpen: handleOpen,
    onMessage: (data) => {
      // Messages are handled by AttachAddon when connected
      // This is a fallback for any messages before AttachAddon is loaded
      if (!attachAddonRef.current && terminalRef.current) {
        terminalRef.current.write(data);
      }
    },
  });

  // Handle terminal input for command sending
  const handleTerminalInput = useCallback(
    (terminal: XTerminal) => {
      // Clean up existing listener
      if (dataListenerRef.current) {
        dataListenerRef.current.dispose();
      }

      // Listen for terminal input
      dataListenerRef.current = terminal.onData((data) => {
        // Handle Enter key
        if (data === '\r' || data === '\n') {
          const command = inputBufferRef.current.trim();
          if (command) {
            sendCommand(command);
          }
          inputBufferRef.current = '';
          terminal.write('\r\n');
          return;
        }

        // Handle Backspace
        if (data === '\x7f' || data === '\b') {
          if (inputBufferRef.current.length > 0) {
            inputBufferRef.current = inputBufferRef.current.slice(0, -1);
            terminal.write('\b \b');
          }
          return;
        }

        // Handle Ctrl+C (cancel current input)
        if (data === '\x03') {
          inputBufferRef.current = '';
          terminal.write('^C\r\n');
          return;
        }

        // Regular character input
        if (data.length === 1 && data.charCodeAt(0) >= 32) {
          inputBufferRef.current += data;
          terminal.write(data);
        }
      });
    },
    [sendCommand]
  );

  // Set up input handler when terminal is ready
  const handleReady = useCallback(
    (terminal: XTerminal) => {
      handleTerminalReady(terminal);
      handleTerminalInput(terminal);
    },
    [handleTerminalReady, handleTerminalInput]
  );

  return (
    <div className="flex h-full flex-col gap-4" aria-label="Terminal page">
      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0 border-b py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Server Console</CardTitle>
            <ConnectionStatus state={connectionState} />
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden p-0">
          <TerminalView
            onReady={handleReady}
            onDispose={handleTerminalDispose}
            className="h-full w-full"
          />
        </CardContent>
      </Card>
    </div>
  );
}
