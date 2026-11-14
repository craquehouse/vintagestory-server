# Story 16.7: File Browser Breadcrumbs

Status: ready-for-dev

<!-- Implements FR174. Beads: VSS-8lh (this story, child of the Epic 16 bead VSS-stm); VSS-3mr (directory navigation E2E test, child of VSS-029 Web UI Test Coverage). Stacks on Story 16.6 (branch story/16-6-settings-layout-on-desktop, PR #153), itself on #152, #151, #150, #149, #148. Last story of Epic 16. No new dependencies; no API change. -->

## Story

As an **administrator**,
I want **to jump to any folder in the current path**,
so that **I can move up several levels in one click**.

## Acceptance Criteria

1. **Given** the File Manager tab (Settings, `/config`)
   **When** I am in a subdirectory, e.g. `Logs/Archive`
   **Then** above the file list and viewer a breadcrumb shows the root `serverdata` and every directory of the path in order (`serverdata › Logs › Archive`); the root and every ancestor directory are buttons, and the current directory is plain text with `aria-current="page"`. At the root the breadcrumb shows `serverdata` alone as the current location
   *(Covers FR174; `VSS-8lh`)*

2. **Given** I am in a subdirectory
   **When** I click the root or an ancestor segment (by mouse, or Tab then Enter/Space)
   **Then** that directory's listing is shown, the breadcrumb ends at that directory, the file selection is cleared, and keyboard focus moves to the new current segment instead of being lost

3. **Given** the breadcrumb
   **When** it is read by assistive technology
   **Then** it is a `nav` landmark labelled "Breadcrumb" containing an ordered list; the `›` separators are hidden from assistive technology; each button's accessible name is the directory name (the root's is "serverdata")

4. **Given** the breadcrumb replaces the Back button
   **When** I browse
   **Then** the Back button (`file-manager-back`) is gone; going up one level is the parent segment; navigating into a directory from the list, selecting and viewing files, word wrap, hidden-directory filtering, loading and empty states behave as before

5. **Given** a deep path or long directory names (e.g. `Cache/unpack/Auto Map Markers 5.0.3 - Vintage Story 1.22.zip_ff41715051bc`) on a 390px-wide phone
   **When** the breadcrumb is shown
   **Then** segments wrap onto further lines and a segment longer than the panel is truncated with an ellipsis (full name in its `title`); the breadcrumb stays inside the file manager panel and does not scroll sideways, and the change adds no horizontal page overflow (the Settings tab list already overflows at 390px, see Dev Notes; that is bead `VSS-uni`, not this story)

6. **Given** a directory name with spaces or special characters
   **When** I navigate to it or to one of its ancestors through the breadcrumb
   **Then** the name is shown as text, the directory is requested with its path URL-encoded as today, and the breadcrumb only ever navigates to the root or a prefix of the current path (directories the API has already listed), never to a path built from anything else

7. **Given** a subdirectory whose listing fails to load
   **When** the error is shown
   **Then** the breadcrumb is still shown above the error, so I can go back to a parent or the root (today the error replaces the whole panel, Back button included)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.7/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [ ] Task 1: `PathBreadcrumb` component + tests (AC: 1, 2, 3, 5, 6)
  - [ ] 1.1: `web/src/components/PathBreadcrumb.tsx`: props `path: string | null` (slash-separated, `null` = root), `rootLabel: string`, `onNavigate: (path: string | null) => void`, `className?`. Renders `nav[aria-label="Breadcrumb"] > ol` (`flex flex-wrap items-center gap-1 text-sm text-muted-foreground`, `min-w-0`); one `li` per segment; root and ancestors are `button type="button"` (ghost-like: `hover:text-foreground`, focus-visible ring, `max-w-full truncate`, `title` = name); the current segment is a `span` (`text-foreground font-medium truncate`, `aria-current="page"`, `tabIndex={-1}`, `title`); separators are `ChevronRight` with `aria-hidden="true"`. Styling matches the mod detail breadcrumb (`ModDetailPage.tsx`). Clicking segment *i* calls `onNavigate(segments.slice(0, i + 1).join('/'))`, the root calls `onNavigate(null)`. After a click the component focuses the new current segment once the path changes (ref + effect, only when the change came from the breadcrumb). Empty segments from stray slashes are ignored. Test ids: `path-breadcrumb`, `path-breadcrumb-root`, `path-breadcrumb-segment-<index>`, `path-breadcrumb-current`
  - [ ] 1.2: `PathBreadcrumb.test.tsx`: root only (current, no buttons); nested path renders root + ancestors as buttons and the last as current with `aria-current="page"`; landmark and list roles, separators hidden; clicking root / each ancestor calls `onNavigate` with `null` / the right prefix; keyboard (Tab to a segment, Enter) navigates; focus moves to the new current segment after a click (rerender with the new path) but not on an external path change; names with spaces, `%`, `#`, `&` and unicode render as text and are passed back unchanged; long names carry `title` and `truncate`

