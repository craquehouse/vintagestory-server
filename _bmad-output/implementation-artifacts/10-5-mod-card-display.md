# Story 10.5: Mod Card Display

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **mods displayed as informative cards**,
So that **I can quickly scan and evaluate mods**.

## Acceptance Criteria

1. **Given** browse results are displayed
   **When** I view the mod grid/list
   **Then** each mod shows: thumbnail image (or placeholder), name, author, download count, short description
   *(Covers FR74)*

2. **Given** a mod card is displayed
   **When** I view the compatibility indicator
   **Then** I see a badge showing compatibility with my game server version (Compatible/Not verified/Incompatible)
   *(Covers FR75)*

3. **Given** I see a mod card
   **When** I click anywhere on the card
   **Then** I navigate to the mod detail view
   *(Covers FR76)*

4. **Given** mods have no thumbnail
   **When** the card is rendered
   **Then** a placeholder image is displayed

## Tasks / Subtasks

<!--
🚨 CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement user login endpoint + tests (AC: 1, 2)
  - [ ] Create login route handler
  - [ ] Add input validation
  - [ ] Write tests for success/failure cases

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement user login endpoint (AC: 1, 2)
- [ ] Task 2: Implement logout endpoint (AC: 3)
- [ ] Task 3: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Enhance ModCard component with thumbnail and compatibility badge + tests (AC: 1, 2, 4)
  - [x] Subtask 1.1: Add thumbnail/logo image with placeholder fallback
  - [x] Subtask 1.2: Integrate CompatibilityBadge component
  - [x] Subtask 1.3: Implement compatibility determination from server version
  - [x] Subtask 1.4: Write tests for image display, badge display, and placeholder

- [x] Task 2: Make ModCard clickable for navigation + tests (AC: 3)
  - [x] Subtask 2.1: Add onClick handler with navigation to detail route
  - [x] Subtask 2.2: Style card for clickable appearance (hover states, cursor)
  - [x] Subtask 2.3: Ensure external link doesn't navigate (prevent event bubbling)
  - [x] Subtask 2.4: Write tests for click navigation behavior

- [x] Task 3: Add compatibility hook and service + tests (AC: 2)
  - [x] Subtask 3.1: Create useModCompatibility hook or utility
  - [x] Subtask 3.2: Fetch server version from useServerStatus for comparison
  - [x] Subtask 3.3: Implement version comparison logic (compatible/not_verified/incompatible)
  - [x] Subtask 3.4: Write tests for compatibility determination

- [x] Task 4: Update BrowseTab to pass server version context + tests (AC: 1, 2)
  - [x] Subtask 4.1: Fetch server version in BrowseTab (if not already available)
  - [x] Subtask 4.2: Pass server version to ModCard via context or props
  - [x] Subtask 4.3: Add loading states for version-dependent content
  - [x] Subtask 4.4: Write integration tests for browse with compatibility display

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
- No new security concerns - using existing API client with auth headers
- Server version endpoint already accessible to authenticated users

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web ModCard` - Run specific test file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Existing Components to Leverage:**

1. **ModCard.tsx** (web/src/components/ModCard.tsx) - Placeholder exists, needs enhancement
   - Currently shows: name, author, summary, downloads, follows, trending
   - Missing: thumbnail image, compatibility badge, click navigation

2. **CompatibilityBadge.tsx** (web/src/components/CompatibilityBadge.tsx) - Ready to use
   - Accepts `status: CompatibilityStatus` ('compatible' | 'not_verified' | 'incompatible')
   - Optional `message` for tooltip
   - Uses Catppuccin color scheme (green/yellow/red)

3. **ModBrowseGrid.tsx** (web/src/components/ModBrowseGrid.tsx) - Container for cards
   - Responsive grid: 1-4 columns based on viewport
   - Loading skeleton state built-in
   - Empty state for no results

**Data Available (ModBrowseItem from types.ts):**
```typescript
interface ModBrowseItem {
  slug: string;
  name: string;
  author: string;
  summary: string | null;
  downloads: number;
  follows: number;
  trendingPoints: number;
  side: BrowseModSide;  // 'client' | 'server' | 'both'
  modType: ModType;     // 'mod' | 'externaltool' | 'other'
  logoUrl: string | null;  // Use this for thumbnail!
  tags: string[];
  lastReleased: string | null;  // ISO timestamp (not version!)
}
```

**IMPORTANT - lastReleased Field:**
- Per Story 10.4 review findings, `lastReleased` is an ISO timestamp (e.g., "2025-10-09 21:28:57")
- NOT a game version string - do NOT use for version compatibility!
- Version compatibility requires:
  1. Server version from `GET /api/v1alpha1/server/status`
  2. Mod's supported versions from individual mod detail endpoint
  3. Simple approach: show "Not verified" for all browse cards (detailed compatibility in Story 10.6)

**Compatibility Strategy for Browse Cards:**

Given API limitations (browse endpoint doesn't include version compatibility):

Option A - **Conservative (Recommended):**
- Show "Not verified" badge for ALL browse cards
- Full compatibility only available in mod detail view (Story 10.6)
- User can click to see detailed compatibility before install

Option B - **Optimistic:**
- Don't show compatibility badge in browse grid
- Show badge only in mod detail view
- Risk: User might not see compatibility issues before clicking

**Recommended: Option A** - Aligns with UX spec's "Trust through transparency" principle.

**Thumbnail Implementation:**

```typescript
// Use logoUrl with placeholder fallback
const imageUrl = mod.logoUrl || '/placeholder-mod.svg';

