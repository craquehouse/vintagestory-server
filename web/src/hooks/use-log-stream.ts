import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Debug logging helper - only logs in development mode, not during tests.
 */
function debugLog(message: string, data?: Record<string, unknown>): void {
  if (import.meta.env.DEV && !import.meta.env.VITEST) {
    if (data) {
      console.log(`[LogStream] ${message}`, data);
    } else {
      console.log(`[LogStream] ${message}`);
    }
  }
}

/**
 * Connection states for the log WebSocket.
 */
export type LogConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'forbidden'
  | 'not_found'
  | 'invalid';

/**
 * WebSocket close codes from the backend.
 */
export const LOG_WS_CLOSE_CODES = {
  NORMAL: 1000,
  UNAUTHORIZED: 4001,
  FORBIDDEN: 4003,
  NOT_FOUND: 4004,
  INVALID: 4005,
} as const;

/**
 * Options for the useLogStream hook.
 */
export interface UseLogStreamOptions {
  /** Log file name to stream (e.g., 'server-main.log') */
  filename: string;
  /** Whether to connect (allows conditional connection) */
  enabled?: boolean;
  /** Number of history lines to fetch on connect (default: 100) */
  historyLines?: number;
  /** Maximum number of reconnection attempts (default: 10) */
  maxRetries?: number;
  /** Base delay for reconnection in ms (default: 1000) */
  baseDelayMs?: number;
  /** Maximum delay for reconnection in ms (default: 30000) */
  maxDelayMs?: number;
  /** Callback when connection state changes */
  onStateChange?: (state: LogConnectionState) => void;
  /** Callback when a message is received */
  onMessage?: (data: string) => void;
  /** Callback when the connection is closed */
  onClose?: (event: CloseEvent) => void;
}

/**
 * Return value from useLogStream hook.
 */
export interface UseLogStreamResult {
  /** Current connection state */
  connectionState: LogConnectionState;
  /** Current retry count */
  retryCount: number;
  /** Whether currently reconnecting */
  isReconnecting: boolean;
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
 * Build the WebSocket URL for the log streaming endpoint.
 */
export function buildLogWebSocketUrl(
  filename: string,
  historyLines: number = 100
): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const apiKey = getApiKey();

  return `${protocol}//${host}/api/v1alpha1/console/logs/ws?file=${encodeURIComponent(filename)}&api_key=${encodeURIComponent(apiKey)}&history_lines=${historyLines}`;
}

/**
 * Custom hook for streaming log file content via WebSocket.
 *
 * Features:
 * - Automatic connection when enabled and filename is provided
 * - Exponential backoff reconnection with jitter
 * - Connection state tracking
 * - Authentication via API key query parameter
 * - History lines on connect
 *
 * @example
 * ```tsx
 * function LogViewer({ filename }: { filename: string }) {
 *   const { connectionState } = useLogStream({
 *     filename,
 *     enabled: !!filename,
 *     onMessage: (data) => terminal.write(data),
 *   });
 *
 *   return <div>Status: {connectionState}</div>;
 * }
 * ```
 */
export function useLogStream(
  options: UseLogStreamOptions
): UseLogStreamResult {
  const {
    filename,
    enabled = true,
    historyLines = 100,
    maxRetries = 10,
    baseDelayMs = 1000,
    maxDelayMs = 30000,
    onStateChange,
    onMessage,
    onClose,
  } = options;

  const [connectionState, setConnectionState] =
    useState<LogConnectionState>('disconnected');
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldReconnectRef = useRef(true);
  const retryCountRef = useRef(0);

  // Store callbacks in refs to avoid recreating connect on callback changes
  const onMessageRef = useRef(onMessage);
  const onCloseRef = useRef(onClose);
  const onStateChangeRef = useRef(onStateChange);

  // Keep refs in sync with latest callbacks
  onMessageRef.current = onMessage;
  onCloseRef.current = onClose;
  onStateChangeRef.current = onStateChange;

  // Update connection state and notify callback
  const updateState = useCallback((state: LogConnectionState) => {
    setConnectionState(state);
    onStateChangeRef.current?.(state);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!filename || !enabled) {
      return;
    }

    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close(LOG_WS_CLOSE_CODES.NORMAL);
      wsRef.current = null;
    }

    updateState('connecting');

    const url = buildLogWebSocketUrl(filename, historyLines);
    debugLog('Connecting', {
      filename,
      url: url.replace(/api_key=[^&]+/, 'api_key=***'),
    });
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      debugLog('Connected', { filename });
      updateState('connected');
      retryCountRef.current = 0;
      setRetryCount(0);
    };

    ws.onmessage = (event) => {
      onMessageRef.current?.(event.data);
    };

    ws.onclose = (event) => {
      debugLog('Connection closed', {
        filename,
        code: event.code,
        reason: event.reason,
      });
      onCloseRef.current?.(event);

      // Handle specific close codes
      if (event.code === LOG_WS_CLOSE_CODES.FORBIDDEN) {
        debugLog('Access forbidden');
        updateState('forbidden');
        return;
      }

      if (event.code === LOG_WS_CLOSE_CODES.UNAUTHORIZED) {
        debugLog('Unauthorized');
        updateState('forbidden');
        return;
      }

      if (event.code === LOG_WS_CLOSE_CODES.NOT_FOUND) {
        debugLog('File not found');
        updateState('not_found');
        return;
      }

      if (event.code === LOG_WS_CLOSE_CODES.INVALID) {
        debugLog('Invalid request');
        updateState('invalid');
        return;
      }

      // Normal close - don't reconnect
      if (event.code === LOG_WS_CLOSE_CODES.NORMAL) {
        debugLog('Normal close, not reconnecting');
        updateState('disconnected');
        return;
      }

      // Unexpected close - attempt reconnection
      updateState('disconnected');

      const currentRetry = retryCountRef.current;
      if (shouldReconnectRef.current && currentRetry < maxRetries) {
        const delay = Math.min(
          baseDelayMs * Math.pow(2, currentRetry),
          maxDelayMs
        );
        const jitter = Math.random() * 1000;
        const totalDelay = delay + jitter;

        debugLog('Scheduling reconnection', {
          filename,
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
    };
  }, [
    filename,
    enabled,
    historyLines,
    maxRetries,
    baseDelayMs,
    maxDelayMs,
    updateState,
  ]);

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
      wsRef.current.close(LOG_WS_CLOSE_CODES.NORMAL);
      wsRef.current = null;
    }

    updateState('disconnected');
  }, [updateState]);

  // Connect on mount or when filename/enabled changes, disconnect on unmount
  useEffect(() => {
    if (enabled && filename) {
      shouldReconnectRef.current = true;
      connect();
    } else {
      disconnect();
    }

    return () => {
      shouldReconnectRef.current = false;

      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(LOG_WS_CLOSE_CODES.NORMAL);
      }
    };
  }, [connect, disconnect, enabled, filename]);

  return {
    connectionState,
    retryCount,
    isReconnecting: retryCount > 0 && connectionState === 'connecting',
    reconnect,
    disconnect,
  };
}
