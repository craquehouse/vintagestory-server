# Story 17.2: Install Picks the Right Release

Status: in-progress

<!-- Implements FR179-FR181 and Epic 17 ADR-2. Beads: VSS-jhf, VSS-43b; also closes Story 17.1 review finding L1 (a release without a file reaching the download). Branch story/17-2-install-picks-the-right-release from main (139eef0, Story 17.1 merged). Not in scope: Story 17.3 (per-mod lock, archive mod ID check, modinfo key case), 17.4 (browse cards recognizing any installed mod ID, update status after install). No new dependencies. -->

## Story

As an **administrator**,
I want **Install to give me the newest stable release of the mod I chose**,
so that **I do not end up with a different mod or a pre-release I did not ask for**.

## Acceptance Criteria

1. **Given** a mod database entry that ships several mod IDs (`mod_instruments.json`: `vsinstrumentsbase`, `vsinstruments`, `instruments`, in that order)
   **When** I install one of them (`POST /api/v1alpha1/mods`), with or without a version
   **Then** only releases whose `modidstr` is exactly that mod ID are considered: `instruments` with no version downloads `instruments` 1.2.2 (file 12840), not `vsinstrumentsbase` 2.0.7; `instruments` with version `1.0.1` downloads file 1002, not `vsinstrumentsbase` 1.0.1 (file 30807); `vsinstruments` with no version downloads 1.2.7 (file 18954). The installed mod has the requested mod ID
   *(Covers FR179; `VSS-jhf`)*

2. **Given** a mod whose newest release is a pre-release (`mod_carryon.json`: `2.0.0-rc.1`, then `1.14.3`)
   **When** I install it without a version
   **Then** the first stable release in list order is installed (`1.14.3`, file 113014); naming `2.0.0-rc.1` installs that pre-release (file 130071). Compatibility with the installed game version does not change which release is picked
   *(Covers FR180; `VSS-43b`)*

3. **Given** a mod ID that has only pre-releases
   **When** I install it without a version
   **Then** its first release in list order that has a file is installed
   *(Covers FR180)*

4. **Given** a version that no release of that mod ID has, including one that exists only under another mod ID of the entry (`instruments` with `2.0.7`) and the literal string `latest`
   **When** I install naming it
   **Then** the response is 404 `MOD_VERSION_NOT_FOUND`, no download is requested and nothing is installed
   *(Covers FR179)*

5. **Given** a release without a downloadable file (`mod_canjewelry.json`: `0.2.20`, `0.1.26`, `0.2.0`)
   **When** releases are chosen for install or a version change
   **Then** it is never picked by default; naming it in an install (`POST /mods`) or a version change (`PUT /mods/{slug}/version`) is refused with 422 `MOD_RELEASE_NOT_DOWNLOADABLE` and a message that says the release has no downloadable file, before any confirmation and with no request to the download endpoint; a plain install of a mod ID none of whose releases has a file gets the same error; `download_release_file` cannot be called with `None`
   *(Covers FR180; Story 17.1 review L1)*

6. **Given** `GET /api/v1alpha1/mods/lookup/{slug}`
   **When** the response is built
   **Then** it has `install_mod_id` (the mod ID an install of this slug installs) and `latest_version` is the version a plain install picks (`null` when that mod ID has no release with a file), both from the same function install uses; when no mod ID of the entry is installed, compatibility is evaluated for `install_mod_id`. For `instruments`: `install_mod_id` `instruments`, `latest_version` `1.2.2`. For `carryon`: `latest_version` `1.14.3`
   *(Covers FR181; ADR-2 decisions 5 and 6)*

7. **Given** the detail page of a mod that is not installed
   **When** I look at the install section
   **Then** the version list holds only the releases of `installModId` (one item per version), `latestVersion` is preselected and is the only item labelled "(Latest)", a release without a file is listed disabled with "(no file)", and Install sends `{ slug: installModId, version: <selected> }`. The "Latest" badge in the Releases list is on that same release. For an installed mod, the version list labels "(Latest)" only when the installed mod ID is `installModId`, and shows releases without a file disabled
   *(Covers FR181)*

8. **Given** a browse card
   **When** I install from it
   **Then** the dialog shows `latestVersion` and the request is `{ slug: installModId, version: latestVersion }`; when the mod's details could not be loaded, the request carries the card's slug and no version (never the string `latest`), the dialog shows "Version: Latest", and the success toast names the version the API installed
   *(Covers FR181; ADR-2 decision 7)*

9. **Given** a mod with one mod ID whose newest release is stable and has a file (every existing install and lookup test)
   **When** it is installed or looked up
   **Then** the result is unchanged: every existing test passes, apart from the changes listed in Dev Notes "Existing tests that change"

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.2/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: Release selection function + tests (AC: 1, 2, 3, 4, 5)
  - [x] 1.1: Create `api/src/vintagestory_api/services/mod_release_selection.py`. It imports only `vintagestory_api.models.moddb` (Dev Notes "Where the function lives"). Move `is_prerelease` here from `services/mod_updates.py:46-48`; `mod_updates.py` imports it from the new module, so `from vintagestory_api.services.mod_updates import is_prerelease` (`services/mods.py:50`, `services/mod_compatibility.py:14`, tests) keeps working
  - [x] 1.2: Add `has_file(fileid: int | None) -> bool` (a positive file ID), the frozen dataclass `InstallSelection` and `select_install_release(slug: str, releases: list[ReleaseDict], version: str | None = None) -> InstallSelection`, implementing ADR-2 rules 1-4 exactly as in Dev Notes "Selection rules". The function is pure: no I/O, no exceptions for a refusal, input not mutated
  - [x] 1.3: Tests in `api/tests/test_mod_release_selection.py`, loading fixtures through `normalize_mod` (as `get_mod` does): every row of Dev Notes "Selection test cases"; `is_prerelease` still importable from `services.mod_updates`

