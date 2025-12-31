# Story 4.3: Console Command Input

Status: done

## Summary
Added ability to send commands to game server stdin via WebSocket or REST API.

## ServerService Changes
- Added `stdin=asyncio.subprocess.PIPE` to subprocess
- New `async def send_command(command: str) -> bool`
- Echoes command to buffer with `[CMD]` prefix before sending

## WebSocket Protocol
Incoming message:
```json
{"type": "command", "content": "/help"}
```

Error responses:
```json
{"type": "error", "content": "Server is not running"}
{"type": "error", "content": "Invalid message format"}
{"type": "error", "content": "Empty command"}
{"type": "error", "content": "Command too long (max 1000 chars)"}
```

## REST API Endpoint
`POST /api/v1alpha1/console/command`
- Body: `{"command": "/help"}`
- Admin only via `RequireConsoleAccess`
- Returns 400 with `SERVER_NOT_RUNNING` if server stopped

## Files Created/Modified
- api/src/vintagestory_api/models/console.py - ConsoleCommandRequest
- api/src/vintagestory_api/services/server.py - send_command()
- api/src/vintagestory_api/routers/console.py - WebSocket + REST

## Tests
25 new tests for command functionality
