# Story 28.4: The Mods Page Adds a Mod from a File or a Link

Status: done

<!-- Implements FR363, FR364, Epic 28 ADR-6. Bead: VSS-guzf.3 (UI-105), closes with this story after merge. Branch story/28-4-the-mods-page-adds-a-mod-from-a-file-or-a-link, stacked on story/28-3-a-mod-can-be-installed-from-an-https-link (PR #237); the PR targets main and merges after 28.3's. Web and E2E. -->

## Story

As an **administrator**,
I want **to add a mod from a file or a link on the mods page**,
so that **I do not need the API to do it**.

## Acceptance Criteria

1. **Given** an Admin key **Then** the Installed tab has "Add from file or link" next to Rescan; **given** a Monitor key **Then** it does not *(FR363; ADR-6)*
2. **Given** the dialog's File tab **When** a `.zip` is picked or dropped and Install is pressed **Then** it is uploaded as the request body *(FR363)*
3. **Given** the Link tab **When** an `https` link is entered and Install is pressed **Then** the link install runs *(FR363)*
4. **Given** a `MOD_ALREADY_INSTALLED` answer **Then** the dialog names the installed mod, version and source, and "Replace it" resends with `replace=true` *(FR364)*
5. **Given** any other error **Then** the dialog shows the API's message and keeps the input. **Given** success **Then** it closes, a toast names the mod and version (and the restart when pending), and the mod list and update status refresh
6. The dialog works on a phone (full width under 640 px, 44 px targets) and from the keyboard
7. **E2E (CI set):** an upload of a generated mod zip shows the mod as "Uploaded file"; an upload of a zip without `modinfo.json` shows the error; a link to a loopback address shows the blocked message
8. **(Quality gates.)** `just check` green

## Tasks / Subtasks

- [x] Task 1: The dialog (AC: 1-6)
  - [x] 1.1: `apiClient` `rawBody`; `uploadMod`, `installModFromUrl`; `ModFileInstallData`; `useAddModFromFileOrLink` (no global toast, invalidates the mods queries)
  - [x] 1.2: `AddModDialog` (File and Link tabs, drop zone, replace prompt, inline errors); the Installed tab's Admin-only button
  - [x] 1.3: Tests: `AddModDialog.test.tsx`, `client.test.ts` (raw body), `InstalledTab.test.tsx` (button)
  - [x] 1.4: Commit `feat(story-28.4/task-1): add a mod from a file or a link on the Installed tab`
- [x] Task 2: E2E (AC: 7) — `web/e2e/add-mod-from-file-or-link.spec.ts`
- [x] Task 3: README; validate and move the story to review (AC: 8)

## Dev Notes

- The API's 409 detail keeps its extra keys (`slug`, `installed_version`, `source`) in `ApiError.details` as sent, snake_case (`handleApiError`, `api/client.ts`).
- `DialogContent` is already `w-full max-w-[calc(100%-2rem)]`, `sm:max-w-lg`, so it is full width on phones.
- The E2E upload tests install into the mods folder, so they skip outside the throwaway container (Epic 24 ADR-8); the blocked-link test installs nothing and runs anywhere. The zip is built in the test (stored, `zlib.crc32`).

### References

- `epics.md` "Story 28.4"; `architecture/epic-28-mods-from-outside-the-mod-database.md` ADR-6

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-27): exit 0; API 4355 passed, web 3998 passed.
- `just test-e2e-ci e2e/add-mod-from-file-or-link.spec.ts` (2026-11-27): 3 passed.

### Implementation decisions

- **One mutation for both tabs** (`useAddModFromFileOrLink`), since the answer and the errors are the same.
- **Install is disabled while the replace prompt shows**, so the only way on is "Replace it" or changing the input (which clears the prompt).
- **The dialog cannot be closed while a request runs**, so a slow link download is not left running unseen.
- **No client-side name check**: the API's message (for example lowercase `.zip`) is shown as is, so the rule lives in one place.
- **The E2E replace step uploads the same archive under another name**: the version stays 1.0.0, and the toast says "Replaced".

### Completion Notes List

- 2026-11-27 (dev-story): Tasks 1 to 3 done. 12 new web tests (8 dialog, 2 raw body, 2 Installed tab) and 3 E2E tests.
- 2026-11-27 (create-story): created from Epic 28's Story 28.4 and ADR-6.

### File List

- `web/src/api/client.ts`, `web/src/api/mods.ts`, `web/src/api/types.ts`, `web/src/hooks/use-mods.ts`, `web/src/components/AddModDialog.tsx` (new), `web/src/features/mods/InstalledTab.tsx`; tests `AddModDialog.test.tsx` (new), `api/client.test.ts`, `features/mods/InstalledTab.test.tsx` (Task 1)
- `web/e2e/add-mod-from-file-or-link.spec.ts` (new) (Task 2)
- `README.md` (Task 3)
- this file; `sprint-status.yaml` (through `just sprint set`)

## Review

Reviewer: GLM-5.3-Flash via opencode (read-only, 2026-11-27). Verdict: approve with changes. 0 HIGH, 0 MEDIUM, 3 LOW; all three fixed:

1. **LOW: Enter in the link field resent the request while the replace prompt showed** (the button was disabled, the key handler was not). `install` now refuses a plain install while the prompt shows. Test (Enter sends nothing more; the prompt stays).
2. **LOW: the link tab's replace (`replace: true` in the body) was untested.** The same test replaces from a link and checks the body.
3. **LOW: the drop zone's highlight flickered over its children.** `dragleave` into a child of the zone is ignored.

After the fixes `just check` exit 0: API 4355 passed, web 3999 passed.

## Change Log

- 2026-11-27: Story 28.4 created (create-story).
- 2026-11-27: Story 28.4 implemented (dev-story): Tasks 1 to 3; status review.
- 2026-11-27: Code review (GLM-5.3-Flash via opencode): approve with changes; 0 HIGH, 0 MEDIUM, 3 LOW; all fixed (see "Review"). Status done.
