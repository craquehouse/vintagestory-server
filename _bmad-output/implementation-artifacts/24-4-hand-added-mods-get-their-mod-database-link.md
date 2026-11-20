# Story 24.4: Hand-Added Mods Get Their Mod Database Link

Status: done

<!-- Implements FR334, FR335, Epic 24 ADR-1. Bead: VSS-v3be (API-093), first half; Stories 24.5 and 24.6 carry the rest and 24.6 closes it after merge. Branch story/24-4-hand-added-mods-get-their-mod-database-link, stacked on story/24-3-mod-file-follow-ups-from-epic-19 at 29a602be (24.3 in review); the PR targets main and merges after 24.3's. -->

## Story

As an **administrator**,
I want **a mod I copied into the mods folder to be linked to its mod database page**,
so that **it behaves like a mod installed through the manager**.

## Acceptance Criteria

1. **Given** an installed mod with asset ID 0 whose mod ID the mod database knows
   **When** the update check runs
   **Then** its entry gets the payload's asset ID (saved), the Installed tab links its ModDB page, and its update status is shown as for any mod
   *(FR334; ADR-1 decision 1)*

2. **Given** an installed mod with a non-zero asset ID, and a payload with another one
   **When** the check runs
   **Then** the stored asset ID is not changed and the difference is logged (`mod_asset_id_differs`)
   *(FR334; ADR-1 decision 2)*

3. **Given** a mod whose install or version change holds its lock when the check reaches it
   **When** the check runs
   **Then** its asset ID is not written, the check does not fail, and the next check fills it in
   *(FR334; ADR-1 decision 3)*

4. **Given** a mod ID the mod database does not know
   **When** the Installed tab shows it
   **Then** its update cell reads "Local mod" (the reason as tooltip and screen reader text), with no Update button, its name is not a link, and enable, disable and remove work as before
   *(FR335; ADR-1 decision 4)*

5. **Given** the mod database is unavailable
   **When** the check runs
   **Then** no asset ID changes
   *(FR334)*

6. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [x] Task 1: The check fills in a missing asset ID (AC: 1, 2, 3, 5, 6)
  - [x] 1.1: Red: `tests/test_mod_asset_id.py`: `fill_asset_id` (fills and saves, mod ID ignoring case, never changes a set one and logs a different one, ignores non-positive values and unknown mods, skips a busy mod, logs a failed save) and the check with a real `ModService` (known mod, unknown mod, database unavailable)
  - [x] 1.2: `ModService.fill_asset_id(slug, asset_id) -> bool`; `InstalledModSource.fill_asset_id`; `ModUpdateService._check_one` calls it with the payload's `assetid` after a lookup that found the mod; the six test fakes get a no-op method
  - [x] 1.3: Commit `fix(story-24.4/task-1): link mods added by hand to their mod database page after an update check`

- [x] Task 2: Local mods in the web UI (AC: 4, 6)
  - [x] 2.1: Red: `ModUpdateCell.test.tsx` (Local mod, no button), `InstalledModParts.test.tsx` (a local mod's name is not a link)
  - [x] 2.2: `ModUpdateCell`: `not_in_database` shows "Local mod" with the reason "Not in the mod database: it has no mod database page and gets no update offers."; `ModNameLink` takes `local`; `isLocalMod(row)`; the table and the cards pass it
  - [x] 2.3: Commit `fix(story-24.4/task-2): show a mod the mod database does not know as a local mod, without a link`

- [x] Task 3: Validate and move the story to review (AC: all)
  - [x] 3.1: `just check` green; `just changelog` lists Tasks 1 and 2
  - [x] 3.2: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 3.3: Commit `chore(story-24.4/task-3): validate and move story 24.4 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `ModUpdateService.check` already looks up every installed mod by its mod ID, hand-added ones included (`services/mod_updates.py:460`); the normalized payload carries `assetid` (`models/moddb.py:93`). So a hand-added mod already got update status and Update; only the asset ID, and with it the ModDB link, was missing.
- `ModNameLink` (`web/src/components/InstalledModParts.tsx`) linked `https://mods.vintagestory.at/show/mod/<assetId>`, or `https://mods.vintagestory.at/<slug>` when the asset ID is 0. The second is kept for a mod not checked yet; a local mod gets no link, since the mod database has no page for it.

### Decisions made in implementation

- **The wording.** The epic said the cell reads "Local mod: not in the mod database". It shows "Local mod", with the reason as the tooltip and screen-reader text, as every other status label in the cell does.
- **The name is plain text for a local mod.** The epic's "no ModDB link" covered the update cell; the name was the only link, so `ModNameLink` takes `local`.
- **Matching ignoring case, one entry only.** `fill_asset_id` matches the mod ID ignoring case, as the mod's lock does, and writes nothing if two entries match (a state from before Story 19.4).
- **A second release note.** Task 2 is user-visible, so it is a `fix(web)` commit of its own.

### References

- `epics.md` "Story 24.4"; `architecture/epic-24-mod-management-follow-ups.md` ADR-1

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4052 passed, web 3863 passed, 0 skipped; Pyright 0/0; lints green.
- `just changelog`: two entries from this story (Tasks 1 and 2).

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.4 and ADR-1; Tasks 1 to 3 done.

### File List

- `api/src/vintagestory_api/services/mods.py`, `services/mod_updates.py` (modified)
- `api/tests/test_mod_asset_id.py` (new)
- `api/tests/test_mod_updates.py`, `test_mod_updates_router.py`, `test_mod_update_all.py`, `test_mod_update_alerts.py`, `jobs/test_mod_cache_refresh.py` (fakes: `fill_asset_id`)
- `web/src/components/ModUpdateCell.tsx`, `InstalledModParts.tsx`, `ModTable.tsx`, `InstalledModCard.tsx` and the two tests (modified)
- `_bmad-output/implementation-artifacts/24-4-hand-added-mods-get-their-mod-database-link.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve. 0 HIGH, 0 MEDIUM, five LOW, all fixed:

1. **LOW: `casefold()` matching differed from the project's `lower()` mod-ID comparison,** so a non-ASCII twin could take another mod's asset ID. `fill_asset_id` now matches with `_lock_key`.
2. **LOW: the fill sat outside the check's per-mod guard.** It is now in a `try` that logs `mod_asset_id_fill_failed`; test.
3. **LOW: ADR-1 decision 3 said `_hold`.** Annotated: synchronous, reads `_busy`, as enable and disable; the docstring carries the "if it ever becomes async" warning.
4. **LOW: test gaps.** Two entries of one mod ID are left alone (test); new `InstalledModCard.test.tsx` covers a local mod's card and a not-checked mod's link.
5. **LOW: `mod_asset_id_filled` was logged after a failed save.** Only on success now; test.

## Change Log

- 2026-11-20: Story 24.4 created and implemented (dev-story): Tasks 1 to 3; status review.
- 2026-11-20: Code review (GLM-5.3-Flash via opencode): approve; 0 HIGH, 0 MEDIUM, 5 LOW, all fixed (see "Review"). Status done.
