# Story 14.3: Update and Version Switching UI

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to update or switch a mod's version from the UI**,
so that **I can manage versions without touching files**.

## Acceptance Criteria

1. **Given** a mod has an offered update
   **When** I view the Installed tab
   **Then** an "Available" column shows the offered version with an Update action
   **And** other statuses show "Up to date", "No compatible update" (blocked) or "Unknown" with the reason as a tooltip
   *(FR133, UX VersionCell)*

2. **Given** the offered update is compatible
   **When** I click Update
   **Then** the mod updates without a confirmation dialog, I see a success toast, and the table shows the new version
   *(FR135)*

3. **Given** the update or switch needs confirmation (the API returns 409 `MOD_CONFIRMATION_REQUIRED`)
   **When** I click Update or Switch
   **Then** a warning dialog lists each reason (not verified, incompatible, pre-release, older release)
   **And** confirming retries with `confirm: true`; cancelling changes nothing
   *(FR136, FR141)*

4. **Given** a version change fails
   **When** the error is returned
   **Then** I see an error toast with the API message and the mod is shown unchanged

5. **Given** I am an Admin
   **When** I click "Check for updates" on the Installed tab
   **Then** a check runs, the table refreshes, and I see when the last full check finished
   *(FR134)*

6. **Given** an installed mod
   **When** I open its detail page
   **Then** the Update button uses the offered update from the update status (not "newest release"), and installing an installed mod is never attempted
   **And** the version selector lists only releases with the installed mod's modid, and switching to one uses the same confirmation flow
   *(FR79, FR140)*

7. **Given** the server is running
   **When** a version change succeeds
   **Then** the success toast says a restart is required, matching the existing enable/disable toasts
   *(FR139)*

## Tasks / Subtasks

- [x] Task 1: Add the release modid to mod lookups + tests (AC: 6)
  - [x] 1.1: Add `modidstr: str` to `ModRelease` in `api/src/vintagestory_api/models/mods.py` and set it in `ModService.lookup_mod` from each release's `modidstr`
  - [x] 1.2: API test that lookup releases carry `modidstr` (instruments fixture: several modids)
  - [x] 1.3: Add `modidstr: string` to `ModRelease` in `web/src/api/types.ts`

