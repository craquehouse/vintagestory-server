# Story 5.2: Mod Installation API

Status: done

## Summary
Implemented mod installation via API with external VintageStory mod database integration.

## Endpoint
`POST /api/v1alpha1/mods`
```json
{"slug": "smithingplus", "version": "1.8.2"}  // version optional
```

## ModApiClient
- Uses httpx.AsyncClient with follow_redirects=True
- Timeouts: 30s API, 120s downloads
- `get_mod(slug)` - Lookup mod by slug
- `download_mod(slug, version)` - Lookup + download to cache
- URL slug extraction (parse full URLs to slug)

## Status Codes
- 200: Success
- 404: Mod not found
- 409: Mod already installed
- 422: Invalid input
- 502: External API error

## Compatibility Check
```python
def check_compatibility(release, game_version) -> Literal["compatible", "not_verified", "incompatible"]
```
- "compatible": Exact version match in tags
- "not_verified": Same major.minor version
- "incompatible": No match

## Error Handling
- Atomic file writes (temp + rename)
- Cleanup on download failure
- Graceful API timeout handling
- Defensive version format handling

## Files Created
- api/src/vintagestory_api/services/mod_api.py
- api/src/vintagestory_api/routers/mods.py
- api/tests/test_mod_api.py (35 tests)
- api/tests/test_mods_router.py (8 tests)
