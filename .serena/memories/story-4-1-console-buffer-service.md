# Story 4.1: Console Buffer Service

Status: done

## Summary
Created in-memory ring buffer for game server output with subscriber pattern for real-time streaming.

## ConsoleBuffer Class
```python
class ConsoleBuffer:
    def __init__(self, max_lines: int = 10000)
    async def append(self, line: str)        # Adds timestamp, notifies subscribers
    def get_history(self, limit: int | None)  # Returns buffered lines
    def subscribe(callback)                   # Register for real-time notifications
    def unsubscribe(callback)                 # Remove callback
```

## Key Features
- Deque-based ring buffer (FIFO when full)
- ISO 8601 timestamp prefixing
- Async subscriber callbacks for WebSocket streaming
- Preserves content on server crash (in-memory only, no persistence)

## Integration with ServerService
- `console_buffer` property on ServerService
- `_read_stream()` captures subprocess stdout/stderr
- Stream reader tasks started on server start, cancelled on stop

## API Endpoint
`GET /api/v1alpha1/console/history` - Admin only
- Optional `?lines=N` param (1-10000)
- Returns: `{"lines": [...], "total": N, "limit": N}`

## Tests
41 tests (20 unit, 9 integration, 12 API)
