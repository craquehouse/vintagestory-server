import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Debug logging helper - only logs in development mode, not during tests.
 */
function debugLog(message: string, data?: Record<string, unknown>): void {
  if (import.meta.env.DEV && !import.meta.env.VITEST) {
    if (data) {
      console.log(`[ConsoleWebSocket] ${message}`, data);
    } else {
      console.log(`[ConsoleWebSocket] ${message}`);
    }
  }
}

/**
 * Connection states for the console WebSocket.
 */
export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'forbidden';

/**
 * WebSocket close codes from the backend.
 */
export const WS_CLOSE_CODES = {
  NORMAL: 1000,
  UNAUTHORIZED: 4001,
  FORBIDDEN: 4003,
} as const;

/**
 * Options for the useConsoleWebSocket hook.
 */
export interface UseConsoleWebSocketOptions {
  /** Number of history lines to fetch on connect (default: 100) */
  historyLines?: number;
  /** Maximum number of reconnection attempts (default: 10) */
  maxRetries?: number;
  /** Base delay for reconnection in ms (default: 1000) */
  baseDelayMs?: number;
  /** Maximum delay for reconnection in ms (default: 30000) */
  maxDelayMs?: number;
  /** Callback when WebSocket is ready */
  onOpen?: (ws: WebSocket) => void;
  /** Callback when connection state changes */
  onStateChange?: (state: ConnectionState) => void;
  /** Callback when a message is received */
  onMessage?: (data: string) => void;
  /** Callback when the connection is closed */
  onClose?: (event: CloseEvent) => void;
}

/**
 * Return value from useConsoleWebSocket hook.
 */
export interface UseConsoleWebSocketResult {
  /** Current connection state */
  connectionState: ConnectionState;
  /** Current retry count */
  retryCount: number;
  /** Whether currently reconnecting */
  isReconnecting: boolean;
  /** Reference to the WebSocket instance */
  wsRef: React.RefObject<WebSocket | null>;
  /** Send a command to the server */
  sendCommand: (command: string) => void;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect from the WebSocket */
  disconnect: () => void;
}

/**
 * Get API key from Vite environment variables.
 */
function getApiKey(): string {
  return import.meta.env.VITE_API_KEY || '';
}

/**
 * Build the WebSocket URL for the console endpoint.
 */
export function buildConsoleWebSocketUrl(historyLines: number = 100): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const apiKey = getApiKey();

  return `${protocol}//${host}/api/v1alpha1/console/ws?api_key=${encodeURIComponent(apiKey)}&history_lines=${historyLines}`;
}

/**
 * Custom hook for managing WebSocket connection to the console endpoint.
 *
 * Features:
 * - Automatic connection on mount
 * - Exponential backoff reconnection with jitter
 * - Connection state tracking
 * - Authentication via API key query parameter
 * - History lines on connect
 *
 * @example
 * ```tsx
 * function ConsoleView() {
 *   const { connectionState, wsRef, sendCommand } = useConsoleWebSocket({
 *     onMessage: (data) => terminal.write(data),
 *     onStateChange: (state) => console.log('Connection:', state),
 *   });
 *
 *   return <div>Status: {connectionState}</div>;
 * }
 * ```
 */
export function useConsoleWebSocket(
  options: UseConsoleWebSocketOptions = {}
): UseConsoleWebSocketResult {
  const {
    historyLines = 100,
    maxRetries = 10,
    baseDelayMs = 1000,
    maxDelayMs = 30000,
    onOpen,
    onStateChange,
    onMessage,
    onClose,
  } = options;

  const [connectionState, setConnectionState] =
    useState<ConnectionState>('connecting');
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);
  // Use ref for retry count in reconnection logic to avoid recreating connect callback
  const retryCountRef = useRef(0);

  // Store callbacks in refs to avoid recreating connect on callback changes
  const onOpenRef = useRef(onOpen);
  const onMessageRef = useRef(onMessage);
  const onCloseRef = useRef(onClose);
  const onStateChangeRef = useRef(onStateChange);

  // Keep refs in sync with latest callbacks
  onOpenRef.current = onOpen;
  onMessageRef.current = onMessage;
  onCloseRef.current = onClose;
  onStateChangeRef.current = onStateChange;

  // Update connection state and notify callback
  const updateState = useCallback((state: ConnectionState) => {
    setConnectionState(state);
    onStateChangeRef.current?.(state);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close(WS_CLOSE_CODES.NORMAL);
      wsRef.current = null;
    }

    updateState('connecting');

    const url = buildConsoleWebSocketUrl(historyLines);
    debugLog('Connecting', { url: url.replace(/api_key=[^&]+/, 'api_key=***') });
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      debugLog('Connected');
      updateState('connected');
      retryCountRef.current = 0;
      setRetryCount(0);
      onOpenRef.current?.(ws);
    };

    ws.onmessage = (event) => {
      onMessageRef.current?.(event.data);
    };

    ws.onclose = (event) => {
      debugLog('Connection closed', { code: event.code, reason: event.reason });
      onCloseRef.current?.(event);

      // Handle specific close codes
      if (event.code === WS_CLOSE_CODES.FORBIDDEN) {
        debugLog('Access forbidden');
        updateState('forbidden');
        return;
      }

      if (event.code === WS_CLOSE_CODES.UNAUTHORIZED) {
        debugLog('Unauthorized');
        updateState('forbidden');
        return;
      }

      // Normal close - don't reconnect
      if (event.code === WS_CLOSE_CODES.NORMAL) {
        debugLog('Normal close, not reconnecting');
        updateState('disconnected');
        return;
      }

      // Unexpected close - attempt reconnection
      updateState('disconnected');

      const currentRetry = retryCountRef.current;
      if (shouldReconnectRef.current && currentRetry < maxRetries) {
        // Calculate delay with exponential backoff and jitter
        const delay = Math.min(
          baseDelayMs * Math.pow(2, currentRetry),
          maxDelayMs
        );
        const jitter = Math.random() * 1000;
        const totalDelay = delay + jitter;

        debugLog('Scheduling reconnection', {
          attempt: currentRetry + 1,
          maxRetries,
          delayMs: Math.round(totalDelay),
        });

        reconnectTimeoutRef.current = window.setTimeout(() => {
          retryCountRef.current += 1;
          setRetryCount(retryCountRef.current);
          connect();
        }, totalDelay);
      } else if (currentRetry >= maxRetries) {
        debugLog('Max retries reached, giving up');
      }
    };

    ws.onerror = (event) => {
      debugLog('WebSocket error', { event: String(event) });
      // Error will trigger onclose
    };
  }, [historyLines, maxRetries, baseDelayMs, maxDelayMs, updateState]);

  // Send a command to the server
  const sendCommand = useCallback((command: string) => {
    if (
      wsRef.current &&
      wsRef.current.readyState === WebSocket.OPEN
    ) {
      wsRef.current.send(JSON.stringify({ type: 'command', content: command }));
    }
  }, []);

  // Manual reconnect
  const reconnect = useCallback(() => {
    shouldReconnectRef.current = true;
    retryCountRef.current = 0;
    setRetryCount(0);
    connect();
  }, [connect]);

  // Disconnect
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(WS_CLOSE_CODES.NORMAL);
      wsRef.current = null;
    }

    updateState('disconnected');
  }, [updateState]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;

      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(WS_CLOSE_CODES.NORMAL);
      }
    };
  }, [connect]);

  return {
    connectionState,
    retryCount,
    isReconnecting: retryCount > 0 && connectionState === 'connecting',
    wsRef,
    sendCommand,
    reconnect,
    disconnect,
  };
}
