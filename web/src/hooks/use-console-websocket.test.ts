import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useConsoleWebSocket,
  buildConsoleWebSocketUrl,
  WS_CLOSE_CODES,
} from './use-console-websocket';

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

describe('useConsoleWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    MockWebSocket.lastUrl = '';
    // @ts-expect-error - Mocking global WebSocket
    global.WebSocket = MockWebSocket;
    import.meta.env.VITE_API_KEY = 'test-api-key';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('buildConsoleWebSocketUrl', () => {
    it('builds correct URL with API key', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });

      const url = buildConsoleWebSocketUrl(100);

      expect(url).toBe(
        'ws://localhost:8000/api/v1alpha1/console/ws?api_key=test-api-key&history_lines=100'
      );
    });

    it('uses wss for https', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'https:', host: 'example.com' },
        writable: true,
      });

      const url = buildConsoleWebSocketUrl(50);

      expect(url).toContain('wss://example.com');
      expect(url).toContain('history_lines=50');
    });

    it('uses default history lines of 100', () => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost' },
        writable: true,
      });

      const url = buildConsoleWebSocketUrl();

      expect(url).toContain('history_lines=100');
    });
  });

  describe('connection lifecycle (AC: 1, 4)', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    it('starts in connecting state', () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      expect(result.current.connectionState).toBe('connecting');
    });

    it('transitions to connected on WebSocket open', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });
    });

    it('transitions to disconnected on normal close', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.NORMAL);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('disconnected');
      });
    });

    it('transitions to forbidden on 4003 close code', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.FORBIDDEN);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('forbidden');
      });
    });

    it('transitions to forbidden on 4001 close code', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.UNAUTHORIZED);
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('forbidden');
      });
    });

    it('calls onOpen callback when connected', async () => {
      const onOpen = vi.fn();
      renderHook(() => useConsoleWebSocket({ onOpen }));

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled();
      });
    });

    it('calls onStateChange callback on state changes', async () => {
      const onStateChange = vi.fn();
      renderHook(() => useConsoleWebSocket({ onStateChange }));

      // Initial connecting state
      expect(onStateChange).toHaveBeenCalledWith('connecting');

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(onStateChange).toHaveBeenCalledWith('connected');
      });
    });

    it('calls onMessage callback when message received', async () => {
      const onMessage = vi.fn();
      renderHook(() => useConsoleWebSocket({ onMessage }));

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateMessage('test message');
      });

      await waitFor(() => {
        expect(onMessage).toHaveBeenCalledWith('test message');
      });
    });

    it('calls onClose callback when connection closes', async () => {
      const onClose = vi.fn();
      renderHook(() => useConsoleWebSocket({ onClose }));

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.NORMAL);
      });

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });
  });

  describe('reconnection logic (AC: 4)', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('does not reconnect on normal close (code 1000)', async () => {
      renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.NORMAL);
      });

      // Advance timers - no reconnection should happen
      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('does not reconnect on forbidden close (code 4003)', async () => {
      renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.FORBIDDEN);
      });

      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('attempts reconnection on unexpected close', async () => {
      renderHook(() =>
        useConsoleWebSocket({
          baseDelayMs: 1000,
          maxRetries: 3,
        })
      );

      // Simulate unexpected close (code 1006)
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006, 'Connection lost');
      });

      // Advance past first retry delay (1000ms + up to 1000ms jitter)
      await act(async () => {
        vi.advanceTimersByTime(2100);
      });

      // Should have created a new WebSocket instance
      expect(MockWebSocket.instances.length).toBeGreaterThan(1);
    });

    it('resets retry count on successful connection', async () => {
      const { result } = renderHook(() =>
        useConsoleWebSocket({
          baseDelayMs: 100,
          maxRetries: 3,
        })
      );

      // Simulate unexpected close
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      // Wait for reconnect
      await act(async () => {
        vi.advanceTimersByTime(1200);
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
        useConsoleWebSocket({
          baseDelayMs: 100,
          maxRetries: 2,
        })
      );

      // First close triggers reconnect
      act(() => {
        MockWebSocket.instances[0]?.simulateClose(1006);
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      // Check that retry count increased
      expect(result.current.retryCount).toBeGreaterThan(0);
    });
  });

  describe('sendCommand', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    it('sends command as JSON message when connected', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected');
      });

      act(() => {
        result.current.sendCommand('/help');
      });

      expect(MockWebSocket.instances[0]?.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'command', content: '/help' })
      );
    });

    it('does not send when WebSocket is closed', () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      // Open and then close the connection
      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateClose(WS_CLOSE_CODES.NORMAL);
      });

      // Clear any previous calls
      const ws = MockWebSocket.instances[0];
      if (ws) {
        ws.send.mockClear();
      }

      act(() => {
        result.current.sendCommand('/help');
      });

      // The WebSocket is closed, so send should not be called
      expect(ws?.send).not.toHaveBeenCalled();
    });
  });

  describe('disconnect', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    it('closes the WebSocket with normal code', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

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
        WS_CLOSE_CODES.NORMAL
      );
    });
  });

  describe('reconnect', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    it('creates a new connection', async () => {
      const { result } = renderHook(() => useConsoleWebSocket());

      const initialInstanceCount = MockWebSocket.instances.length;

      act(() => {
        result.current.reconnect();
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(
        initialInstanceCount
      );
    });
  });

  describe('cleanup', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:8000' },
        writable: true,
      });
    });

    it('closes WebSocket on unmount', () => {
      const { unmount } = renderHook(() => useConsoleWebSocket());

      unmount();

      expect(MockWebSocket.instances[0]?.close).toHaveBeenCalledWith(
        WS_CLOSE_CODES.NORMAL
      );
    });
  });
});
