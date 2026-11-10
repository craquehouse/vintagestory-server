# Story 14.4: Update All

Status: review

## Story

As an **administrator**,
I want **to apply all compatible updates at once**,
so that **routine updates take a single action**.

## Acceptance Criteria

1. **Given** mods have compatible updates
   **When** I request `POST /api/v1alpha1/mods/updates/apply-all` as Admin
   **Then** each is updated, one at a time, using the version change operation (Story 14.2)
   **And** the response lists a result per mod: updated, skipped or failed
   *(FR143, FR145)*

2. **Given** a mod's offered update is not verified for the installed game version
   **When** update all runs
   **Then** it is skipped with reason `not_verified` and reported for individual review
   *(FR144)*

3. **Given** an offered update that looked compatible no longer is when applied (fresh lookup)
   **When** update all reaches it
   **Then** it is skipped with the reasons the version change reported; nothing is confirmed on the user's behalf

4. **Given** one mod fails to update (lookup, download, validation or file error)
   **When** update all continues
   **Then** the remaining mods are still processed and the failure is reported with its message
   *(FR145)*

5. **Given** update all is already running
   **When** another request arrives
   **Then** it returns 409 `MOD_UPDATE_ALL_IN_PROGRESS`; a Monitor key gets 403

6. **Given** compatible updates exist
   **When** I click "Update all" on the Installed tab
   **Then** a confirmation lists the mods to update (installed → offered) and those skipped as not verified
   **And** after confirming I see a per-mod summary (updated, skipped, failed) and at most one restart message
   *(UX Update All Flow)*

## Tasks / Subtasks

- [x] Task 1: Update all in the service + tests (AC: 1, 2, 3, 4, 5)
  - [x] 1.1: `ModUpdateService.apply_all(change_version)` in `services/mod_updates.py`: take status items with `status == "update_available"`; skip `offered_compatibility != "compatible"` with reasons `[offered_compatibility]`; otherwise call `change_version(slug, offered_version)` (no confirm) sequentially
  - [x] 1.2: Map `ModConfirmationRequiredError` → skipped with its reasons; known errors (version change, lookup, download, validation, `OSError`) → failed with the message; continue in every case
  - [x] 1.3: Lock: a second call while running raises `ModUpdateAllInProgressError`
  - [x] 1.4: Result types: `UpdateAllItem(slug, name, from_version, to_version, outcome, reasons, error)` and `UpdateAllSummary(results, updated, skipped, failed, pending_restart)`
  - [x] 1.5: Tests with a fake `change_version`: mixed outcomes, skip not-verified without calling, confirmation-required becomes skipped, one failure does not stop the rest, order, lock

- [x] Task 2: Endpoint + tests (AC: 1, 5)
  - [x] 2.1: Error code `MOD_UPDATE_ALL_IN_PROGRESS`
  - [x] 2.2: `POST /mods/updates/apply-all` (Admin), declared before `/{slug}` routes; passes `ModService.change_version`; returns the summary; 409 on the lock
  - [x] 2.3: Router tests: success payload with real fixtures (respx), 409, 403 Monitor, 401

- [x] Task 3: Web API layer + tests (AC: 6)
  - [x] 3.1: Types `ModUpdateAllItem`, `ModUpdateAllData`; `applyAllModUpdates()`; hook `useApplyAllModUpdates()` (skips the global error toast like the other update hooks; invalidates `['mods']` when settled, since mods may have changed even on a failed request)
  - [x] 3.2: Tests

- [x] Task 4: Update All action, confirmation and summary + tests (AC: 6)
  - [x] 4.1: "Update all" button in `InstalledTab`, shown when any status is `update_available`; disabled while running
  - [x] 4.2: `UpdateAllDialog`: confirm step lists "Will update" (name, installed → offered) and "Skipped, not verified" (review individually); confirm runs the request; result step lists each mod's outcome with reasons or error, plus "A server restart is required for changes to take effect." when `pendingRestart`; Close
  - [x] 4.3: Error toast if the request itself fails (including 409)
  - [x] 4.4: Component tests: button visibility, confirmation lists, summary rendering, restart line once, cancel sends nothing

