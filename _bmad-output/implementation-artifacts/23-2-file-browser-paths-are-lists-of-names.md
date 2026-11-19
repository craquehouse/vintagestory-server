# Story 23.2: File Browser Paths Are Lists of Names

Status: ready-for-dev

<!-- Implements FR312, Epic 23 ADR-3. Bead: VSS-o8s (UI-081), closed by this story after merge. Branch story/23-2-file-browser-paths-are-lists-of-names, stacked on story/23-1-configs-with-comments-can-be-viewed at 03218c12 (23.1 in review); the PR targets main and merges after 23.1's. Web only: no API change, no new dependency. Line references verified at 03218c12. -->

## Story

As a **developer**,
I want **the file browser to carry paths as lists of directory names**,
so that **a name is never split or joined by mistake, and the editor and history are built on one path representation**.

## Acceptance Criteria

1. **Given** the file browser at `ModConfig/sub` with a file selected
   **When** I use the breadcrumb, open directories and select files
   **Then** behaviour is as before (Story 16.7's breadcrumb tests still check the same things, with their inputs written as lists), and the panel's state and the breadcrumb's props are `string[]` (the selected file `{ directory: string[]; name: string }`)
   *(FR312; ADR-3 decision 1)*

2. **Given** a directory listing that returns a name containing `/`, a NUL character, or a name that is `.`, `..` or empty (a mocked response)
   **When** it is opened or a file in it is selected
   **Then** no request is sent for it and the panel shows the error "Invalid name in path: ..." instead of requesting another path
   *(FR312; ADR-3 decision 2)*

3. **Given** the API client
   **When** a path is built for a request
   **Then** it is built only by `toConfigPath`, which has unit tests for joining and for each rejected name, and the fetch functions and hooks take `readonly string[]`
   *(FR312; ADR-3 decisions 2 and 3)*

4. **Given** a file selected in a subfolder (`ModConfig/x.json`)
   **When** the list is shown
   **Then** `x.json` is highlighted as selected (today the list compares the bare name with the full path, so a file in a subfolder is never highlighted; found in story creation)
   *(FR312; found in story creation, backlog drawdown)*

5. **(Quality gates.)** `just check` is green with 0 skipped tests; no added line holds a lint or type suppression, a `cast`, `as`-style escape beyond the existing patterns, a skip or `.only`; `git diff` of `api/` is empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-23.2/task-N): ... One user-visible commit: Task 3 (fix(web)). -->

