# Story 3.3: Server Status API

Status: done

## Summary
Added GET /status endpoint accessible by both Admin and Monitor roles.

## Endpoint
`GET /api/v1alpha1/server/status` - Returns ServerStatus

## Response Format
```json
{
  "status": "ok",
  "data": {
    "state": "running",          // ServerState enum
    "version": "1.21.3",         // null if not installed
    "uptime_seconds": 3600,      // null if not running
    "last_exit_code": null       // exit code from last run
  }
}
```

## Key Implementation
- Uses `get_current_user` dependency (not `require_admin`) for read-only access
- Intentionally no lock for monitoring endpoint - transitional states acceptable
- Leverages existing `ServerService.get_server_status()` method

## Tests
12 new tests covering Admin/Monitor access, all states, edge cases
