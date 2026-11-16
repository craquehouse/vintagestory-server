# Story 18.3: Game Version Badge on Browse Cards

Status: ready-for-dev

<!-- Implements FR201-FR202. Beads: VSS-4f3 (UI-068), parent VSS-5w8. Governed by Epic 18 ADR-3 (supersedes Epic 10 ADR-2 for browse cards and replaces decision 6 of Epic 16 ADR-2). Stories are implemented in the order 18.1, 18.2, 18.3, 18.4, each stacked on the previous one: branch story/18-3-game-version-badge-on-browse-cards from the head of story/18-2-install-and-version-change-keep-records-right (or from main once 18.2 is merged). Line references were verified at b9606f1 (epic-18-planning, code identical to main 574e125) and MUST be re-checked at implementation time: Stories 18.1 and 18.2 edit routers/mods.py, models/mods.py and web/src/api/types.ts in other places. No new npm or Python dependency. -->

## Story

As an **administrator**,
I want **each mod browser card to tell me whether the mod has a release for my game version**,
so that **I do not open mod after mod to find the ones I can use**.

## Acceptance Criteria

1. **Given** a game server is installed and its version has a tag in the mod database
   **When** I request `GET /api/v1alpha1/mods/browse`
   **Then** the response has `game_version` set to the installed version, and every item has `has_release_for_game_version` `true` (the entry's numeric `modid` is in the mod database's listing filtered by that version's tag) or `false`
   *(Covers FR201; `VSS-4f3`)*

2. **Given** two or more browse requests within the cache lifetime (5 minutes), for any pages, sorts or filters, one after another or at the same moment
   **When** they are served
   **Then** the mod database receives at most one filtered listing request (`/api/mods?gameversion=<tagid>`) for the installed version and no request per mod
   *(Covers FR201)*

3. **Given** a card whose flag is `true`
   **When** I see it
   **Then** it shows a badge "Has a release for 1.22.7" (with the response's `game_version`); a card whose flag is `false` shows muted text "No release for 1.22.7"; neither uses the words "Compatible" or "Incompatible" or the `CompatibilityBadge` component; both are readable in the light and the dark theme and stay inside the card at phone width (390px)
   *(Covers FR201)*

4. **Given** no game server is installed, or the installed version has no tag in the mod database
   **When** I browse
   **Then** the response is 200 with `game_version: null` and every flag `null`, the mod database receives no filtered listing request, and the cards show no game version indicator
   *(Covers FR202)*

5. **Given** the mod database fails or is slow on the game version list or the filtered listing
   **When** I browse
   **Then** the response is 200; the flags come from the last copy for that version when one exists (even an expired one) and are `null` with `game_version: null` otherwise; the request waits at most 5 seconds for the flags (`VERSION_FLAGS_WAIT`), a fetch that is still running then finishes in the background and fills the cache, and after a failure or a timeout the flag lookup is not retried for 60 seconds (`VERSION_FLAGS_RETRY_AFTER`), so later browse requests do not wait again. A failure of the main listing is still 502 `EXTERNAL_API_ERROR`, as today
   *(Covers FR202)*

6. **Given** I install a different game server version
   **When** the API serves the next browse request
   **Then** the flags and `game_version` are for the new version, without restarting the API and without clearing anything
   *(Covers FR201)*

7. **Given** I pick a game version in the browse filter (`?version=`)
   **When** I change pages, sorts or other filters
   **Then** the filtered listing is served from the same cache (one mod database request per version per 5 minutes), the cards' flags still refer to the installed version, and everything else about the filter is as today: 400 `GAME_VERSION_NOT_FOUND` for an unknown version, 502 `EXTERNAL_API_ERROR` when the listing cannot be fetched and no unexpired copy exists, the same items in the same order
   *(Covers FR201)*

8. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory; `getBrowseCardCompatibility` and its test are gone
   *(Epic 18 ADR-3 decision 10)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-18.3/task-N): ... ; feat/fix/perf only for changes an admin (or an API user) can see, subject written for them. Red first. -->

- [ ] Task 1: `ModApiClient` caches filtered listings per tag ID + tests (AC: 2, 5, 7, 8)
  - [ ] 1.1: `api/src/vintagestory_api/services/mod_api.py`: add `import asyncio` (imports `:9-18`). Above `class ModApiClient` (`:260`) add the frozen dataclass `VersionListing` (`mods: list[ModDict]`, `mod_ids: frozenset[int]`, `fetched_at: datetime`); `dataclass` is already imported (`:11`). Class constants after `GAMEVERSIONS_CACHE_TTL` (`:279`): `VERSION_LISTING_MAX_ENTRIES = 3`, `VERSION_FLAGS_WAIT = 5.0` (seconds), `VERSION_FLAGS_RETRY_AFTER = timedelta(seconds=60)`; list them in the class docstring (`:266-272`). State in `__init__` after the game versions cache (`:303-305`): `self._version_listings: dict[int, VersionListing] = {}`, `self._version_fetches: dict[int, asyncio.Task[VersionListing]] = {}`, `self._version_flags_failed_at: datetime | None = None`
  - [ ] 1.2: Rename today's `get_mods_by_version` body (`:665-755`) to `_fetch_mods_by_version(self, version_tagid: int) -> list[ModDict]`, unchanged (same request, same errors, same log events). Add the helpers and the new public `get_mods_by_version` exactly as in Dev Notes "The client cache": `_fresh_version_listing`, `_refresh_version_listing` (stores the listing, evicts the entry with the oldest `fetched_at` while more than three are held), `_version_fetch` (one shared `asyncio.Task` per tag ID while a fetch is running), `get_mods_by_version` (an unexpired copy, else the shared fetch; raises `ExternalApiError` as today). Replace the docstring sentence "Results are NOT cached since they vary by version" (`:669-670`)
  - [ ] 1.3: New public `async def get_version_mod_ids(self, game_version: str) -> frozenset[int] | None` (Dev Notes "The client cache"): never raises `ExternalApiError`; returns the `modid` set for the version's tag, an expired copy when the refresh fails or is slow, `None` when the version has no tag or nothing is known
  - [ ] 1.4: `clear_browse_cache` (`:656-663`) also clears `_version_listings` and `_version_flags_failed_at` (ADR-3 decision 1); a fetch that is running is left to finish. `close` (`:316-320`) cancels every task in `_version_fetches` before closing the HTTP client
  - [ ] 1.5: `get_game_versions` (`:767-852`), the loop at `:818-823`: skip an entry that is not an object, whose `name` is not a `str` or whose `tagid` is not an `int` (a `bool` is not an `int` here, as in `models/moddb.py:34-38`); a body that is not a JSON object, or a `gameversions` value that is present and not a list, raises `ExternalApiError("VintageStory mod API returned an unexpected response")` (the message `get_all_mods` uses at `:625`); a missing key stays an empty map, as today. Reason: browse now reads this list on every request, and today a malformed entry raises `AttributeError`, which would turn every browse request into a 500 (Dev Notes "ADR against the code")
  - [ ] 1.6: Tests in `api/tests/test_mod_api.py` (Dev Notes "API tests", Task 1 rows) and the one test in "Existing tests that change" that belongs to Task 1

- [ ] Task 2: Browse API returns `game_version` and `has_release_for_game_version` + tests (AC: 1, 2, 4, 5, 6, 7, 8)
  - [ ] 2.1: `api/src/vintagestory_api/models/mods.py`: `ModBrowseItem` (`:312-377`) gains `has_release_for_game_version: bool | None = None` after `last_released` (`:376-377`); `ModBrowseResponse` (`:406-417`) gains `game_version: str | None = None` after `pagination`. Docstrings: Dev Notes "What the flag means" in two sentences each. Careful: `ModLookupResponse` has similar fields; these go in the two browse models only
  - [ ] 2.2: `routers/mods.py`: add `import asyncio` (`:3`). `_api_mod_to_browse_item` (`:197-230`) gains a second parameter `release_mod_ids: frozenset[int] | None = None` and sets `has_release_for_game_version=(mod["modid"] in release_mod_ids) if release_mod_ids is not None and mod["modid"] else None` (an item whose `modid` is missing is normalized to `0` and cannot be matched, so it gets `null`)
  - [ ] 2.3: `browse_mods` (`:233-419`), the block at `:324-337`: as in Dev Notes "The route". Read the installed version once, before any request; in the `?version=` branch keep `get_game_versions()` and the `GameVersionNotFoundError` check exactly as they are; then await the listing (`get_mods_by_version` or `get_all_mods`) together with `service.api_client.get_version_mod_ids(game_version)` in one `asyncio.gather` (ADR-3 decision 6). `:376` passes `release_mod_ids`; `:388` passes `game_version=game_version if release_mod_ids is not None else None`. Docstring (`:301-304`, `:306-310`): the two new fields, and that a failed flag lookup never fails the request
  - [ ] 2.4: Tests in `api/tests/test_mods_router.py` and `tests/test_mod_models.py` (Dev Notes "API tests", Task 2 rows), and the changes in "Existing tests that change" that belong to Task 2

- [ ] Task 3: Browse cards show the game version indicator + tests (AC: 3, 4, 8)
  - [ ] 3.1: `web/src/api/types.ts`: `ModBrowseItem` (`:392-416`) gains `hasReleaseForGameVersion: boolean | null` after `lastReleased` (`:415`); `ModBrowseData` (`:433-436`) gains `gameVersion: string | null`. Both required (the API always sends them), each with a doc comment from Dev Notes "What the flag means". Careful: the `lastReleased` at `:203` belongs to another interface. `apiClient` already converts `has_release_for_game_version` and `game_version` to camelCase; `web/src/api/mods.ts` does not change
  - [ ] 3.2: `web/src/hooks/use-browse-mods.ts`: the hook returns `gameVersion: query.data?.data?.gameVersion ?? null` beside `mods` and `pagination` (`:179-191`); one line in the header comment (`:1-12`)
  - [ ] 3.3: `web/src/components/ModCard.tsx`: new optional prop `gameVersion?: string | null` ("the game version the cards' flags refer to; from the browse response"). Add the local component from Dev Notes "The card" and render it directly after the side badge (`:188-190`), before the install footer (`:192`). Add "Story 18.3" to the header comment (`:1-14`). Do not import `CompatibilityBadge`
  - [ ] 3.4: `web/src/components/ModBrowseGrid.tsx`: prop `gameVersion?: string | null` (`:16-28`, `:69-74`), passed to each `ModCard` (`:105-110`). `web/src/features/mods/BrowseTab.tsx`: take `gameVersion` from `useBrowseMods` (`:151-169`) and pass it to `ModBrowseGrid` (`:289-294`). Do not use `installedVersion` (`:91`, from the server status) for the card: the text must name the version the flags were computed for
  - [ ] 3.5: Tests (Dev Notes "Web tests") and the fixture changes in "Existing tests that change" that belong to Task 3

- [ ] Task 4: Remove the Epic 10 browse card default (AC: 8)
  - [ ] 4.1: First run `rg -n "getBrowseCardCompatibility|BROWSE_CARD_DEFAULT_STATUS|mod-compatibility'" web/src web/e2e`. At b9606f1 the only hits are `web/src/lib/mod-compatibility.ts` and `web/src/lib/mod-compatibility.test.ts`. If anything else imports them (Stories 18.1 and 18.2 are not expected to), stop and ask
  - [ ] 4.2: `web/src/lib/mod-compatibility.ts`: delete `getBrowseCardCompatibility` (`:26-40`) and `BROWSE_CARD_DEFAULT_STATUS` (`:13-24`, used only by that function and its test), and rewrite the header comment (`:1-9`), which says the browse API carries no version data. `checkVersionCompatibility` (`:42-65`) stays: it is a Story 10.6 placeholder, not part of ADR-3 (Follow-ups). `web/src/lib/mod-compatibility.test.ts`: delete the `BROWSE_CARD_DEFAULT_STATUS` and `getBrowseCardCompatibility` describes (`:9-31`) and their imports (`:2-6`); the `checkVersionCompatibility` describe stays

- [ ] Task 5: E2E against the Docker dev stack (AC: 1, 3, 4)
  - [ ] 5.1: New `web/e2e/browse-game-version.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/browse-game-version.spec.ts` and the admin key from `.env` (`just test-e2e-web` stops the stack afterwards). Also re-run `e2e/mod-browse-state.spec.ts`, `e2e/mod-browse-name-sort.spec.ts`, `e2e/mods-navigation.spec.ts`, `e2e/installed-status.spec.ts` and `e2e/mod-detail-bad-data.spec.ts` (they all read the browse grid)
  - [ ] 5.2: Manual check on the same stack (per `project-context.md` a manual check is ticked only with the user's confirmation), recorded in the Dev Agent Record without screenshots: `/game-server/mods/browse?q=carry+on&sort=downloads` and `?q=player+corpse&sort=downloads`; write down the response's `game_version` and what the `carryon` and `playercorpse` cards show (on 1.22.7 the epic expects the badge on Carry On and "No release for 1.22.7" on Player Corpse; on another installed version record what is shown and check it against `https://mods.vintagestory.at/api/mods?gameversion=<tagid>`); then pick that version in the filter and change pages twice, and confirm in the container log that `mods_by_version_fetched` appears once. Do not start, stop or install a game server

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast`; after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 6.2: Story status `review`, `just sprint set 18-3-game-version-badge-on-browse-cards review`, PR (base `story/18-2-install-and-version-change-keep-records-right` while its PR is open, otherwise `main`), PR link on `VSS-4f3`. The PR description copies "API contract changes" below and names the maintainer's open choice (positive-only cards, Dev Notes "The card")

## Dev Notes

### Today (verified at b9606f1)

- **Cards.** `ModCard` shows nothing about the game version (`web/src/components/ModCard.tsx`). `getBrowseCardCompatibility()` (`web/src/lib/mod-compatibility.ts:38`) always returns `not_verified` and is called only by its own test.
- **The listing has no release data.** `GET /api/mods` items carry `modid`, `modidstrs`, `tags` and so on, no releases and no game versions (Epic 18 architecture, "Mod Database Facts"). `GET /api/mods?gameversion=<tagid>` returns the entries with at least one release tagged for that version: 5,651 of 9,633 for 1.22.7, 2.5 MB, 2.0 s. Every item of both listings has an int `modid`.
- **Caches.** `get_all_mods` keeps the listing for 5 minutes (`BROWSE_CACHE_TTL`, `services/mod_api.py:278`, `:583-654`). `get_game_versions` keeps the name-to-tag map for 1 hour (`:279`, `:757-852`); when it expires the old map stays in `_gameversions_cache` until a refresh replaces it. `get_mods_by_version` (`:665-755`) is not cached, and the browse route calls it on every request with `?version=` (`routers/mods.py:326-334`), so every page change in a filtered browse downloads 2.5 MB.
- **Tag names.** `GET /api/gameversions` returns 247 entries `{tagid, name, color}`; names have no `v` prefix (`"1.22.7"`, `"1.4.4-dev.2"`), tag IDs are negative ints (checked against the public API on 2026-11-16).
- **Installed version.** `ModService.game_version()` (`services/mods.py:351-353`) calls the provider, by default `installed_game_version` (`services/mod_updates.py:542-548`), which reads the `current_version` file on every call (`services/server.py:511-520`) and is `None` when no server is installed. `check_compatibility` strips a leading `v`/`V` before comparing (`services/mod_api.py:238`); this story does the same before the tag lookup.
- **Timeouts.** Every mod database request uses the client's `DEFAULT_TIMEOUT` of 30 s (`:276`, `:307-314`). Without a bound of its own, a hanging filtered listing would hold a browse request for 30 s even though the main listing is cached.

### What the flag means

`has_release_for_game_version: true` means: at least one release of this mod database entry is tagged for exactly the installed game version. It is **not** the detail page's compatibility status. The detail page and the install dialog judge the one release an install would pick for the entry's install mod ID (Epic 17 ADR-2, `ModService.lookup_mod`), with `check_compatibility` and its same-minor rules. So the two can differ, in both directions:

- A card can say "Has a release for 1.22.7" while the detail page shows "Not verified" or "Incompatible" for the release it would install, for example when the entry has several mod IDs and the tagged release belongs to another one, or when the newest release is tagged only for a later version and an older one is tagged for 1.22.7.
- A card can say "No release for 1.22.7" for a mod tagged only for 1.22.6, which the detail page may treat as compatible within the same minor version, and which may work.
- It is per entry, not per mod ID.

That is why the card never says "Compatible" or "Incompatible", never uses `CompatibilityBadge`, and why this sentence goes into the docstrings of both new API fields and both web types. `null` means "not known" (no server, no tag for the version, mod database failure with no earlier copy, or an item without a numeric `modid`), and the card then shows nothing: Epic 10 ADR-2's rule in its narrower form (ADR-3 decision 10).

### The client cache (`services/mod_api.py`)

```python
@dataclass(frozen=True)
class VersionListing:
    """The mod database listing filtered by one game version tag, as cached (Story 18.3)."""

    mods: list[ModDict]
    mod_ids: frozenset[int]
    fetched_at: datetime


# in ModApiClient
def _fresh_version_listing(self, version_tagid: int) -> VersionListing | None:
    """The cached listing for a tag if it has not expired."""
    listing = self._version_listings.get(version_tagid)
    if listing is None or datetime.now() - listing.fetched_at >= self.BROWSE_CACHE_TTL:
        return None
    return listing

async def _refresh_version_listing(self, version_tagid: int) -> VersionListing:
    mods = await self._fetch_mods_by_version(version_tagid)
    listing = VersionListing(
        mods=mods,
        mod_ids=frozenset(m["modid"] for m in mods if m["modid"]),
        fetched_at=datetime.now(),
    )
    self._version_listings[version_tagid] = listing
    while len(self._version_listings) > self.VERSION_LISTING_MAX_ENTRIES:
        oldest = min(self._version_listings, key=lambda t: self._version_listings[t].fetched_at)
        del self._version_listings[oldest]
    return listing

def _version_fetch(self, version_tagid: int) -> asyncio.Task[VersionListing]:
    """The running fetch for a tag, started if there is none. Callers share it."""
    task = self._version_fetches.get(version_tagid)
    if task is None:
        task = asyncio.create_task(self._refresh_version_listing(version_tagid))
        self._version_fetches[version_tagid] = task

        def finished(done: asyncio.Task[VersionListing]) -> None:
            self._version_fetches.pop(version_tagid, None)
            if not done.cancelled():
                done.exception()  # retrieved, so a failure nobody awaited is not reported as lost

        task.add_done_callback(finished)
    return task

async def get_mods_by_version(self, version_tagid: int) -> list[ModDict]:
    listing = self._fresh_version_listing(version_tagid)
    if listing is None:
        listing = await asyncio.shield(self._version_fetch(version_tagid))
    return listing.mods

async def get_version_mod_ids(self, game_version: str) -> frozenset[int] | None:
    tagid: int | None = None
    if self._is_gameversions_cache_valid():
        tagid = (self._gameversions_cache or {}).get(game_version)
        if tagid is None:
            return None
        listing = self._fresh_version_listing(tagid)
        if listing is not None:
            return listing.mod_ids
    failed_at = self._version_flags_failed_at
    if failed_at is None or datetime.now() - failed_at >= self.VERSION_FLAGS_RETRY_AFTER:
        try:
            async with asyncio.timeout(self.VERSION_FLAGS_WAIT):
                tagid = (await self.get_game_versions()).get(game_version)
                if tagid is None:
                    return None
                return (await asyncio.shield(self._version_fetch(tagid))).mod_ids
        except (TimeoutError, ExternalApiError):
            self._version_flags_failed_at = datetime.now()
            # log at warning level: event "version_flags_unavailable", game_version, tagid
    if tagid is None:
        tagid = (self._gameversions_cache or {}).get(game_version)  # an expired map is still a map
    stale = self._version_listings.get(tagid) if tagid is not None else None
    return stale.mod_ids if stale is not None else None
```

This is the prototype that was run (see "Existing tests that change"); pyright strict reported 0 errors on `src/` with it. Add docstrings in the file's style. Points that are easy to get wrong:

- **One fetch per tag, shared.** The version filter and the flag lookup ask for the same tag when the admin filters by the installed version, and the web can send two browse requests at once. Both await the same `asyncio.Task`, so AC 2 holds for concurrent requests too. `asyncio.shield` keeps one caller's cancellation (a closed browser tab, the 5 s timeout) from cancelling the fetch for the others.
- **The filter path raises, the flag path does not.** `get_mods_by_version` behaves as today on failure (`ExternalApiError`, 502 from the route), also when an expired copy exists: the unfiltered listing does the same (`get_all_mods` raises rather than serving an expired cache). `get_version_mod_ids` returns the expired copy. The filter path ignores the 60 s pause; an explicit filter request always tries.
- **Expired entries stay** in `_version_listings` until they are replaced or evicted. That is what "the last copy" in AC 5 is.
- **Eviction** is by oldest `fetched_at`, not by least recent use. With the installed version plus three filter versions browsed inside 5 minutes, one of the four is refetched on its next use; no bookkeeping is worth that case.
- **`modid` 0** (missing in the source, normalized by `_as_int`) is left out of the set.
- **The pause is one timestamp for the client, not one per tag.** After a failure, a browse request for another installed version (installed within the same minute) also answers without trying until the 60 s have passed. Simpler than a dictionary that needs pruning, and the cost is at most one minute without indicators.
- **Exceptions other than `ExternalApiError` and `TimeoutError` are not caught.** `_fetch_mods_by_version` and `get_game_versions` turn every `httpx` error and bad body into `ExternalApiError` (after Task 1.5). Do not add `except Exception`.
- **`asyncio.timeout`** needs Python 3.11; the project requires 3.14 (`api/pyproject.toml:5`).

### Does the first browse request wait for the filtered listing? (decision)

It waits, concurrently with the main listing, for at most `VERSION_FLAGS_WAIT` (5 s), and the fetch carries on in the background when the wait ends.

- **Why wait at all.** The web keeps each browse page for 5 minutes (`BROWSE_STALE_TIME`, `web/src/hooks/use-browse-mods.ts:23`). If the first response went out with `null` flags and the cache filled in the background, page 1, the page every admin sees, would show no indicator for 5 minutes or until a reload. When both caches are cold the two requests run together, so the page costs about the slower one (2.0 s measured against 1.7 s), not the sum (ADR-3 decision 6).
- **Why bound it.** The client timeout is 30 s. A browse whose main listing is cached must not hang for 30 s on an optional badge. 5 s is 2.5 times the measured fetch.
- **Why the 60 s pause.** Without it, every browse request during a mod database problem would wait 5 s again. With it, the cost of a failing mod database is one wait of at most 5 s per minute across all requests; in between, requests answer at once from the expired copy or with `null`. A fetch that outlives the wait still fills the cache, and the next request then gets real flags without waiting (the unexpired-copy check comes before the pause check).
- **Rejected: background fill only** (first page has no indicators for 5 minutes, see above). **Rejected: waiting without a bound** (30 s). **Rejected: a per-request httpx timeout on the filtered listing**: it would also shorten the version filter's own request, which must behave as today.
- **Known limit, accepted.** A page served with `null` flags because the wait ran out keeps them in the browser for up to 5 minutes. The API's next response for any other page has the flags.

### The route (`routers/mods.py:324-337`)

```python
# The version the cards' flags refer to (Story 18.3); None when no server is installed
game_version = (service.game_version() or "").lstrip("vV") or None

if version:
    game_versions = await service.api_client.get_game_versions()
    version_tagid = game_versions.get(version)
    if version_tagid is None:
        raise GameVersionNotFoundError(version)
    listing = service.api_client.get_mods_by_version(version_tagid)
else:
    listing = service.api_client.get_all_mods()

release_mod_ids: frozenset[int] | None = None
if game_version is None:
    all_mods = await listing
else:
    all_mods, release_mod_ids = await asyncio.gather(
        listing, service.api_client.get_version_mod_ids(game_version)
    )
```

- `service.game_version()` is read once per request, before any await and before the listing coroutine is created (a coroutine that is created and never awaited warns). Reading it on every request is the whole invalidation (ADR-3 decision 4, AC 6): another installed version is another tag ID, so another cache key.
- In the `?version=` branch the game version list is fetched first, as today, so `get_version_mod_ids` finds it cached and the two do not both request it.
- `"stable"` (`UNKNOWN_VERSION`, `services/mods.py:59`) or any other string that is not a tag name gives `None` from `get_version_mod_ids`: flags `null`, `game_version: null`.
- If the listing raises, `gather` lets the flag lookup finish on its own; it is bounded and does not raise, so nothing is left unretrieved. The `except` blocks (`:403-419`) do not change.
- The flag is computed per returned item only (`:376`), one set lookup each.
- Response: `game_version` is the stripped installed version when `release_mod_ids is not None`, else `None` (ADR-3 decision 7: `null` when the flags are `null`).

### The card (`web/src/components/ModCard.tsx`)

```tsx
/**
 * Whether the entry has a release tagged for the installed game version (Story 18.3,
 * Epic 18 ADR-3). Not a compatibility verdict: the detail page judges the release an
 * install would pick. Shows nothing when the flag or the version is unknown.
 */
function GameVersionIndicator({
  slug,
  hasRelease,
  gameVersion,
}: {
  slug: string;
  hasRelease: boolean | null;
  gameVersion: string | null | undefined;
}) {
  if (!gameVersion) return null;
  if (hasRelease === true) {
    return (
      <div className="mt-2" data-testid={`mod-card-game-version-${slug}`} data-has-release="true">
        <Badge variant="secondary" className="max-w-full whitespace-normal text-left">
          Has a release for {gameVersion}
        </Badge>
      </div>
    );
  }
  // VSS-4f3, maintainer's open choice: delete this block for positive-only cards
  if (hasRelease === false) {
    return (
      <p
        className="mt-2 text-xs text-muted-foreground"
        data-testid={`mod-card-game-version-${slug}`}
        data-has-release="false"
      >
        No release for {gameVersion}
      </p>
    );
  }
  return null;
}
```

- `Badge` is `@/components/ui/badge` (`variant="secondary"`, theme tokens `bg-secondary` / `text-secondary-foreground`); the muted text uses `text-muted-foreground` like the author line (`ModCard.tsx:149-151`). Both follow the theme through CSS variables; no colour is hard-coded. `Badge` is `whitespace-nowrap` by default (`components/ui/badge.tsx:8`); `max-w-full whitespace-normal` lets a long pre-release version wrap instead of leaving the card.
- No icon. The card's "Installed" line uses a green check (`:196-202`); a second check beside it would read as "installed and compatible".
- The comparisons are `=== true` and `=== false` on purpose: `null`, and a response that lacks the field (an untyped test fixture), show nothing.
- **Positive-only.** The change proposal leaves the `false` rendering as the maintainer's choice (open question 2). Deleting the marked block, its two `ModCard` tests and the `false` assertions in the E2E spec is the whole change. The API field stays three-valued either way.
- Use the exact strings `Has a release for <version>` and `No release for <version>` (AC 3).

### API contract changes (`v1alpha1`)

| Endpoint | Change | Kind |
|---|---|---|
| `GET /mods/browse` | New `game_version` (string or `null`) beside `mods` and `pagination`: the installed game version the items' flags refer to; `null` when the flags are `null` | Added field |
| `GET /mods/browse` | New `has_release_for_game_version` (`true`, `false` or `null`) on every item: whether the entry has a release tagged for exactly `game_version`; `null` when not known | Added field |
| `GET /mods/browse?version=...` | Results for a version filter are cached for up to 5 minutes per version, like unfiltered results; errors and status codes are unchanged | Behavior change |

No new error code, no new endpoint, no removed or renamed field. `GET /mods/gameversions` keeps its shape; a malformed entry in the mod database's version list is now skipped instead of failing the request (Task 1.5).

### API tests

Tests use respx on `https://mods.vintagestory.at/api/gameversions` and `https://mods.vintagestory.at/api/mods`. Register the filtered routes (`params={"gameversion": "<tagid>"}`, a string, as `tests/test_mods_router.py:2231-2234` does) before a plain `/api/mods` route and assert each route's `call_count`; check in the first test that the plain route does not also answer the filtered request. Synthetic listings (`{"statuscode": "200", "mods": [{"modid": 1, ...}]}`) are enough; no fixture file is added or changed.

Do not read private members in tests (pyright strict, `reportPrivateUsage`; the story adds no suppression). To make a copy expire or the wait short, set the public class constants on the test's client (`client.BROWSE_CACHE_TTL = timedelta(0)`, `client.VERSION_FLAGS_WAIT = 0.05`) or use a small subclass that overrides them.

| Task | File / class | Test |
|---|---|---|
| 1 | `test_mod_api.py`, `TestModApiClientModsByVersion` (`:1991`) | **Hit:** two `get_mods_by_version(tag)` calls, one request, same list (replaces `test_get_mods_by_version_not_cached`). **Miss:** another tag makes its own request. **Expiry:** with the lifetime at zero the second call requests again. **Failure is not cached:** a failing first call raises `ExternalApiError`, the next call requests again and succeeds. **Failure with an expired copy:** `get_mods_by_version` still raises |
| 1 | same file, new `TestModApiClientVersionListingCache` | **Eviction at three:** fetch tags A, B, C, D; then D, C, B again cost no request and A costs one. **Shared fetch:** `asyncio.gather(get_version_mod_ids("1.22.7"), get_mods_by_version(tag), get_version_mod_ids("1.22.7"))` makes one filtered request. **`clear_browse_cache`** drops the listings (next call requests again) |
| 1 | same class | `get_version_mod_ids`: **hit** returns the `modid` set (an item with `modid` missing is not in it) and a second call makes no request; **unknown version** (`"9.9.9"`, `"stable"`) returns `None` with no filtered request; **failure without a copy** (HTTP 500, connect error, bad JSON) returns `None` and does not raise; **failure with an expired copy** returns the old set; **pause:** after a failure the next call makes no request, and after `VERSION_FLAGS_RETRY_AFTER` (set to zero) it does; **game version list fails** with no map known: `None`; with an expired map and an expired listing: the old set |
| 1 | same class | **Slow fetch is bounded and still fills the cache:** a respx `side_effect` that awaits an `asyncio.Event`; with `VERSION_FLAGS_WAIT = 0.05`, `get_version_mod_ids` returns `None`, a second call returns `None` at once and makes no second request, then set the event, await `get_mods_by_version(tag)`, and `get_version_mod_ids` returns the set; the route was called once. **`close()`** with a fetch running cancels it without an error |
| 1 | `test_mod_api.py`, `TestModApiClientGameVersions` (`:1809`) | entries `null`, `"x"`, `{"name": 5, "tagid": -1}`, `{"name": "1.0.0", "tagid": "a"}`, `{"name": "1.0.1", "tagid": true}` are skipped and the valid ones kept; a body that is a list, and `"gameversions": "x"`, raise `ExternalApiError`; a missing key gives `{}` |
| 2 | `test_mods_router.py`, new `TestBrowseGameVersionFlag` (own fixtures; `ModService(..., game_version_provider=lambda: installed["version"])` with a dict the test can change) | **True and false (AC 1):** version list has `1.22.7`, filtered listing holds `modid` 1 of the listing's 1, 2, 3: items are `true`, `false`, `false`, `game_version == "1.22.7"`. **A `v` prefix** (`"v1.22.7"` installed) gives the same result with `game_version == "1.22.7"`. **One request (AC 2):** pages 1 and 2, another sort and a search: the filtered route's `call_count` is 1 and no `/api/mod/<slug>` request is made (no such route is registered; respx fails an unmocked request) |
| 2 | same class | **No server (AC 4):** provider returns `None`: 200, `game_version` is `None`, every flag `None`, neither the version list nor a filtered listing is requested. **Untagged version:** installed `"1.99.0"`: the same, with one version list request. **Failure without a copy (AC 5):** filtered route answers 500: 200, flags `None`, `game_version` `None`. **Failure with an earlier copy:** first request succeeds, set `mod_service.api_client.BROWSE_CACHE_TTL = timedelta(0)`, make the filtered route fail: 200, flags as before, `game_version == "1.22.7"`. **Version list fails:** 200, flags `None`. **Main listing fails:** still 502 `EXTERNAL_API_ERROR` |
| 2 | same class | **Changed version (AC 6):** two tags, two filtered routes with different `modid`s; browse, change `installed["version"]`, browse: flags and `game_version` follow, each filtered route called once, the main listing once. **Item without `modid`:** its flag is `None` while the others are `true`/`false` |
| 2 | same class | **Filter and flags together (AC 7):** installed `1.22.7`, `?version=1.21.3` with page 1 then page 2: the `1.21.3` route is called once, the `1.22.7` route once, the plain listing not at all; the items come from the `1.21.3` listing and their flags from the `1.22.7` set. **Filter by the installed version:** one filtered request in total. **Unknown filter version** is still 400 `GAME_VERSION_NOT_FOUND`; **filter listing fails** is still 502 (the existing version filter tests at `:2209-2356` stay and must pass unchanged) |
| 2 | `test_mod_models.py`, `TestModBrowseItem` (`:660`), `TestModBrowseResponse` (`:976`) | defaults `None` for both fields; `True`/`False`/`None` round-trip through `model_dump(mode="json")` |

The slow-fetch and shared-fetch cases are tested on `ModApiClient` (async tests, one event loop), not through `TestClient`: a `TestClient` used without `with` runs each request in its own event loop, and a fetch task left running after a request would belong to a closed loop.

### Web tests

| Task | File | Test |
|---|---|---|
| 3 | `src/components/ModCard.test.tsx` (new describe "game version indicator (Story 18.3)") | `hasReleaseForGameVersion: true`, `gameVersion="1.22.7"`: `mod-card-game-version-carrycapacity` has the text "Has a release for 1.22.7" and `data-has-release="true"`. `false`: "No release for 1.22.7", `data-has-release="false"`. `null`: no such element. `true` with `gameVersion` `null` or not passed: no such element. In the `true` and `false` cases the card's text does not match `/compatible/i`. The indicator is rendered with and without `installedMods` |
| 3 | `src/components/ModBrowseGrid.test.tsx` | `gameVersion` reaches the cards: one `true` and one `false` item show their texts with the grid's `gameVersion` |
| 3 | `src/hooks/use-browse-mods.test.tsx` | `gameVersion` is `null` before the data arrives and the response's value afterwards |
| 3 | `src/features/mods/BrowseTab.test.tsx` | a browse response with `gameVersion: '1.22.7'` and items `true`, `false`, `null`: the three cards show the badge, the muted text and nothing; with `gameVersion: null` no card has an indicator |
| 3 | `src/api/mods.test.ts` (`:46`) | the fixture gains the field; assert that `has_release_for_game_version` and `game_version` in the wire response arrive as `hasReleaseForGameVersion` and `gameVersion` |
| 4 | `src/lib/mod-compatibility.test.ts` | only the `checkVersionCompatibility` describe remains and passes |

### E2E (`web/e2e/browse-game-version.spec.ts`)

Style of `e2e/mod-detail-bad-data.spec.ts` (header comment with requirements, `API_KEY` from `VS_API_KEY_ADMIN`, `addInitScript` for the key) and `e2e/layout-widths.spec.ts` (stubbed API, several viewports). The spec changes no state: it installs nothing, writes nothing and does not start or stop the game server, so it needs no snapshot guard. No screenshots.

1. **Stubbed, true / false / null.** `page.route(/\/api\/v1alpha1\/mods\/browse(\?.*)?$/, ...)` fulfils `{ status: 'ok', data: { mods: [...three items...], pagination: {...one page...}, game_version: '1.22.7' } }` in the API's snake_case, with slugs that cannot be confused with real mods (`e2e-has`, `e2e-none`, `e2e-unknown`), `has_release_for_game_version` `true`, `false`, `null`, and `logo_url: null`. The real path is `/api/v1alpha1/mods/browse` (`routers/mods.py:51`, `:233`; `e2e/mod-browse-name-sort.spec.ts:64`). The installed mods list (`/api/v1alpha1/mods`) and everything else stay live; the regex does not match them. Open `/game-server/mods/browse`: `mod-card-game-version-e2e-has` has the text "Has a release for 1.22.7"; `mod-card-game-version-e2e-none` has "No release for 1.22.7"; `mod-card-game-version-e2e-unknown` has count 0; `mod-browse-grid` does not contain text matching `/compatible/i`.
2. **Stubbed, version unknown.** The same items with `game_version: null` and every flag `null`: no `[data-testid^="mod-card-game-version-"]` element.
3. **Phone width and dark theme.** Test 1's stub at 390x844, once with `page.emulateMedia({ colorScheme: 'light' })` and once with `'dark'` (the theme follows the system by default, `contexts/ThemeContext.tsx:12`): both indicators are visible, each indicator's bounding box lies inside its card's (`mod-card-e2e-has`, `mod-card-e2e-none`), and the page does not scroll sideways (`document.documentElement.scrollWidth <= clientWidth`). In dark, assert `document.documentElement` has the class `dark` so the test cannot pass on the light theme by accident.
4. **Live, read-only.** Without a stub, open `/game-server/mods/browse?q=carry+on&sort=downloads` and wait for the browse response (`page.waitForResponse`, path ends with `/api/v1alpha1/mods/browse`). Read `data.game_version` and the items from the response body, not hard-coded: when `game_version` is a string, every item with a boolean flag has a `mod-card-game-version-<slug>` element whose text is `Has a release for <game_version>` or `No release for <game_version>` accordingly; when it is `null` (no server installed on this stack, or the mod database did not answer), no card has an indicator. The test passes in both cases and logs which one it saw (`test.info().annotations`), so a run on a stack without a server is not mistaken for coverage of the badge.

### Existing tests that change (deliberately)

Found by running the API suite against a throwaway prototype of Tasks 1 and 2 (since discarded) and the web typecheck against the two new required fields. API: with the four fixture changes below applied, 2676 passed and 6 failed, all listed. The web runtime suite was not run against a prototype card.

- `api/tests/test_mod_api.py:2052-2069` `TestModApiClientModsByVersion::test_get_mods_by_version_not_cached`: becomes the "hit" test (second call makes no request). (Task 1)
- `api/tests/test_mod_models.py:820` `TestModBrowseItem::test_serialization_for_api_response`: the exact dict gains `"has_release_for_game_version": None`. (Task 2)
- `api/tests/test_mods_router.py:3854` `TestBrowseWithIncompleteModData::test_every_sort_succeeds_with_defaults` (4 parametrized cases): the exact dict (`:3866-3882`) gains `"has_release_for_game_version": None`. (Task 2)
- **Fixtures, four browse test classes.** Their `mod_service` fixtures pass `game_version="1.21.3"`: `TestBrowseModsEndpoint` (`:1774`), `TestBrowseItemSlugUrlalias` (`:2750`), `TestBrowseModsFilters` (`:3083`), `TestBrowseWithIncompleteModData` (`:3836`). With an installed version the route now asks for the game version list, which those tests do not mock, and respx fails the unmocked request (`AllMockedAssertionError`): 40 router tests failed in the prototype. Change those four fixtures to `game_version_provider=lambda: None` (no server installed; `game_version=None` alone would fall back to the real `installed_game_version`, which reads the dev data directory). Their tests then mean what they meant before, and the flag has its own class. The other eleven `game_version="1.21.3"` fixtures in the file (`:121`, `:516`, `:931`, `:1104`, `:1282`, `:1493`, `:2391`, `:2583`, `:3401`, `:3584`, `:3686`) do not browse and do not change. (Task 2)
- Web typecheck, `hasReleaseForGameVersion` missing in `ModBrowseItem` literals: `web/src/api/mods.test.ts:46`, `src/components/ModBrowseGrid.test.tsx:78`, `:95`, `:112`, `src/components/ModCard.test.tsx:97` (the other ModCard fixtures spread it), `src/features/mods/BrowseTab.test.tsx:172`, `:189`, `src/hooks/use-browse-mods.test.tsx:41`, `:58`, `:75`. Add `hasReleaseForGameVersion: null`. (Task 3)
- Web typecheck, `gameVersion` missing in `ModBrowseData` literals: `src/features/mods/BrowseTab.test.tsx:230`, `:353`, `:410`, `:703`, `:785`, `src/hooks/use-browse-mods.test.tsx:96`, `:367`, `:516`, `:1094`, `:1304`, `:1336`, `:1391`, `:1607`, `:1680`. Add `gameVersion: null`. (Task 3)
- Not failing, change for consistency: the untyped browse fixture in `web/src/features/mods/ModsPage.test.tsx:80-110` gains both fields. (Task 3)
- `web/src/lib/mod-compatibility.test.ts:2-31`: two describes and two imports removed. (Task 4)
- Environment, not this story: in a checkout without `.env`, `just test-api` reports 77 errors and 6 failures in `tests/console/`, `tests/test_jobs_router.py`, `tests/test_jobs_registration.py` and `tests/test_scheduler.py` ("VS_API_KEY_ADMIN must be set"). They pass with the variable set.
- Known flakes under load in a full `vitest run` (Story 17.4): `InstallConfirmDialog`, `QuickInstallButton`, `SettingField`, `GameConfigPanel`. Re-run before suspecting this story.
- Anything else that fails is a regression (AC 8): fix the code, not the test.

### ADR against the code

ADR-3 holds against the code, and its file and line references are right at b9606f1. Four places where the story goes further than the ADR, each because the code requires it:

1. **The wait is bounded and failures pause retries (AC 5).** ADR-3 decision 5 says the browse request "still succeeds" when the filtered listing cannot be fetched, and decision 6 fetches both listings concurrently. With the client's 30 s timeout, "succeeds" would mean up to 30 s per browse request, on every request, while the mod database hangs. `VERSION_FLAGS_WAIT` and `VERSION_FLAGS_RETRY_AFTER` are this story's additions.
2. **Concurrent requests share one fetch.** The ADR's cache alone does not give "at most one filtered listing request" (epic AC 2) when two requests arrive while the cache is cold, or when the admin filters by the installed version.
3. **The game version list is hardened (Task 1.5).** The ADR maps the version to a tag with `get_game_versions` and does not mention that its parsing raises `AttributeError` on a malformed entry (`services/mod_api.py:819-823`). Until now that could only break the version filter and `GET /mods/gameversions`; with this story it would break every browse request.
4. **An item without a numeric `modid` gets `null`.** ADR-3 decision 2 relies on every listing item having an int `modid`, which was true of all 9,633 items checked, but the normalizer turns a missing one into `0` (`models/moddb.py:34-38`, `:80`). Such an item cannot be matched, so the story reports "not known" rather than "No release".

ADR-3 decision 10 names `getBrowseCardCompatibility()` and its test. The module also exports `BROWSE_CARD_DEFAULT_STATUS`, which exists only for that function, and `checkVersionCompatibility`, an unused Story 10.6 placeholder. The story removes the first two and leaves the placeholder (Follow-ups in the hand-off).

### Not changed (do not "fix" these here)

- The detail page, the install dialog, `CompatibilityBadge`, `check_compatibility` and `lookup_mod`. Compatibility of a specific release is still judged there (ADR-3 decision 9).
- Epic 16 ADR-2 decisions 1 to 5 (installed status on cards, Story 17.4's `mod_ids` matching).
- `get_all_mods` and its cache, including that it raises instead of serving an expired copy.
- The `?version=` filter's semantics, parameter pattern and error codes; `GET /mods/gameversions`' response shape; the game version dropdown in `BrowseTab` and its `installedVersion` prop.
- The web's 5-minute browse cache. After the admin installs another game version, pages already loaded in the browser keep the old version's flags and text until they go stale or the page is reloaded; AC 6 is about the API's next response. Invalidating browse queries when the installed version changes is a follow-up, not part of `VSS-4f3`.
- The array form `?gameversions[]=` (meaning unknown, ADR-3 decision 11), any per-mod request, any web-side intersection.
- `checkVersionCompatibility` in `web/src/lib/mod-compatibility.ts`.
- No sort or filter by the flag ("only mods with a release for my version" is what the existing version filter already does).
- Pre-existing and out of scope: `VSS-1ar` (3 pyright warnings in tests), `VSS-hnl` (4 skipped web tests), `VSS-6wj`.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- After Task 1 and before Task 2 the route still calls `get_mods_by_version` and is simply cached; after Task 2 and before Task 3 the API sends the fields and the web ignores them. Every commit is green.
- No test may reach the real `get_mod_service` singleton or write under `dev/`: every router test class builds its `ModService` on `tmp_path` and overrides `get_mod_service` (pattern: `tests/test_mods_router.py:1747-1785`). `git status --short` after `just test-api` must show nothing under `dev/`.
- A completion note must be true of the code: when the Dev Agent Record says a case is tested, name the test.

### Security Requirements

- No new endpoint and no new input: `GET /mods/browse` keeps its auth (`RequireAuth`, Admin and Monitor) and its parameters. The installed game version is already visible to both roles through the server status. The flag is derived from public mod database data.
- The version string is rendered as text by React; nothing from the mod database is put into `href`, `src` or HTML by this story.
- Memory is bounded: at most three filtered listings (about 5,600 small dictionaries each) beside the main listing, and at most one running fetch per tag ID.

### Development Commands

- `just test-api tests/test_mod_api.py`, `just test-api tests/test_mods_router.py tests/test_mod_models.py`, `just test-web src/components/ModCard.test.tsx src/components/ModBrowseGrid.test.tsx src/hooks/use-browse-mods.test.tsx src/features/mods/BrowseTab.test.tsx src/api/mods.test.ts src/lib/mod-compatibility.test.ts`, `just typecheck`, `just lint`, `just check`.
- Do not run `just format-api` (it reformats unrelated files; Story 17.2 process note). Do not run `just release`.

### Previous Story Intelligence

- **17.4:** added `mod_ids` to browse items the same way (model field, `_api_mod_to_browse_item`, required web type, fixture churn). Its review flagged a `feat` subject that read like a UI feature for an API field (L1): name the API in Task 2's subject. Its prototype found that a router test without a dependency override wrote into `dev/`; hence the fixture rule above. A doc comment that is false for an edge case was a review finding (L2): the new docstrings must say what `null` means.
- **17.3:** a TanStack Query v5 hook-level `onError` replaces the client default, so such a hook must call `handleApiError` itself. This story adds no mutation and no `onError`; keep it that way.
- **17.2 / 17.4 E2E:** real-state changes need a snapshot guard and must restore the stack exactly. This story's spec changes nothing, by design; do not add an install to it.
- **17.1 (Epic 17 ADR-1):** listings are normalized where they enter (`normalize_mod_list`); `mod["modid"]` is always an `int`, `0` when missing. The filtered listing goes through the same normalizer (`services/mod_api.py:711`).
- **17.8:** layout checks at 390px assert that nothing scrolls sideways; test 3 of the E2E spec follows it.
- **Reviews of 17.x in general:** a `feat`/`fix`/`perf` subject must describe something an admin can see; a completion note must be true of the code.

### Git Intelligence

- Base for line references: `b9606f1` (`docs(epic-18): plan epic 18 mod media and fixes`), code identical to `574e125` (main after Epic 17).
- Release notes come from commit subjects. Planned: Task 1 `perf(story-18.3/task-1): browsing mods filtered by game version no longer downloads the list on every page change`; Task 2 `feat(story-18.3/task-2): browse API reports whether each mod has a release for the installed game version`; Task 3 `feat(story-18.3/task-3): mod browser cards show whether a mod has a release for your game version`; Task 4 `refactor(story-18.3/task-4): remove the unused browse card compatibility default`; Task 5 `test(story-18.3/task-5): ...`; Task 6 `docs(story-18.3/task-6): ...`.

### Latest Technical Information

- No new libraries. `asyncio.timeout`, `asyncio.shield`, `asyncio.gather` and `asyncio.Task.add_done_callback` are standard library (Python 3.14 here). `asyncio.timeout` raises the builtin `TimeoutError`; `shield` leaves the inner task running when the outer wait is cancelled.
- A task created with `asyncio.create_task` must be referenced until it is done; `_version_fetches` holds it and the done callback removes it.
- FastAPI runs the app on one event loop in production, so a fetch that outlives its request finishes normally. See "API tests" for `TestClient`.
- respx fails any request that no route matches, which is how "no request per mod" is asserted.

### Project Structure Notes

- New: `web/e2e/browse-game-version.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mod_api.py`, `routers/mods.py`, `models/mods.py`; `api/tests/test_mod_api.py`, `test_mods_router.py`, `test_mod_models.py`; `web/src/api/types.ts`, `web/src/hooks/use-browse-mods.ts`, `web/src/components/ModCard.tsx`, `ModBrowseGrid.tsx`, `web/src/features/mods/BrowseTab.tsx`, `web/src/lib/mod-compatibility.ts`, and the web tests listed above. No fixture file, no new module, no dependency.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.3: Game Version Badge on Browse Cards]
- [Source: _bmad-output/planning-artifacts/prd.md] FR201, FR202
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md#ADR-3] and "Mod Database Facts"
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] ADR-1 (normalization at the boundary), ADR-2 (the release an install picks)
- [Source: _bmad-output/planning-artifacts/architecture/epic-10-architecture-decisions.md] ADR-2 (superseded for cards); [epic-16-ui-polish.md#ADR-2] decision 6 (replaced)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-16.md] (API changes table; open questions 2 and 5)
- [Source: _bmad-output/implementation-artifacts/17-4-installed-status-is-right-everywhere.md] (browse item field pattern, Completion Notes, Senior Developer Review)
- Beads: `VSS-4f3`, parent `VSS-5w8`
- `project-context.md` - critical implementation rules (no suppressions; commit message format; manual checks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Story created 2026-11-16: context analysis of `ModApiClient` (listing, game version and filtered listing fetches and their caches), the browse route and models, `ModService.game_version`, the web browse hook, `ModCard`, `ModBrowseGrid`, `BrowseTab`, `mod-compatibility.ts`, the E2E specs of Stories 17.1, 17.4 and 17.8, and Story 17.4's notes and review. The client cache and the route change were prototyped and run (six client cache cases passed, pyright strict clean on `src/`); the API tests that change were found by running the whole API suite against that prototype, the web fixtures by running the web typecheck with the two new fields. The prototype was discarded.

### File List

## Change Log

- 2026-11-16: Story 18.3 created (ready-for-dev).
- 2026-11-16: Validated against the create-story checklist: every cited path and line re-read at b9606f1; the client cache and route prototyped and run; added the bounded wait, the retry pause and the shared fetch (AC 2, AC 5) after working out the 30 s client timeout and the concurrent case; added the four browse fixture changes after 44 tests failed on an unmocked game version request; added the game version list hardening (Task 1.5); settled the item without a `modid`, the `v` prefix and what is removed from `mod-compatibility.ts`.