- [ ] Task 2: File Manager uses the breadcrumb instead of the Back button + tests (AC: 1, 2, 4, 6, 7)
  - [ ] 2.1: `FileManagerPanel`: panel becomes a column (`flex flex-col h-[500px]`); a breadcrumb bar (`border-b px-3 py-2`, `data-testid="file-manager-breadcrumb-bar"`) spans the panel above the existing split row (`flex flex-1 min-h-0`). `PathBreadcrumb` with `rootLabel="serverdata"`, `path={currentDirectory}`, `onNavigate` = set directory and clear the selection. Remove `handleNavigateBack`, the Back button and the unused `ChevronLeft`/`Button` imports. In the error state, render the breadcrumb above the existing error box when `currentDirectory` is set (error test id and text unchanged). Update the doc comment (Story 16.7)
  - [ ] 2.2: `FileManagerPanel.test.tsx`: migrate every `file-manager-back` test to the breadcrumb (parent segment for one level up; root for "back to root"; rapid repeated clicks on the root); add: breadcrumb at root shows only the current `serverdata`; two levels deep, clicking the root jumps straight to the root listing (one click, AC "several levels"); clicking the middle segment shows that level's listing and clears the selection; no element with `file-manager-back` exists; error in a subdirectory still shows the breadcrumb and clicking the root recovers the root listing; a directory named with spaces is requested URL-encoded. Existing non-navigation tests pass unchanged

- [ ] Task 3: Browser verification against the Docker dev stack + E2E spec (AC: 1-7)
  - [ ] 3.1: Before measurements on the running 16.6 build (scratchpad): panel box, document overflow, Back button box at 390 and 1280 in `Logs/Archive`
  - [ ] 3.2: `web/e2e/file-browser-navigation.spec.ts` (the directory navigation test from `VSS-3mr`): discovers a nested path through the read-only API (`/api/v1alpha1/config/directories`, breadth-first over non-hidden directories, up to three levels, preferring the deepest), so it does not depend on fixed names; opens `/config` → File Manager; navigates down by clicking directories in the list and checks the breadcrumb segments and `aria-current` at each level; clicks the root from the deepest level and gets the root listing in one click; navigates down again and clicks a middle segment; uses Tab + Enter for one jump and checks focus lands on the current segment; at 390x844 the breadcrumb's box is inside the panel's box, the `ol` does not scroll sideways, and the document overflow equals the overflow with the File Manager at the root (the change adds none). Reads only: no file or directory is created, changed or deleted
  - [ ] 3.3: `just docker restart` (rebuild from this branch); run the spec; take after measurements; browser console clean; compare before/after in the Dev Agent Record. Screenshots stay in the session scratchpad (the File Manager shows no server name or password, but if one is committed, mask `header span.font-semibold`)

