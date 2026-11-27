# Story 28.1: Each Installed Mod Records Where It Came From

Status: review

<!-- Implements FR354, FR355, Epic 28 ADR-1 and ADR-2. Bead: VSS-guzf.1 (API-100), closes with this story after merge. Branch story/28-1-each-installed-mod-records-where-it-came-from from main; the PR targets main. API and web. -->

## Story

As an **administrator**,
I want **to see where each installed mod came from**,
so that **I know which mods the mod database updates and which I manage myself**.

## Acceptance Criteria

1. **Given** an install from the mod database, the start-up sync or a rescan
   **Then** the mod's state has `source` `moddb` or `folder`
   **Given** a state file written before this story
   **Then** an entry reads as `moddb` when its asset ID is set and `folder` otherwise, and loading rewrites nothing
   *(FR354; ADR-1)*

2. **Given** `GET /mods`
   **Then** each mod has `source` and `source_url`
   *(FR354)*

3. **Given** a mod with source `upload` or `url`
   **When** the update check runs
   **Then** it is not looked up in the mod database, its asset ID is not filled in, and its status is `unknown` with reason `manual_install`
   *(FR355; ADR-2)*

4. **Given** a `folder` mod
   **Then** the check behaves as today: found mods get updates, others are local mods
   *(ADR-2 decision 2)*

5. **Given** a mod with source `upload` or `url` in the Installed tab
   **Then** its name has no mod database link, its compatibility is not looked up and reads "Not verified" with "Not from the mod database", and its update cell reads "Uploaded file" or "Installed from a link" (the host in the tooltip), on the table and the phone cards
   *(FR355)*

6. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [x] Task 1: The source on the state (AC: 1-4)
  - [x] 1.1: `ModSource`; `ModState.source` (legacy default by asset ID, a `model_validator(mode="before")`), `source_url`; `ModInfo` and `list_mods`/`get_mod`
  - [x] 1.2: `_place_install` sets `moddb`; the sync sets `folder`; the version change keeps source and URL
  - [x] 1.3: `UnknownReason` `manual_install`; `build_status_items` and `_check_one` skip `upload`/`url` mods (no lookup, no asset ID fill)
  - [x] 1.4: Tests: legacy entries, each setter, `GET /mods`, the check skipping, status reason, folder unchanged
  - [x] 1.5: Commit `feat(story-28.1/task-1): record where each installed mod came from`

- [x] Task 2: The web (AC: 5)
  - [x] 2.1: `ModInfo.source`, `sourceUrl`; reason `manual_install`
  - [x] 2.2: `ModTable`: no compatibility lookup for manual mods, "Not verified" with "Not from the mod database"; `isLocalMod` true for them; `ModUpdateCell` labels by source
  - [x] 2.3: Tests: table and cards for each source
  - [x] 2.4: Commit `feat(story-28.1/task-2): mark uploaded mods and mods installed from a link`

- [x] Task 3: Validate and move the story to review (AC: 6)

## Dev Notes

### The code today (verified at 0da3d584)

- `ModState` (`api/src/vintagestory_api/models/mods.py:63`); built in `_place_install` (`services/mods.py:1650`), the version change (`services/mods.py:1344`) and the sync (`services/mod_state.py:657`); copied in `fill_asset_id` and `repair_fallback_entries` (`model_copy`, which keeps every field).
- `build_status_items` (`services/mod_updates.py:217`) and `_check_one` (`:534`). The check iterates `list_mods()` (ModInfo), so `ModInfo.source` is enough to skip.
- Web: `useModsCompatibility` (`web/src/hooks/use-mods.ts:293`) looks every listed mod up; `ModTable.tsx:165` passes all mods. `isLocalMod` (`components/InstalledModParts.tsx:34`) drives the name link; `ModUpdateCell` gets only the status.

### References

- `epics.md` "Story 28.1"; `architecture/epic-28-mods-from-outside-the-mod-database.md` ADR-1, ADR-2

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-27): exit 0; API 4245 passed, web 3985 passed; Pyright 0/0; lints green.

### Implementation decisions

- **`ModState.source` has a default of `folder` for the type checker**, but a `mode="before"` validator sets it from the asset ID whenever it is missing, so an entry (or a constructor call) without a source reads as `moddb` with an asset ID and `folder` without. Every construction site in `api/src` passes the source explicitly.
- **`MANUAL_SOURCES`** (`upload`, `url`) is one constant used by the status and the check, and `isManualMod` its web twin.
- **The check counts only looked-up mods** (`checked`), so a manual mod never shows as a failed lookup.
- **A record left from before a replace is ignored** for a manual mod (its lookup error too), since it describes the mod-database mod.
- **The web keeps "Local mod"** for a `folder` mod the database does not know; uploaded and linked mods get their own label. `isLocalMod` (no mod page) covers both.
- **The compatibility of a manual mod** is built in `ModTable` (status `not_verified`, message "Not from the mod database"), so the badge and the phone card's message read the same with no request.

### Completion Notes List

- 2026-11-27 (dev-story): Tasks 1 to 3 done. 16 new API tests (`test_mod_source.py`, one in `test_mod_version_change.py`, one assertion in `test_mod_service.py`), 6 new web tests (ModUpdateCell, ModTable, InstalledModCard). The ModTable lookup test was checked to fail without the filter.

- 2026-11-27 (create-story): created from Epic 28's Story 28.1, ADR-1 and ADR-2.

### File List

- API: `models/mods.py`, `models/mod_updates.py`, `services/mods.py`, `services/mod_state.py`, `services/mod_updates.py`; tests `test_mod_source.py` (new), `test_mod_models.py`, `test_mod_service.py`, `test_mod_version_change.py` (Task 1)
- Web: `api/types.ts`, `components/InstalledModParts.tsx`, `components/ModTable.tsx`, `components/ModUpdateCell.tsx`, `components/InstalledModCard.tsx`; tests `ModUpdateCell.test.tsx`, `ModTable.test.tsx`, `InstalledModCard.test.tsx`, `InstalledModParts.test.tsx`, `api/mods.test.ts` (Task 2)
- this file; `sprint-status.yaml` (through `just sprint set`)

## Change Log

- 2026-11-27: Story 28.1 created (create-story); status in-progress.
- 2026-11-27: Story 28.1 implemented (dev-story): Tasks 1 to 3; status review.