- [x] Task 2: Install uses the selection, and a release without a file is refused + tests (AC: 1, 2, 3, 4, 5, 9)
  - [x] 2.1: `services/mod_api.py`: add `ModReleaseNotDownloadableError(ModApiError)` beside `ModVersionNotFoundError` (`:71-77`), with `slug`, `version: str | None` and the messages in Dev Notes "Errors". `download_mod` (`:355-413`): replace the selection block (`:392-403`) with `select_install_release(slug, releases, version)`; `refusal == "version_not_found"` raises `ModVersionNotFoundError(slug, version)`, `"no_file"` raises `ModReleaseNotDownloadableError(slug, version)`; pass `selection.file_id` (typed `int`) to `download_release_file`, not `release["fileid"]`. Keep the debug log with the chosen mod ID and version. Update the docstring ("latest" is the newest stable release of the mod ID that has a file)
  - [x] 2.2: `download_release_file` (`:415-487`): first statement refuses `fileid <= 0` with `ModReleaseNotDownloadableError(slug)`; the parameter stays `fileid: int`. `ModService._prepare_version_change` (`services/mods.py:975-1023`): after the target is resolved (`:1001-1004`) and before the compatibility and confirmation checks, `target.fileid <= 0` raises `ModReleaseNotDownloadableError(slug, version)` (`StoredRelease` stores "no file" as 0, `models/mod_updates.py:66-71`); add it to both docstrings' Raises
  - [x] 2.3: `models/errors.py` (`:57-64`): `MOD_RELEASE_NOT_DOWNLOADABLE`. `routers/mods.py`: import the error (`:16-26`); `install_mod` (`:657-751`) and `change_mod_version` (`:967-1005`) return 422 with that code and `str(e)`; add it to the install docstring's Raises; `ModInstallRequest.version` description (`:650-654`): without a version, the newest stable release of the mod ID that has a downloadable file
  - [x] 2.4: Tests. `tests/test_mod_api.py` (`TestModApiClientDownloadMod`, respx on `https://mods.vintagestory.at/api/mod/{slug}` with the fixture and on `https://mods.vintagestory.at/download?fileid=<id>`): AC 1, 2, 3 file IDs; AC 4 (`instruments` + `2.0.7`, `carryon` + `latest`) with the download route not called; AC 5 with `mod_canjewelry.json` (`canjewelry` + `0.2.20` raises `ModReleaseNotDownloadableError`, download not called; no version picks `0.8.2`, file 138875); a synthetic mod ID with no file at all; `download_release_file("demo", 0, "x.zip")` raises and sends nothing. `tests/test_mod_service.py` (`TestModServiceInstallMod`): installing `instruments` from the fixture with a zip whose `modinfo.json` is `instruments` 1.2.2 gives `InstallResult.slug == "instruments"`, version `1.2.2`, file `instruments_1.2.2.zip` in the mods directory; installing `carryon` gives `1.14.3`. `tests/test_mods_router.py` (`TestInstallModEndpoint`, `TestInstallModVersionNotFound`): 404 `MOD_VERSION_NOT_FOUND` for `instruments` + `2.0.7` and for `"version": "latest"`; 422 `MOD_RELEASE_NOT_DOWNLOADABLE` for `canjewelry` + `0.2.20`, with nothing in the mods directory or state. `tests/test_mod_version_change.py` (`TestPrepareVersionChange`, `MOD_URL.format("canjewelry")`) and `tests/test_mod_version_change_router.py` (its `MOD_URL` is fixed to `carryon`; mock the `canjewelry` URL in the new test): `canjewelry` installed at `0.2.19`, change to `0.2.20` with `confirm` false raises `ModReleaseNotDownloadableError` (router 422), not `ModConfirmationRequiredError`, and the download route is not called. `tests/test_mod_update_all.py`: a `change_version` that raises `ModReleaseNotDownloadableError` is recorded as a failed item and the run continues (it is a `ModApiError`, caught at `services/mod_updates.py:389-400`)

- [x] Task 3: Lookup reports the install mod ID and what a plain install picks + tests (AC: 6, 9)
  - [x] 3.1: `models/mods.py` `ModLookupResponse` (`:193`): add required `install_mod_id: str` (docstring: the mod ID an install of the looked-up slug installs, Epic 17 ADR-2) and make `latest_version: str | None` (`:228`; docstring: the version an install without a named version picks for `install_mod_id`; `None` when none of its releases has a file)
  - [x] 3.2: `ModService.lookup_mod` (`services/mods.py:492-636`): call `select_install_release(slug, releases)` once, after the empty-releases check; replace `:535-536` with `latest_version = (selection.release["modversion"] or "unknown") if selection.release is not None else None`; pass `install_mod_id=selection.mod_id`. `_compatibility_modid` (`:470-490`) takes the default mod ID as a parameter (`selection.mod_id`) instead of computing `releases[0]`'s (`:486`); update its docstring and `lookup_mod`'s. Which release is evaluated (`:540-545`) is not changed (Dev Notes "Not changed")
  - [x] 3.3: `routers/mods.py` lookup docstring (`:576-578`, `:591`): the default mod ID is the install mod ID; describe `install_mod_id` and `latest_version`
  - [x] 3.4: Tests. `tests/test_mod_service.py` and `tests/test_mods_router.py` (`TestLookupModEndpoint`): `instruments` → `install_mod_id` `instruments`, `latest_version` `1.2.2`; `vsinstruments` → `vsinstruments`, `1.2.7`; `carryon` → `carryon`, `1.14.3`, with `compatibility.mod_version` still `2.0.0-rc.1`; a slug no release carries (fixture `egocaribautomapmarkers` looked up as `automapmarkers`) → `install_mod_id` `egocaribautomapmarkers`, `latest_version` `5.0.3`; `canjewelry` → `0.8.2`; a mod ID whose only releases have no file → `latest_version` `null`, 200; for each fixture, `latest_version` equals the version `download_mod(slug)` selects (one parametrized test that calls both). `tests/test_mod_models.py`: `install_mod_id` round-trips and `latest_version=None` dumps as `null`. Update the tests in "Existing tests that change"

