# Story 6.4: Settings UI

Status: complete

## Story

As an **administrator**,
I want **a web interface for managing game and API settings**,
So that **I can configure the server visually and see console command feedback**.

## Acceptance Criteria

1. **Given** I navigate to the GameServer tab as Admin, **When** the page loads on desktop (≥1024px), **Then** I see Game Config panel on left and Console on right (split view).

2. **Given** I navigate to the GameServer tab on mobile (<1024px), **When** the page loads, **Then** I see Console on top and Game Config below (stacked, scrollable).

3. **Given** I change the ServerName field in Game Config, **When** I blur the field (auto-save), **Then** the API is called and I see the `/serverconfig` command execute in Console, **And** a success toast appears.

4. **Given** I change a restart-required setting (e.g., Port), **When** the save completes, **Then** the PendingRestartBanner appears (consistent with mod changes).

5. **Given** a setting is managed by VS_CFG_* environment variable, **When** I view the setting, **Then** it shows an "Env: VS_CFG_*" badge and the input is disabled.

6. **Given** I navigate to the Settings tab, **When** the page loads, **Then** I see tabs for "API Settings" and "File Manager", **And** API Settings shows auto_start, env handling, and refresh intervals, **And** File Manager shows a "coming soon" stub.

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

- [x] Task 1: Create Game Settings API hooks + types + tests (AC: 3, 4, 5)
  - [x] Subtask 1.1: Add game config types to `web/src/api/types.ts`
  - [x] Subtask 1.2: Add game config API functions to `web/src/api/config.ts`
  - [x] Subtask 1.3: Add query keys for game config to `web/src/api/query-keys.ts`
  - [x] Subtask 1.4: Create `web/src/hooks/use-game-config.ts` with useGameConfig query hook
  - [x] Subtask 1.5: Create useUpdateGameSetting mutation hook with optimistic updates
  - [x] Subtask 1.6: Write tests for useGameConfig and useUpdateGameSetting hooks

- [x] Task 2: Create API Settings hooks + tests (AC: 6)
  - [x] Subtask 2.1: Add api settings types to `web/src/api/types.ts`
  - [x] Subtask 2.2: Add api settings API functions to `web/src/api/config.ts`
  - [x] Subtask 2.3: Add query keys for api settings to `web/src/api/query-keys.ts`
  - [x] Subtask 2.4: Create `web/src/hooks/use-api-settings.ts` with useApiSettings and useUpdateApiSetting hooks
  - [x] Subtask 2.5: Write tests for useApiSettings and useUpdateApiSetting hooks

- [x] Task 3: Create useSettingField custom hook + tests (AC: 3, 4, 5)
  - [x] Subtask 3.1: Create `web/src/hooks/use-setting-field.ts` with Zod validation pattern
  - [x] Subtask 3.2: Implement field state management (value, error, isDirty, isPending)
  - [x] Subtask 3.3: Implement auto-save on blur with validation
  - [x] Subtask 3.4: Write tests for validation, save, and error handling

- [x] Task 4: Create SettingField component + tests (AC: 3, 5)
  - [x] Subtask 4.1: Create `web/src/components/SettingField.tsx` base component
  - [x] Subtask 4.2: Implement text/number/boolean input variants
  - [x] Subtask 4.3: Implement env_managed badge and disabled state
  - [x] Subtask 4.4: Add loading spinner during save, error display
  - [x] Subtask 4.5: Write tests for all variants and states

- [x] Task 5: Create SettingGroup component + tests (AC: 3)
  - [x] Subtask 5.1: Create `web/src/components/SettingGroup.tsx` for grouping related settings
  - [x] Subtask 5.2: Implement collapsible sections with Card wrapper
  - [x] Subtask 5.3: Write tests for render and collapse behavior