// Or use inline placeholder
<div className="relative aspect-[4/3] overflow-hidden rounded-t-lg bg-muted">
  {mod.logoUrl ? (
    <img
      src={mod.logoUrl}
      alt={`${mod.name} thumbnail`}
      className="h-full w-full object-cover"
      onError={(e) => {
        // Fallback on load error
        e.currentTarget.src = '/placeholder-mod.svg';
      }}
    />
  ) : (
    <div className="flex h-full items-center justify-center">
      <Package className="h-12 w-12 text-muted-foreground" />
    </div>
  )}
</div>
```

**Navigation Pattern:**

```typescript
import { useNavigate } from 'react-router-dom';

function ModCard({ mod }: ModCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    // Navigate to mod detail (Story 10.6 route)
    navigate(`/mods/browse/${mod.slug}`);
  };

  return (
    <Card
      className="h-full cursor-pointer hover:shadow-lg transition-shadow"
      onClick={handleClick}
      data-testid={`mod-card-${mod.slug}`}
    >
      {/* ... */}
    </Card>
  );
}
```

**External Link Handling:**
```typescript
// Prevent external link from triggering card navigation
<a
  href={`https://mods.vintagestory.at/${mod.slug}`}
  target="_blank"
  rel="noopener noreferrer"
  onClick={(e) => e.stopPropagation()}  // Stop bubbling to card!
>
```

### Previous Story Intelligence (Story 10.4)

**From Story 10.4 (Filter & Sort Controls):**

- ModCard is already rendered in BrowseTab via ModBrowseGrid
- Filter state is managed via URL search params
- `useBrowseMods` hook returns filtered/sorted mods
- CompatibilityBadge component exists and is ready to use

**Key Learnings from 10.4:**
- Game version filtering was disabled (API limitation - `lastReleased` is timestamp, not version)
- Tags are now dynamically extracted from available mods
- Sort includes client-side "name" option
- `just check` must pass - all 949 web tests + lint + typecheck

**Files Modified in 10.4:**
- `web/src/components/FilterControls.tsx` - Dynamic tags
- `web/src/hooks/use-browse-mods.ts` - Filter/sort logic
- `web/src/features/mods/BrowseTab.tsx` - Integrated filters

### Git Intelligence

**Recent Commits (Story 10.4):**
```
169cc84 Merge pull request #51 from craquehouse/story/10-4-filter-and-sort-controls
817b597 fix(story-10.4/review): address all 11 code review findings
6e172ab feat(story-10.4/task-4): integrate filter and sort UI in BrowseTab + tests
```

**Patterns Established:**
- Component tests co-located with components (`.test.tsx`)
- lucide-react for icons
- shadcn/ui Card components for card UI
- Catppuccin color scheme for badges

### Implementation Details

**Enhanced ModCard Structure:**

```typescript
// web/src/components/ModCard.tsx
interface ModCardProps {
  mod: ModBrowseItem;
  serverVersion?: string;  // For compatibility badge
  onClick?: () => void;    // For navigation
}

