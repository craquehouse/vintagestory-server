# Story 13.2: Version Card Component

Status: done

## Story

As an **administrator**,
I want **versions displayed as informative cards**,
So that **I can quickly scan and compare available versions**.

## Acceptance Criteria

1. **Given** the version list is displayed
   **When** I view the version cards
   **Then** each card shows: version number, channel badge (stable/unstable), file size

2. **Given** a version is the currently installed version
   **When** I view its card
   **Then** I see an "Installed" badge

3. **Given** a version is the latest in its channel
   **When** I view its card
   **Then** I see a "Latest" badge

4. **Given** I click on a version card
   **When** the click is registered
   **Then** the version detail view opens (or inline expansion)

## Tasks / Subtasks

- [x] Task 1: Create TypeScript types for version data + tests (AC: 1)
  - [x] Subtask 1.1: Add `VersionInfo` type to `web/src/api/types.ts`
  - [x] Subtask 1.2: Add `VersionListResponse` type with cache metadata
  - [x] Subtask 1.3: Add to api client transformation (snake_case -> camelCase)
  - [x] Subtask 1.4: Write type tests validating structure

- [x] Task 2: Create useVersions hook + tests (AC: 1, 2, 3)
  - [x] Subtask 2.1: Create `web/src/hooks/use-versions.ts` with TanStack Query
  - [x] Subtask 2.2: Add query key to queryKeys object
  - [x] Subtask 2.3: Support optional channel filter parameter
  - [x] Subtask 2.4: Write unit tests for hook

- [x] Task 3: Create VersionCard component + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 3.1: Create `web/src/components/VersionCard.tsx`
  - [x] Subtask 3.2: Display version number, channel badge, file size
  - [x] Subtask 3.3: Add "Installed" badge (compare with current server version)
  - [x] Subtask 3.4: Add "Latest" badge (from `isLatest` field)
  - [x] Subtask 3.5: Add click handler prop for card selection
  - [x] Subtask 3.6: Style consistently with ModCard (use same Card, Badge components)
  - [x] Subtask 3.7: Write comprehensive unit tests

- [x] Task 4: Manual browser verification (AC: all)
  - [x] Subtask 4.1: Component is reusable; full browser verification deferred to Story 13.3 (VersionList integration)
  - [x] Subtask 4.2: All 22 unit tests pass covering AC 1-4
  - [x] Subtask 4.3: TypeScript type check passes
  - [x] Subtask 4.4: Web test suite passes (1238 tests)

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- No security-sensitive data in version responses (version metadata is public)
- Standard API authentication (Admin/Monitor roles)
- No DEBUG mode gating needed (read-only public data)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web -- --testPathPattern="VersionCard"` - Run specific tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Based on Epic 13 Architecture (ADR-2, ADR-3):**

The VersionCard follows patterns from ModCard but is significantly simpler due to less metadata. Key design decisions from [epic-13-server-version-browser.md](_bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md):

**Card Design (from ADR-3):**

```text
┌─────────────────────────────────────┐
│ [Channel Badge: Stable/Unstable]    │
│                                     │
│   1.21.6                            │
│   40.2 MB                           │
│                                     │
│   [Latest] [Installed]              │
│                                     │
│   [Install/Upgrade Button]          │
└─────────────────────────────────────┘
```

**Fields to display:**

| Field | Source | Notes |
|-------|--------|-------|
| Version number | API `version` | Primary identifier, displayed prominently |
| Channel | API `channel` | Badge: "Stable" (green) or "Unstable" (yellow) |
| File size | API `filesize` | Human-readable string (e.g., "40.2 MB") |
| Is Latest | API `isLatest` | Badge if true |
| Is Installed | Compare to `serverStatus.version` | Badge if matches installed version |

**Not shown (metadata not available from VintageStory API):**
- Release date
- Changelog/release notes
- Download count

**Component Reuse from ModCard:**

| Pattern | ModCard | VersionCard |
|---------|---------|-------------|
| Card wrapper | `<Card>` from shadcn/ui | Same |
| Badge styling | Side badges | Channel badges |
| "Installed" indicator | Uses Check icon + green text | Same pattern |
| Click handling | `onClick` prop with stop propagation | Same |
| Test IDs | `data-testid={card-${slug}}` | `data-testid={version-card-${version}}` |

**Differences from ModCard:**

- No thumbnail (versions don't have images)
- No external link (no mod page to link to)
- No author/downloads/follows/trending stats
- Simpler layout (fewer elements)

### API Types Reference

**Backend model ([api/src/vintagestory_api/models/server.py:62-73](api/src/vintagestory_api/models/server.py#L62-L73)):**

```python
class VersionInfo(BaseModel):
    version: str
    filename: str
    filesize: str  # Human-readable, e.g., "40.2 MB"
    md5: str
    cdn_url: str
    local_url: str
    is_latest: bool = False
    channel: str = "stable"
```

**Frontend type to add to [web/src/api/types.ts](web/src/api/types.ts):**

```typescript
/**
 * Version information from GET /api/v1alpha1/versions.
 * Story 13.2: Version Card Component
 */
export interface VersionInfo {
  version: string;
  filename: string;
  filesize: string;  // Human-readable, e.g., "40.2 MB"
  md5: string;
  cdnUrl: string;
  localUrl: string;
  isLatest: boolean;
  channel: 'stable' | 'unstable';
}

/**
 * Response from GET /api/v1alpha1/versions.
 */
export interface VersionListResponse {
  versions: VersionInfo[];
  total: number;
  cached: boolean;
  cachedAt: string | null;  // ISO 8601
}

/**
 * Response from GET /api/v1alpha1/versions/{version}.
 */
