"""Helpers for asserting on WebSocket streams with Starlette's test client.

``WebSocketTestSession.receive_text()`` has no timeout and blocks until the server
sends something, so tests of long-lived streams need a bounded receive.
"""

from typing import Any, cast

import anyio
from starlette.testclient import WebSocketTestSession

DEFAULT_RECEIVE_TIMEOUT = 5.0


def receive_text_within(
    websocket: WebSocketTestSession, timeout: float = DEFAULT_RECEIVE_TIMEOUT
) -> str:
    """Return the next text message, failing if none arrives in time.

    Raises:
        TimeoutError: If the server sends nothing within ``timeout`` seconds.
        WebSocketDisconnect: If the server closes the connection.
    """

    async def receive() -> Any:
        with anyio.fail_after(timeout):
            return await websocket._send_rx.receive()

    message = websocket.portal.call(receive)
    websocket._raise_on_close(message)
    return cast(str, message["text"])
