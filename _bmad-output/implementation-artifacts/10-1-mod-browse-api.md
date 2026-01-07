# Story 10.1: Mod Browse API

Status: ready-for-dev

## Story

As an **administrator**,
I want **to browse all available mods from the VintageStory mod database**,
So that **I can discover and evaluate mods for installation**.

## Acceptance Criteria

1. **Given** I am authenticated as Admin or Monitor
   **When** I call `GET /api/v1alpha1/mods/browse`
   **Then** I receive a paginated list of all available mods from the mod database
   **And** each mod includes: slug, name, author, summary, downloads, tags, logo URL
   *(Covers FR56)*

2. **Given** I am browsing mods
   **When** I request the list
   **Then** I can specify page size (default 20, max 100) and page number
   **And** the response includes total count and pagination metadata
   *(Covers FR57)*

3. **Given** I am browsing mods
   **When** I request the list with `?sort=downloads` or `?sort=trending` or `?sort=recent`
   **Then** the results are sorted accordingly (downloads desc, trending points desc, lastreleased desc)
   *(Covers FR58)*

4. **Given** the mod database API is unavailable
   **When** I call the browse endpoint
   **Then** I receive a 502 error with code `EXTERNAL_API_ERROR`
   **And** the error message indicates the mod database is unavailable
   *(Covers NFR: graceful degradation)*

5. **Given** I provide invalid pagination parameters
   **When** I call the browse endpoint with `page=0` or `page_size=500`
   **Then** I receive a 400 error with appropriate validation message

## Tasks / Subtasks

- [ ] Task 1: Add Pydantic models for browse response + tests (AC: 1, 2)
  - [ ] Subtask 1.1: Create `ModBrowseItem` model in `api/src/vintagestory_api/models/mods.py`
  - [ ] Subtask 1.2: Create `ModBrowseResponse` model with pagination metadata
  - [ ] Subtask 1.3: Write unit tests for model serialization and validation

- [ ] Task 2: Extend ModApiClient with browse method + tests (AC: 1, 3)
  - [ ] Subtask 2.1: Add `get_all_mods()` method to `ModApiClient` in `mod_api.py`
  - [ ] Subtask 2.2: Implement in-memory caching with TTL (5 minutes) for mod list
  - [ ] Subtask 2.3: Add sorting logic (downloads, trending, recent)
  - [ ] Subtask 2.4: Write unit tests for API call, caching, and sorting

- [ ] Task 3: Add browse API endpoint + tests (AC: 1-5)
  - [ ] Subtask 3.1: Add `GET /mods/browse` endpoint to `routers/mods.py`
  - [ ] Subtask 3.2: Implement pagination (page, page_size with defaults and limits)
  - [ ] Subtask 3.3: Implement sort parameter validation and application
  - [ ] Subtask 3.4: Write integration tests for all AC scenarios

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Both Admin and Monitor roles can access browse endpoint (read-only)
- No sensitive data in browse results
- Rate limiting consideration for external API calls (cache helps)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-api -k "browse"` - Run browse-related tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Existing ModApiClient (api/src/vintagestory_api/services/mod_api.py):**
- Already has `get_mod(slug)` for single mod lookup
- Uses httpx async client with timeout handling
- Has ExternalApiError for API failures
- **New:** Add `get_all_mods()` using `/api/mods` endpoint

**VintageStory ModDB API Reference (agentdocs/vintagestory-modapi.md):**
```
GET /api/mods
Response:
{
  "statuscode": "200",  // STRING, not integer!
  "mods": [
    {
      "modid": 2655,
      "name": "Smithing Plus",
      "summary": "Brief description",
      "author": "jayu",
      "downloads": 204656,
      "follows": 2348,
      "trendingpoints": 1853,
      "side": "both",
      "type": "mod",
      "logo": "https://moddbcdn.vintagestory.at/logo.png",  // May be null
      "tags": ["Crafting", "QoL"],
      "lastreleased": "2025-10-09 21:28:57",
      "urlalias": "smithingplus"  // May be null - use modidstrs[0] as fallback
    }
  ]
}
```

**Important API Notes:**
- Returns 550+ mods in single response (no server-side pagination)
- Results ordered by `lastreleased` (newest first) by default
- `logo` and `urlalias` may be `null`
- `statuscode` is STRING "200", not integer 200
- `modidstrs` array contains slug alternatives when `urlalias` is null

**Caching Strategy:**
- Cache full mod list in memory with 5-minute TTL
- Pagination and sorting applied client-side from cache
- Single cache entry, not per-page caching
- This avoids hammering external API while allowing instant pagination

**Response Envelope Pattern (project-context.md):**
```python
# Success
{"status": "ok", "data": {"mods": [...], "pagination": {...}}}

