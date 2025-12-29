import { useCallback, useRef } from 'react';
import type { Terminal as XTerminal } from '@xterm/xterm';
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

  // Handle WebSocket messages
  const handleOpen = useCallback((ws: WebSocket) => {
    if (terminalRef.current) {
      // Attach WebSocket for bidirectional I/O
      const attachAddon = new AttachAddon(ws);
      attachAddonRef.current = attachAddon;
      terminalRef.current.loadAddon(attachAddon);
    }
  }, []);

  // Handle terminal ready
  const handleTerminalReady = useCallback((terminal: XTerminal) => {
    terminalRef.current = terminal;
  }, []);

  // Handle terminal cleanup
  const handleTerminalDispose = useCallback(() => {
    terminalRef.current = null;
    attachAddonRef.current = null;
  }, []);

  const { connectionState } = useConsoleWebSocket({
    onOpen: handleOpen,
    onMessage: (data) => {
      // Messages are handled by AttachAddon when connected
      // This is a fallback for any messages before AttachAddon is loaded
      if (!attachAddonRef.current && terminalRef.current) {
        terminalRef.current.write(data);
      }
    },
  });

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
            onReady={handleTerminalReady}
            onDispose={handleTerminalDispose}
            className="h-full w-full"
          />
        </CardContent>
      </Card>
    </div>
  );
}
