# Story 17.4: Installed Status Is Right Everywhere

Status: ready-for-dev

<!-- Implements FR184-FR185. Beads: VSS-49n, VSS-br2. Branch story/17-4-installed-status-is-right-everywhere, stacked on story/17-3-mod-operations-are-safe-against-each-other (affef98, PR #158 open, itself stacked on PR #157; neither merged). Line references are to affef98. Not in scope: VSS-4f3 ("has a release for your game version" on cards), VSS-z7e (filename collision on install). No ADR in Epic 17 governs this story (the Epic 17 ADR file and the 2026-11-15 change proposal both say so); it builds on Epic 16 ADR-2 decision 2 / Story 16.2 (an installed mod belongs to an entry by any of its mod IDs) and Epic 14 ADR-4 (update status is computed from stored mod database data). No new dependencies. -->

## Story

As an **administrator**,
I want **a mod I have installed to show as installed, with its update status, wherever I see it**,
so that **I do not install a mod twice or wonder whether a new mod is up to date**.

## Acceptance Criteria

1. **Given** the browse API (`GET /api/v1alpha1/mods/browse`)
   **When** it returns a mod
   **Then** the item has `mod_ids`: every mod ID of the entry, taken from the listing's `modidstrs` in listing order, each once, without empty strings, and without any request per mod; an entry with no mod IDs has `mod_ids: []`; `slug` is unchanged (`modidstrs[0]`, or the existing fallback)
   *(Covers FR184; `VSS-49n`)*

2. **Given** a mod database entry with several mod IDs (Instruments: `instruments`, `vsinstruments`, `vsinstrumentsbase`) and an installed mod whose ID is one of them but not the first
   **When** I see the entry's card in the mod browser
   **Then** the card shows Installed and no Install button, as the entry's detail page does since Story 16.2
   *(Covers FR184; `VSS-49n`)*

3. **Given** an installed mod whose ID differs from one of the entry's mod IDs only in case (`VSInstrumentsBase` installed, entry lists `vsinstrumentsbase`)
   **When** I see the entry's card or its detail page
   **Then** both show it installed. Card and detail page use the same helper (`web/src/lib/mod-ids.ts`), so they cannot disagree
   *(Covers FR184; consistent with Story 17.3's case-insensitive installed check)*

4. **Given** I have just installed a mod (`POST /api/v1alpha1/mods` returned 200)
   **When** I open the Installed list without running an update check
   **Then** its Available column shows a real status ("Up to date", an offered update, or "No compatible update") computed from the mod database data the install already fetched; the install makes no extra mod database request for it
   *(Covers FR185; `VSS-br2`)*

5. **Given** storing the update record after an install fails (the record cannot be built, or the store file cannot be written)
   **When** the install itself succeeded
   **Then** the install still returns 200 with the same body as today, and the failure is logged as a warning
   *(Covers FR185)*

6. **Given** an update check is running while a mod is installed
   **When** the check finishes
   **Then** the new mod's record (stored by the install) is kept, not pruned as "no longer installed"
   *(Covers FR185)*

7. **Given** an installed mod with no stored update data (reason `not_checked`, for example one found on disk at startup)
   **When** I open the Installed list, on a desktop (table) or a phone (cards)
   **Then** its Available column shows "Not checked yet", not "Unknown". Every other unknown reason still shows "Unknown"
   *(Covers FR185)*

8. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.4/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [ ] Task 1: Browse items list every mod ID of the entry + tests (AC: 1, 8)
  - [ ] 1.1: `api/src/vintagestory_api/models/mods.py` `ModBrowseItem` (`:312-369`): add `mod_ids: list[str] = []` directly after `slug` (`:319-324`), docstring: every mod ID of the mod database entry (the listing's `modidstrs`), in listing order, each once; `slug` is the first; used by the web to recognize an installed mod by any of them (Story 17.4). Careful: `ModLookupResponse` (`:193`) has the same `slug`/`urlalias` docstrings; the field goes in `ModBrowseItem` only (the prototype put it in the wrong class first)
  - [ ] 1.2: `routers/mods.py` `_api_mod_to_browse_item` (`:197-228`): `mod_ids=list(dict.fromkeys(m for m in modidstrs if m))` (reuse the `modidstrs` local at `:209`). `_as_str_list` (`models/moddb.py:58-64`) already drops non-strings but keeps empty strings, hence the filter
  - [ ] 1.3: Tests. `tests/test_mods_router.py` `TestBrowseItemSlugUrlalias` (`:2560`): an item with `modidstrs: ["instruments", "vsinstruments", "vsinstrumentsbase"]` has `mod_ids` equal to that list; `["a", "", "a", "b"]` gives `["a", "b"]`; `[]` gives `[]` with the existing slug fallback. `tests/test_mod_models.py` `TestModBrowseItem`: default `[]`. Update the two exact-dict tests in "Existing tests that change"

- [ ] Task 2: Browse cards recognize any installed mod ID, ignoring case + tests (AC: 2, 3, 8)
  - [ ] 2.1: `web/src/api/types.ts` `ModBrowseItem` (`:378-395`): `modIds: string[]` after `slug`, with a doc comment (every mod ID of the entry, `slug` first). Required, not optional: the API always sends it. Careful: `ModLookupData` above it has the same `slug`/`urlalias` lines
  - [ ] 2.2: `web/src/lib/mod-ids.ts`: add `findInstalledModByIds<T extends { slug: string }>(installedMods: readonly T[] | undefined, modIds: readonly string[]): T | undefined` (Dev Notes "The helper"); `findInstalledModForEntry` (`:35-54`) becomes `findInstalledModByIds(installedMods, [entry.slug, ...entryModIds(entry.releases)])`, keeping its doc and preference order. Update the module comment (`:9`, "compared exactly") and `findInstalledModForEntry`'s doc: installed mod IDs are matched without case, as Story 17.3's install check does; `entryModIds` and `versionChoices` stay exact
  - [ ] 2.3: `web/src/components/ModCard.tsx`: prop `installedSlugs?: Set<string>` (`:29-30`) becomes `installedMods?: readonly { slug: string }[]` ("installed mods, their `slug` is the mod ID; omit to hide the install footer"); `isInstalled` (`:47`) is `findInstalledModByIds(installedMods, [mod.slug, ...mod.modIds]) !== undefined`; the footer condition (`:190`) is `installedMods !== undefined`. Add "Story 17.4" to the header comment. `ModBrowseGrid.tsx` (`:24`, `:70`, `:106`): same rename and type. `features/mods/BrowseTab.tsx` (`:82-87`): `const installedMods = useMemo(() => modsData?.data?.mods ?? [], [modsData]);` passed at `:287`. An empty array while the list loads keeps today's behavior (Install button shown until the list arrives)
  - [ ] 2.4: Tests (Dev Notes "Web tests", Task 2 rows) and the changes in "Existing tests that change" that belong to Task 2

- [ ] Task 3: Install stores the new mod's update record + tests (AC: 4, 5, 6, 8)
  - [ ] 3.1: `services/mod_api.py` `ResolvedInstall` (`:60-77`): add `releases: list[ReleaseDict]` ("every release of the mod database entry, newest first, as `get_mod` returned them; Story 17.4 stores them as the new mod's update record"), required, no default. `resolve_install` (`:473-479`) passes the `releases` local (`:454`)
  - [ ] 3.2: `services/mods.py`: `InstallResult` (`:221-241`) gains `releases: list[ReleaseDict]` (same docstring idea; it is an internal dataclass, not the response model). `install_mod` (`:1206`) passes `resolved.releases` to `_place_install` (`:1228`), which gains a `releases: list[ReleaseDict]` parameter and sets it on the `InstallResult` (`:1316-1323`). Nothing else in the install flow changes; the lock, the checks and their order stay exactly as Story 17.3 left them
  - [ ] 3.3: `services/mod_updates.py` `ModUpdateService`: new public method `record_install(self, modid: str, releases: list[ReleaseDict]) -> None` (Dev Notes "Recording after install"), placed after `get_status` (`:344-346`). It never raises
  - [ ] 3.4: `services/mod_updates.py` `check` (`:418-450`): prune against the installed list as it is at the end of the check, not the list read at the start: `self._store.prune({mod.slug for mod in self._mod_source.list_mods()})` at `:437` (AC 6, Dev Notes "Check and install at the same time"). Update the docstring sentence "Records for mods that are no longer installed are removed" to say "when the check ends"
  - [ ] 3.5: `routers/mods.py` `install_mod` (`:663-668`): add `update_service: ModUpdateService = Depends(get_mod_update_service)` (both names are already imported, `:34-35`); after `result = await service.install_mod(...)` (`:698`) call `update_service.record_install(result.slug, result.releases)`. The response body (`:706-715`) is unchanged; `releases` is not added to it. Docstring: one sentence that the new mod's update status is stored from the install's lookup
  - [ ] 3.6: Tests (Dev Notes "API tests"), including the dependency overrides in "Existing tests that change" so no router test reaches the real `get_mod_update_service` singleton

- [ ] Task 4: "Not checked yet" for a mod without update data + tests (AC: 7, 8)
  - [ ] 4.1: `web/src/components/ModUpdateCell.tsx` `case 'unknown'` (`:101-111`): label `status.reason === 'not_checked' ? 'Not checked yet' : 'Unknown'`. The `not_checked` tooltip (`:13`) becomes `'Use "Check for updates" to look it up now.'` (the label already says "Not checked yet"); the error suffix (`withError`, `:32-34`) is unchanged. Header comment (`:4-5`): list "Not checked yet" among the labels
  - [ ] 4.2: Tests (Dev Notes "Web tests", Task 4 rows). `InstalledModCard` (phones, `components/InstalledModCard.tsx:73`) and `ModTable` (desktop, `components/ModTable.tsx:281`) both render `ModUpdateCell`, so there is one source change; one test per surface pins it

- [ ] Task 5: E2E against the Docker dev stack (AC: 2, 4, 7)
  - [ ] 5.1: New `web/e2e/installed-status.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/installed-status.spec.ts` and the admin key from `.env` (`just test-e2e-web` stops the stack afterwards). Also re-run `e2e/installed-mod-any-modid.spec.ts`, `e2e/mod-install-release.spec.ts` and `e2e/installed-mods-phone.spec.ts`
  - [ ] 5.2: The dev stack ends with the same installed mods it started with (Dev Notes "E2E", cleanup rules); record the before/after comparison in the Dev Agent Record

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast`; after `just test-api`, `git status --short` shows nothing under `dev/` (no `dev/vsmanager/state/mod-updates.json`)
  - [ ] 6.2: Story status `review`, `just sprint set 17-4-installed-status-is-right-everywhere review`, PR (base `story/17-3-mod-operations-are-safe-against-each-other` while PR #158 is open, otherwise `main`), PR link on `VSS-49n` and `VSS-br2`. The PR description names the API addition (`mod_ids` on browse items)

## Dev Notes

### The bugs (verified on this branch, affef98)

- **Browse cards (`VSS-49n`).** `BrowseTab` builds a `Set` of installed mod IDs (`features/mods/BrowseTab.tsx:82-87`) and `ModCard` checks only the browse slug: `installedSlugs?.has(mod.slug)` (`components/ModCard.tsx:47`; the bead's `:49` is stale). The browse slug is `modidstrs[0]` (`routers/mods.py:209-210`), and `ModBrowseItem` carries nothing else (`models/mods.py:312-369`). With `vsinstrumentsbase` installed, the Instruments card offers Install while its detail page shows the installed section (`features/mods/ModDetailPage.tsx:550-553`, `:720-741`, via `findInstalledModForEntry`). The listing items already hold every mod ID, normalized (`models/moddb.py:99`, `"modidstrs": _as_str_list`).
- **Update status after install (`VSS-br2`).** The Installed list's Available column comes from `GET /mods/updates`, computed by `build_status_items` (`services/mod_updates.py:217-241`) from the stored records only. A mod with no record gets `unknown` / `not_checked` (`:224-226`), which `ModUpdateCell` labels "Unknown" (`components/ModUpdateCell.tsx:101-111`). Only `check()` (`:418-450`) writes records, so a mod installed after the last check stays "Unknown" until the next scheduled check or a manual "Check for updates". Yet the install has just fetched the whole entry: `resolve_install` calls `get_mod` (`services/mod_api.py:450`) and holds `mod["releases"]` (`:454`), then keeps only the selected release in `ResolvedInstall` (`:473-479`).

### The helper (`web/src/lib/mod-ids.ts`)

```ts
/**
 * The installed mod whose ID is one of `modIds`, compared without case. Earlier IDs
 * win: the first of `modIds` that matches an installed mod decides.
 */
export function findInstalledModByIds<T extends { slug: string }>(
  installedMods: readonly T[] | undefined,
  modIds: readonly string[]
): T | undefined {
  if (!installedMods || installedMods.length === 0) return undefined;
  for (const modId of modIds) {
    const key = modId.toLowerCase();
    const match = installedMods.find((mod) => mod.slug.toLowerCase() === key);
    if (match) return match;
  }
  return undefined;
}
```

- **One helper, two callers.** The detail page keeps calling `findInstalledModForEntry` (`[entry.slug, ...entryModIds(entry.releases)]`), the card calls `findInstalledModByIds` with `[mod.slug, ...mod.modIds]`. Both lists hold the same IDs (the listing's `modidstrs` and the lookup's release `modidstr`s are the same entry); the order differs (listing order vs. newest release first), which only matters when two of an entry's mod IDs are installed, and then the card only needs a yes/no.
- **Case.** Story 17.3's review (M1) made install refuse a mod ID installed in another case (`services/mods.py` `_refuse_if_installed`, lowercased lock key). If the UI matched exactly, a card for `vsinstrumentsbase` with `VSInstrumentsBase` installed would offer Install and the API would answer 409 `MOD_ALREADY_INSTALLED`. Matching without case makes the UI agree with the API. This changes the detail page too (the existing test "compares mod IDs exactly", `mod-ids.test.ts:72-74`, flips; see "Existing tests that change"). `versionChoices` and `entryModIds` stay exact: they select releases by `modidstr`, as the update check and version change API do (`evaluate_update`, `services/mod_updates.py:94`).
- **Why the prop changes from a `Set` to the installed mods.** Reusing the helper means passing what it takes; a `Set` of slugs would need either a second, set-based matcher or lowercased keys whose contract lives only in a comment. `ModCard` and `ModBrowseGrid` are used only by `BrowseTab` (`rg -n "installedSlugs" web/src` lists only these three files and their tests).

### Card install action when another mod ID is installed (decision)

The card shows Installed and no Install button whenever any of the entry's mod IDs is installed. This matches the detail page since Story 16.2, which then shows the installed mod's version section (`InstalledVersionSection` for `installedMod.slug`) instead of the install section (`ModDetailPage.tsx:720-741`). So from the UI an admin cannot install a second mod ID of an entry that already has one installed; that is today's detail-page behavior and is not changed here. The API still accepts such an install (Story 17.3 table: `instruments` proceeds while `vsinstrumentsbase` is installed). If that UI limit ever matters, it is a new story for both views together.

### Recording after install (`VSS-br2`)

```python
def record_install(self, modid: str, releases: list[ReleaseDict]) -> None:
    """Store a newly installed mod's releases from the install's lookup (Story 17.4).

    The install has just fetched the whole mod database entry, so the Installed list
    can show the new mod's status without waiting for the next check, and without a
    second request. Never raises: a failure is logged and leaves the mod `not_checked`
    (or, if only the save failed, the record lives in memory until restart, as in `check`).
    """
    try:
        record = StoredModRecord(
            checked_at=datetime.now(UTC),
            found=True,
            releases=[StoredRelease.from_api(r) for r in releases],
        )
        self._store.set(modid, record)
        self._store.clear_lookup_error(modid)
        self._store.save()
    except (OSError, ValueError, TypeError) as e:
        logger.warning("mod_update_record_after_install_failed", slug=modid, error=str(e))
```

- **Where it runs: the router, through the existing dependency.** `ModUpdateService` already depends on `ModService` (`get_mod_update_service`, `services/mod_updates.py:536-548`, passes `get_mod_service()` as `mod_source`); the reverse dependency would be a cycle, and a second `ModUpdateStore` would be wrong: each store holds the file in memory (`_load` at construction, `:131-133`), so a record written through another instance would be overwritten by the singleton's next `save()`. The router already injects both services for Update All (`routers/mods.py:149-153`). `install_mod` stays free of update logic.
- **Key: `result.slug`.** `InstallResult.slug` is `metadata.modid` (`services/mods.py:1318`), the mod ID as stored in the state, which is what `build_status_items` looks up (`store.get(mod.slug)`, `:223`). The requested slug can differ (`automapmarkers` installs `egocaribautomapmarkers`).
- **Same record as a check.** `_check_one` stores `_record_from_payload(get_mod(slug))` (`:481-514`): `found=True`, every release through `StoredRelease.from_api`, `clear_lookup_error`. The install's `releases` are the same normalized list from the same `get_mod`, looked up by the requested slug, which returns the same entry as a lookup by the installed mod ID. Reuse is deliberate: do not call `_record_from_payload` with a fake dict, and do not add a lookup.
- **Errors caught.** `StoredRelease.from_api` raises `TypeError` for a non-object (cannot happen for normalized data) and pydantic `ValidationError` (a `ValueError`); `save()` raises `OSError`, or `ValueError` when pydantic cannot serialize (the same tuple `check` catches at `:440-447`). Anything else is a bug and is not swallowed.
- **Install still succeeds** (AC 5): the call comes after `install_mod` returned, `record_install` cannot raise those errors, and the response is built from `result` as before.
- **Status values.** `evaluate_update` compares `modidstr` with the installed mod ID exactly (`:94`). A mod whose archive spells its ID differently from the mod database (state `Demo`, releases `demo`) gets `unknown` / `installed_release_not_listed`, exactly as it does after a check today. Not changed here.
- **Web.** `useInstallMod` invalidates `queryKeys.mods.all` (`['mods']`, `hooks/use-mods.ts:94-97`), which covers `queryKeys.mods.updateStatus` (`['mods', '@updates']`, `api/query-keys.ts:40`), so the Installed list refetches the status after an install. No web change for AC 4; one hook test pins the invalidation.

### Check and install at the same time (AC 6)

`check()` reads the installed list once (`:431`), awaits one lookup per mod, then prunes every record whose mod ID is not in that list (`:437`). An install that finishes during those awaits stores its record, and the old prune would delete it, leaving "Not checked yet" until the following check. Pruning against `self._mod_source.list_mods()` at the end keeps it. A mod removed during the check is still pruned. No lock is added: `record_install` is synchronous and the store is in memory, so it cannot interleave with a `set` or `prune` in `check`.

### Remove and version change (checked; not changed)

- **Remove** (`remove_mod`) leaves the mod's record in the store. Nothing shows it: `build_status_items` iterates installed mods only, and the next check prunes it. If the mod is installed again, Task 3 overwrites the record with fresh data. No stale or wrong status results; not changed.
- **Version change / Update All** keep the record. Status is computed at read time against the installed version (Epic 14 ADR-4), so moving to any release that is in the stored list shows the right status at once. Update All only applies offers computed from that list. The one gap: from the detail page an admin can pick a release published after the last check; the stored list then lacks the installed version, and the status is `unknown` / `installed_release_not_listed` until the next check. Storing the version change's lookup (`_prepare_version_change`, `services/mods.py:1071-1075`) would close it, but `VersionChangeResult` is serialized whole into the API response (`asdict(result)`, `routers/mods.py:1068`), so it needs its own design; it is outside FR185 ("a newly installed mod") and is left as a follow-up for the maintainer to file (no bead created by this story).

### Browse payload size (decision)

`GET /mods/browse` is paginated (`page_size` 1-100, default 20; `routers/mods.py:240-243`), and `mod_ids` is added per returned item only; the full listing stays in the API's memory as today. Most entries have one mod ID (about 367 of several thousand have more), so an item grows by about `"mod_ids":["<its slug>"],` (around 20-40 bytes): roughly 0.5-1 KB on a default page and at most a few KB at 100 items. Acceptable; no option to omit it.

### API tests

- `tests/test_mod_updates.py` (reuse `make_service` `:323-332`, `installed` `:197`; `fixture_releases` `:31` returns `StoredRelease`s, so load the raw `mod_carryon.json` and pass `normalize_mod(...)["releases"]`, which is what `get_mod` hands the install): `record_install("carryon", releases)` with `carryon` installed at `1.14.1` makes `get_status()` report `update_available` offering `1.14.3` (as `test_check_stores_found_and_missing_mods`, `:337-355`, does after a check), `checked_at` set, the record persisted (`ModUpdateStore(tmp_path / "state").get("carryon")`), and a previous `lookup_error` cleared. Failure: make `store.save` raise `OSError` (monkeypatch) → no exception, a warning is logged, and the in-memory status is still computed. Bad data: a release list holding a non-dict → no exception, nothing stored (`not_checked`). 
- `tests/test_mod_updates.py`, AC 6: a mod source whose installed list gains a mod during the check: inside a respx `side_effect` for the first lookup, add the mod to the source and call `service.record_install` for it. `FakeModSource` keeps its list in `_mods` (`:315-320`), which pyright strict forbids reading from outside the class (`reportPrivateUsage`), so give the test its own small source class with a public `mods` list (or make `FakeModSource`'s attribute public and update its uses); after `check()` the new mod's record is still stored and its status is not `not_checked`; a mod that disappears from the list during the check is pruned.
- `tests/test_mods_router.py` `TestInstallModEndpoint` (`:85`): with the fixture's override (below), `POST /mods {"slug": "smithingplus"}` then `GET /api/v1alpha1/mods/updates` returns `smithingplus` with status `up_to_date` and no `reason`, and the respx lookup route was called once. `SMITHINGPLUS_MOD` (`:67-82`) has no `modidstr` on its release, so build the lookup for this test as `{**SMITHINGPLUS_MOD, "releases": [{**release, "modidstr": "smithingplus"}]}` (otherwise the status is `installed_release_not_listed`). A second test (AC 5): monkeypatch the injected service's `store.save` to raise `OSError` → `POST /mods` still returns 200 with the same body as `test_install_mod_success` (`:139-177`) and the mod is installed.
- `tests/test_mod_service.py` `TestModServiceInstallMod` (`:773`): `install_mod("instruments")` (fixture `mod_instruments.json`) returns `InstallResult.releases` equal to the entry's whole normalized release list (all three mod IDs), and the lookup route was called once. `tests/test_mod_api.py` `TestResolveInstall` (`:1105`): `resolve_install` for `instruments` carries the entry's whole release list in `releases`.

### Web tests

| Task | File | Test |
|---|---|---|
| 2 | `src/lib/mod-ids.test.ts` | `findInstalledModByIds`: first matching ID wins; matches without case (`VSInstrumentsBase` installed, ids `['vsinstrumentsbase']`); `undefined` for no match, `[]`, an empty or not loaded list. `findInstalledModForEntry` matches `VSInstrumentsBase` (replaces "compares mod IDs exactly") |
| 2 | `src/components/ModCard.test.tsx` | Instruments card (`slug: 'instruments'`, `modIds: ['instruments', 'vsinstruments', 'vsinstrumentsbase']`) with `installedMods=[{ slug: 'vsinstrumentsbase' }]` shows `mod-card-installed-instruments` and no `mod-card-install-instruments`; with `[{ slug: 'VSInstrumentsBase' }]` the same; with `[{ slug: 'smithingplus' }]` the Install button; with `installedMods={[]}` the Install button; without the prop no footer (existing test, renamed) |
| 2 | `src/components/ModBrowseGrid.test.tsx` | the existing "passes installedSlugs to ModCard" tests (`:253-275`) pass `installedMods` |
| 2 | `src/features/mods/BrowseTab.test.tsx` | a browse response with the Instruments item (`modIds` as above) and an installed list (`GET /mods`) holding `vsinstrumentsbase`: the card shows Installed |
| 3 | `src/hooks/use-mods.test.tsx` `useInstallMod` (`:174`) | after a successful install, `queryKeys.mods.updateStatus` is invalidated (spy on `queryClient.invalidateQueries` or check the query is stale) |
| 4 | `src/components/ModUpdateCell.test.tsx` | `not_checked` shows "Not checked yet" with the new tooltip; with `error` the tooltip ends with `Last check failed: ...` (`:100-111`, new text); the other three reasons still show "Unknown" with their tooltips (`:87-98`, `not_checked` row moves out) |
| 4 | `src/components/ModTable.test.tsx` | a mod whose status is `unknown` / `not_checked` shows "Not checked yet" in the table (desktop) and, in the "Story 16.5: cards below md" block (`:1616`, `renderAtPhoneWidth`, its fetch mock serves `/mods/updates` from `updatesResponse`), on `installed-mod-card-<slug>`. `InstalledModCard` has no test file of its own; `ModTable` renders it below `md` (`ModTable.tsx:400-412`) |

### E2E (`web/e2e/installed-status.spec.ts`)

Style of `e2e/installed-mod-any-modid.spec.ts` (stubbed installed list, live mod database) and `e2e/mod-install-release.spec.ts` (real install guarded by a snapshot). Header comment with requirements as in those files.

1. **Card, stubbed.** `fakeInstalledMods` (copy the helper from `installed-mod-any-modid.spec.ts:32-58`) with `vsinstrumentsbase`; open `/game-server/mods/browse?q=instruments` (live browse; if the search does not return the `instruments` card, fail with a clear message rather than skipping); the Instruments card (`mod-card-instruments`) shows `mod-card-installed-instruments` and has no `mod-card-install-instruments`. Then open its detail page from the card: `mod-detail-installed-indicator` is visible (card and page agree). Nothing is installed.
2. **"Not checked yet", stubbed.** Stub `GET /api/v1alpha1/mods` with one mod and `GET /api/v1alpha1/mods/updates` with that mod's status `unknown`, reason `not_checked` (shape: `installed-mods-phone.spec.ts`, which stubs both); at desktop width (1440x900) and phone width (390x844), `mod-update-<slug>` has text "Not checked yet".
3. **Real install shows a status at once.** Serial describe with the snapshot guard copied from `mod-install-release.spec.ts:215-243` (`beforeAll` snapshot of installed slugs with `hasSnapshot`; `afterEach` refuses to clean up without it and deletes only touched slugs missing from the snapshot). Pick the first of `['playercorpse', 'carryon']` not in the snapshot (`test.skip` if both are installed). `POST /mods {"slug": <it>}` (timeout 60 s); without calling `POST /mods/updates/check`, `GET /mods/updates` lists it with `status` not `unknown`; open `/game-server/mods/installed` and `mod-update-<slug>` does not read "Not checked yet" or "Unknown". Then `DELETE /mods/<slug>` in the test body (the `afterEach` is the backstop).

The stack must end with the same installed mods: compare `GET /mods` before and after the run and a SHA-1 listing of `data/serverdata/Mods` (as Story 17.3 did). The removed mod's record stays in `mod-updates.json` until the next check prunes it (see "Remove and version change"); that is expected and not "installed mods". Do not start or stop the game server.

### Existing tests that change (deliberately)

Found by running both suites against a throwaway prototype of Tasks 1-4 (since discarded): API 2508 passed, 6 failed; web: typecheck errors and runtime failures listed below.

- `api/tests/test_edge_cases.py:258-284` `test_failed_install_reports_original_error_if_file_is_gone`: its `ResolvedInstall(...)` (`:270-272`) needs `releases=[DEMO_RELEASE]`. (Task 3)
- `api/tests/test_mod_models.py:819` `TestModBrowseItem::test_serialization_for_api_response`: the exact dict gains `"mod_ids": []`. (Task 1)
- `api/tests/test_mods_router.py:3604` `TestBrowseWithIncompleteModData::test_every_sort_succeeds_with_defaults` (4 parametrized cases): the exact dict at `:3653` gains `"mod_ids"` (`[]` for the entry with no mod IDs). (Task 1)
- **Not failing, but must change:** `api/tests/test_mods_router.py:118-126` (`TestInstallModEndpoint.test_app`) and `api/tests/test_mod_operation_lock_router.py:110-122` (`client`) must also override `get_mod_update_service` with `ModUpdateService(store=ModUpdateStore(<tmp>/"state"), mod_source=<the test's ModService>, game_version_provider=lambda: <the fixture's game version>)`. Without it the prototype passed but wrote `dev/vsmanager/state/mod-updates.json` (`just test-api` sets `VS_DATA_DIR=../dev`) through the real singleton, which also builds a real `ModService`. (Task 3)
- `web/src/lib/mod-ids.test.ts:72-74` "compares mod IDs exactly": now matches. (Task 2)
- Typecheck, `modIds` missing in `ModBrowseItem` literals: `web/src/api/mods.test.ts:46`, `src/components/ModBrowseGrid.test.tsx:78`, `:94`, `:110`, `src/components/ModCard.test.tsx:97` (the other ModCard fixtures spread it), `src/features/mods/BrowseTab.test.tsx:171`, `:187`, `src/hooks/use-browse-mods.test.tsx:41`, `:57`, `:73`. Add `modIds: [<the slug>]`. (Task 2)
- Runtime only (untyped fixture): `web/src/features/mods/ModsPage.test.tsx:91` lacks `modIds`, and the card's spread throws (7 tests). Add it. The missing fixture fields above also fail 46 `BrowseTab` tests and the ModCard/ModBrowseGrid tests at runtime until fixed. (Task 2)
- Prop rename `installedSlugs` → `installedMods`: `src/components/ModCard.test.tsx:477-847` (11 renders; `new Set<string>()` → `[]`, `new Set(['carrycapacity'])` → `[{ slug: 'carrycapacity' }]`, test name at `:477`), `src/components/ModBrowseGrid.test.tsx:253-384` (3 renders and the describe/test names). (Task 2)
- `web/src/components/ModUpdateCell.test.tsx:87-98` (the `not_checked` row of "shows Unknown...") and `:100-111` (tooltip text). (Task 4)
- Not related: in a full `vitest run` under load, `InstallConfirmDialog`, `QuickInstallButton`, `SettingField` and `GameConfigPanel` each failed one test and passed when run alone. If they fail in `just check`, re-run before suspecting this story.
- Anything else that fails is a regression (AC 8): fix the code, not the test.

### Not changed (do not "fix" these here)

- `VSS-4f3` (cards showing whether a release supports the installed game version) and `VSS-z7e` (filename collision on install).
- The detail page's behavior, apart from case-insensitive matching (AC 3): it still hides the install section when any of the entry's mod IDs is installed.
- `versionChoices`, `entryModIds`, `evaluate_update` and the version change API compare `modidstr` exactly.
- Version change and remove do not touch the update store (see "Remove and version change").
- The install response body, `ModLookupResponse`, and the `InstallConfirmDialog` / `ModCard` install payload (Story 17.2) are unchanged.
- The "Check for updates" flow, scheduled checks, webhook alerts (an install records no `notified` entry; the next check alerts as usual).

### API contract (`v1alpha1`)

- `GET /mods/browse` items gain `mod_ids: string[]` (additive).
- `POST /mods` responses are unchanged; as a side effect the new mod appears in `GET /mods/updates` with real data right away.
- `GET /mods/updates` is unchanged (`reason: "not_checked"` still exists; only its web label changes).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/mod/{slug}` and `https://mods.vintagestory.at/download`; assert the lookup route's `call_count == 1` where AC 4 says no extra request.
- Fixtures under `api/tests/fixtures/moddb/` are captured data and are not changed; synthetic data is built in the tests.
- Router tests that install must inject a `ModUpdateService` on a temp directory (see "Existing tests that change"); `git status --short` after `just test-api` must show nothing under `dev/`.
- After Task 1 and before Task 2 the API sends `mod_ids` and the web ignores it; every commit is green.

### Security Requirements

- No new endpoint. `POST /mods` stays Admin-only and `GET /mods/browse` keeps its auth (`RequireAuth`); `mod_ids` is public mod database data already in the listing. The stored record holds mod database data only (same as a check); release text goes through `StoredRelease.from_api`'s surrogate cleaning. Mod IDs are rendered as text by React.

### Development Commands

- `just test-api tests/test_mods_router.py tests/test_mod_models.py`, `just test-api tests/test_mod_updates.py tests/test_mod_service.py tests/test_mod_api.py tests/test_edge_cases.py tests/test_mod_operation_lock_router.py`, `just test-web src/lib/mod-ids.test.ts src/components/ModCard.test.tsx src/components/ModBrowseGrid.test.tsx src/features/mods/BrowseTab.test.tsx src/features/mods/ModsPage.test.tsx src/components/ModUpdateCell.test.tsx`, `just typecheck-web`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **17.3:** `install_mod` is `resolve_install` → checks → `with self._hold(mod_id)` → `download_resolved` → archive check → `_place_install`; keep that order and add nothing awaited inside the held section. Its review (M1) made the installed check case-insensitive, which is why AC 3 matches without case. Its Task 4 finding: a hook's own `onError` replaces the query client's default; irrelevant here (no new mutation), but check any new web error path the same way. Tests must not read private members (`reportPrivateUsage`); `ModUpdateService.store` is public.
- **17.2:** E2E cleanup must be guarded by a snapshot (review L1); `ModCard` must not send `""` as the slug (review L2), unchanged here. `just format-api` must not be used.
- **17.1:** browse reads normalized data; `mod["modidstrs"]` is always a `list[str]`. pyright strict, baseline 0 errors and 3 pre-existing warnings in tests (`tests/test_mod_service.py`, `tests/test_mods_router.py`). Keep each commit green.
- **16.2:** introduced `findInstalledModForEntry` and the E2E pattern of stubbing `GET /mods` only; its bead `VSS-ywb` is this story's sibling.
- **14.1 / ADR-4:** status is computed at read time from stored releases; storing the install's releases is exactly the data a check stores.

### Git Intelligence

- Recent commits are Story 17.3's (`346e133`, `cb3683e`, `5b2e416`, `05c5ad2`, `affef98`). Release notes come from commit subjects (`cliff.toml`). Planned: Task 1 `feat` (mod browser results list every mod ID of each mod), Task 2 `fix` (a browse card shows Installed when any of the mod's IDs is installed), Task 3 `fix` (a newly installed mod shows its update status right away), Task 4 `fix` (a mod that has not been checked for updates says "Not checked yet"), Task 5 `test`, Task 6 `docs`.

### Latest Technical Information

- No new libraries. FastAPI resolves both `Depends` of `install_mod` per request; `get_mod_update_service` is the existing singleton factory, already injected by three routes (`GET /mods/updates`, `POST /mods/updates/check`, `POST /mods/updates/apply-all`). TanStack Query v5 `invalidateQueries({ queryKey: ['mods'] })` matches every key starting with `'mods'`, including `['mods', '@updates']`.

### Project Structure Notes

- New: `web/e2e/installed-status.spec.ts`.
- Modified: `api/src/vintagestory_api/models/mods.py`, `routers/mods.py`, `services/mod_api.py`, `services/mods.py`, `services/mod_updates.py`; `api/tests/test_mods_router.py`, `test_mod_models.py`, `test_mod_updates.py`, `test_mod_service.py`, `test_mod_api.py`, `test_edge_cases.py`, `test_mod_operation_lock_router.py`; `web/src/api/types.ts`, `web/src/lib/mod-ids.ts`, `web/src/components/ModCard.tsx`, `ModBrowseGrid.tsx`, `ModUpdateCell.tsx`, `web/src/features/mods/BrowseTab.tsx`, and the web tests listed above. No fixture.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.4: Installed Status Is Right Everywhere]
- [Source: _bmad-output/planning-artifacts/prd.md] FR184, FR185
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (ADR-1: `modidstrs` normalized at the boundary; ADR-2: install mod ID; ADR-3: install lock order; ADR-4/ADR-5 do not touch this story)
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-2] decision 2 (installed mod by any mod ID)
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md#ADR-4: Update Status Store]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md] (17.4 needs no architecture decision; `mod_ids` listed as an API change)
- [Source: _bmad-output/implementation-artifacts/17-3-mod-operations-are-safe-against-each-other.md] (Install flow, Completion Notes, Senior Developer Review)
- [Source: _bmad-output/implementation-artifacts/16-2-installed-mods-recognized-by-any-mod-id.md]
- Beads: `VSS-49n`, `VSS-br2`, parent `VSS-4v5`; related `VSS-ywb`
- `project-context.md` - critical implementation rules (no suppressions; manual test tasks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-15: context analysis of the browse mapping and model, the normalized listing, `ModCard`/`ModBrowseGrid`/`BrowseTab`, `mod-ids.ts` and the detail page's use of it, the install flow after Stories 17.2/17.3 (`resolve_install`, `ResolvedInstall`, `InstallResult`, `_place_install`), `ModUpdateService` (store, `check`, prune, `get_mod_update_service`), `ModUpdateCell` and its two callers, the install hook's invalidation, the E2E specs of Stories 16.2, 16.5 and 17.2, and the reviews of 17.1-17.3. The tests that change were found by running both suites against a throwaway prototype of Tasks 1-4.

### File List

## Change Log

- 2026-11-15: Story 17.4 created (ready-for-dev).
- 2026-11-15: Validated against the create-story checklist: every cited path and line re-read on affef98; fixed the `ModLookupResponse` line, the number of routes that inject the update service, the phone-card test location (`ModTable.test.tsx`, no `InstalledModCard` test file), the update-store test helpers (`fixture_releases` returns stored releases; `FakeModSource._mods` is private under pyright strict), and a pointless E2E step; added the router-test dependency overrides after the prototype wrote `dev/vsmanager/state/mod-updates.json`, and the `SMITHINGPLUS_MOD` fixture's missing `modidstr`.