- [x] Task 4: Web version lists, "(Latest)" and install requests follow the lookup + tests (AC: 7, 8, 9)
  - [x] 4.1: `web/src/api/types.ts` `ModLookupData` (`:173-195`): `installModId: string` and `latestVersion: string | null` (`:182`), with comments
  - [x] 4.2: `web/src/lib/mod-ids.ts`: add `versionChoices(releases, modId): Array<{ version: string; installable: boolean }>`: the releases whose `modidstr === modId`, one per version keeping the first listing (the rule `InstalledVersionSection` applies today, `ModDetailPage.tsx:309-314`), `installable` when that listing's `fileId` is a positive number. Tests in `web/src/lib/mod-ids.test.ts`
  - [x] 4.3: `ModDetailPage.tsx` `InstallSection` (`:202-273`): receives `slug={mod.installModId}` (today `mod.slug`, `:701`); lists `versionChoices(releases, installModId)` (replacing `:230-239`); "(Latest)" on `choice.version === latestVersion` instead of `index === 0` (`:237`); a choice that is not installable is `<SelectItem disabled>` with " (no file)"; state starts at `latestVersion`; when `latestVersion` is `null` the Install button is disabled and reads "No downloadable release". The dialog call (`:256-270`) is unchanged apart from the slug
  - [x] 4.4: `InstalledVersionSection` (`:297-427`): build the list with `versionChoices(releases, slug)`; "(Latest)" (`:406`) only when the section's `slug` equals the new `installModId` prop and the version equals the new `latestVersion` prop; not installable choices disabled with " (no file)"; keep the message for an empty list (`:386-389`). Pass both new props where the section is rendered (`:693-698`). `ReleaseItem` (`:745-751`): `isLatest` is true for the first release with `modidstr === mod.installModId && version === mod.latestVersion`, not `index === 0`. Add a Story 17.2 line to the header doc comment
  - [x] 4.5: `InstallConfirmDialog.tsx`: `mod.version?: string | null` (`:35-41`); "Version: Latest" when it is not set (`:163-168`); `install({ slug: mod.slug, version: mod.version ?? undefined })` (`:100-103`); the success toast (`:105-107`) names `response?.data.version ?? mod.version`. `ModCard.tsx`: delete `LATEST_VERSION` (`:30-33`); pass `slug: modDetails?.data?.installModId ?? mod.slug` and `version: modDetails?.data?.latestVersion` (`:230-237`); update the header comment
  - [x] 4.6: Tests: Dev Notes "Web tests"

- [x] Task 5: E2E and browser verification against the Docker dev stack (AC: 1, 2, 4, 5, 7, 8)
  - [x] 5.1: Add `web/e2e/mod-install-release.spec.ts` (Dev Notes "E2E spec"): lookup and UI tests with the install call stubbed, two refused installs, and one real install that is removed again
  - [x] 5.2: `just docker restart` (rebuild from this branch); `cd web && bunx playwright test e2e/mod-install-release.spec.ts e2e/installed-mod-any-modid.spec.ts e2e/mod-detail-bad-data.spec.ts` (admin key from `.env`)
  - [x] 5.3: Manual check (Dev Notes "Manual check"): install Carry On from a browse card and from its detail page, removing it after each; Instruments and C&N Jewelry version lists. Record the results, including that the Installed list and `data/serverdata/Mods` are as they were before, in the Dev Agent Record. Screenshots stay outside the repo unless the server name (`header span.font-semibold`) is masked

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression
  - [ ] 6.2: Story status `review`, `just sprint set 17-2-install-picks-the-right-release review`, PR to `main`, PR link on `VSS-jhf` and `VSS-43b`

## Dev Notes

### The bugs (verified on `main` 139eef0)

- `ModApiClient.download_mod` picks `releases[0]` when no version is given and otherwise the first release whose `modversion` matches, across every mod ID of the entry (`services/mod_api.py:392-403`). In `mod_instruments.json`, `releases[0]` is `vsinstrumentsbase` 2.0.7, and `1.0.1` exists under `vsinstrumentsbase` (file 30807) before `instruments` (file 1002) (`VSS-jhf`). In `mod_carryon.json`, `releases[0]` is `2.0.0-rc.1` (`VSS-43b`).
- The web always names a version, so the "no version" path alone changes nothing an admin sees. The detail page preselects `latestVersion` (`ModDetailPage.tsx:212`), which is `releases[0]`'s version (`services/mods.py:535-536`), lists the releases of every mod ID and labels index 0 "(Latest)" (`:230-239`). It installs with `slug={mod.slug}` (`:701`), which is `modidstrs[0]` (`services/mods.py:603-606`), not the slug that was looked up. The browse card sends `latestVersion`, or the string `'latest'` when the details did not load (`ModCard.tsx:33`, `:234`).
- **The `'latest'` string (checked):** `ModInstallRequest.version` is a free string (`routers/mods.py:650`), so `'latest'` is matched against `modversion`, nothing matches, and the API answers 404 `MOD_VERSION_NOT_FOUND`. That is the right answer for a version no release has; the defect is the web sending it. The API keeps that behavior (pinned by a test) and the web stops sending it.
- **A release without a file (17.1 review L1):** `download_mod` passes `release["fileid"]` (`Any`, can be `None`) to `download_release_file(slug, fileid: int, filename)` (`:406`, `:415`); only the empty filename stops it (`safe_release_filename("")` raises, giving 502 `DOWNLOAD_FAILED` "Unusable release filename"). A release with `fileid` null and a filename would request `download?fileid=None` (`:442`). For a version change the stored `fileid` is 0 (`models/mod_updates.py:71`) and the same empty filename gives 422 `MOD_VALIDATION_FAILED`, after the confirmation step.

### Selection rules (ADR-2 decisions 1-4)

`select_install_release(slug, releases, version=None)` takes the slug after `extract_slug` and the normalized releases of one entry (from `get_mod`), newest first:

1. **Install mod ID.** `slug` if any release has `modidstr == slug` (exact, case-sensitive); otherwise `releases[0]["modidstr"]`. With no releases: `slug`.
2. **Candidates:** releases with `modidstr ==` the install mod ID and `has_file(fileid)`.
3. **No version:** the first candidate with `not is_prerelease(modversion)`; if there is none, the first candidate; if there are no candidates, refusal `"no_file"`.
4. **Version named:** the first candidate with that `modversion`. Otherwise, if any release of the install mod ID has that `modversion`, refusal `"no_file"`; otherwise refusal `"version_not_found"`.

