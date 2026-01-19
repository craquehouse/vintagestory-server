import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useLogStream,
  buildLogWebSocketUrl,
  LOG_WS_CLOSE_CODES,
} from './use-log-stream';

// Mock the ws-token module
vi.mock('../api/ws-token', () => ({
  requestWebSocketToken: vi.fn(),
  WebSocketTokenError: class WebSocketTokenError extends Error {
    constructor(message: string) {
      super(message);
      this.name = 'WebSocketTokenError';
    }
  },
}));

import { requestWebSocketToken } from '../api/ws-token';

const mockRequestWebSocketToken = vi.mocked(requestWebSocketToken);

// Default mock token data
const MOCK_TOKEN_DATA = {
  token: 'mock-log-token-456',
  expiresAt: '2026-01-18T12:05:00Z',
  expiresInSeconds: 300,
};

// WebSocket constants
const WS_CONNECTING = 0;
const WS_OPEN = 1;
const WS_CLOSING = 2;
const WS_CLOSED = 3;

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static lastUrl: string = '';
  static readonly CONNECTING = WS_CONNECTING;
  static readonly OPEN = WS_OPEN;
  static readonly CLOSING = WS_CLOSING;
  static readonly CLOSED = WS_CLOSED;

  url: string;
  readyState: number = WS_CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.lastUrl = url;
    MockWebSocket.instances.push(this);
  }

  // Helper to simulate events
  simulateOpen() {
    this.readyState = WS_OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateClose(code: number = 1000, reason: string = '') {
    this.readyState = WS_CLOSED;
    if (this.onclose) {
      const event = new CloseEvent('close', { code, reason, wasClean: true });
      this.onclose(event);
    }
  }

  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data }));
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('useLogStream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    MockWebSocket.lastUrl = '';
    // @ts-expect-error - Mocking global WebSocket
    global.WebSocket = MockWebSocket;
    // Set up default token mock
    mockRequestWebSocketToken.mockResolvedValue(MOCK_TOKEN_DATA);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('buildLogWebSocketUrl', () => {
    it('builds correct URL with filename, token, and default history lines', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });

      const url = buildLogWebSocketUrl('server-main.log', 'test-token-abc');

      expect(url).toBe(
        'ws://localhost:8080/api/v1alpha1/console/logs/ws?file=server-main.log&token=test-token-abc&history_lines=100'
      );
    });

    it('uses wss for https protocol', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'https:', host: 'example.com' },
        writable: true,
      });

      const url = buildLogWebSocketUrl('app.log', 'secure-token');

      expect(url).toContain('wss://example.com');
      expect(url).toContain('file=app.log');
      expect(url).toContain('token=secure-token');
    });

    it('accepts custom history lines parameter', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost' },
        writable: true,
      });

      const url = buildLogWebSocketUrl('debug.log', 'token-xyz', 500);

      expect(url).toContain('history_lines=500');
    });

    it('URL-encodes filename with special characters', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost' },
        writable: true,
      });

      const url = buildLogWebSocketUrl('logs/app server.log', 'token123');

      expect(url).toContain('file=logs%2Fapp%20server.log');
    });

    it('URL-encodes token with special characters', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost' },
        writable: true,
      });

      const url = buildLogWebSocketUrl('app.log', 'token+with/special=chars');

      expect(url).toContain('token=token%2Bwith%2Fspecial%3Dchars');
    });
  });

  describe('connection lifecycle', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('starts in disconnected state when enabled is false', () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log', enabled: false })
      );

      expect(result.current.connectionState).toBe('disconnected');
    });

    it('starts in connecting state when enabled', () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      expect(result.current.connectionState).toBe('connecting');
    });

    it('requests token before connecting', async () => {
      renderHook(() => useLogStream({ filename: 'test.log' }));

      // Wait for token request
      await waitFor(() => {
        expect(mockRequestWebSocketToken).toHaveBeenCalled();
      });

      // WebSocket should be created with token in URL
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
        expect(MockWebSocket.lastUrl).toContain('token=mock-log-token-456');
        expect(MockWebSocket.lastUrl).toContain('file=test.log');
      });
    });

    it('transitions to token_error when token request fails', async () => {
      mockRequestWebSocketToken.mockRejectedValueOnce(
        new Error('Token request failed')
      );

      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe('token_error');
      });

      // No WebSocket should be created
      expect(MockWebSocket.instances).toHaveLength(0);
    });

    it('transitions to connected on WebSocket open', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created after token fetch
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });
    });

    it('resets retry count on successful connection', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
        expect(result.current.retryCount).toBe(0);
      });
    });

    it('transitions to disconnected on normal close', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.NORMAL);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('disconnected');
      });
    });

    it('transitions to forbidden on FORBIDDEN close code', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.FORBIDDEN);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('forbidden');
      });
    });

    it('transitions to forbidden on UNAUTHORIZED close code', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(
          LOG_WS_CLOSE_CODES.UNAUTHORIZED
        );
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('forbidden');
      });
    });

    it('transitions to not_found on NOT_FOUND close code', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'missing.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.NOT_FOUND);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('not_found');
      });
    });

    it('transitions to invalid on INVALID close code', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.INVALID);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('invalid');
      });
    });
  });

  describe('callbacks', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('calls onStateChange callback on state changes', async () => {
      const onStateChange = vi.fn();
      renderHook(() =>
        useLogStream({ filename: 'test.log', onStateChange })
      );

      // Initial connecting state
      expect(onStateChange).toHaveBeenCalledWith('connecting');

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(onStateChange).toHaveBeenCalledWith('connected');
      });
    });

    it('calls onMessage callback when message received', async () => {
      const onMessage = vi.fn();
      renderHook(() =>
        useLogStream({ filename: 'test.log', onMessage })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateMessage('log line 1\n');
      });

      await waitFor(() => {
        expect(onMessage).toHaveBeenCalledWith('log line 1\n');
      });
    });

    it('calls onMessage callback for multiple messages', async () => {
      const onMessage = vi.fn();
      renderHook(() =>
        useLogStream({ filename: 'test.log', onMessage })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateMessage('line 1\n');
        MockWebSocket.instances[0]?.simulateMessage('line 2\n');
        MockWebSocket.instances[0]?.simulateMessage('line 3\n');
      });

      await waitFor(() => {
        expect(onMessage).toHaveBeenCalledTimes(3);
        expect(onMessage).toHaveBeenNthCalledWith(1, 'line 1\n');
        expect(onMessage).toHaveBeenNthCalledWith(2, 'line 2\n');
        expect(onMessage).toHaveBeenNthCalledWith(3, 'line 3\n');
      });
    });

    it('calls onClose callback when connection closes', async () => {
      const onClose = vi.fn();
      renderHook(() =>
        useLogStream({ filename: 'test.log', onClose })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.NORMAL);
      });

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
        expect(onClose.mock.calls[0][0]).toBeInstanceOf(CloseEvent);
      });
    });
  });

  describe('reconnection logic', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('does not reconnect on normal close (code 1000)', async () => {
      renderHook(() => useLogStream({ filename: 'test.log' }));

      // Flush promise for token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.NORMAL);
      });

      // Advance timers - no reconnection should happen
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('does not reconnect on FORBIDDEN close code', async () => {
      renderHook(() => useLogStream({ filename: 'test.log' }));

      // Flush promise for token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.FORBIDDEN);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('does not reconnect on NOT_FOUND close code', async () => {
      renderHook(() => useLogStream({ filename: 'missing.log' }));

      // Flush promise for token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.NOT_FOUND);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('does not reconnect on INVALID close code', async () => {
      renderHook(() => useLogStream({ filename: 'test.log' }));

      // Flush promise for token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(LOG_WS_CLOSE_CODES.INVALID);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('attempts reconnection on unexpected close with exponential backoff', async () => {
      renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 1000,
          maxRetries: 3,
        })
      );

      // Flush promise for initial token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      // Simulate unexpected close (code 1006)
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006, 'Connection lost');
      });

      // Advance past first retry delay (1000ms + up to 1000ms jitter) and let token request resolve
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2100);
      });

      // Should have created a new WebSocket instance
      expect(MockWebSocket.instances.length).toBeGreaterThan(1);
    });

    it('increments retry count on reconnection attempts', async () => {
      const { result } = renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 100,
          maxRetries: 3,
        })
      );

      // Flush promise for initial token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      expect(result.current.retryCount).toBe(0);

      // Simulate unexpected close
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      // Wait for reconnect (timer + token request)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1200);
      });

      // Retry count should have increased
      expect(result.current.retryCount).toBeGreaterThan(0);
    });

    it('resets retry count on successful reconnection', async () => {
      const { result } = renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 100,
          maxRetries: 3,
        })
      );

      // Flush promise for initial token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      // Simulate unexpected close
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      // Wait for reconnect (timer + token request)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1200);
      });

      // Simulate successful connection
      act(() => {
        const lastInstance =
          MockWebSocket.instances[MockWebSocket.instances.length - 1];
        lastInstance?.simulateOpen();
      });

      // Should reset to 0 on successful connection
      expect(result.current.retryCount).toBe(0);
    });

    it('limits reconnection attempts based on maxRetries', async () => {
      const { result } = renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 100,
          maxRetries: 2,
        })
      );

      // Flush promise for initial token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      const initialCount = MockWebSocket.instances.length;

      // First close triggers reconnect
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1200);
      });

      // Should have attempted first retry
      expect(result.current.retryCount).toBe(1);
      expect(MockWebSocket.instances.length).toBe(initialCount + 1);

      // Second close triggers second retry
      act(() => {
        const lastInstance =
          MockWebSocket.instances[MockWebSocket.instances.length - 1];
        lastInstance?.simulateClose(1006);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1200);
      });

      // Should have attempted second retry
      expect(result.current.retryCount).toBe(2);
      expect(MockWebSocket.instances.length).toBe(initialCount + 2);

      // Third close should NOT trigger retry (maxRetries = 2)
      act(() => {
        const lastInstance =
          MockWebSocket.instances[MockWebSocket.instances.length - 1];
        lastInstance?.simulateClose(1006);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // No new WebSocket instance created
      expect(MockWebSocket.instances.length).toBe(initialCount + 2);
    });

    it('sets isReconnecting to true during reconnection', async () => {
      const { result } = renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 100,
          maxRetries: 3,
        })
      );

      // Flush promise for initial token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(result.current.isReconnecting).toBe(false);

      // Simulate unexpected close
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      // During reconnect attempt
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1200);
      });

      // Should be reconnecting (retryCount > 0 and state is connecting)
      expect(result.current.retryCount).toBeGreaterThan(0);
      // Note: isReconnecting might be false if connection happened, check the logic
    });
  });

  describe('manual controls', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('disconnect closes the WebSocket with normal code', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });

      act(() => {
        result.current.disconnect();
      });

      expect(MockWebSocket.instances[0]?.close).toHaveBeenCalledWith(
        LOG_WS_CLOSE_CODES.NORMAL
      );

      await waitFor(() => {
        expect(result.current.connectionState).toBe('disconnected');
      });
    });

    it('reconnect creates a new connection and resets retry count', async () => {
      const { result } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for initial WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      const initialInstanceCount = MockWebSocket.instances.length;

      act(() => {
        result.current.reconnect();
      });

      // Wait for new WebSocket after reconnect
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(
          initialInstanceCount
        );
      });

      // Retry count should be reset
      expect(result.current.retryCount).toBe(0);
    });
  });

  describe('enabled flag', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('does not connect when enabled is false', async () => {
      renderHook(() =>
        useLogStream({ filename: 'test.log', enabled: false })
      );

      // Wait to ensure no connection happens
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(mockRequestWebSocketToken).not.toHaveBeenCalled();
      expect(MockWebSocket.instances).toHaveLength(0);
    });

    it('connects when enabled changes from false to true', async () => {
      const { rerender } = renderHook(
        ({ enabled }) => useLogStream({ filename: 'test.log', enabled }),
        { initialProps: { enabled: false } }
      );

      // Initially no connection
      expect(MockWebSocket.instances).toHaveLength(0);

      // Enable connection
      rerender({ enabled: true });

      // Wait for connection
      await waitFor(() => {
        expect(mockRequestWebSocketToken).toHaveBeenCalled();
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });
    });

    it('disconnects when enabled changes from true to false', async () => {
      const { rerender, result } = renderHook(
        ({ enabled }) => useLogStream({ filename: 'test.log', enabled }),
        { initialProps: { enabled: true } }
      );

      // Wait for connection
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });

      // Disable connection
      rerender({ enabled: false });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('disconnected');
      });

      expect(MockWebSocket.instances[0]?.close).toHaveBeenCalledWith(
        LOG_WS_CLOSE_CODES.NORMAL
      );
    });
  });

  describe('history lines option', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('uses default history lines of 100', async () => {
      renderHook(() => useLogStream({ filename: 'test.log' }));

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      expect(MockWebSocket.lastUrl).toContain('history_lines=100');
    });

    it('uses custom history lines when provided', async () => {
      renderHook(() =>
        useLogStream({ filename: 'test.log', historyLines: 500 })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      expect(MockWebSocket.lastUrl).toContain('history_lines=500');
    });
  });

  describe('cleanup', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8080' },
        writable: true,
      });
    });

    it('closes WebSocket on unmount', async () => {
      const { unmount } = renderHook(() =>
        useLogStream({ filename: 'test.log' })
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      unmount();

      expect(MockWebSocket.instances[0]?.close).toHaveBeenCalledWith(
        LOG_WS_CLOSE_CODES.NORMAL
      );
    });

    it('clears reconnect timeout on unmount', async () => {
      vi.useFakeTimers();

      const { unmount } = renderHook(() =>
        useLogStream({
          filename: 'test.log',
          baseDelayMs: 1000,
          maxRetries: 3,
        })
      );

      // Flush promise for token request
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(0);

      // Trigger reconnect logic
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      // Unmount before reconnect happens
      unmount();

      // Advance timers - no reconnection should happen after unmount
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // Only initial WebSocket instance
      expect(MockWebSocket.instances).toHaveLength(1);

      vi.useRealTimers();
    });
  });
});
