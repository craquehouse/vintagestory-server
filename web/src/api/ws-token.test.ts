/**
 * Tests for WebSocket token API.
 *
 * Story 9.1: Secure WebSocket Authentication
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  requestWebSocketToken,
  WebSocketTokenError,
  type WebSocketTokenData,
} from './ws-token';

// Mock the apiClient module
vi.mock('./client', () => ({
  apiClient: vi.fn(),
}));

import { apiClient } from './client';

const mockApiClient = vi.mocked(apiClient);

describe('requestWebSocketToken', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns token data on successful request', async () => {
    const mockTokenData: WebSocketTokenData = {
      token: 'test-token-123',
      expiresAt: '2026-01-03T12:05:00Z',
      expiresInSeconds: 300,
    };

    mockApiClient.mockResolvedValueOnce({
      status: 'ok',
      data: mockTokenData,
    });

    const result = await requestWebSocketToken();

    expect(result).toEqual(mockTokenData);
    expect(mockApiClient).toHaveBeenCalledWith('/api/v1alpha1/auth/ws-token', {
      method: 'POST',
    });
  });

  it('throws WebSocketTokenError on API error', async () => {
    mockApiClient.mockRejectedValue(new Error('Unauthorized'));

    await expect(requestWebSocketToken()).rejects.toThrow(WebSocketTokenError);
    await expect(requestWebSocketToken()).rejects.toThrow('Unauthorized');
  });

  it('throws WebSocketTokenError with default message on unknown error', async () => {
    mockApiClient.mockRejectedValue('some non-Error value');

    await expect(requestWebSocketToken()).rejects.toThrow(WebSocketTokenError);
    await expect(requestWebSocketToken()).rejects.toThrow(
      'Failed to request WebSocket token'
    );
  });
});

describe('WebSocketTokenError', () => {
  it('has correct name property', () => {
    const error = new WebSocketTokenError('test message');
    expect(error.name).toBe('WebSocketTokenError');
  });

  it('stores status code when provided', () => {
    const error = new WebSocketTokenError('test message', 401);
    expect(error.statusCode).toBe(401);
  });

  it('has undefined statusCode when not provided', () => {
    const error = new WebSocketTokenError('test message');
    expect(error.statusCode).toBeUndefined();
  });
});
