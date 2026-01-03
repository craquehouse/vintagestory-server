"""WebSocket token endpoint for secure WebSocket authentication.

Story 9.1: Secure WebSocket Authentication

This router provides the `POST /api/v1alpha1/auth/ws-token` endpoint that
issues short-lived tokens for WebSocket authentication. Users exchange
their API key for a token, which can then be used to authenticate
WebSocket connections without exposing the API key in the URL.
"""

from fastapi import APIRouter, Depends

from vintagestory_api.middleware.auth import CurrentUser
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.models.ws_token import WebSocketTokenData
from vintagestory_api.services.ws_token_service import (
    WebSocketTokenService,
    get_ws_token_service,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/ws-token", response_model=ApiResponse)
async def request_websocket_token(
    current_user: CurrentUser,
    token_service: WebSocketTokenService = Depends(get_ws_token_service),
) -> ApiResponse:
    """Request a short-lived token for WebSocket authentication.

    This endpoint issues a token that can be used to authenticate WebSocket
    connections. The token embeds the user's role and expires after 5 minutes.

    Tokens are designed for immediate use - request a fresh token just before
    establishing a WebSocket connection.

    Security benefits:
    - API keys are never exposed in WebSocket URLs
    - Tokens have a short TTL (5 minutes) limiting exposure window
    - Tokens are single-purpose (for WebSocket auth only)

    Requires:
        Valid API key (Admin or Monitor) via X-API-Key header.

    Returns:
        ApiResponse with token data including:
        - token: The WebSocket authentication token
        - expires_at: ISO 8601 timestamp when token expires
        - expires_in_seconds: Seconds until expiration (300 = 5 minutes)

    Example:
        ```
        POST /api/v1alpha1/auth/ws-token
        X-API-Key: <your-api-key>

        Response:
        {
          "status": "ok",
          "data": {
            "token": "abc123...",
            "expires_at": "2026-01-03T12:05:00Z",
            "expires_in_seconds": 300
          }
        }
        ```
    """
    # Create token with user's role embedded
    stored_token = token_service.create_token(current_user)

    # Build response data
    token_data = WebSocketTokenData(
        token=stored_token.token,
        expires_at=stored_token.expires_at.isoformat(),
        expires_in_seconds=int(
            (stored_token.expires_at - stored_token.created_at).total_seconds()
        ),
    )

    return ApiResponse(status="ok", data=token_data.model_dump())
