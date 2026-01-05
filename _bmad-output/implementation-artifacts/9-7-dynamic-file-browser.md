# Story 9.7: Dynamic File Browser

Status: ready-for-dev

## Story

As an **administrator**,
I want **the file browser to show all directories dynamically**,
So that **I can access ModConfigs, Macros, Playerdata, and other directories**.

## Acceptance Criteria

1. **Given** I open the file browser
   **When** the directory listing loads
   **Then** all directories under `/data/serverdata/` are displayed
   **And** this includes ModConfigs, Macros, Playerdata, and any others present
   *(Covers FR54)*

2. **Given** the file browser lists directories
   **When** the list is generated
   **Then** it is dynamically discovered from the filesystem (not hardcoded)
   *(Covers FR55)*

3. **Given** a new directory is created in `/data/serverdata/`
   **When** I refresh the file browser
   **Then** the new directory appears in the listing

## Tasks / Subtasks

- [ ] Task 1: Extend ConfigFilesService to list directories + tests (AC: 2, 3)
  - [ ] Subtask 1.1: Add `list_directories()` method to `ConfigFilesService`
  - [ ] Subtask 1.2: Dynamically discover all subdirectories in serverdata_dir
  - [ ] Subtask 1.3: Write unit tests for directory listing behavior

- [ ] Task 2: Add API endpoint for directory listing + tests (AC: 2)
  - [ ] Subtask 2.1: Add `GET /config/directories` endpoint to config router
  - [ ] Subtask 2.2: Return list of directory names under serverdata
  - [ ] Subtask 2.3: Write integration tests for the new endpoint

- [ ] Task 3: Extend ConfigFilesService to support subdirectory file listing + tests (AC: 1, 3)
  - [ ] Subtask 3.1: Modify `list_files()` to accept optional `directory` parameter
  - [ ] Subtask 3.2: List files within specified subdirectory when provided
  - [ ] Subtask 3.3: Write tests for subdirectory file listing

- [ ] Task 4: Update frontend hooks and FileManagerPanel UI + tests (AC: 1)
  - [ ] Subtask 4.1: Add `useConfigDirectories` hook in `use-config-files.ts`
  - [ ] Subtask 4.2: Update `useConfigFiles` to accept optional directory parameter
  - [ ] Subtask 4.3: Update `FileList` component to show directories with folder icons
  - [ ] Subtask 4.4: Update `FileManagerPanel` to handle directory navigation
  - [ ] Subtask 4.5: Write component tests for directory browsing UI

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Path traversal prevention is CRITICAL - the existing `_safe_path()` pattern in ConfigFilesService must be applied to all directory operations
- Reject any directory path containing `..` or absolute paths
- Only allow navigation within serverdata_dir

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-web` - Run web tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Current Implementation (ConfigFilesService - api/src/vintagestory_api/services/config_files.py):**
- `list_files()` lists JSON files in serverdata_dir (non-recursive, top-level only)
- `read_file()` reads a specific JSON file with path traversal protection
- Uses `_safe_path()` pattern to prevent directory escape attacks

**Current API Endpoints (api/src/vintagestory_api/routers/config.py):**
- `GET /config/files` - List JSON files (calls `list_files()`)
- `GET /config/files/{filename}` - Read file content (calls `read_file()`)

**Current Frontend (web/src/features/settings/FileManagerPanel.tsx):**
- Uses `useConfigFiles()` hook to fetch file list
- Uses `useConfigFileContent(filename)` hook to fetch file content
- FileList component renders files with selection state
- FileViewer component renders file content with JSON highlighting (Story 9.6)

**Required Changes:**

1. **Backend:**
   - Add `list_directories()` method → returns list of subdirectory names
   - Modify `list_files()` to accept optional `directory` parameter
   - Add `GET /config/directories` endpoint
   - Modify `GET /config/files` to accept optional `?directory=` query param

2. **Frontend:**
   - Add `useConfigDirectories()` hook
   - Modify `useConfigFiles(directory?)` to accept optional directory
   - Update FileList to show directories with folder icons
   - Add breadcrumb navigation for directory hierarchy
   - Handle directory selection vs file selection

### VintageStory Server Data Directory Structure

The `/data/serverdata/` directory typically contains:
```
serverdata/
├── serverconfig.json       (main config file)
├── servermapconfig.json    (world generation settings)
├── ModConfigs/             (per-mod configuration files)
│   ├── modname.json
│   └── ...
├── Macros/                 (player macros)
├── Playerdata/             (player data files)
├── Worlds/                 (save data - might be large)
└── [other dynamic dirs]
```

**Important:** Some directories like `Worlds/` may contain many files. Consider pagination or lazy loading if performance becomes an issue (post-MVP).

### Implementation Details

**Backend - list_directories():**
```python
def list_directories(self) -> list[str]:
    """List all subdirectories in serverdata directory.

    Returns:
        List of subdirectory names (not full paths) found in serverdata_dir.
        Empty list if directory doesn't exist.
    """
    serverdata_dir = self.settings.serverdata_dir

    if not serverdata_dir.exists():
        return []

    return sorted(
        d.name for d in serverdata_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    )
```

**Backend - modified list_files():**
```python
def list_files(self, directory: str | None = None) -> list[str]:
    """List JSON files in serverdata directory or subdirectory.

    Args:
        directory: Optional subdirectory name within serverdata_dir.

    Returns:
        List of JSON filenames (not full paths).
    """
    serverdata_dir = self.settings.serverdata_dir

    if directory:
        # Validate path traversal
        target_dir = self._safe_path(serverdata_dir, directory)
        if not target_dir.is_dir():
            return []
    else:
        target_dir = serverdata_dir

    # ... rest of implementation
```

**Frontend - useConfigDirectories hook:**
```typescript
export function useConfigDirectories() {
  return useQuery({
    queryKey: ['config', 'directories'],
    queryFn: async () => {
      const response = await api.get('/config/directories');
      return response.data;
    },
  });
}
```

**Frontend - FileManagerPanel State:**
```typescript
// Add directory navigation state
const [currentDirectory, setCurrentDirectory] = useState<string | null>(null);

// Use directory in file query
const { data: filesData } = useConfigFiles(currentDirectory);
```

### UI Design Notes

**FileList with directories:**
- Show directories at the top with folder icons
- Show files below with file icons
- Clicking a directory navigates into it
- Clicking a file selects it for viewing

**Breadcrumb Navigation:**
- Show path like: `serverdata / ModConfigs / modname.json`
- Root label: "serverdata" (clickable to go back)
- Each path segment clickable for navigation

### Previous Story Intelligence (9-6)

**Patterns Established:**
- JSON syntax highlighting is already working in FileViewer
- Theme colors from Catppuccin palette
- FileViewer handles unknown content gracefully

**Applicable Learnings:**
- Keep backend changes minimal - just add directory support to existing service
- Frontend changes should build on existing component patterns
- Path security is already well-handled by `_safe_path()` - reuse it

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: epics.md#Story-9.7] - Story requirements (FR54, FR55)
- [Source: api/src/vintagestory_api/services/config_files.py] - ConfigFilesService with _safe_path() pattern
- [Source: api/src/vintagestory_api/routers/config.py] - Config API endpoints
- [Source: web/src/features/settings/FileManagerPanel.tsx] - File manager UI
- [Source: web/src/components/FileList.tsx] - File list component
- [Source: web/src/hooks/use-config-files.ts] - Config files hooks

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