export function ModCard({ mod, serverVersion, onClick }: ModCardProps) {
  // Determine compatibility status
  // For browse grid, use 'not_verified' as conservative default
  // Full compatibility check deferred to mod detail view (Story 10.6)
  const compatibilityStatus: CompatibilityStatus = 'not_verified';

  return (
    <Card
      className="h-full cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
      data-testid={`mod-card-${mod.slug}`}
    >
      {/* Thumbnail */}
      <div className="relative aspect-[16/9] overflow-hidden rounded-t-lg bg-muted">
        {mod.logoUrl ? (
          <img
            src={mod.logoUrl}
            alt={`${mod.name} thumbnail`}
            className="h-full w-full object-cover"
            data-testid={`mod-card-logo-${mod.slug}`}
          />
        ) : (
          <div className="flex h-full items-center justify-center" data-testid={`mod-card-placeholder-${mod.slug}`}>
            <Package className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{mod.name}</CardTitle>
          <CompatibilityBadge status={compatibilityStatus} />
        </div>
        <p className="text-sm text-muted-foreground">by {mod.author}</p>
      </CardHeader>

      <CardContent className="pt-0">
        {mod.summary && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {mod.summary}
          </p>
        )}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Download className="h-3.5 w-3.5" />
            {formatNumber(mod.downloads)}
          </span>
          {/* ... other stats */}
        </div>
      </CardContent>
    </Card>
  );
}
```

**BrowseTab Navigation Integration:**

```typescript
// web/src/features/mods/BrowseTab.tsx
import { useNavigate } from 'react-router-dom';

export function BrowseTab() {
  const navigate = useNavigate();
  // ... existing code

  const handleModClick = (slug: string) => {
    navigate(`/mods/browse/${slug}`);
  };

  return (
    // ...
    <ModBrowseGrid
      mods={filteredMods}
      isLoading={isLoading}
      onModClick={handleModClick}  // New prop
    />
  );
}
```

**ModBrowseGrid Update:**

```typescript
// web/src/components/ModBrowseGrid.tsx
interface ModBrowseGridProps {
  mods: ModBrowseItem[];
  isLoading?: boolean;
  onModClick?: (slug: string) => void;  // New prop
}

export function ModBrowseGrid({ mods, isLoading, onModClick }: ModBrowseGridProps) {
  // ...
  return (
    <div className="grid ...">
      {mods.map((mod) => (
        <ModCard
          key={mod.slug}
          mod={mod}
          onClick={() => onModClick?.(mod.slug)}
        />
      ))}
    </div>
  );
}
```

### Deferred Items (Not in This Story)

Per Epic 10 planning:
- **Story 10.6:** Full mod detail view with actual compatibility check (requires API call)
- **Story 10.7:** Pagination for browse results
- **Story 10.8:** Install integration from browse

**Polish Backlog Items from 10.4:**
- API-028: Game version pre-filtering (requires server version detection)
- API-029: sort=name option in backend API
- API-030: Filter parameters in backend API

### Project Structure Notes

**Files to Modify:**
- `web/src/components/ModCard.tsx` - Add thumbnail, compatibility badge, click handler
- `web/src/components/ModCard.test.tsx` - Add tests for new features
- `web/src/components/ModBrowseGrid.tsx` - Add onModClick prop passthrough
- `web/src/components/ModBrowseGrid.test.tsx` - Add tests for click handling
- `web/src/features/mods/BrowseTab.tsx` - Add navigation handler

**New Files (if needed):**
- `web/public/placeholder-mod.svg` - Placeholder image for mods without logos (or use icon)

**Naming Conventions (project-context.md):**
- React components: PascalCase (`ModCard.tsx`)
- Test files: same name + `.test.tsx`
- Hooks: kebab-case with `use` prefix
- data-testid pattern: `mod-card-{slug}`, `mod-card-logo-{slug}`, etc.

### Git Commit Pattern

```bash
# Task commits should follow this pattern:
git commit -m "feat(story-10.5/task-1): enhance ModCard with thumbnail and compatibility badge"
git commit -m "feat(story-10.5/task-2): add click navigation to ModCard"
git commit -m "feat(story-10.5/task-3): create mod compatibility determination utility"
git commit -m "feat(story-10.5/task-4): integrate navigation in BrowseTab"
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: web/src/components/ModCard.tsx] - Existing placeholder implementation
- [Source: web/src/components/CompatibilityBadge.tsx] - Compatibility badge component
- [Source: web/src/components/ModBrowseGrid.tsx] - Grid container component
- [Source: web/src/features/mods/BrowseTab.tsx] - Browse tab with filters
- [Source: web/src/api/types.ts] - ModBrowseItem interface
- [Source: epics.md#Story-10.5] - Epic requirements (FR74-FR76)
- [Source: 10-4-filter-and-sort-controls.md] - Previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 (2026-01-09):** Enhanced ModCard with thumbnail and compatibility badge. Added aspect-video container with logo image display or Package icon placeholder. Integrated CompatibilityBadge with conservative 'not_verified' default (full compatibility deferred to Story 10.6). All 954 web tests pass.
- **Task 2 (2026-01-09):** Added click navigation support. Optional onClick prop with conditional cursor-pointer and hover shadow styles. External link stopPropagation prevents bubbling. All 959 web tests pass.
- **Task 3 (2026-01-09):** Created mod-compatibility utility with conservative 'not_verified' default for browse cards. Per Dev Notes recommendation, full version comparison deferred to Story 10.6. ModCard now uses getBrowseCardCompatibility(). All 965 web tests pass.
- **Task 4 (2026-01-09):** Integrated navigation in BrowseTab and ModBrowseGrid. Added onModClick prop passthrough to ModCard, useNavigate hook in BrowseTab navigates to /mods/browse/{slug}. All 972 web tests pass.

### File List

- `web/src/components/ModCard.tsx` - Modified: Added thumbnail display, CompatibilityBadge, onClick prop, uses getBrowseCardCompatibility()
- `web/src/components/ModCard.test.tsx` - Modified: Added tests for thumbnail, logo, placeholder, badge, and click navigation behavior
- `web/src/lib/mod-compatibility.ts` - Created: Compatibility utility with conservative defaults and placeholder for Story 10.6
- `web/src/lib/mod-compatibility.test.ts` - Created: Tests for compatibility utility functions
- `web/src/components/ModBrowseGrid.tsx` - Modified: Added onModClick prop for navigation passthrough
- `web/src/components/ModBrowseGrid.test.tsx` - Modified: Added tests for onModClick handler
- `web/src/features/mods/BrowseTab.tsx` - Modified: Added handleModClick with useNavigate for card navigation
- `web/src/features/mods/BrowseTab.test.tsx` - Modified: Added tests for navigation on card click

