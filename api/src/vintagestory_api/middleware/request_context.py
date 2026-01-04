"""Request context middleware for request correlation.

This middleware:
- Generates a unique UUID for each request
- Binds the request_id to structlog context vars
- Ensures all logs for a request include the same request_id

Security Note:
- Never log sensitive data (API keys, passwords) in request context
- Use key prefixes only: api_key[:8] + "..."

Runtime Debug Toggle (FR48):
    Debug logging is controlled via internal state, not per-request env checks.
    Use set_debug_enabled() from config module or the debug toggle API endpoint
    to enable/disable debug logging at runtime without server restart.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that adds request correlation ID to all logs.

    For each incoming request:
    1. Clears any stale context vars from previous requests
    2. Generates a new UUID4 request_id
    3. Binds request_id to structlog context vars

    This ensures all logs within a request share the same request_id,
    making request tracing straightforward.

    Example log output:
        2024-01-15T10:30:00Z [info] server_starting request_id=abc-123-def
        2024-01-15T10:30:01Z [info] mod_installed request_id=abc-123-def mod=vsvillage
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and bind correlation context.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            The response from downstream handlers
        """
        # Clear any stale context from previous requests
        clear_contextvars()

        # Generate new request ID for this request
        request_id = str(uuid.uuid4())

        # Bind to structlog context - available to all loggers in this request
        bind_contextvars(request_id=request_id)

        # Also store on request.state for access in handlers if needed
        request.state.request_id = request_id

        return await call_next(request)
