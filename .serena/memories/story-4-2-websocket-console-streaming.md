# Story 4.2: WebSocket Console Streaming

Status: done

## Summary
Implemented real-time console output streaming via WebSocket with Admin authentication.

## WebSocket Endpoint
`WS /api/v1alpha1/console/ws?api_key=<admin-key>&history_lines=100`

## Authentication
- Query param `?api_key=` (browsers can't set WebSocket headers)
- Timing-safe comparison with `secrets.compare_digest()`
- Close codes:
  - 4001: Unauthorized (missing/invalid key)
  - 4003: Forbidden (Monitor role, Admin required)

## Connection Flow
1. Validate API key → reject if invalid
2. Accept connection
3. Send history (default 100 lines, configurable)
4. Subscribe callback to ConsoleBuffer
5. Stream new lines as they arrive
6. Unsubscribe on disconnect

## Configuration
- `VS_CONSOLE_HISTORY_LINES` - Default history on connect (100)

## Key Implementation
- Separate `ws_router` to bypass api_v1's auth dependency
- Client IP extraction handles proxy headers
- Error logging with client IP

## Tests
9 WebSocket tests added
