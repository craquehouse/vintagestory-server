"""WebSocket token models for secure authentication.

Story 9.1: Secure WebSocket Authentication

These models define the request/response structures for WebSocket token
authentication flow. Tokens are short-lived (5 minute TTL) and used to
authenticate WebSocket connections without exposing API keys in URLs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebSocketTokenData(BaseModel):
    """Data payload for WebSocket token response."""

    token: str = Field(..., description="Short-lived WebSocket authentication token")
    expires_at: str = Field(..., description="Token expiration time (ISO 8601)")
    expires_in_seconds: int = Field(..., description="Seconds until token expires")


class WebSocketTokenResponse(BaseModel):
    """Response for WebSocket token request endpoint."""

    status: str = Field(default="ok")
    data: WebSocketTokenData
