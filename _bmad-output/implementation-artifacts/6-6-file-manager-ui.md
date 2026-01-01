# Story 6.6: File Manager UI

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator or monitor**,
I want **a web interface to browse and view server configuration files**,
So that **I can troubleshoot configuration issues without SSH access**.

## Acceptance Criteria

1. **Given** I navigate to the Settings tab and select "File Manager", **When** the page loads, **Then** I see a list of available JSON configuration files.

2. **Given** the file list is displayed, **When** I click on a file name (e.g., `serverconfig.json`), **Then** the file contents are displayed in a read-only JSON viewer.

3. **Given** a file is displayed, **When** I view the content, **Then** the JSON is formatted with proper indentation and syntax highlighting.

4. **Given** no file is selected, **When** I view the File Manager, **Then** I see a prompt to select a file from the list.

5. **Given** the serverdata directory is empty, **When** the file list loads, **Then** I see an appropriate empty state message.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

CORRECT PATTERN:
- [ ] Task 1: Implement user login endpoint + tests (AC: 1, 2)
  - [ ] Create login route handler
  - [ ] Add input validation
  - [ ] Write tests for success/failure cases

WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement user login endpoint (AC: 1, 2)
- [ ] Task 2: Implement logout endpoint (AC: 3)
- [ ] Task 3: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Create config files API hooks + types + tests (AC: 1, 2, 5)
  - [x] Subtask 1.1: Add config file types to `web/src/api/types.ts`
    - `ConfigFileListResponse`: `{ files: string[] }`
    - `ConfigFileContentResponse`: `{ filename: string, content: unknown }`
  - [x] Subtask 1.2: Add config files API functions to `web/src/api/config.ts`
    - `fetchConfigFiles()`: GET /config/files
    - `fetchConfigFileContent(filename)`: GET /config/files/{filename}
  - [x] Subtask 1.3: Add query keys for config files to `web/src/api/query-keys.ts`
  - [x] Subtask 1.4: Create `web/src/hooks/use-config-files.ts`
    - `useConfigFiles()`: Query hook for file list
    - `useConfigFileContent(filename)`: Query hook for file content (enabled when filename provided)
  - [x] Subtask 1.5: Write tests for hooks (loading, success, error states)

- [x] Task 2: Create FileList component + tests (AC: 1, 4, 5)
  - [x] Subtask 2.1: Create `web/src/components/FileList.tsx`
  - [x] Subtask 2.2: Display list of file names with click handlers
  - [x] Subtask 2.3: Highlight selected file
  - [x] Subtask 2.4: Handle empty state (no files available)
  - [x] Subtask 2.5: Handle loading state with skeleton
  - [x] Subtask 2.6: Write tests for all states and selection behavior

- [x] Task 3: Create FileViewer component + tests (AC: 2, 3, 4)
  - [x] Subtask 3.1: Create `web/src/components/FileViewer.tsx`
  - [x] Subtask 3.2: Display JSON with proper formatting (JSON.stringify with indentation)
  - [x] Subtask 3.3: Use monospace font and preserve whitespace
  - [x] Subtask 3.4: Handle "no file selected" state with prompt message
  - [x] Subtask 3.5: Handle loading state with skeleton
  - [x] Subtask 3.6: Handle error state (file not found, etc.)
  - [x] Subtask 3.7: Write tests for all states