- [x] Task 5: Manual browser verification and final validation (AC: all)
  - [x] 5.1: Throwaway container with a real server and mods with compatible, not-verified and no updates; run Update all; check the summary, restart banner and mods directory; check the browser console
  - [x] 5.2: Run `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

Delivers FR143–FR145 on top of Stories 14.1–14.3. **Out of scope:** scheduled checks and badges (14.5), webhooks (14.6), a mobile layout (`VSS-rr5`).

### Rules

- "Update all = compatible only" (correct-course decision). The offered version from the update status is used; `change_version` does a fresh lookup and returns confirmation reasons if it is no longer compatible, so the apply re-evaluates without extra code. Never pass `confirm=True`.
- ADR-1 never offers an incompatible release, so offered compatibility is `compatible` or `not_verified`; anything other than `compatible` is skipped with that value as its reason.
- Sequential, not parallel (UX: "Mods update one at a time"). Each change already holds its per-mod lock; a mod being changed elsewhere fails with `MOD_VERSION_CHANGE_IN_PROGRESS`, which is reported, not retried.
- Pending restart: `change_version` marks it per mod when the server runs; the summary's `pending_restart` is true if any change set it. The UI shows the restart message once.

### API

`POST /api/v1alpha1/mods/updates/apply-all` (Admin), no body. Response `data`:

```json
{
  "results": [
    {"slug": "carryon", "name": "Carry On", "from_version": "1.14.1", "to_version": "1.14.3",
     "outcome": "updated", "reasons": [], "error": null}
  ],
  "updated": 1, "skipped": 0, "failed": 0, "pending_restart": false
}
```

`outcome`: `updated | skipped | failed`. Errors: 409 `MOD_UPDATE_ALL_IN_PROGRESS`; 401; 403.

### Existing code to reuse

| Need | Use |
|---|---|
| Status items | `ModUpdateService.get_status()` |
| Version change | `ModService.change_version` and its exceptions (`services/mods.py`) |
| Router pattern | `routers/mods.py` `check_mod_updates` and `_version_change_error` |
| Web hooks | `hooks/use-mods.ts` `useCheckModUpdates` (global `onError` override) |
| Dialog | `components/ui/alert-dialog.tsx`, as `VersionChangeConfirmDialog` |
| Toasts | `sonner`, as `InstalledTab` |

### Testing Requirements

- Service tests use a fake `change_version` coroutine; router tests use `respx` with `tests/fixtures/moddb/` as in `test_mod_version_change_router.py`.
- Web tests follow `InstalledTab.test.tsx` (URL-aware `fetch` mocks).
- Commit only when lint, typecheck and the task's tests pass. Task 5 browser verification is required for this UI story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.4]
- [Source: _bmad-output/planning-artifacts/prd.md] FR143–FR145
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] API Additions, Frontend
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] Update All Flow
- [Source: _bmad-output/implementation-artifacts/14-2-version-change-api.md], [14-3-update-and-version-switching-ui.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Browser verification screenshots were kept locally only (`.playwright-mcp/`, git-ignored).

### Completion Notes List

- Task 1: `ModUpdateService.apply_all(change_version)` walks the status items with an offered update in order, skips offers that are not `compatible` (reason = offered compatibility), and calls `change_version(slug, offered)` without confirmation. `ModConfirmationRequiredError` → skipped with its reasons; mod database, lookup, validation, version change and `OSError` errors → failed with the message; the run continues. A second run raises `ModUpdateAllInProgressError`. `services.mods` imports `mod_updates`, so its error types are imported inside the method (the module's existing lazy-import pattern) and `VersionChangeResult` only under `TYPE_CHECKING`. 9 tests with a fake `change_version`.
- Task 2: `POST /mods/updates/apply-all` (Admin) returns the summary via `asdict`; 409 `MOD_UPDATE_ALL_IN_PROGRESS`. 5 router tests use the real `ModService` with the Carry On fixture. Writing the failed-lookup test exposed that `ModApiClient.get_mod` raised a bare `JSONDecodeError` for an HTTP error with an empty body (aborting the whole run) and returned None, read as "not found", for an unexpected `statuscode`. It now raises `ExternalApiError` for both, like the other fetchers (`VSS-d15`, closed with an AAR; 4 tests).
- Task 3: Types, `applyAllModUpdates()` and `useApplyAllModUpdates()` (no global error toast; refetches `['mods']` when settled, since some mods may have changed even if the request failed). 2 tests.
- Task 4: `UpdateAllDialog`: confirm step lists "Will update" (installed → offered) and "Skipped: not verified for game version …"; confirm runs the request; the summary shows counts, each mod's outcome (reasons or error) and the restart message once. A failed request closes the dialog with an error toast. `InstalledTab` shows "Update all (N)" when N compatible updates exist. 8 tests.
- Task 5: Browser check in a throwaway container (VintageStory 1.22.7 running; Carry On 1.14.1 with a compatible 1.14.3; Auto Map Markers 5.0.2 with a not verified 5.0.3): "Update all (1)", the confirmation listed Carry On to update and Auto Map Markers as skipped; the summary showed "1 updated, 1 skipped, 0 failed", one restart line and the restart banner; the button then disappeared, Carry On showed v1.14.3 "Up to date", Auto Map Markers kept its individual Update action; the mods directory held one file per mod; no browser console errors.

### File List

- Created: `api/tests/test_mod_update_all.py`, `api/tests/test_mod_update_all_router.py`
- Created: `web/src/components/UpdateAllDialog.tsx`, `web/src/components/UpdateAllDialog.test.tsx`
- Modified: `api/src/vintagestory_api/services/mod_updates.py`, `api/src/vintagestory_api/routers/mods.py`, `api/src/vintagestory_api/models/errors.py`
- Modified: `api/src/vintagestory_api/services/mod_api.py`, `api/tests/test_mod_api.py` (`VSS-d15`)
- Modified: `web/src/api/types.ts`, `web/src/api/mods.ts`, `web/src/api/mods.test.ts`, `web/src/hooks/use-mods.ts`, `web/src/hooks/use-mods.test.tsx`
- Modified: `web/src/features/mods/InstalledTab.tsx`, `web/src/features/mods/InstalledTab.test.tsx`

## Change Log

- 2026-11-09: Implemented update all (service, endpoint, web hook, confirmation and summary dialog) and fixed `get_mod` error handling (`VSS-d15`). Browser-verified in a throwaway container. `just check` passes with 1978 API tests and 2975 web tests.