- [x] Task 6: Create GameConfigPanel component + tests (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 6.1: Create `web/src/features/game-server/GameConfigPanel.tsx`
  - [x] Subtask 6.2: Organize settings into SettingGroups (Server Info, Player Settings, World Settings)
  - [x] Subtask 6.3: Wire up each setting field with appropriate validation schema
  - [x] Subtask 6.4: Handle loading and error states with skeletons
  - [x] Subtask 6.5: Write tests for render, field updates, and validation

- [x] Task 7: Create GameServerPage with responsive split layout + tests (AC: 1, 2)
  - [x] Subtask 7.1: Create `web/src/features/game-server/GameServerPage.tsx`
  - [x] Subtask 7.2: Implement desktop split layout (lg:flex-row, left: GameConfigPanel, right: Console)
  - [x] Subtask 7.3: Implement mobile stacked layout (flex-col, top: Console, bottom: GameConfigPanel)
  - [x] Subtask 7.4: Extract console functionality from Terminal.tsx to reusable component
  - [x] Subtask 7.5: Write tests for responsive layout behavior

- [x] Task 8: Rename Console → GameServer in navigation + tests (AC: 1)
  - [x] Subtask 8.1: Update `web/src/components/layout/Sidebar.tsx` - change Terminal label to "Game Server"
  - [x] Subtask 8.2: Update `web/src/App.tsx` - rename route from /terminal to /game-server, update import
  - [x] Subtask 8.3: Update any references to old route paths
  - [x] Subtask 8.4: Write/update navigation tests

- [x] Task 9: Create ApiSettingsPanel component + tests (AC: 6)
  - [x] Subtask 9.1: Create `web/src/features/settings/ApiSettingsPanel.tsx`
  - [x] Subtask 9.2: Display auto_start_server, block_env_managed_settings, enforce_env_on_restart toggles
  - [x] Subtask 9.3: Display mod_list_refresh_interval, server_versions_refresh_interval number inputs
  - [x] Subtask 9.4: Wire up settings with useApiSettings and useUpdateApiSetting hooks
  - [x] Subtask 9.5: Write tests for render and setting updates

- [x] Task 10: Create SettingsPage with tabs + tests (AC: 6)
  - [x] Subtask 10.1: Create `web/src/features/settings/SettingsPage.tsx`
  - [x] Subtask 10.2: Implement shadcn/ui Tabs component with "API Settings" and "File Manager" tabs
  - [x] Subtask 10.3: Add ApiSettingsPanel under "API Settings" tab
  - [x] Subtask 10.4: Add "Coming Soon" placeholder under "File Manager" tab
  - [x] Subtask 10.5: Update `web/src/App.tsx` - route /config to SettingsPage instead of ConfigEditor
  - [x] Subtask 10.6: Write tests for tab switching and content rendering

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- DEBUG mode gating for test/dev endpoints
- Timing-safe comparison for sensitive data (API keys, passwords)
- Never log sensitive data in plaintext
- Proxy-aware client IP logging
- RBAC patterns for endpoint protection

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server

### Architecture & Patterns

**Architectural Context (Epic 6):**

The architectural pivot means console commands handle live updates, not file editing. The frontend simply calls `POST /config/game/settings/{key}` - it never constructs console commands. The API decides whether to use console command or file update based on server state.

**Two Config Domains:**
- `/api/v1alpha1/config/game` - Game server settings (serverconfig.json)
- `/api/v1alpha1/config/api` - API operational settings (api-settings.json)

**Game Settings Response Format (from architecture.md):**

```json
{
  "status": "ok",
  "data": {
    "settings": [
      {
        "key": "ServerName",
        "value": "My Server",
        "type": "string",
        "live_update": true,
        "env_managed": false
      },
      {
        "key": "Port",
        "value": 42420,
        "type": "int",
        "live_update": false,
        "requires_restart": true
      }
    ],
    "source_file": "serverconfig.json",
    "last_modified": "2025-12-30T10:00:00Z"
  }
}
```

**Game Setting Update Response:**

```json
{
  "status": "ok",
  "data": {
    "key": "ServerName",
    "value": "New Server Name",
    "method": "console_command",
    "pending_restart": false
  }
}
```

**API Settings Response Format (from Story 6.3):**

```json
{
  "status": "ok",
  "data": {
    "settings": {
      "auto_start_server": false,
      "block_env_managed_settings": true,
      "enforce_env_on_restart": false,
      "mod_list_refresh_interval": 3600,
      "server_versions_refresh_interval": 86400
    }
  }
}
```

**useSettingField Pattern (from architecture.md):**

```typescript
function useSettingField<T>(key: string, initialValue: T) {
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const mutation = useUpdateGameSetting();

  const validate = (val: unknown): string | null => {
    const fieldSchema = gameSettingSchema.shape[key];
    if (!fieldSchema) return null;
    const result = fieldSchema.safeParse(val);
    return result.success ? null : result.error.errors[0]?.message ?? "Invalid";
  };

  const save = async () => {
    const err = validate(value);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    await mutation.mutateAsync({ key, value });
  };

  return {
    value,
    setValue,
    error: error ?? (mutation.error ? String(mutation.error) : null),
    save,
    isPending: mutation.isPending,
    isDirty: value !== initialValue,
  };
}
```

**Responsive Layout Pattern:**

```tsx
// GameServerPage responsive split
<div className="flex h-full flex-col lg:flex-row gap-4">
  {/* Desktop: left panel, Mobile: bottom panel */}
  <div className="order-2 lg:order-1 lg:w-1/2 overflow-auto">
    <GameConfigPanel />
  </div>
  {/* Desktop: right panel, Mobile: top panel */}
  <div className="order-1 lg:order-2 lg:w-1/2 flex-1 lg:flex-none">
    <ConsolePanel />
  </div>
</div>
```

### Previous Story Intelligence (Story 6.3)

**Key learnings:**

1. **ApiSettingsService pattern** - Service at `api/src/vintagestory_api/services/api_settings.py`
2. **Atomic file writes** - Use temp file + rename pattern
3. **Router pattern** - API settings endpoints at `/config/api`
4. **Admin-only access** - All API settings endpoints require Admin role
5. **Scheduler callback stub** - Ready for Epic 7 integration

**Files created in Story 6.3:**
- `api/src/vintagestory_api/services/api_settings.py`
- `api/tests/test_api_settings.py`
- Router extensions in `api/src/vintagestory_api/routers/config.py`

### Existing Code to Reuse

**File: `web/src/features/terminal/Terminal.tsx`**
- Console functionality can be extracted to a reusable ConsolePanel component
- WebSocket hook pattern from `use-console-websocket.ts`

**File: `web/src/hooks/use-mods.ts`**
- Pattern for TanStack Query hooks with optimistic updates
- Cache invalidation pattern for mutations

**File: `web/src/hooks/use-server-status.ts`**
- Pattern for polling queries
- Pattern for toast notifications on state changes

**File: `web/src/components/ModTable.tsx`**
- Pattern for table with loading/empty states

**File: `web/src/components/PendingRestartBanner.tsx`**
- Already integrated with mods - needs to also respond to config changes
- Uses `useModsPendingRestart()` - may need to extend to config pending restart

### Project Structure Notes

**New files to create:**
- `web/src/api/config.ts` - API functions for game/api config
- `web/src/hooks/use-game-config.ts` - Game config query/mutation hooks
- `web/src/hooks/use-api-settings.ts` - API settings query/mutation hooks
- `web/src/hooks/use-setting-field.ts` - Field state management hook
- `web/src/components/SettingField.tsx` - Reusable setting input component
- `web/src/components/SettingGroup.tsx` - Setting group container
- `web/src/features/game-server/GameServerPage.tsx` - Main game server page
- `web/src/features/game-server/GameConfigPanel.tsx` - Game config settings panel
- `web/src/features/settings/SettingsPage.tsx` - Settings page with tabs
- `web/src/features/settings/ApiSettingsPanel.tsx` - API settings panel

**Files to modify:**
- `web/src/App.tsx` - Update routes
- `web/src/components/layout/Sidebar.tsx` - Rename Terminal → GameServer
- `web/src/api/types.ts` - Add game/api config types
- `web/src/api/query-keys.ts` - Add config query keys
- `web/src/features/terminal/Terminal.tsx` - Extract ConsolePanel

**Directories to create:**
- `web/src/features/game-server/`
- `web/src/features/settings/`

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-4-settings-ui

# Task-level commits
git commit -m "feat(story-6.4/task-1): create game settings API hooks and types"
git commit -m "feat(story-6.4/task-2): create API settings hooks"
git commit -m "feat(story-6.4/task-3): create useSettingField hook with Zod validation"
git commit -m "feat(story-6.4/task-4): create SettingField component"
git commit -m "feat(story-6.4/task-5): create SettingGroup component"
git commit -m "feat(story-6.4/task-6): create GameConfigPanel component"
git commit -m "feat(story-6.4/task-7): create GameServerPage with split layout"
git commit -m "refactor(story-6.4/task-8): rename Console to GameServer in navigation"
git commit -m "feat(story-6.4/task-9): create ApiSettingsPanel component"
git commit -m "feat(story-6.4/task-10): create SettingsPage with tabs"

# Push and create PR
git push -u origin story/6-4-settings-ui
gh pr create --title "Story 6.4: Settings UI" --body "..."
```

### UX Design Considerations (from ux-design-specification.md)

**Key UX Requirements:**

1. **Relief-oriented design** - Eliminate steps, show success immediately
2. **Fail loudly, succeed quietly** - Errors prominent, success subtle (toasts)
3. **Auto-save on blur** - No explicit save button for individual fields
4. **Pending restart awareness** - Consistent pattern with mod changes
5. **Env-managed visual distinction** - Clear badge + disabled input
6. **Responsive breakpoints** - Desktop ≥1024px (lg), Mobile <1024px

**Component Patterns:**
- Use shadcn/ui Card for panels
- Use shadcn/ui Input for text/number fields
- Use shadcn/ui Switch for boolean fields
- Use shadcn/ui Badge for env_managed indicator
- Use shadcn/ui Tabs for Settings page sections
- Use sonner toast for success/error feedback

**Color Semantics (Catppuccin):**
- Success: `#a6e3a1` (subtle treatment)
- Error: `#f38ba8` (prominent treatment)
- Warning: `#f9e2af` (pending restart, env-managed)
- Info: `#89b4fa` (informational badges)

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` - Full architecture details
- `_bmad-output/planning-artifacts/ux-design-specification.md` - UX patterns and component guidance
- `_bmad-output/implementation-artifacts/6-3-api-settings-service.md` - Previous story (API settings backend)
- `web/src/hooks/use-mods.ts` - TanStack Query hook patterns
- `web/src/features/terminal/Terminal.tsx` - Console component to extract

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

1. **All 10 tasks completed** - Full implementation of Settings UI story
2. **551 tests passing** - All web tests pass with clean output
3. **Test quality improvements made:**
   - Fixed React `act()` warnings in `SettingField.test.tsx` by wrapping promise resolution in `act()`
   - Fixed Radix UI accessibility warnings in `Layout.tsx` by adding `SheetTitle` and `SheetDescription` with `sr-only` class
   - Suppressed debug logs during tests by adding `!import.meta.env.VITEST` check to `debugLog()` in `use-console-websocket.ts`
4. **Navigation updated:** Terminal → "Game Server" (kept Terminal icon per user preference)
5. **Routes updated:** `/terminal` → `/game-server`, `/config` → SettingsPage with tabs

### File List

**New files created:**
- `web/src/components/ConsolePanel.tsx` - Reusable console panel extracted from Terminal
- `web/src/components/ConsolePanel.test.tsx` - Tests for ConsolePanel
- `web/src/features/game-server/GameServerPage.tsx` - Responsive split layout page
- `web/src/features/game-server/GameServerPage.test.tsx` - Tests for GameServerPage
- `web/src/features/game-server/index.ts` - Feature exports
- `web/src/features/settings/ApiSettingsPanel.tsx` - API settings management panel
- `web/src/features/settings/ApiSettingsPanel.test.tsx` - Tests for ApiSettingsPanel
- `web/src/features/settings/SettingsPage.tsx` - Tabbed settings page
- `web/src/features/settings/SettingsPage.test.tsx` - Tests for SettingsPage
- `web/src/features/settings/index.ts` - Feature exports
- `web/src/components/ui/tabs.tsx` - shadcn/ui Tabs component

**Files modified:**
- `web/src/App.tsx` - Updated routes for game-server and settings
- `web/src/components/layout/Sidebar.tsx` - Changed Terminal to "Game Server"
- `web/src/components/layout/Sidebar.test.tsx` - Updated navigation tests
- `web/src/components/layout/Layout.tsx` - Added SheetTitle/SheetDescription for accessibility
- `web/src/components/SettingField.test.tsx` - Fixed act() warnings
- `web/src/hooks/use-console-websocket.ts` - Suppressed debug logs during tests
- `web/src/hooks/use-setting-field.ts` - Updated validator types to use SettingValue union
