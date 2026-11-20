# Story 24.6: Rescan and Unused Files on the Installed Tab

Status: review

<!-- Implements FR336, FR339, FR340 (README), Epic 24 ADR-3, ADR-4, ADR-8. Beads: VSS-hv60 (UI-103) and VSS-v3be (API-093), both closed by this story after merge. Branch story/24-6-rescan-and-unused-files-on-the-installed-tab, stacked on story/24-5-unused-files-and-rescan-in-the-api at 237f5281 (24.5 in review); the PR targets main and merges after 24.5's. Web and README only. -->

## Story

As an **administrator**,
I want **a Rescan button and a list of unused files on the Installed tab**,
so that **I can pick up hand-added mods and clean up the mods folder from the web UI**.

## Acceptance Criteria

1. **Given** an Admin key on the Installed tab
   **When** I press Rescan
   **Then** the button shows progress, a toast gives the numbers added, removed and skipped (and asks for a restart when the API says so), and the mods, updates and unused-files data refresh; a refusal (`MODS_BUSY`) is a toast with the API's message
   *(FR336; ADR-4)*

2. **Given** the mods folder has unused files
   **When** an Admin key opens the Installed tab
   **Then** a notice says how many files the mods folder holds that the manager does not use; expanding it lists each with name, size, age and reason
   *(FR339; ADR-3)*

3. **Given** the list is open
   **When** I press Delete on a file and confirm in the dialog that names it
   **Then** it is deleted, a toast says so, and the list refreshes; Cancel deletes nothing; the notice disappears when the list is empty (the dialog stays mounted while the last delete runs)
   *(FR339; ADR-3 decision 5)*

4. **Given** a Monitor key
   **When** it opens the Installed tab
   **Then** there is no Rescan button and no notice, and the unused-files list is never requested
   *(FR336, FR339)*

5. **Given** the README
   **Then** it explains mods added by hand, Rescan, local mods, unused files, and that `.cs` and folder mods are left alone
   *(FR340)*

6. **(Quality gates.)** `just check` green with 0 skipped unit tests; no suppression added; the new E2E passes in the CI set.

## Tasks / Subtasks

- [x] Task 1: The web UI (AC: 1 to 4, 6)
  - [x] 1.1: `types.ts` (`UnusedFile`, `UnusedFilesData`, `UnusedFileDeleteData`, `ModRescanData`); `mods.ts` (`fetchUnusedFiles`, `deleteUnusedFile`, `rescanMods`); `queryKeys.mods.unusedFiles` (under `mods`); hooks `useUnusedFiles({ enabled })`, `useDeleteUnusedFile`, `useRescanMods` (each mutation invalidates `mods`)
  - [x] 1.2: `UnusedFilesNotice` (collapsed button with `aria-expanded`, the list, `AlertDialog` kept mounted, toasts, 44px targets below `lg`); `InstalledTab`: Rescan (Admin only, `useIsAdmin`) and the notice
  - [x] 1.3: Tests: `UnusedFilesNotice.test.tsx` (12), `InstalledTab.test.tsx` Rescan (5), `mods.test.ts` (3)
  - [x] 1.4: Commit `feat(story-24.6/task-1): rescan the mods folder, and see and delete unused files in it, from the Installed tab`

- [x] Task 2: E2E (AC: 1 to 3, 6)
  - [x] 2.1: `web/e2e/mods-rescan-and-unused-files.spec.ts`: writes an archive (with the container's `python3`) and a `.tmp` with `docker exec`, only in the throwaway container; Rescan lists the mod; the `.tmp` is listed, deleted after confirming, and gone from the folder; cleans up
  - [x] 2.2: Commit `test(story-24.6/task-2): check Rescan and unused files on a throwaway container`

- [x] Task 3: README (AC: 5)
  - [x] 3.1: New section "Mods added by hand"; the installation step links to it
  - [x] 3.2: Commit `docs(story-24.6/task-3): explain mods added by hand, Rescan and unused files`

- [x] Task 4: Validate and move the story to review (AC: all)
  - [x] 4.1: `just check` green; the E2E in the CI set
  - [x] 4.2: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 4.3: Commit `chore(story-24.6/task-4): validate and move story 24.6 to review`

## Dev Notes

### Decisions made in implementation

- **One release note instead of two.** The epic planned `feat(web)` subjects for Rescan and for unused files; they share the types, API module, hooks and `InstalledTab`, so they ship as one commit whose subject names both.
- **The notice is collapsed at first.** It says how many files there are; the list opens on demand, so the Installed tab does not grow by a list nobody asked for.
- **`relativeTime` is reused** from `features/settings/ConfigHistoryPanel.tsx` (Story 23.7); sizes get their own `formatFileSize` with MiB, since mod archives are larger than config files.
- **Monitor never asks for the list**: the query is disabled unless the role is Admin, so no 403 is logged.

### References

- `epics.md` "Story 24.6"; `architecture/epic-24-mod-management-follow-ups.md` ADR-3, ADR-4, ADR-8; Story 21.4 (dialog kept mounted)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4087 passed, web 3883 passed, 0 skipped; Pyright 0/0; lints green.
- `just changelog`: one entry from this story (Task 1).
- `just test-e2e-ci e2e/mods-rescan-and-unused-files.spec.ts` (throwaway container): web 2 passed, API E2E 4 passed.

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.6; Tasks 1 to 4 done.

### File List

- `web/src/api/types.ts`, `api/mods.ts`, `api/query-keys.ts`, `hooks/use-mods.ts`, `features/mods/InstalledTab.tsx` (modified)
- `web/src/components/UnusedFilesNotice.tsx`, `UnusedFilesNotice.test.tsx` (new)
- `web/src/api/mods.test.ts`, `web/src/features/mods/InstalledTab.test.tsx` (modified)
- `web/e2e/mods-rescan-and-unused-files.spec.ts` (new)
- `README.md`
- `_bmad-output/implementation-artifacts/24-6-rescan-and-unused-files-on-the-installed-tab.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-20: Story 24.6 created and implemented (dev-story): Tasks 1 to 4; status review.