List order decides; no version strings are compared (`parse_base_version` is not used). Game compatibility is not an input.

```python
@dataclass(frozen=True)
class InstallSelection:
    mod_id: str                      # rule 1, always set
    release: ReleaseDict | None      # the chosen release, None when refused
    file_id: int | None              # the chosen release's file ID (int when release is set)
    refusal: Literal["version_not_found", "no_file"] | None
```

Narrow `file_id` with `isinstance(value, int)` when reading it from the release dict, so callers get a real `int` rather than `Any`. In `download_mod`, raise on `refusal` first; if pyright still sees `int | None` afterwards, narrow with an explicit `if selection.release is None or selection.file_id is None:` branch that raises `ModReleaseNotDownloadableError`. No `cast`, no `assert`, no suppression.

### Selection test cases

| Fixture / data | slug | version | Result |
|---|---|---|---|
| `instruments` | `instruments` | none | `instruments` 1.2.2, file 12840 |
| `instruments` | `instruments` | `1.0.1` | file 1002 |
| `instruments` | `instruments` | `2.0.7` | `version_not_found`, `mod_id` `instruments` |
| `instruments` | `vsinstruments` | none | 1.2.7, file 18954 |
| `instruments` | `vsinstrumentsbase` | none | 2.0.7, file 72936 |
| `instruments` | `Instruments` | none | no exact match: `mod_id` `vsinstrumentsbase`, 2.0.7 |
| `carryon` | `carryon` | none | 1.14.3, file 113014 |
| `carryon` | `carryon` | `2.0.0-rc.1` | file 130071 |
| `carryon` | `carryon` | `latest` | `version_not_found` |
| `egocaribautomapmarkers` | `automapmarkers` | none | `mod_id` `egocaribautomapmarkers`, 5.0.3 |
| `egocaribautomapmarkers` | `egocaribresinmapmarkers` | none | 1.0.0, file 1631 |
| `canjewelry` | `canjewelry` | none | 0.8.2, file 138875 |
| `canjewelry` | `canjewelry` | `0.2.20` | `no_file` |
| synthetic: `2.0.0-rc.2`, `2.0.0-rc.1` | its mod ID | none | `2.0.0-rc.2` |
| synthetic: `2.0.0` (no file), `1.9.0-rc.1`, `1.8.0` | its mod ID | none | `1.8.0` (stable with a file before a newer pre-release) |
| synthetic: `1.0.0-rc.2` (no file), `1.0.0-rc.1` | its mod ID | none | `1.0.0-rc.1` |
| synthetic: every release without a file | its mod ID | none | `no_file`, `release` None |
| synthetic: `1.0.0` (no file), then `1.0.0` with a file | its mod ID | `1.0.0` | the listing with a file |
| synthetic: `"fileid": 0` | its mod ID | none | `no_file` |
| `[]` | `x` | none | `mod_id` `x`, `no_file` |

Synthetic data is built in the tests (`fixtures/moddb/` holds only captured data); `_synthetic_mod` in `tests/test_mod_service.py:1984-2008` shows the shape.

### Where the function lives

`services/mod_updates.py` imports `ModApiClient` from `services/mod_api.py` (`:29-35`), so `mod_api.py` cannot import `is_prerelease` from it. The new module is a leaf (it imports only `models/moddb.py`), holds `is_prerelease` and is imported by `mod_api.py`, `mods.py` and `mod_updates.py`. This is the pattern Story 17.1 used for `ModDict` (`models/moddb.py`, re-imported by `mod_api.py`). Do not solve the cycle with an import inside a function.

### Errors

| Case | Exception | HTTP |
|---|---|---|
| Named version not among the mod ID's releases | `ModVersionNotFoundError(slug, version)` (existing) | 404 `MOD_VERSION_NOT_FOUND` |
| Named release has no file | `ModReleaseNotDownloadableError(slug, version)`: "Version '0.2.20' of mod 'canjewelry' has no downloadable file in the mod database" | 422 `MOD_RELEASE_NOT_DOWNLOADABLE` |
| No version, and no release of the mod ID has a file; or `download_release_file` called with `fileid <= 0` | `ModReleaseNotDownloadableError(slug)`: "Mod 'x' has no release with a downloadable file in the mod database" | 422 `MOD_RELEASE_NOT_DOWNLOADABLE` |

422 matches `MOD_VALIDATION_FAILED`, the existing "this release cannot be used" answer (`routers/mods.py:997-998`). The web shows `detail.message` in its failure toast for both install and version change; no web change is needed for the new code.

### Lookup (ADR-2 decisions 5 and 6)