- [ ] Task 4: Quality gate and review hand-off (AC: all)
  - [ ] 4.1: `just check` passes
  - [ ] 4.2: Status review, `just sprint set 16-7-file-browser-breadcrumbs review`, PR to `story/16-6-settings-layout-on-desktop` (stacks on #153, #152, #151, #150, #149, #148), PR link on `VSS-8lh` and `VSS-3mr`; `VSS-3mr` stays open with a comment that the "new directory appears on refresh" part is not covered

## Dev Notes

### Today's behavior (Docker stack on `story/16-6-settings-layout-on-desktop` b173874, Chromium)

- Settings → File Manager tab (`/config`). `FileManagerPanel` is `flex h-[500px]`: a 224px (`w-56`) left column with the list and, in a subdirectory, a full-width ghost Back button (`ChevronLeft` + the whole path, truncated, e.g. "Logs/Archive"); the viewer fills the rest.
- The Back button goes up one level (`handleNavigateBack`): from `Cache/unpack/<mod>` it takes three clicks to reach the root.
- Measured in `Logs/Archive`: at 1280 the panel is 1,072px wide at x 184, Back button 207px wide; at 390 the panel is 358px at x 15 and fits.
- **At 390px the page already scrolls sideways by 144px with the File Manager tab open**: the cause is the Settings `TabsList` (4 tabs, 518px wide, `w-fit`), not the file browser. Filed as `VSS-uni` (top-level, outside Epic 16's stories). AC 5 therefore requires that the breadcrumb adds no overflow and stays inside the panel, not that the page has none.
- API (`api/src/vintagestory_api/routers/config.py`, `services/config_files.py`): `GET /config/directories?directory=` and `GET /config/files?directory=` take a slash-separated path relative to `serverdata_dir`; every path goes through `_safe_path` (resolve + containment check, 400 `CONFIG_PATH_INVALID` on traversal). The client encodes the path with `encodeURIComponent` (`web/src/api/config.ts`), already tested for slashes. Hidden directories are returned and filtered in the panel. The API is read-only: there is no endpoint to create a directory.

### Decisions

- **Back button removed** (the epic: "Replace the Back button with breadcrumb segments"). The parent segment is the one-level-up control, reachable with Tab like the Back button was, and the breadcrumb also shows where you are (WCAG 2.4.8 Location). Keeping both would put two controls for the same action next to each other. Accessibility does not argue for keeping it: the breadcrumb is a labelled landmark of real buttons, and focus is moved to the current segment after a jump (the Back button lost focus to `body` whenever it disappeared at the root).
- **Root label `serverdata`**, the directory the API lists and the root label the Story 9.7 Dev Notes planned before breadcrumbs were deferred.
- **Buttons, not links.** The current directory is component state with no URL, so the segments are `button`s (links without an `href` are not focusable and would announce the wrong role). The current segment is a non-interactive `span` with `aria-current="page"` (WAI-ARIA APG breadcrumb pattern). The selected file is not a breadcrumb segment: the viewer header already shows it, and FR174 is about directories.
- **Breadcrumb spans the whole panel**, above the list and viewer, and is always shown (at the root as the current `serverdata`), so its position does not jump. In the 224px list column a deep path would wrap into many lines and push the list down.
- **Long paths wrap, long names truncate.** Wrapping keeps every segment reachable, which a collapsed middle (`…`) would hide behind another control; real depths are 2-4 levels. A single name wider than the panel (unpacked mod caches have 60+ character names) truncates with its full name in `title`.
- **Error state keeps the breadcrumb** (AC 7): the Back button vanished with the rest of the panel on error, leaving no way out except switching tabs.
- **New shared component `PathBreadcrumb`** in `web/src/components/` (state-driven, buttons). The mod detail breadcrumb uses router `Link`s and is not touched; only its look (`text-sm text-muted-foreground`, `ChevronRight`, `hover:text-foreground`, current `text-foreground font-medium`) is reused. There is no shadcn `breadcrumb` primitive in `components/ui`, and adding one is not needed.
- **`VSS-3mr`**: its directory navigation E2E test is Task 3.2. "New directory appears on refresh" is not included: the API has no create endpoint and this story must not create files in `./data` directly, so the bead stays open with a comment.

### Layout

```text
┌ File Manager panel (h 500) ─────────────────────────────────────────────┐
│ serverdata › Cache › unpack › Auto Map Markers 5.0.3 - Vintage St…      │  breadcrumb bar (border-b)
├──────────────┬──────────────────────────────────────────────────────────┤
│ 📁 …          │ viewer                                                   │
│ 📄 …          │                                                          │
└──────────────┴──────────────────────────────────────────────────────────┘
```

### Out of scope

- The Settings tab list overflowing at 390px (`VSS-uni`), file editing (`VSS-glz`), the "new directory appears on refresh" E2E test, the file browser's split layout on phones, any other Epic 16 story.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- `FileManagerPanel.test.tsx` mocks `fetch` by URL (`directory=level1%2Flevel2` etc.); reuse its `createTestQueryClient`/`createWrapper`. Text queries like `getByText('level1')` may now match both a list item and a breadcrumb segment: scope with `within(screen.getByTestId('path-breadcrumb'))`.
- jsdom applies no CSS: assert classes for wrap/truncate; geometry (inside the panel, no overflow) is in the E2E spec.
- E2E specs set `localStorage.apiKey` with an init script (`VS_API_KEY_ADMIN`, default `changeme`); use the same key for `request` calls (`X-API-Key` header, see `web/src/api/client.ts`). A first run seconds after `just docker restart` can fail while the server starts; rerun once healthy.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080). The file browser is used read-only against `./data`. Committed screenshots (none planned) must mask `header span.font-semibold`, `#ServerName` and the password. Check the browser console.

### Security Requirements

- UI-only, no API change. The breadcrumb only emits the root or prefixes of the current path, which came from directory names the API listed; the API still validates every path with `_safe_path`. Names are rendered as React text (no HTML injection).

### Development Commands

- `just test-web src/components/PathBreadcrumb.test.tsx`, `just test-web src/features/settings/FileManagerPanel.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/file-browser-navigation.spec.ts`.

### Previous Story Intelligence

- **16.6:** E2E spec pattern (`open()` with init script, `documentOverflowX`, boxes with half-pixel tolerance); `just lint-web` is `tsc --noEmit`; commit types by user impact; before/after measurements recorded in the Dev Agent Record; screenshots kept in the scratchpad.
- **16.5:** a first E2E run right after `just docker restart` can fail while the server starts.
- **9.7:** introduced directory browsing and the Back button; its review deferred breadcrumbs to the polish backlog (this story) and planned the `serverdata` root label. Post-story commits on a done story were a retro violation: discoveries become beads.
- **6.6:** `FileList`/`FileViewer` are shared presentational components; `FileList` is unchanged by this story.

### Git Intelligence

- Branch `story/16-7-file-browser-breadcrumbs` from `origin/story/16-6-settings-layout-on-desktop` (b173874). `FileManagerPanel.tsx` last changed in `8ba5e68` (Story 9.7 review). Planned types: Task 1 `refactor` (component not yet visible), Task 2 `feat`, Task 3 `test`, Task 4 `chore`.

### Latest Technical Information

- No new libraries. `lucide-react` `ChevronRight` (already used). Tailwind v4 `truncate` needs a bounded width: `max-w-full` on the segment and `min-w-0` on the flex/list containers.

### Project Structure Notes

- New: `web/src/components/PathBreadcrumb.tsx` (+ test), `web/e2e/file-browser-navigation.spec.ts`.
- Modified: `web/src/features/settings/FileManagerPanel.tsx` (+ test).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.7: File Browser Breadcrumbs]
- [Source: _bmad-output/planning-artifacts/prd.md] FR174
- [Source: _bmad-output/implementation-artifacts/9-7-dynamic-file-browser.md] (Back button, deferred breadcrumbs, `serverdata` root label)
- [Source: _bmad-output/implementation-artifacts/6-6-file-manager-ui.md]
- [Source: _bmad-output/implementation-artifacts/16-6-settings-layout-on-desktop.md]
- [Source: web/src/features/mods/ModDetailPage.tsx] breadcrumb styling
- [Source: api/src/vintagestory_api/services/config_files.py] `_safe_path`
- Beads: `VSS-8lh` (this story), parent `VSS-stm`; `VSS-3mr` (E2E), parent `VSS-029`; out of scope `VSS-uni`, `VSS-glz`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-11-13: Story 16.7 created (ready-for-dev). Ultimate context engine analysis completed - comprehensive developer guide created.
