# Story 13.0: Epic 13 Technical Preparation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **to research VintageStory version APIs and plan the browser implementation**,
So that **subsequent stories have accurate API documentation and design**.

## Acceptance Criteria

1. **Given** we need to fetch available versions
   **When** I research the VintageStory version API
   **Then** I document the response format from stable.json and unstable.json
   **And** I note all available fields (version, filename, filesize, md5, etc.)

2. **Given** we want to show release information
   **When** I research available metadata
   **Then** I document what release info is available (date, changelog, etc.)
   **And** I note any limitations

3. **Given** we need to cache version data
   **When** I design the caching strategy
   **Then** I document cache TTL (versions don't change frequently)
   **And** I specify how to handle cache refresh

4. **Given** we want a similar UX to mod browser
   **When** I design the UI approach
   **Then** I document which patterns can be reused from Epic 10

## Tasks / Subtasks

<!--
🚨 NOTE: This is a documentation/research story. Story 13.1 (Server Versions API)
was already completed before this story was created. The tasks below focus on
documenting findings and updating architecture docs based on what was learned.
-->

- [x] Task 1: Document VintageStory version API findings (AC: 1, 2)
  - [x] Subtask 1.1: Review agentdocs/server-installation.md for existing API documentation
  - [x] Subtask 1.2: Document any gaps or clarifications based on 13-1 implementation
  - [x] Subtask 1.3: Note metadata limitations (no release date, no changelog)

- [x] Task 2: Document caching strategy used in 13-1 (AC: 3)
  - [x] Subtask 2.1: Document VersionsCache extension from Story 13-1
  - [x] Subtask 2.2: Document cache TTL approach (background job refresh)
  - [x] Subtask 2.3: Document cache fallback behavior for API failures

- [x] Task 3: Plan UI component reuse from Epic 10 (AC: 4)
  - [x] Subtask 3.1: Identify mod browser patterns applicable to version browser
  - [x] Subtask 3.2: Document UI component architecture for stories 13.2-13.5
  - [x] Subtask 3.3: Note differences (no tags, no search, simpler filtering)

- [x] Task 4: Update architecture.md with Epic 13 decisions
  - [x] Subtask 4.1: Create architecture/epic-13-server-version-browser.md
  - [x] Subtask 4.2: Document ADRs for version caching and UI patterns
  - [x] Subtask 4.3: Update architecture.md index to include new file

## Dev Notes

### Context: Story 13-1 Already Completed

**Important:** Story 13-1 (Server Versions API) was implemented BEFORE this preparation story was created. The API infrastructure is already in place:

**Files already created/modified in 13-1:**
- `api/src/vintagestory_api/services/versions_cache.py` - Extended with full version list caching
- `api/src/vintagestory_api/routers/versions.py` - New versions router
- `api/src/vintagestory_api/models/versions.py` - Version response models
- `api/src/vintagestory_api/jobs/server_versions.py` - Updated to populate full cache

**This story's focus:** Document what was learned and create architecture decisions for the remaining UI stories (13.2-13.7).

### VintageStory Version API Findings (from 13-1)

**Endpoints:**
```
Stable: https://api.vintagestory.at/stable.json
Unstable: https://api.vintagestory.at/unstable.json
```

**Response Structure (linuxserver platform only):**
```json
{
  "1.21.6": {
    "linuxserver": {
      "filename": "vs_server_linux-x64_1.21.6.tar.gz",
      "filesize": "40.2 MB",
      "md5": "checksum_here",
      "urls": {
        "cdn": "https://cdn.vintagestory.at/gamefiles/stable/...",
        "local": "https://vintagestory.at/api/gamefiles/stable/..."
      },
      "latest": true
    }
  }
}
```

**Available Fields:**
| Field | Type | Notes |
|-------|------|-------|
| version | string | Dictionary key (e.g., "1.21.6") |
| filename | string | Archive filename |
| filesize | string | Human-readable (e.g., "40.2 MB") |
| md5 | string | Checksum for verification |
| urls.cdn | string | Primary download URL |
| urls.local | string | Fallback download URL |
| latest | boolean | Only on newest version |

**Metadata Limitations:**
- ❌ No release date
- ❌ No changelog/release notes
- ❌ No release title/description
- ❌ No dependencies or requirements info

The API is purely for download discovery, not release metadata.

### Caching Strategy (from 13-1 Implementation)

**Cache Architecture:**
```
LatestVersionsCache (singleton)
├── _versions: LatestVersions (stable/unstable latest only)
├── _version_lists: dict[channel, list[VersionInfo]]
└── _cached_at: datetime
```

**Cache Population:**
- Background job `server_versions_check` runs periodically
- Fetches both stable and unstable channels
- Caches full version lists + latest version strings
- TTL: Controlled by job interval (versions change infrequently)

**Cache Fallback:**
- If API fails, return cached data with `cached: true` indicator
- If no cache exists, return 503 error

### UI Patterns from Epic 10 to Reuse

**Reusable Patterns:**
| Epic 10 Pattern | Epic 13 Application |
|----------------|---------------------|
| Card component layout | VersionCard similar to ModCard |
| Channel badges (stable/unstable) | Already planned in 13-2 AC |
| "Installed" badge | Show on currently installed version |
| "Latest" badge | Show on newest in channel |
| TanStack Query cache sync | Invalidate on install/upgrade |

**Not Applicable (simpler than mod browser):**
| Epic 10 Feature | Why Not Needed |
|----------------|----------------|
| Text search | Version numbers are scannable |
| Tag filtering | No tags on versions |
| Side filtering | N/A for server versions |
| Complex pagination | Typically <20 versions total |

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

This is primarily a documentation story, so testing focuses on:
- Verifying architecture documentation is accurate to implementation
- No new code to test

### Security Requirements

Not applicable - this is a documentation/research story.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Key Decision:** Version browser will be simpler than mod browser
- Client-side filtering only (channel filter)
- No search needed
- No pagination needed (small dataset)
- Focus on card display and install flow

### Project Structure Notes

**New file to create:**
- `_bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md`

**File to update:**
- `_bmad-output/planning-artifacts/architecture.md` (add to index)

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: agentdocs/server-installation.md] - VintageStory version API documentation
- [Source: _bmad-output/implementation-artifacts/13-1-server-versions-api.md] - Completed API implementation
- [Source: api/src/vintagestory_api/services/versions_cache.py] - Cache implementation
- [Source: api/src/vintagestory_api/routers/versions.py] - Versions router
- [Source: _bmad-output/planning-artifacts/architecture/epic-10-architecture-decisions.md] - Reusable UI patterns

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Update File List to include Story 13.1 test changes - api/tests/test_server_versions_job.py and api/tests/test_versions_router.py were modified in commit 697420e but not documented in Story 13.0's File List
- [x] [AI-Review][MEDIUM] Update File List to include .mise.toml bump - **Not applicable**: .mise.toml was merged from main (commit f642557), not part of this story's implementation
- [x] [AI-Review][MEDIUM] Add reference in ADR-3 to version tracking documentation - Link to agentdocs/server-installation.md → Version Tracking section for how to determine installed status
- [x] [AI-Review][MEDIUM] Document VersionDetailView contents in ADR - Add ADR-6 or expand ADR-3 to explain what VersionDetailView displays given limited metadata
- [x] [AI-Review][MEDIUM] Justify or make configurable the 24h cache TTL - Document monitoring strategy or add env-specific intervals

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - documentation/research story with no code debugging required.

### Completion Notes List

- Task 1: Updated agentdocs/server-installation.md with metadata limitations (no release dates, changelogs), version ordering caveat (don't rely on key order), and cache architecture pattern from Story 13-1.
- Task 2: Added cache TTL strategy documentation (24h default via server_versions_refresh_interval) and cache fallback behavior (graceful degradation with cached indicator).
- Task 3: Documented UI component reuse strategy - identified reusable patterns (card layout, grid, badges, TanStack Query) and patterns NOT to reuse (search, pagination, complex filters).
- Task 4: Created architecture/epic-13-server-version-browser.md with 6 ADRs covering simplified architecture, UI reuse, version card design, query cache sync, channel filter implementation, and version detail view design.

### File List

- Modified: agentdocs/server-installation.md (Epic 13 implementation notes section)
- Created: _bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md
- Modified: _bmad-output/planning-artifacts/architecture.md (added Epic 13 to index)
- Modified: api/tests/test_versions_router.py (type annotations fix - lint follow-up)
- Modified: api/tests/test_server_versions_job.py (type annotations fix - lint follow-up)