# Error
{"detail": {"code": "EXTERNAL_API_ERROR", "message": "..."}}
```

**Pagination Model:**
```python
class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
```

### Implementation Details

**ModBrowseItem Model:**
```python
class ModBrowseItem(BaseModel):
    """Single mod in browse list."""
    slug: str  # urlalias or modidstrs[0]
    name: str
    author: str
    summary: str | None = None
    downloads: int
    follows: int
    trending_points: int
    side: Literal["client", "server", "both"]
    mod_type: Literal["mod", "externaltool", "other"]
    logo_url: str | None = None
    tags: list[str] = []
    last_released: str | None = None  # ISO timestamp
```

**Caching Implementation:**
```python
from datetime import datetime, timedelta
from typing import Any

class ModApiClient:
    CACHE_TTL = timedelta(minutes=5)

    def __init__(self, ...):
        ...
        self._mods_cache: list[dict[str, Any]] | None = None
        self._mods_cache_time: datetime | None = None

    def _is_cache_valid(self) -> bool:
        if self._mods_cache is None or self._mods_cache_time is None:
            return False
        return datetime.now() - self._mods_cache_time < self.CACHE_TTL

    async def get_all_mods(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        if not force_refresh and self._is_cache_valid():
            return self._mods_cache

        # Fetch from API
        client = await self._get_client()
        response = await client.get(f"{self.BASE_URL}/mods")
        data = response.json()

        if data.get("statuscode") == "200":
            self._mods_cache = data["mods"]
            self._mods_cache_time = datetime.now()
            return self._mods_cache

        raise ExternalApiError("Failed to fetch mod list")
```

**Sorting Implementation:**
```python
def sort_mods(
    mods: list[dict[str, Any]],
    sort_by: Literal["downloads", "trending", "recent"] = "recent"
) -> list[dict[str, Any]]:
    """Sort mod list by specified criteria."""
    key_map = {
        "downloads": lambda m: m.get("downloads", 0),
        "trending": lambda m: m.get("trendingpoints", 0),
        "recent": lambda m: m.get("lastreleased", ""),
    }
    return sorted(mods, key=key_map[sort_by], reverse=True)
```

**Endpoint Implementation:**
```python
@router.get("/browse", response_model=ApiResponse)
async def browse_mods(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort: Literal["downloads", "trending", "recent"] = Query(
        default="recent", description="Sort order"
    ),
    _: RequireAuth,
    service: ModService = Depends(get_mod_service),
) -> ApiResponse:
    """Browse available mods from the VintageStory mod database."""
    ...
```

### Project Structure Notes

**Files to modify/create:**
- `api/src/vintagestory_api/models/mods.py` - Add ModBrowseItem, PaginationMeta
- `api/src/vintagestory_api/services/mod_api.py` - Add get_all_mods(), caching
- `api/src/vintagestory_api/routers/mods.py` - Add browse endpoint
- `api/tests/test_mod_api.py` - Add tests for get_all_mods()
- `api/tests/test_routers_mods.py` - Add tests for browse endpoint

**Naming Conventions (project-context.md):**
- Python files: snake_case
- Python classes: PascalCase
- API routes: kebab-case in URLs
- JSON fields: snake_case (API boundary)

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: agentdocs/vintagestory-modapi.md] - VintageStory mod database API documentation
- [Source: api/src/vintagestory_api/services/mod_api.py] - Existing ModApiClient patterns
- [Source: api/src/vintagestory_api/routers/mods.py] - Existing mod router patterns
- [Source: epics.md#Epic-10] - Epic requirements (FR56-FR58)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List
