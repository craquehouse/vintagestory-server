# Story 14.5: Scheduled Checks and Update Badges

Status: review

## Story

As an **administrator**,
I want **updates found automatically and shown at a glance**,
so that **I notice them without checking**.

## Acceptance Criteria

1. **Given** `mod_list_refresh_interval` is greater than 0
   **When** the refresh job runs
   **Then** update status is recorded for each installed mod
   **And** a failure for one mod does not affect the others
   *(FR146)*

2. **Given** `mod_list_refresh_interval` is 0
   **When** the scheduler starts
   **Then** no scheduled checks run
   **And** on-demand checks still work
   *(FR146)*

3. **Given** an on-demand check is running when the job fires
   **When** the job runs
   **Then** it skips this run without error

4. **Given** updates are available
   **When** I view the Dashboard or navigation
   **Then** I see the count of mods with updates
   **And** selecting it takes me to the Installed tab
   *(FR148)*

5. **Given** no updates are available
   **When** I view the Dashboard or navigation
   **Then** no count is shown

## Tasks / Subtasks

- [x] Task 1: Scheduled checks in the refresh job + tests (AC: 1, 2, 3)
  - [x] 1.1: `jobs/mod_cache_refresh.py` runs `ModUpdateService.check()` (ADR-5) instead of its own reachability loop, which made the same requests and stored nothing; logs a summary with the update count
  - [x] 1.2: `ModUpdateCheckInProgressError` → log `mod_cache_refresh_skipped` and return
  - [x] 1.3: Rewrite `tests/jobs/test_mod_cache_refresh.py`: status recorded per mod with one failing lookup (respx), skip when a check runs, no mods, `safe_job` contract; interval 0 stays covered by `test_jobs_registration.py`

- [x] Task 2: Update count in the navigation + tests (AC: 4, 5)
  - [x] 2.1: `SubNavItem.badge` (count) in `ExpandableNavItem`: a count pill on the item when > 0, in the collapsed-sidebar tooltip, and a dot on the parent while the group is closed, with an accessible label
  - [x] 2.2: `Sidebar` sets the Mods item's badge from `useModUpdates()` (`updateCount`); the item already opens the Installed tab (`/game-server/mods` → `installed`)
  - [x] 2.3: Tests: badge shown with count, hidden at 0, parent total while closed, collapsed tooltip

- [x] Task 3: Update notice on the Dashboard + tests (AC: 4, 5)
  - [x] 3.1: `ModUpdatesNotice`: "N mod updates available" linking to `/game-server/mods/installed`; renders nothing when the count is 0 or unknown
  - [x] 3.2: Shown on the installed-server Dashboard below the disk space warning
  - [x] 3.3: Tests

- [x] Task 4: Manual browser verification and final validation (AC: all)
  - [x] 4.1: Throwaway container with a short `mod_list_refresh_interval` and a mod with an update: without clicking Check, the job records status and the badge and notice appear; following them opens the Installed tab; check the browser console
  - [x] 4.2: Run `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

FR146 and FR148; FR147 (status survives an API restart) is already met by the persisted store from Story 14.1. **Out of scope:** webhooks (14.6).

### Rules

- ADR-5: no new job or setting. The job is registered only when `mod_list_refresh_interval > 0` (`jobs/__init__.py`), so interval 0 disables scheduled checks while `POST /mods/updates/check` keeps working.
- The check isolates failures per mod, keeps the previous data on a failed lookup and records the error (Story 14.1); since `VSS-d15`, mod database errors raise instead of reading as "not found".
- `updateCount` counts every `update_available` mod, including not verified offers (it is "updates available", not "safe to apply"); this matches the Installed tab's Available column.

### Existing code to reuse

| Need | Use |
|---|---|
| Update check | `ModUpdateService.check()`, `get_mod_update_service()` |
| Update count | `useModUpdates()` → `data.updateCount` |
| Navigation | `components/layout/Sidebar.tsx`, `ExpandableNavItem.tsx` |
| Dashboard | `features/dashboard/Dashboard.tsx`; banner pattern `components/DiskSpaceWarningBanner.tsx` |

### Testing Requirements

- Job tests patch `get_mod_update_service` in the job module and use `respx` with `tests/fixtures/moddb/`.
- Web tests follow the existing `ExpandableNavItem`, `Sidebar` and `Dashboard` tests.
- Task 4 browser verification is required for this UI story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.5]
- [Source: _bmad-output/planning-artifacts/prd.md] FR146–FR148
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-5
- [Source: _bmad-output/implementation-artifacts/14-1-update-detection-and-status-api.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Browser verification screenshots were kept locally only (`.playwright-mcp/`, git-ignored).

### Completion Notes List

- Task 1: `refresh_mod_cache` now runs `ModUpdateService.check()` (ADR-5) and logs `checked`, `failed`, `failed_slugs` and `updates_available`; an on-demand check in progress makes it log `mod_cache_refresh_skipped` and return. Its old loop called `get_mod` per installed mod only to log reachability, so the request count per interval is unchanged. The job tests were rewritten for the new behavior (status recorded per mod with one failing lookup, skip while a check runs, no mods, `safe_job` contract); the old tests asserted the removed loop. API test count drops from 1978 to 1972 accordingly.
- Task 2: `SubNavItem.badge` and `badgeLabel`: a count pill on the item, a dot plus "(N)" tooltip in the icon-only sidebar, and a dot on the parent icon while the group is closed. The count is `aria-hidden`; screen readers get the label (the Mods link reads "Mods, 2 mod updates available"). `Sidebar` takes the count from `useModUpdates()`. 7 tests.
- Task 3: `ModUpdatesNotice` on the installed-server Dashboard: "N mod updates available … Review", linking to `/game-server/mods/installed`; nothing when the count is 0 or not loaded. 5 tests.
- Task 4: Browser check in a throwaway container (Carry On 1.14.1 and Auto Map Markers 5.0.2): with the interval at 30 s and no manual check, the job recorded both updates (`mod_cache_refresh_summary checked=2 failed=0 updates_available=2`); the Dashboard notice and the Mods badge showed 2; the notice opened the Installed tab; no console errors. The first layout put a count pill on the closed Game Server group, which pushed its chevron out of the 160 px sidebar; it is now a dot on the icon (fixed and rechecked).
- Found, not fixed (filed as `VSS-8bl`): changing `mod_list_refresh_interval` through the settings API does not reschedule the job until the API restarts (`get_api_settings_service` never passes the scheduler callback, an Epic 7 TODO). The check above restarted the container to apply 30 s.

### File List

- Created: `web/src/components/ModUpdatesNotice.tsx`, `web/src/components/ModUpdatesNotice.test.tsx`
- Modified: `api/src/vintagestory_api/jobs/mod_cache_refresh.py`, `api/tests/jobs/test_mod_cache_refresh.py`
- Modified: `web/src/components/layout/ExpandableNavItem.tsx`, `web/src/components/layout/ExpandableNavItem.test.tsx`
- Modified: `web/src/components/layout/Sidebar.tsx`, `web/src/components/layout/Sidebar.test.tsx`
- Modified: `web/src/features/dashboard/Dashboard.tsx`, `web/src/features/dashboard/Dashboard.test.tsx`

## Change Log

- 2026-11-09: Scheduled update checks in the mod refresh job, update count in the navigation and on the Dashboard. Browser-verified; fixed the closed-group badge layout. `just check` passes with 1972 API tests and 2990 web tests.
