/**
 * WebSocket token API for secure WebSocket authentication.
 *
 * Story 9.1: Secure WebSocket Authentication
 *
 * This module provides functions to request short-lived tokens for WebSocket
 * connections. Tokens are used instead of API keys in WebSocket URLs to
 * avoid exposing credentials in browser history and logs.
 */

import { apiClient } from './client';

/**
 * Response data from the WebSocket token endpoint.
 */
export interface WebSocketTokenData {
  /** Short-lived WebSocket authentication token */
  token: string;
  /** Token expiration time (ISO 8601) */
  expiresAt: string;
  /** Seconds until token expires (300 = 5 minutes) */
  expiresInSeconds: number;
}

/**
 * API response envelope for WebSocket token request.
 */
export interface WebSocketTokenResponse {
  status: 'ok';
  data: WebSocketTokenData;
}

/**
 * Error thrown when token request fails.
 */
export class WebSocketTokenError extends Error {
  readonly statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'WebSocketTokenError';
    this.statusCode = statusCode;
  }
}

/**
 * Request a short-lived token for WebSocket authentication.
 *
 * Tokens have a 5-minute TTL and should be requested just before
 * establishing a WebSocket connection.
 *
 * @returns Promise resolving to token data
 * @throws WebSocketTokenError if request fails
 *
 * @example
 * ```ts
 * const tokenData = await requestWebSocketToken();
 * const wsUrl = `wss://host/api/v1alpha1/console/ws?token=${tokenData.token}`;
 * const ws = new WebSocket(wsUrl);
 * ```
 */
export async function requestWebSocketToken(): Promise<WebSocketTokenData> {
  try {
    const response = await apiClient<WebSocketTokenResponse>(
      '/api/v1alpha1/auth/ws-token',
      { method: 'POST' }
    );
    return response.data;
  } catch (error) {
    // Re-wrap errors for consistent handling
    if (error instanceof Error) {
      throw new WebSocketTokenError(error.message);
    }
    throw new WebSocketTokenError('Failed to request WebSocket token');
  }
}