- `install_mod_id` and `latest_version` come from one `select_install_release(slug, releases)` call with the looked-up slug, so the lookup and `download_mod` cannot disagree. The parametrized test in 3.4 guards that.
- `_compatibility_modid` keeps its installed-mod logic (Story 16.2/16.3); only the fallback changes, from `releases[0]`'s mod ID to the install mod ID. With nothing installed, looking up `instruments` now evaluates `instruments` (newest `1.2.2`, last supported game version 1.18.6) instead of `vsinstrumentsbase`.
- `latest_version` keeps the `or "unknown"` display fallback for an empty `modversion` (Story 17.1: an empty value breaks the web's select).
- API contract (`v1alpha1`): `install_mod_id` added; `latest_version` changes meaning and can be `null`; new 422 code on install and version change.

### Not changed (do not "fix" these here)

- **Which release compatibility is evaluated for** stays Epic 16 ADR-2 decision 3: the newest release of the evaluated mod ID (`services/mods.py:540-545`). For `carryon` the header and badge therefore still describe `2.0.0-rc.1` while "(Latest)" is `1.14.3`. ADR-2 changes only the default mod ID.
- **The install dialog's compatibility** is the lookup's, whatever version is selected, as today.
- `install_mod`'s already-installed check by the requested slug (`services/mods.py:1096-1101`), the archive's mod ID not being compared with the install mod ID, and locking: Story 17.3 (ADR-3).
- `ModCard`'s `installedSlugs.has(mod.slug)` (`ModCard.tsx:49`): Story 17.4.
- `evaluate_update` (`services/mod_updates.py:80-124`) can still offer a release without a file as an update; the version change is then refused with the 422 above. Changing which update is offered is not part of ADR-2.
- `normalize_release` and `StoredRelease` (`fileid: int = 0`) are unchanged.

### ADR-2 against the code

- ADR-2's line references are to `ebca566`; Story 17.1 moved them. This story cites `main` 139eef0.
- **Decision 5** ("one function ... used by both install and lookup") needs `is_prerelease`, which `mod_api.py` cannot import from `mod_updates.py`; hence the new module.
- **Decision 2** says "fileid not null". This story uses "a positive file ID" (`has_file`): `StoredRelease` stores a missing file as 0, so 0 can never mean a file, and one rule then serves install, version change and the web.
- **Decision 3** does not say what happens when the mod ID has no release with a file. Here: install is refused with `MOD_RELEASE_NOT_DOWNLOADABLE` and the lookup's `latest_version` is `null`.
- **Decision 7** does not mention that the install section posts `mod.slug` (`modidstrs[0]`) rather than the looked-up slug; the web must post `installModId`, or a page opened by another mod ID of the entry would send the wrong mod ID with the right version.
- **Decision 7** puts "(Latest)" on "the release with that version" in both dropdowns. In the installed section the list belongs to the installed mod ID, which can differ from `installModId`, and a version can repeat across mod IDs (`1.0.1`). The label is therefore shown there only when the two mod IDs are equal. On an entry page opened by one mod ID while another is installed, the installed list has no "(Latest)" label.
- **Decision 7** names the two dropdowns only; the Releases list's "Latest" badge (`ModDetailPage.tsx:749`) follows the same rule, since FR181 defines what "(Latest)" marks.
- **Duplicate versions:** the pickers show a version once, by its first listing. If that listing has no file but a later re-upload has one, the picker shows it disabled while an install by name through the API succeeds (rule 4). Not seen in mod database data; accepted.

### Existing tests that change (deliberately)

API (found by running the suite against a prototype of Tasks 2 and 3: these five fail, everything else passes):

- `tests/test_mod_service.py:2125-2132` `test_not_installed_entry_uses_the_newest_release_mod_id`: rename to `..._uses_the_install_mod_id`; `mod_version` `1.2.2`, `latest_supported_game_version` `1.18.6`, message "Last supported game version: 1.18.6.", `latest_version` `1.2.2`.
- `tests/test_mod_service.py:2134-2143` `test_installed_mod_id_decides_compatibility`: `latest_version` `1.2.2` (the compatibility assertions stay).
- `tests/test_mod_service.py:2169-2174` `test_mod_id_comparison_is_exact`: `mod_version` `1.2.2` (an installed `VSInstruments` still matches nothing; the fallback is now `instruments`).
- `tests/test_mod_service.py:1720-1739` and `tests/test_mods_router.py:634-656` `test_lookup_mod_with_null_in_every_field`: the only release has no file and an empty mod ID, so `latest_version` is `None` and `install_mod_id` is `""`.
- `tests/test_mod_models.py` (`:406`, `:435`, `:457`, `:488`, `:535`, `:580`): each `ModLookupResponse(...)` gains `install_mod_id`; the dict at `:502` too if it is validated.

Web:

- `ModDetailPage.test.tsx`: add `install_mod_id` to `mockModDetailResponse` (`:63-110`, `'smithingplus'`) and `mockMinimalResponse` (`:113-140`, `'simplemod'`); `instrumentsEntry` (`:1124-1140`) gets `install_mod_id: 'instruments'` and `latest_version: '1.2.2'` (was `'2.0.7'`). The expected options at `:1206` and `:1233` lose "(Latest)" (`['v2.0.7', 'v2.0.6 (Installed)']`, `['v1.2.7', 'v1.2.6 (Installed)']`): the installed mod ID is not the install mod ID there. `:1293-1309` ("marks latest version") asserts nothing about the label today; replace it with the tests below. `:986` and `:1085` keep "(Latest)".
- `ModCard.test.tsx`: add `installModId` to the lookup mocks (`:630-656`, `:701-727`); `:696` "uses fetched version instead of LATEST_VERSION" is renamed (the constant is gone). `ModBrowseGrid.test.tsx:284-300`: add `installModId`.
- Anything else that fails is a regression (AC 9): fix the code, not the test.

### Web tests

- `mod-ids.test.ts`: `versionChoices` filters by exact mod ID, keeps the first listing of a repeated version, marks `fileId` `null` and `0` as not installable, returns `[]` for an unknown mod ID.
- `ModDetailPage.test.tsx`, new block "Story 17.2: install picks the right release" (not installed, `mockInstalled`-style fetch mock that records `POST /api/v1alpha1/mods` bodies; the Radix Select needs the jsdom shims at `:792-797`):
  - `instrumentsEntry`: the options are exactly `['v1.2.2 (Latest)', 'v1.0.1']`; the trigger shows `v1.2.2`; Install then confirm posts `{ slug: 'instruments', version: '1.2.2' }`.
  - a carryon-shaped entry (`2.0.0-rc.1`, `1.14.3`, `latest_version: '1.14.3'`): options `['v2.0.0-rc.1', 'v1.14.3 (Latest)']`, `1.14.3` preselected; choosing `2.0.0-rc.1` posts that version; in the Releases list the "Latest" badge is on `mod-detail-release-1.14.3` and not on `2.0.0-rc.1`.
  - an entry opened at `/browse/vsinstruments` whose `slug` is `instruments` and `install_mod_id` is `vsinstruments`: the post carries `slug: 'vsinstruments'`.
  - a release with `file_id: null`: its option has `aria-disabled="true"` and the text "(no file)"; with `latest_version: null` the button is disabled and reads "No downloadable release".
  - installed section: with the installed mod ID equal to `install_mod_id`, "(Latest)" is on `latest_version` even when a newer pre-release is listed above it; a release without a file is disabled.
- `InstallConfirmDialog.test.tsx`: without `version`, the dialog shows "Version: Latest" and `mutate` is called with `{ slug, version: undefined }`; the toast uses the response's version when `onSuccess` receives one; the existing test at `:295-327` (no response argument) passes unchanged.
- `ModCard.test.tsx`: with details loaded, `mutate` gets `{ slug: <installModId>, version: <latestVersion> }` (use an `installModId` different from the card's slug); when the details fail (`:673`), `{ slug: 'carrycapacity', version: undefined }` and the dialog shows "Version: Latest". `api/mods.test.ts`: `installMod('x')` sends a body without a `version` key.

### E2E spec

`web/e2e/mod-install-release.spec.ts`, in the style of `e2e/installed-mod-any-modid.spec.ts` (init script for `localStorage.apiKey`, `fakeInstalledMods`, live lookups served to the page from one probed response) and `e2e/mod-detail-bad-data.spec.ts`. Expected versions are computed from the probed lookup response, never hard-coded, because the mod database changes: `expectedDefault(releases, modId)` is the first release with that `modidstr`, a positive `file_id` and no `-` in `version`, else the first with a positive `file_id`.

1. **Lookup (API only):** for `carryon` and `instruments`, `install_mod_id` equals the slug and `latest_version` equals `expectedDefault`.
2. **Detail page, install stubbed:** with `fakeInstalledMods(page, [])` and the probed lookup, open `/game-server/mods/browse/carryon`; the trigger shows `v<latest>`; every option's test ID is `mod-detail-version-option-<version>` for a version of `carryon`; exactly one option contains "(Latest)" and it is `<latest>`. Route `POST /api/v1alpha1/mods` (method check as in `fakeInstalledMods`) to capture the body and fulfill `{ status: 'ok', data: { slug, version, filename: 'stub.zip', compatibility: 'compatible', pending_restart: false } }`; click Install, confirm; the captured body is `{ slug: 'carryon', version: <latest> }`.
3. **Instruments detail page:** the options are exactly the `instruments` versions; none belongs only to `vsinstrumentsbase`.
4. **Browse card, install stubbed:** open a search that shows `mod-card-carryon` (for example `?q=carry+on`), click `mod-card-install-carryon`; `install-dialog-mod-version` shows `<latest>`; confirm; the captured body is `{ slug: 'carryon', version: <latest> }`.
5. **Refused installs (real API, nothing can be installed when the story works):** `POST /mods` with `{ slug: 'instruments', version: <a version only vsinstrumentsbase has> }` → 404 `MOD_VERSION_NOT_FOUND`; with `{ slug: 'canjewelry', version: <a version whose file_id is null> }` → 422 `MOD_RELEASE_NOT_DOWNLOADABLE` (skip with a message if the live entry no longer has such a release).
6. **One real install:** `POST /mods { slug: 'carryon' }` → 200, `data.slug` `carryon`, `data.version` equals `<latest>`; `GET /mods` lists it; then `DELETE /mods/carryon`.

**The dev stack must end as it started.** `beforeAll` reads `GET /mods` and skips the spec's real-API tests (5 and 6) with a clear message if `carryon`, `canjewelry`, `instruments`, `vsinstruments` or `vsinstrumentsbase` is already installed. `afterEach` deletes any of those five that is installed and was not in the `beforeAll` snapshot, so a red run (the bug installing the wrong mod) is cleaned up too. Run tests 5 and 6 serially (`test.describe.configure({ mode: 'serial' })`); the config is `fullyParallel`. Wait for specific responses and DOM markers, never `networkidle` or fixed delays; allow 60 s for the real download. If the game server is running, test 6 leaves the pending-restart notice set; it clears on the next server restart and is not a failure.

### Manual check

Docker stack (`just docker restart`, http://localhost:8080). Note the Installed list before starting.

1. Browser, search "carry on": Install on the card; the dialog names the newest stable version, not a pre-release; install; the Installed tab shows Carry On at that version. Remove it.
2. Carry On detail page: the version list holds only Carry On releases, "(Latest)" is on the newest stable one and it is preselected, pre-releases are selectable; the Releases list's "Latest" badge is on the same release. Install the preselected version; verify; remove it.
3. Instruments detail page: the version list holds only `instruments` releases. Install nothing.
4. C&N Jewelry detail page: v0.2.20 is listed disabled with "(no file)". Install nothing.
5. Browser console clean. The Installed list and `data/serverdata/Mods` are as before (a pending-restart notice from the installs may remain until the server restarts).

Manual test tasks need the user's confirmation before they are marked complete (`project-context.md`).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/mod/{slug}` and `https://mods.vintagestory.at/download` (match `params={"fileid": ...}` as `tests/test_mod_version_change.py:249` does, and assert `route.called` is false where nothing may be downloaded). Load fixtures as `tests/test_mod_api.py:28` (`FIXTURES`) and `tests/test_mod_service.py:1979-1981` (`_fixture_mod`) do. Install tests need a zip with a `modinfo.json` (`create_mod_zip_bytes`, `tests/test_mods_router.py:39-44`).
- Between Task 2 and Task 4 the branch is internally inconsistent for multi-ID entries (the API selects correctly while the web still posts `releases[0]`'s version). Every commit is green; the E2E and manual checks run only after Task 4.
- E2E is not part of `just check`.

### Security Requirements

- No new endpoint. The install and version change routes stay Admin-only; lookup stays readable by Monitor. The requested slug is validated by `validate_slug` in `get_mod` before any selection; `safe_release_filename` still guards every download filename. The file ID sent to the download endpoint is now always a positive integer from the mod database.

### Development Commands

- `just test-api tests/test_mod_release_selection.py`, `just test-api tests/test_mod_api.py tests/test_mod_service.py tests/test_mods_router.py tests/test_mod_models.py`, `just test-api tests/test_mod_version_change.py tests/test_mod_version_change_router.py tests/test_mod_update_all.py tests/test_mod_updates.py tests/test_mod_compatibility.py`, `just test-web src/lib/mod-ids.test.ts src/features/mods/ModDetailPage.test.tsx src/components/ModCard.test.tsx src/components/InstallConfirmDialog.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/mod-install-release.spec.ts`.

### Previous Story Intelligence

- **17.1:** `get_mod` returns a normalized entry, so read `r["modidstr"]`, `r["modversion"]`, `r["fileid"]` directly; `fileid` is `int | None`. `ModRelease.file_id` / `fileId` are already nullable. Its Task 2 had to absorb a test change planned for Task 3 because the cause landed earlier: keep each commit green and move a test change to the commit that causes it. pyright is strict; baseline is 0 errors and 3 pre-existing warnings in tests. Review finding L1 is this story's AC 5.
- **16.2 / 16.3:** `findInstalledModForEntry` and `_compatibility_modid` decide which installed mod an entry page is about; mod IDs are compared exactly. `instrumentsEntry` in `ModDetailPage.test.tsx` is the multi-ID mock to reuse.
- **16.1:** E2E waits for responses and DOM markers. `main.tsx` renders under StrictMode; `just lint-web` is `tsc --noEmit`.
- **14.x:** release order, not version comparison, decides "newer" (Epic 14 ADR-1); a re-uploaded version keeps its first listing.

### Git Intelligence

- Recent commits are Story 17.1's (`c7127ab` to `86d463a`, merged as 139eef0). Planned types: Task 1 `refactor` (function not yet used), Task 2 `fix` (Install picks the newest stable release of the mod you chose; releases without a file are refused with a clear message), Task 3 `fix` (mod details report the release Install will pick), Task 4 `fix` (version lists and "(Latest)" match what Install picks), Task 5 `test`, Task 6 `docs`.

### Latest Technical Information

- No new libraries. Radix `Select.Item` takes `disabled`; the option then has `aria-disabled="true"` and `data-disabled`, already styled in `web/src/components/ui/select.tsx:110`. TanStack Query v5 passes the mutation result as the first argument of a `mutate` call's `onSuccess`. `JSON.stringify` omits a key whose value is `undefined`, so `installMod(slug)` (`web/src/api/mods.ts:67-75`) already sends no `version`.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/mod_release_selection.py`, `api/tests/test_mod_release_selection.py`, `web/e2e/mod-install-release.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mod_api.py`, `services/mods.py`, `services/mod_updates.py`, `routers/mods.py`, `models/mods.py`, `models/errors.py`; `web/src/api/types.ts`, `web/src/lib/mod-ids.ts`, `web/src/features/mods/ModDetailPage.tsx`, `web/src/components/ModCard.tsx`, `web/src/components/InstallConfirmDialog.tsx` (+ the tests named in the tasks). No fixture is added or changed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.2: Install Picks the Right Release]
- [Source: _bmad-output/planning-artifacts/prd.md] FR179, FR180, FR181
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-2: Release Selection for Install]; ADR-1 decision 4 (stored `fileid` 0); ADR-3 (Story 17.3, out of scope)
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md#ADR-1: Detect Updates by Release Order]
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-2: Most Recent Supported Game Version] (decisions 2 and 3)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md]
- [Source: _bmad-output/implementation-artifacts/17-1-mod-detail-pages-cannot-fail-on-bad-data.md] (Senior Developer Review, L1)
- [Source: api/tests/fixtures/moddb/README.md]
- Beads: `VSS-jhf`, `VSS-43b`, parent `VSS-4v5`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Baseline before Task 1: `just test-api` passed; `just typecheck-api` 0 errors, 3 warnings (pre-existing, in tests).

### Completion Notes List

- Task 1: `services/mod_release_selection.py` holds `is_prerelease` (moved from `mod_updates.py`, which now imports it, so every existing import keeps working), `has_file`, the frozen `InstallSelection` and `select_install_release`. The file ID is narrowed with `isinstance` (a `bool` is not a file ID), so `file_id` is a real `int`. Red first: the new test file failed at collection (module missing). 27 new tests (every row of "Selection test cases", `has_file`, the `is_prerelease` re-export and an input-not-mutated check). `just test-api` 2429 passed; pyright 0 errors, the same 3 warnings.
- Task 2: `download_mod` calls `select_install_release`; `version_not_found` raises `ModVersionNotFoundError`, and a selection without a release or file ID raises `ModReleaseNotDownloadableError(slug, version)`, which also narrows `file_id` to `int` for `download_release_file` with no `cast`. The debug event is now `selected_install_release` (slug, mod ID, version, requested version), replacing the two old events; nothing referenced them. The empty-releases `ModNotFoundError` check is kept, so a mod with no releases is still 404 `MOD_NOT_FOUND`. `download_release_file` refuses `fileid <= 0` first. `_prepare_version_change` refuses `target.fileid <= 0` right after the target is resolved. Router: 422 `MOD_RELEASE_NOT_DOWNLOADABLE` on install and version change. Red first: `test_mod_api.py`, `test_mod_version_change.py`, `test_mod_update_all.py` failed to import the new error; 5 service/router tests failed on behavior (instruments installed `vsinstrumentsbase` 2.0.7, carryon installed `2.0.0-rc.1`, instruments `2.0.7` installed, canjewelry `0.2.20` gave 502, the version change gave 409 confirmation). `carryon` + `latest` already returned 404, as the Dev Notes say; the test pins it. No existing test changed in this task. `just test-api` 2450 passed; pyright 0 errors, 3 warnings.
- Task 3: `ModLookupResponse` gains required `install_mod_id`; `latest_version` is `str | None`. `lookup_mod` calls `select_install_release(slug, releases)` once after the empty-releases check; `latest_version` keeps the `or "unknown"` display fallback; `_compatibility_modid(slug, releases, default)` takes the install mod ID as its fallback (the old `releases[0]` read is gone). Which release compatibility is evaluated for is unchanged (carryon's `compatibility.mod_version` stays `2.0.0-rc.1`, pinned by a test). Red first: the 5 "Existing tests that change" were updated to their new values and failed with the new tests (19 failures in `test_mod_service.py` alone); everything else passed unchanged, as the Dev Notes predicted. The parametrized "lookup equals download" test covers 8 slugs over 5 fixtures (including `playercorpse` and both automapmarkers mod IDs). `test_mod_models.py` also checks that `install_mod_id` is required. `just test-api` 2473 passed; pyright 0 errors, 3 warnings.
- Task 4: `ModLookupData` has `installModId` and `latestVersion: string | null`. `versionChoices(releases, modId)` in `lib/mod-ids.ts` (exact mod ID, first listing of a version, `installable` for a positive `fileId`) builds both version lists. `InstallSection` gets `slug={mod.installModId}`, labels "(Latest)" on `latestVersion`, lists a release without a file as a disabled item with " (no file)", and with `latestVersion` null shows a disabled "No downloadable release" button (the Select then has value `''`, its placeholder). `InstalledVersionSection` takes `installModId` and `latestVersion`; "(Latest)" only when the installed mod ID is the install mod ID. The Releases list's "Latest" badge is on the first release with `modidstr === installModId && version === latestVersion`. `InstallConfirmDialog`: `version?: string | null`, "Version: Latest" when unset, sends `version: undefined`, and the toast names `response?.data.version ?? mod.version ?? 'Latest'` (the last fallback is mine, so a toast never reads "Version undefined" when the mutation resolves without data, as the existing test at `:295` does). `ModCard`: `LATEST_VERSION` removed; sends `installModId ?? mod.slug` and `latestVersion`. Red first: 18 new or changed tests failed (4 `versionChoices`, 2 card, 3 dialog, 9 detail page including the two instruments installed-list expectations). Beyond the tests the Dev Notes list, `installModId` was also added to the `use-mod-detail`-shaped mock at `ModCard.test.tsx:524`/`:572` and to `mods.test.ts`'s typed `mockLookupResponse`, which `tsc` needs now that the field is required. `just test-web` 3155 passed, 4 skipped; `tsc` clean.
- Task 5: `web/e2e/mod-install-release.spec.ts` as in Dev Notes "E2E spec": four UI and lookup tests (installed list and `POST /mods` stubbed, lookups served from one probed response, expected versions computed with `expectedDefault`) and two real-API tests in a serial describe with a `beforeAll` snapshot and an `afterEach` cleanup of the five mod IDs. In a real browser the Select trigger shows the whole item text, so test 2 expects `v<latest> (Latest)` on the trigger. `just docker restart` rebuilt the stack from this branch (the game server was installed, not running, and was not started or stopped). `bunx playwright test e2e/mod-install-release.spec.ts e2e/installed-mod-any-modid.spec.ts e2e/mod-detail-bad-data.spec.ts` with the admin key from `.env`: 10 passed, 1 skipped; then `mod-install-release.spec.ts --repeat-each=3`: 15 passed, 3 skipped.
- Task 5 deviation (dev stack state): Carry On (`2.0.0-rc.1`) was already installed on the dev stack, so it could not be installed and removed without touching an existing install. (a) The skip condition is per test, on the mods that test touches, instead of the story's "skip 5 and 6 if any of the five is installed": test 5 (instruments, vsinstrumentsbase, canjewelry) ran and passed against the real API; test 6 (real `carryon` install) was skipped with "carryon is already installed on this stack". (b) Manual steps 1 and 2 were done with Instruments in place of Carry On for the real installs, since Instruments also exercises AC 1 and was not installed.
- Task 5.3 manual check (Docker stack, an agent-driven browser tab, no screenshots kept): Browse "carry on": the Carry On card shows Installed (already installed). Carry On detail page (installed section, installed mod ID = install mod ID): indicator "Installed: v2.0.0-rc.1"; the list holds only `carryon` releases, `v2.0.0-rc.1 (Installed)` then `v1.14.3 (Latest)` then the `2.0.0-pre.*` pre-releases; the Releases list's "Latest" badge is on 1.14.3 only. Instruments detail page: 19 options, all `instruments` versions (1.2.2 to 1.0.1, none from `vsinstruments`/`vsinstrumentsbase`), `v1.2.2 (Latest)` preselected, button "Install v1.2.2", "Latest" badge on 1.2.2; Install, dialog "Version: 1.2.2", confirm: the Installed tab listed Instruments `instruments` v1.2.2 (`instruments_1.2.2.zip`); removed. Browse "instruments", card Install: dialog "Version: 1.2.2"; confirm: the card shows Installed and the API lists `instruments` 1.2.2; removed. C&N Jewelry: 179 options, `v0.8.2 (Latest)` preselected, `v0.2.20 (no file)`, `v0.1.26 (no file)`, `v0.2.0 (no file)` disabled; nothing installed. Browser console: no entries. Afterwards the SHA-1 of every file in `data/serverdata/Mods` and `data/vsmanager/state` matched the snapshot taken before Task 5, the API lists the same five mods, no pending restart, game server still installed and not running. The maintainer's own hand check is left open in the PR.
- Story created 2026-11-15: context analysis of `download_mod`, `download_release_file`, `lookup_mod`, `_compatibility_modid`, the version change path, the detail page's two version lists, the browse card and the install dialog, the mod database fixtures, Story 17.1 and its review, and Epic 17 ADR-2. The API tests that change were found by running the suite against a throwaway prototype of the selection and lookup change.

### File List

- `api/src/vintagestory_api/services/mod_release_selection.py` (new)
- `api/src/vintagestory_api/services/mod_updates.py`
- `api/tests/test_mod_release_selection.py` (new)
- `api/src/vintagestory_api/services/mod_api.py`
- `api/src/vintagestory_api/services/mods.py`
- `api/src/vintagestory_api/routers/mods.py`
- `api/src/vintagestory_api/models/errors.py`
- `api/tests/test_mod_api.py`
- `api/tests/test_mod_service.py`
- `api/tests/test_mods_router.py`
- `api/tests/test_mod_version_change.py`
- `api/tests/test_mod_version_change_router.py`
- `api/tests/test_mod_update_all.py`
- `api/src/vintagestory_api/models/mods.py`
- `api/tests/test_mod_models.py`
- `web/src/api/types.ts`
- `web/src/api/mods.test.ts`
- `web/src/lib/mod-ids.ts`
- `web/src/lib/mod-ids.test.ts`
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `web/src/components/InstallConfirmDialog.tsx`
- `web/src/components/InstallConfirmDialog.test.tsx`
- `web/src/components/ModCard.tsx`
- `web/src/components/ModCard.test.tsx`
- `web/src/components/ModBrowseGrid.test.tsx`
- `web/e2e/mod-install-release.spec.ts` (new)

## Change Log

- 2026-11-15: Story 17.2 created (ready-for-dev).