- [x] Task 1: `toConfigPath`, and the fetch functions and hooks taking `readonly string[]` + tests (AC: 2, 3, 5)
  - [x] 1.1: Red first: `config.test.ts` rows for `toConfigPath` (joins; throws `InvalidConfigPathError` for `''`, `.`, `..`, a name with `/`, a name with `\0`, and the root `[]` joins to `''`), and the existing `fetchConfigDirectories`/`fetchConfigFiles`/`fetchConfigFileContent` rows rewritten with lists (`['Mods']`, `['path', 'with', 'slashes']`); a row that an invalid list rejects without calling `apiClient`. `use-config-files.test.tsx` rows rewritten with lists; see them fail
  - [x] 1.2: `web/src/api/config.ts`: `export class InvalidConfigPathError extends Error`; `export function toConfigPath(segments: readonly string[]): string`; `fetchConfigDirectories(directory: readonly string[] = [])`, `fetchConfigFiles(directory: readonly string[] = [])` (no `?directory=` for `[]`), `fetchConfigFileContent(path: readonly string[])` (the file's directory names and its name); each builds its path with `toConfigPath` before calling `apiClient`, so an invalid name rejects with `InvalidConfigPathError` and sends nothing
  - [x] 1.3: `web/src/hooks/use-config-files.ts`: `useConfigDirectories(directory: readonly string[] = [])`, `useConfigFiles(directory: readonly string[] = [])`, `useConfigFileContent(path: readonly string[] | null)`; query keys from `queryKeys.config.*` with `segments.join('/')` (keys only identify the cache entry; validation is the fetch's, so a key never throws during render). `query-keys.ts` is unchanged
  - [x] 1.4: `FileManagerPanel` adapts minimally to the new hook signatures (it still holds strings until Task 2: split with `.split('/')` only here, to be removed in Task 2)
  - [x] 1.5: `just test-web`; `just typecheck-web`; `just format-web`, `just lint-web`
  - [x] 1.6: Commit `refactor(story-23.2/task-1): build config file paths from lists of names in one place`

- [x] Task 2: `PathBreadcrumb` takes `segments`, and `FileManagerPanel` holds lists + tests (AC: 1, 2, 5)
  - [x] 2.1: Red first: `PathBreadcrumb.test.tsx` rewritten with `segments={[...]}` and `onNavigate` receiving lists (`[]` for the root; `[['a'], ['a', 'b'], ['a', 'b', 'c']]` for the ancestors); the row with empty parts in a slash string (`'/Logs//Archive/'`) is replaced by one showing that the names are shown as given (no splitting); `FileManagerPanel.test.tsx` gets AC 2's row (a directory listing returns `'a/b'`; clicking it shows "Invalid name in path" and fetch is never called with `a%2Fb` or `a/b`); see them fail
  - [x] 2.2: `PathBreadcrumb.tsx`: props `segments: readonly string[]`, `onNavigate: (segments: string[]) => void`; the focus logic compares joined lists through a key built with `JSON.stringify(segments)` (a string key that cannot collide for different lists)
  - [x] 2.3: `FileManagerPanel.tsx`: `currentDirectory: string[]` (`[]` root), `selectedFile: { directory: string[]; name: string } | null`; `handleSelectFile(name)`, `handleSelectDirectory(name)` append to the list; `handleNavigate(segments)`; the error state shows the breadcrumb when `currentDirectory.length > 0`; `FileViewer`'s `filename` is `toConfigPath`'s join of the selected file for display (on `InvalidConfigPathError`, the plain join, since the read already failed and shows the error); `FileList`'s `selectedFile` stays as it was in Task 1 (the full path string), so behaviour is unchanged in this task
  - [x] 2.4: `just test-web`; `just typecheck-web`; `just format-web`, `just lint-web`
  - [x] 2.5: Commit `refactor(story-23.2/task-2): carry file browser paths as lists of names`

- [ ] Task 3: Highlight the selected file in a subfolder + test (AC: 4, 5)
  - [ ] 3.1: Red first: `FileManagerPanel.test.tsx`: open `ModConfig`, select `x.json`; the item has the selected state (the attribute or class the existing root-level test "highlights selected file in the list" checks); see it fail
  - [ ] 3.2: `FileManagerPanel.tsx`: pass `FileList` the selected file's `name` when its `directory` equals `currentDirectory` (element by element), else `null`
  - [ ] 3.3: Commit `fix(story-23.2/task-3): highlight the selected file in a subfolder of the file browser`

- [ ] Task 4: Validate and move the story to review (AC: all)
  - [ ] 4.1: `just check` green (web 0 skipped); `git diff 03218c12 -- api` empty; added lines hold no suppression, `cast`, skip or `.only`
  - [ ] 4.2: `just changelog` lists exactly one entry from this story (Task 3)
  - [ ] 4.3: Status `review`; `just sprint set 23-2-file-browser-paths-are-lists-of-names review`; Dev Agent Record and File List
  - [ ] 4.4: Commit `chore(story-23.2/task-4): validate and move story 23.2 to review`

## Dev Notes

### The code today (verified at 03218c12)

- `web/src/features/settings/FileManagerPanel.tsx`: `selectedFile: string | null` (full path), `currentDirectory: string | null` (`:51-54`); `handleSelectFile` and `handleSelectDirectory` join with `/` (`:104-116`); `handleNavigate(path: string | null)` (`:119-122`); the breadcrumb `<PathBreadcrumb path={currentDirectory} ...>`; the error state shows the breadcrumb when `currentDirectory` is truthy; `FileList selectedFile={selectedFile}`; `FileViewer filename={selectedFile}`, plus Story 23.1's `parseError` and `text`.
- `web/src/components/FileList.tsx:127`: `const isSelected = item.name === selectedFile;` so with a full path (`ModConfig/x.json`) nothing in a subfolder is ever selected (AC 4).
- `web/src/components/PathBreadcrumb.tsx` (Story 16.7): `path: string | null` split on `/` with empty parts dropped (`:44`); ancestors are buttons calling `onNavigate(segments.slice(0, index).join('/'))`; the root calls `onNavigate(null)`; the focus moves to the new current segment after a click (`focusTarget` ref compared to `currentPath`).
- `web/src/api/config.ts`: `fetchConfigDirectories(directory?: string)`, `fetchConfigFiles(directory?: string)` (`?directory=` + `encodeURIComponent`), `fetchConfigFileContent(filename: string)` (Story 23.1: `transformResponse: false` and the mapping).
- `web/src/hooks/use-config-files.ts`: the three hooks take strings; `web/src/api/query-keys.ts:46-55` builds keys from strings.
- The API takes `directory=` and `{filename:path}` as `/`-joined relative paths and refuses traversal itself (`_safe_path`); nothing here changes it.

### Design

- `toConfigPath(segments)`: for each name, throw `new InvalidConfigPathError(name)` (message `Invalid name in path: ${JSON.stringify(name)}`) when it is `''`, `'.'`, `'..'`, or contains `'/'` or `'\0'`; return `segments.join('/')`. `[]` returns `''`. Export both.
- Fetches call `toConfigPath` first, so an invalid name never reaches `apiClient`; TanStack Query reports the rejection as the query's error, which the panel already shows ("Failed to load files" with the message for a directory; the viewer's error state for a file).
- Hooks keep their `enabled` rules (`useConfigFileContent(null)` is disabled).
- `PathBreadcrumb` keeps its DOM, test ids, classes and focus behaviour; only its props change.

### Testing rules

- Web only; mock `fetch` / `apiClient` as the existing tests do. No E2E change is needed (the DOM is unchanged), but `e2e/` specs that use the breadcrumb's test ids must still pass in CI.

### References

- `epics.md` "Story 23.2"; `architecture/epic-23-config-file-editing.md` ADR-3
- Story 16.7 (`16-7-file-browser-breadcrumbs.md`) for the breadcrumb's behaviour and tests
- Story 23.1 (`23-1-configs-with-comments-can-be-viewed.md`) for `fetchConfigFileContent`'s mapping

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
