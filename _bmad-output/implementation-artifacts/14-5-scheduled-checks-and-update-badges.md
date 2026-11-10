# Story 14.5: Scheduled Checks and Update Badges

Status: in-progress

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

- [ ] Task 1: Scheduled checks in the refresh job + tests (AC: 1, 2, 3)
  - [ ] 1.1: `jobs/mod_cache_refresh.py` runs `ModUpdateService.check()` (ADR-5) instead of its own reachability loop, which made the same requests and stored nothing; logs a summary with the update count
  - [ ] 1.2: `ModUpdateCheckInProgressError` → log `mod_cache_refresh_skipped` and return
  - [ ] 1.3: Rewrite `tests/jobs/test_mod_cache_refresh.py`: status recorded per mod with one failing lookup (respx), skip when a check runs, no mods, `safe_job` contract; interval 0 stays covered by `test_jobs_registration.py`

- [ ] Task 2: Update count in the navigation + tests (AC: 4, 5)
  - [ ] 2.1: `SubNavItem.badge` (count) in `ExpandableNavItem`: a count pill on the item when > 0, in the collapsed-sidebar tooltip, and on the parent while the group is closed, with an accessible label
  - [ ] 2.2: `Sidebar` sets the Mods item's badge from `useModUpdates()` (`updateCount`); the item already opens the Installed tab (`/game-server/mods` → `installed`)
  - [ ] 2.3: Tests: badge shown with count, hidden at 0, parent total while closed, collapsed tooltip

- [ ] Task 3: Update notice on the Dashboard + tests (AC: 4, 5)
  - [ ] 3.1: `ModUpdatesNotice`: "N mod updates available" linking to `/game-server/mods/installed`; renders nothing when the count is 0 or unknown
  - [ ] 3.2: Shown on the installed-server Dashboard below the disk space warning
  - [ ] 3.3: Tests

- [ ] Task 4: Manual browser verification and final validation (AC: all)
  - [ ] 4.1: Throwaway container with a short `mod_list_refresh_interval` and a mod with an update: without clicking Check, the job records status and the badge and notice appear; following them opens the Installed tab; check the browser console
  - [ ] 4.2: Run `just check`; update the Dev Agent Record and File List

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

### Debug Log References

### Completion Notes List

### File List