- [x] Task 2: Add the web API layer for updates and version changes + tests (AC: 2, 3, 4, 5)
  - [x] 2.1: `api/client.ts`: pass `errorData.detail.details` into `ApiError` so confirmation reasons reach the UI
  - [x] 2.2: Types: `ModUpdateStatus`, `ModUpdatesData`, `ModUpdateCheckData`, `ModVersionChangeData` in `api/types.ts` (camelCase, per the client's transform)
  - [x] 2.3: `api/mods.ts`: `fetchModUpdates()`, `checkModUpdates()`, `changeModVersion(slug, version, confirm)`
  - [x] 2.4: Query key `mods.updateStatus` as `['mods', '@updates']` (`@` cannot appear in a modid, so it cannot collide with `mods.detail(slug)`)
  - [x] 2.5: Hooks in `hooks/use-mods.ts`: `useModUpdates()`, `useCheckModUpdates()`, `useChangeModVersion()`; mutations invalidate `queryKeys.mods.all` (which covers the update status key)
  - [x] 2.6: Tests for the client change, API functions and hooks

- [x] Task 3: Show update status in the Installed tab + tests (AC: 1, 5)
  - [x] 3.1: Add an "Available" column to `ModTable` driven by `useModUpdates()`, keyed by slug
  - [x] 3.2: "Check for updates" button and "Last checked …" text in `InstalledTab`; spinner while running; error toast on failure (including 409 when a check is already running)
  - [x] 3.3: Component tests for each status, the check button and last-checked text

- [x] Task 4: Version change flow with confirmation + tests (AC: 2, 3, 4, 7)
  - [x] 4.1: Shared `useVersionChangeFlow()` hook or component: call `changeModVersion` without `confirm`; on `MOD_CONFIRMATION_REQUIRED` open `VersionChangeConfirmDialog` listing reasons; on confirm retry with `confirm: true`
  - [x] 4.2: `VersionChangeConfirmDialog` (AlertDialog): title "Update {name} to v{version}?" or "Switch {name} to v{version}?", one line per reason, primary "Update anyway" / "Switch anyway", "Cancel" secondary (UX spec Compatibility Warnings)
  - [x] 4.3: Update action in the Available column uses the flow; per-row spinner; success and error toasts (restart wording when the server is running)
  - [x] 4.4: Tests: compatible update (no dialog), each reason rendered, confirm retries with `confirm: true`, cancel makes no second call, error toast

- [ ] Task 5: Version switching on the mod detail page + tests (AC: 6)
  - [ ] 5.1: In `InstallSection`, when installed: offered update from `useModUpdates()`; version list filtered to `release.modidstr === installed slug`; the action button switches versions through the Task 4 flow
  - [ ] 5.2: Remove the `installedVersion !== latestVersion` comparison (it reports any non-latest version, including a rollback, as an update)
  - [ ] 5.3: Not installed: keep the existing install flow and `InstallConfirmDialog` unchanged
  - [ ] 5.4: Tests: update button only when an update is offered, filtered version list, switch calls the version change API, install path unchanged

- [ ] Task 6: Manual browser verification and final validation (AC: all)
  - [ ] 6.1: Build the image, run it in a throwaway container with a real server and a mod at an older version: update, roll back with confirmation, check for updates; check browser console for errors
  - [ ] 6.2: Run `just check`; update this story's Dev Agent Record and File List

## Dev Notes

### Scope

Delivers the UI for Stories 14.1 and 14.2, plus a one-field API addition (Task 1). **Out of scope:** update all (14.4), Dashboard and navigation badges (14.5), webhooks (14.6). Do not change `ModService.lookup_mod` compatibility (`VSS-tpe`); the Compatibility column keeps its current behavior.

### APIs this story consumes (Stories 14.1 and 14.2)

- `GET /api/v1alpha1/mods/updates` (Admin or Monitor): `{gameVersion, checkedAt, updateCount, mods: [{slug, name, installedVersion, status, offeredVersion, offeredCompatibility, offeredPrerelease, reason, checkedAt, error}]}` after the client's camelCase transform. `status`: `update_available | up_to_date | blocked | unknown`; `reason` (for unknown): `not_checked | not_in_database | installed_release_not_listed | version_unparsable`.
- `POST /api/v1alpha1/mods/updates/check` (Admin): same payload plus `check: {checked, failed, failedSlugs}`; 409 `MOD_UPDATE_CHECK_IN_PROGRESS`.
- `PUT /api/v1alpha1/mods/{slug}/version` (Admin), body `{version, confirm}`: returns `{slug, previousVersion, version, filename, compatibility, changed, pendingRestart}`. Errors: 409 `MOD_CONFIRMATION_REQUIRED` with `details: {reasons, compatibility}`; 409 `MOD_VERSION_CHANGE_IN_PROGRESS`; 404 `MOD_NOT_INSTALLED`, `MOD_NOT_FOUND`, `MOD_VERSION_NOT_FOUND`; 422 `MOD_VALIDATION_FAILED`; 502 `EXTERNAL_API_ERROR`, `DOWNLOAD_FAILED`; 500 `MOD_VERSION_CHANGE_FAILED`.

**Client gap:** `web/src/api/client.ts` currently builds `new ApiError(code, message, status)` without `detail.details`, so the confirmation reasons would be lost. Task 2.1 fixes it.

### Reason wording (dialog)

| Reason | Text |
|---|---|
| `not_verified` | Not verified for game version {gameVersion}. It may still work. |
| `incompatible` | Not tagged for game version {gameVersion}. It may not load. |
| `prerelease` | v{version} is a pre-release; the installed version is a stable release. |
| `older` | v{version} is older than the installed v{installed}. Worlds saved with a newer version may not load correctly. |

### Existing UI to reuse

| Need | Use |
|---|---|
| Table | `components/ModTable.tsx` (TanStack Table v9 with `columnHelper.columns`); add a display column after Version |
| Dialog | `components/ui/alert-dialog.tsx`, as the remove dialog in `ModTable` does |
| Toasts | `sonner` (`toast.success` / `toast.error`), as `InstalledTab` does |
| Server running | `useServerStatus()` → `data.data.state === 'running'`, as `InstalledTab` does |
| Detail page | `features/mods/ModDetailPage.tsx` `InstallSection` (lines 132-269) |
| Badges | `CompatibilityBadge` for the offered release's compatibility |

### UX (from `ux-design-specification.md`, updated for Epic 14)

- Available column: offered version plus Update action, or a status label. Informational, not loud.
- Warning dialogs: risk description, "Cancel" secondary, "Update anyway" / "Switch anyway" primary.
- Version switching lives on the mod detail page; the table offers only the update.

### Testing Requirements

- Web tests use Vitest and Testing Library; follow `components/ModTable.test.tsx` and `features/mods/ModDetailPage.test.tsx` for mocking hooks and API modules.
- API test for Task 1 goes in `api/tests/test_mod_service.py` or a new focused test using `mod_instruments.json`.
- Commit only when `just lint`, `just typecheck-web` (or `just check`) and the task's tests pass.
- UI story: Task 6 manual browser verification is required (project-context.md "UI-focused stories MUST include a manual browser verification task").

### Security

- Update and switch actions are Admin-only at the API; the UI hides them for Monitor keys only if the app already has a role signal; otherwise rely on the 403 error toast. Do not add a client-side role system in this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.3]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] Mod Update Flow, Version Switch Flow, VersionCell, Compatibility Warnings
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] API Additions, Frontend
- [Source: _bmad-output/implementation-artifacts/14-1-update-detection-and-status-api.md], [14-2-version-change-api.md]
- [Source: project-context.md] Frontend patterns, TanStack Query conventions

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