- [ ] Task 4: Create FileManagerPanel component + tests (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 4.1: Create `web/src/features/settings/FileManagerPanel.tsx`
  - [ ] Subtask 4.2: Compose FileList and FileViewer in split layout
  - [ ] Subtask 4.3: Manage selected file state
  - [ ] Subtask 4.4: Wire up hooks for data fetching
  - [ ] Subtask 4.5: Write integration tests for component interaction

- [ ] Task 5: Integrate FileManagerPanel into SettingsPage + tests (AC: 1)
  - [ ] Subtask 5.1: Replace "Coming Soon" placeholder in SettingsPage.tsx
  - [ ] Subtask 5.2: Import and render FileManagerPanel in File Manager tab
  - [ ] Subtask 5.3: Update SettingsPage tests to verify File Manager renders correctly

- [ ] Task 6: Run full test suite and verify (AC: 1, 2, 3, 4, 5)
  - [ ] Subtask 6.1: Run `just check` to verify lint, typecheck, and all tests pass
  - [ ] Subtask 6.2: Manual verification: navigate to Settings > File Manager, select a file
  - [ ] Subtask 6.3: Verify JSON content displays with proper formatting

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server

### API Endpoints (from Story 6.5)

**List Config Files:**
```
GET /api/v1alpha1/config/files
Authorization: Bearer <api-key>

Response:
{
  "status": "ok",
  "data": {
    "files": ["serverconfig.json", "other-config.json"]
  }
}
```

**Read Config File:**
```
GET /api/v1alpha1/config/files/{filename}
Authorization: Bearer <api-key>

Response:
{
  "status": "ok",
  "data": {
    "filename": "serverconfig.json",
    "content": { /* raw JSON from file */ }
  }
}
```

**Error Response (file not found):**
```json
{
  "detail": {
    "code": "CONFIG_FILE_NOT_FOUND",
    "message": "Config file not found: nonexistent.json"
  }
}
```

### Architecture & Patterns

**Component Layout:**

```
FileManagerPanel
├── FileList (left, ~200px width)
│   ├── File item (clickable)
│   ├── File item (selected, highlighted)
│   └── ...
└── FileViewer (right, flex-1)
    └── JSON content (formatted, read-only)
```

**Responsive Considerations:**
- Desktop: Side-by-side layout (list left, viewer right)
- Mobile: Could stack vertically or use sheet/drawer pattern for file selection

**Query Hook Pattern (from existing hooks):**

```typescript
// Pattern from use-mods.ts
export function useConfigFiles() {
  return useQuery({
    queryKey: queryKeys.configFiles.list(),
    queryFn: fetchConfigFiles,
  });
}

export function useConfigFileContent(filename: string | null) {
  return useQuery({
    queryKey: queryKeys.configFiles.content(filename ?? ''),
    queryFn: () => fetchConfigFileContent(filename!),
    enabled: !!filename, // Only fetch when filename is provided
  });
}
```

**JSON Display Pattern:**

```tsx
// Simple formatted JSON display
<pre className="font-mono text-sm whitespace-pre overflow-auto">
  {JSON.stringify(content, null, 2)}
</pre>
```

For syntax highlighting, consider:
- Simple approach: Just use proper formatting with monospace font
- Enhanced approach: Use a lightweight syntax highlighter if available

### Previous Story Intelligence (Story 6.4)

**Key learnings:**

1. **Tabbed interface** - SettingsPage already uses shadcn/ui Tabs
2. **Component patterns** - ApiSettingsPanel provides good reference for panel structure
3. **Hook patterns** - use-api-settings.ts shows query/mutation patterns for config endpoints
4. **Test patterns** - SettingsPage.test.tsx shows how to test tab content

**Files to reference:**
- `web/src/features/settings/SettingsPage.tsx` - Where File Manager lives
- `web/src/features/settings/ApiSettingsPanel.tsx` - Panel component pattern
- `web/src/hooks/use-api-settings.ts` - Hook pattern for config endpoints
- `web/src/api/config.ts` - Existing config API functions

### Project Structure Notes

**New files to create:**
- `web/src/hooks/use-config-files.ts` - Hooks for config file queries
- `web/src/hooks/use-config-files.test.tsx` - Hook tests
- `web/src/components/FileList.tsx` - File list component
- `web/src/components/FileList.test.tsx` - File list tests
- `web/src/components/FileViewer.tsx` - JSON viewer component
- `web/src/components/FileViewer.test.tsx` - Viewer tests
- `web/src/features/settings/FileManagerPanel.tsx` - Composed panel
- `web/src/features/settings/FileManagerPanel.test.tsx` - Panel tests

**Files to modify:**
- `web/src/api/types.ts` - Add config file response types
- `web/src/api/config.ts` - Add fetch functions
- `web/src/api/query-keys.ts` - Add config files query keys
- `web/src/features/settings/SettingsPage.tsx` - Replace placeholder
- `web/src/features/settings/SettingsPage.test.tsx` - Update tests

### UX Design Considerations

**From ux-design-specification.md:**

1. **Relief-oriented design** - Show file content immediately on selection
2. **Loading states** - Use skeletons while fetching file list and content
3. **Error handling** - Show clear error messages if file can't be loaded
4. **Empty states** - Provide helpful message when no files exist

**Color Semantics (Catppuccin):**
- Selected file: Use accent color for highlight
- Error: `#f38ba8` for error messages
- Muted: `text-muted-foreground` for empty state prompts

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-6-file-manager-ui

# Task-level commits
git commit -m "feat(story-6.6/task-1): create config files API hooks and types"
git commit -m "feat(story-6.6/task-2): create FileList component"
git commit -m "feat(story-6.6/task-3): create FileViewer component"
git commit -m "feat(story-6.6/task-4): create FileManagerPanel component"
git commit -m "feat(story-6.6/task-5): integrate FileManagerPanel into SettingsPage"
git commit -m "feat(story-6.6/task-6): verify full test suite passes"

# Push and create PR
git push -u origin story/6-6-file-manager-ui
gh pr create --title "Story 6.6: File Manager UI" --body "..."
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/implementation-artifacts/6-5-raw-config-viewer.md` - API implementation story
- `_bmad-output/implementation-artifacts/6-4-settings-ui.md` - Previous UI story patterns
- `api/src/vintagestory_api/routers/config.py` - API endpoint definitions
- `web/src/features/settings/SettingsPage.tsx` - Integration target
- `web/src/hooks/use-api-settings.ts` - Hook pattern reference

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

