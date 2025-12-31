# Story 5.0: Epic 5 Technical Preparation

Status: done

## Summary
Technical preparation for Epic 5 (Mod Management) - research, test refactoring, documentation updates.

## Key Deliverables

### 1. Architecture Document Update
Added Epic 5 patterns:
- External API integration (httpx client)
- Mod service boundaries
- Caching architecture (TTL-based)
- Pending restart pattern
- Testing with respx

### 2. Test Refactoring
Split large test files into focused modules:
- `tests/server/` - 136 tests (validation, versions, install, lifecycle, endpoints)
- `tests/console/` - 75 tests (buffer, service, history, command, websocket)
- Total: 308 tests

### 3. Research Documents Created
- `agentdocs/pending-restart-patterns.md` - UI pattern for restart tracking
- `agentdocs/caching-patterns.md` - TTL strategy for API responses
- `agentdocs/test-refactoring-guide.md` - Migration plan

### 4. Manual Test Checklist
`docs/epic-5-manual-test-checklist.md` - 30+ test cases for Epics 1-4

## VintageStory Mod API Notes
- Base URL: `https://mods.vintagestory.at/api/`
- Status codes are STRINGS ("200", "404")
- `releases[0]` is always latest
- Download redirects to CDN

## Caching TTLs
| Cache Type | TTL |
|------------|-----|
| Mod details | 1 hour |
| Game versions | 24 hours |
| Server tarballs | Permanent |
| Mod files | Permanent |
