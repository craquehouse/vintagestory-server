# Story 5.5: Mod List API

Status: done

## Summary
Simple story exposing existing ModService.list_mods() via API endpoint.

## Endpoint
`GET /api/v1alpha1/mods`
- Both Admin and Monitor can access (read-only)
- Returns installed mods list with pending_restart flag

## Response Format
```json
{
  "status": "ok",
  "data": {
    "mods": [
      {
        "filename": "smithingplus_v1.8.3.zip",
        "slug": "smithingplus",
        "version": "1.8.3",
        "enabled": true,
        "installed_at": "2025-12-29T10:00:00Z",
        "name": "Smithing Plus",
        "authors": ["Author Name"],
        "description": "Mod description"
      }
    ],
    "pending_restart": false
  }
}
```

## Key Design
- Uses existing `ModService.list_mods()` from Story 5.1
- Added `restart_state` property to ModService for testable access
- Empty array when no mods (not 404)
- Inlined response format (no separate model)

## Tests
8 new tests covering all acceptance criteria