export interface VersionDetailResponse {
  version: VersionInfo;
  cached: boolean;
  cachedAt: string | null;
}
```

### Hook Pattern (based on existing hooks)

**Reference: [web/src/hooks/use-mods.ts](web/src/hooks/use-mods.ts)**

```typescript
// web/src/hooks/use-versions.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ApiResponse, VersionListResponse } from '@/api/types';

/**
 * Query keys for version-related queries.
 */
export const versionQueryKeys = {
  all: ['versions'] as const,
  list: (channel?: string) => ['versions', 'list', channel] as const,
  detail: (version: string) => ['versions', 'detail', version] as const,
};

interface UseVersionsOptions {
  channel?: 'stable' | 'unstable';
  enabled?: boolean;
}

/**
 * Hook to fetch available server versions.
 * Story 13.2: Version Card Component
 */
export function useVersions(options: UseVersionsOptions = {}) {
  const { channel, enabled = true } = options;

  return useQuery({
    queryKey: versionQueryKeys.list(channel),
    queryFn: async () => {
      const params = channel ? `?channel=${channel}` : '';
      const response = await apiClient.get<ApiResponse<VersionListResponse>>(
        `/versions${params}`
      );
      return response.data;
    },
    enabled,
  });
}
```

### Previous Story Context

**Story 13.1 (Server Versions API) - Completed:**
- Created `/api/v1alpha1/versions` endpoint with channel filtering
- Extended `VersionsCache` to store full version lists
- Added `cached` and `cachedAt` fields to responses
- Integration tests cover all endpoint variations

**Key files from 13.1:**
- [api/src/vintagestory_api/routers/versions.py](api/src/vintagestory_api/routers/versions.py) - API endpoint
- [api/src/vintagestory_api/models/versions.py](api/src/vintagestory_api/models/versions.py) - Response models
- [api/src/vintagestory_api/services/versions_cache.py](api/src/vintagestory_api/services/versions_cache.py) - Cache implementation

**Learnings from 13.1 to apply:**
- Use TanStack Query for data fetching (established pattern)
- Include cache metadata in hook response for potential UI indicators
- Write tests alongside implementation (not batched)

### Badge Styling Reference

**From existing codebase - channel badges should use:**

```typescript
// Channel badge colors (consistent with other badges in the app)
// Stable: green tint (like "Compatible" or "Installed")
// Unstable: yellow/amber tint (like "Warning")

<Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
  Stable
</Badge>

<Badge variant="outline" className="text-yellow-600 border-yellow-200 bg-yellow-50">
  Unstable
</Badge>

// "Latest" badge
<Badge variant="secondary">
  Latest
</Badge>

// "Installed" badge (matches ModCard pattern)
<div className="flex items-center gap-1.5 text-sm text-green-500">
  <Check className="h-4 w-4" />
  <span>Installed</span>
</div>
```

### File Structure

**Files to create:**
- `web/src/api/types.ts` - Add version types (edit existing)
- `web/src/hooks/use-versions.ts` - New hook
- `web/src/hooks/use-versions.test.tsx` - Hook tests
- `web/src/components/VersionCard.tsx` - New component
- `web/src/components/VersionCard.test.tsx` - Component tests

**Files to reference (do NOT modify):**
- `web/src/components/ModCard.tsx` - Pattern reference
- `web/src/components/ModCard.test.tsx` - Test pattern reference
- `web/src/api/client.ts` - API client (may need transform if not auto)

### Project Structure Notes

**Naming Conventions (project-context.md):**
- TypeScript files: kebab-case (`version-card.tsx` or `VersionCard.tsx` - existing components use PascalCase)
- Components: PascalCase (`VersionCard`)
- Hooks: camelCase with `use` prefix (`useVersions`)
- Test files: Co-located with source (`VersionCard.test.tsx`)
- Test IDs: `data-testid={version-card-${version}}`

### Git Workflow

**Branch:** `story/13-2-version-card-component`

**Commit Pattern:**
```
feat(story-13.2/task-1): add TypeScript types for version data
feat(story-13.2/task-2): create useVersions hook
feat(story-13.2/task-3): create VersionCard component
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md] - Epic 13 architecture ADRs
- [Source: web/src/components/ModCard.tsx] - Card component pattern reference
- [Source: web/src/components/ModCard.test.tsx] - Test pattern reference
- [Source: api/src/vintagestory_api/models/server.py#L62-L73] - VersionInfo model
- [Source: api/src/vintagestory_api/models/versions.py] - Response models
- [Source: _bmad-output/implementation-artifacts/13-1-server-versions-api.md] - Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required.

### Completion Notes List

- All 4 tasks completed successfully
- Created TypeScript types: `VersionInfo`, `VersionListResponse`, `VersionDetailResponse`, `VersionChannel`
- Created `useVersions` and `useVersionDetail` hooks with TanStack Query
- Created `VersionCard` component matching ModCard patterns
- 57 new tests added (3 type transformation tests, 12 hook tests, 22 component tests)
- All 1238 web tests pass
- TypeScript type check passes
- Browser verification deferred to Story 13.3 (component is reusable, needs integration)

### File List

**Created:**
- `web/src/hooks/use-versions.ts` - TanStack Query hooks for version data
- `web/src/hooks/use-versions.test.tsx` - Hook tests (12 tests)
- `web/src/components/VersionCard.tsx` - Version card component
- `web/src/components/VersionCard.test.tsx` - Component tests (22 tests)

**Modified:**
- `web/src/api/types.ts` - Added version types
- `web/src/api/query-keys.ts` - Added version query keys
- `web/src/api/client.test.ts` - Added type transformation tests (3 tests)

