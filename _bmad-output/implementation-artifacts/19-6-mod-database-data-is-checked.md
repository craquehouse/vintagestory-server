# Story 19.6: Mod Database Data Is Checked

Status: review

<!-- Implements FR224-FR227, Epic 19 ADR-12 and ADR-13. Beads: VSS-2zis (API-081), VSS-ce0h (API-086), VSS-0lkb (API-090); parent VSS-fl9b. Stories run in order 19.1 to 19.7, each stacked on the previous. Line references were verified at b6ae2f2 (epic-19-planning; api/ and web/ identical to 048fea9, the commit the ADRs cite) and must be re-checked at implementation time: Stories 19.1 to 19.5 land first, and Story 19.4 edits services/mod_api.py (download cache, around :555-630) and services/mods.py in other places. API and web change. No new dependencies. -->

## Story

As an **administrator**,
I want **the manager to pass on only URLs it has checked and to treat a broken mod database answer as an upstream error**,
so that **a mod author's data or a mod database fault cannot misuse or break the pages I use**.

## Acceptance Criteria

1. **Given** a mod whose logo is an `https://moddbcdn.vintagestory.at/` URL
   **When** I look it up (`GET /api/v1alpha1/mods/lookup/{slug}`) or see it in the browse results (`GET /api/v1alpha1/mods/browse`)
   **Then** `logo_url` is that URL unchanged
   *(Covers FR224; `VSS-2zis`)*

2. **Given** a mod whose logo is an `http:` URL, a URL on another host, a `data:` or `javascript:` URL, or not a URL
   **When** I look it up or browse
   **Then** the response is 200, `logo_url` is `null`, and the page shows the placeholder
   *(Covers FR224)*

3. **Given** a mod logo on a browse card, the detail page or the install dialog
   **When** the image is requested
   **Then** the `<img>` has `referrerpolicy="no-referrer"` and the request carries no `Referer` header
   *(Covers FR224)*

4. **Given** a mod whose homepage or source URL is an `https` URL
   **When** I look it up
   **Then** `homepage_url` or `source_url` is that URL unchanged and the detail page shows the link
   *(Covers FR225)*

5. **Given** a homepage or source value that is empty, an `http:`, `javascript:` or `data:` URL, has user info, has a space (any whitespace), control character or backslash, or is longer than 2,048 characters
   **When** I look the mod up
   **Then** the response is 200, the field is `null` and the detail page shows no such link; the "ModDB Page" link is unaffected
   *(Covers FR225)*

6. **Given** a URL dropped by AC 2 or AC 5
   **When** it is dropped
   **Then** a debug-level log event names the mod slug and the field, never the URL; an empty or missing value is not logged
   *(Covers FR224, FR225; ADR-12 decision 6)*

7. **Given** the mod database answers the listing, a filtered listing, a mod lookup or the game version list with HTML, an empty body, `[]`, `"text"` or `null`
   **When** a mod route needs that answer
   **Then** the response is 502 `EXTERNAL_API_ERROR`, never 500, and the previous cached copy and its time, where there is one, are unchanged
   *(Covers FR226; `VSS-ce0h`)*

8. **Given** the mod database answers correctly on the next request
   **When** I retry
   **Then** the route works; nothing malformed was cached
   *(Covers FR226)*

9. **Given** the game version cache is cold and several requests need it at once
   **When** they are served
   **Then** the mod database receives one `/api/gameversions` request, every caller gets its result, and a failure reaches every waiting caller and is not kept (the next call fetches again)
   *(Covers FR227; `VSS-0lkb`)*

10. **Given** the mod listing cache is cold or expired and several browse requests arrive together
    **When** they are served
    **Then** the mod database receives one `/api/mods` request, every request gets its result, and a failure reaches every waiting request and is not kept
    *(Covers FR227; `VSS-0lkb`)*

11. **Given** a listing fetch (or a game version list fetch) is running
    **When** a refresh is forced (`force_refresh=True`)
    **Then** it waits for the running fetch instead of starting a second one; with no fetch running it starts one, as today
    *(Covers FR227)*

12. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory (`dev/`)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-19.6/task-N): ...; feat/fix/perf only for changes an admin can see, subject written for admins. Red first. -->

- [x] Task 1: Only checked logo, homepage and source URLs leave the API, and logos load without a referrer + tests (AC: 1, 2, 3, 4, 5, 6, 12) (`VSS-2zis`)
  - [x] 1.1: `services/mod_media.py`: new `MAX_LINK_LENGTH = 2048` and `external_link_url(url: str | None) -> str | None` (Dev Notes "URL rules"). Update the module docstring's "Rules" (`:7-16`) with the link rule and with the logo now using the image rule. Keep the module pure apart from the logger
  - [x] 1.2: `services/mod_media.py`: new `checked_url(url, rule, *, slug: str, field: str) -> str | None` that returns `rule(url)` and logs `mod_url_dropped` at debug level with `slug` and `field` (never the URL) when `url` is non-empty and the rule returned `None` (Dev Notes "Logging"). `rule` is `Callable[[str | None], str | None]` (`from collections.abc import Callable`)
  - [x] 1.3: `services/mods.py` `lookup_mod`: the import at `:51` adds `checked_url`, `external_link_url`, `mod_image_url`. `logo_url=` (`:690`) is `checked_url(mod["logofilename"], mod_image_url, slug=response_slug, field="logo_url")`; `homepage_url=` (`:693`) and `source_url=` (`:694`) use `external_link_url` with fields `homepage_url` and `source_url`. Docstring (`:563-564`): extend the `services/mod_media.py` sentence to the three fields
  - [x] 1.4: `routers/mods.py` `_api_mod_to_browse_item` (`:203-246`): `logo_url=checked_url(mod["logo"], mod_image_url, slug=slug, field="logo_url")` (`:238`); import `checked_url` and `mod_image_url` from `vintagestory_api.services.mod_media` between the `services.mod_api` imports (`:18-32`) and `services.mod_updates` (`:33`); ruff `I001` has the last word. Only the page's items are checked, in this function, never the cached listing (ADR-12 decision 2)
  - [x] 1.5: API documentation: `models/mods.py` docstrings of `ModLookupResponse.logo_url` (`:268-269`), `homepage_url` (`:277-278`), `source_url` (`:280-281`) and `ModBrowseItem.logo_url` (`:392-393`) say when the value is `null` (Dev Notes "API documentation"); the lookup route docstring's `Returns:` list (`routers/mods.py:634-653`) gains `logo_url`, `homepage_url` and `source_url` lines; the browse route docstring's `mods` line (`:318-320`) says `logo_url` is null unless an https URL on the mod database CDN. These docstrings are the routes' OpenAPI descriptions; the models are not in the OpenAPI schema (`response_model=ApiResponse`)
  - [x] 1.6: Web: `referrerPolicy="no-referrer"` on the three logo `<img>` elements, right after `src` (`web/src/components/ModCard.tsx:142-147`, `web/src/components/InstallConfirmDialog.tsx:142-147`, `web/src/features/mods/ModDetailPage.tsx:620-624`). These are the only places a mod logo renders (Dev Notes "Web"). No other web source change: the placeholder and the `&&` around the two links (`ModDetailPage.tsx:702`, `:714`) already handle `null`
  - [x] 1.7: Tests (Dev Notes "API tests" and "Web tests", Task 1 rows), red first

- [x] Task 2: One guarded JSON fetch for the four `ModApiClient` fetchers + tests (AC: 7, 8, 12) (`VSS-ce0h`)
  - [x] 2.1: `services/mod_api.py` `ModApiClient`: new private `_get_json_object(self, url: str, *, params: dict[str, int] | None = None, require_200: bool = False) -> dict[str, object]` (Dev Notes "The guarded fetch"). It owns the three `httpx` `except` branches, the optional HTTP 200 check (before parsing), the JSON parse and the object check, and raises `ExternalApiError` for each. Reuse `_is_json_object` (`:261-263`)
  - [x] 2.2: `get_mod` (`:371-449`): use the helper with `require_200=False` (it reads the body of any HTTP status today; ADR-13 decision 2). Remove the local parse, the `isinstance` check and `cast(ModDict, payload)` (`:396-406`); `normalize_mod` takes `object` (`models/moddb.py:155`). The `statuscode` handling (`:408-434`) does not change. Drop `cast` from the `typing` import (`:15`) when nothing else uses it (it is the only `cast(` in the file at b6ae2f2)
  - [x] 2.3: `get_all_mods` (`:642-703`): the request and parse move into a new private `_fetch_all_mods(self) -> list[ModDict]` that uses the helper (`require_200=False`, as today: no HTTP status check), keeps the `statuscode == "200"` rule, `normalize_mod_list` and the "unexpected status" error, and writes `_browse_cache` / `_browse_cache_time` only on success. `get_all_mods` keeps the cache check and calls it (Task 3 adds the shared fetch)
  - [x] 2.4: `_fetch_mods_by_version` (`:826-914`) and `get_game_versions` (`:926-1025`): use the helper with `require_200=True` (both check HTTP 200 before parsing today). `get_game_versions`'s fetch moves into a private `_fetch_game_versions(self) -> dict[str, int]` that keeps the `gameversions` array check and the per-entry guards of Story 18.3 and writes the cache only on success
  - [x] 2.5: Tests (Dev Notes "API tests", Task 2 rows), red first; the listing route test is red before the change (500)

- [x] Task 3: One shared in-flight fetch for the game version list, the full listing and the filtered listings + tests (AC: 9, 10, 11, 12) (`VSS-0lkb`)
  - [x] 3.1: `services/mod_api.py`: new module-level generic class `SharedFetches[K, T]` (PEP 695; Python is 3.14) after `_is_json_array` (`:266-268`), holding the pattern of `_version_fetch` (`:741-755`): `get(key, fetch) -> asyncio.Task[T]` starts `fetch()` as a task only when none is running for `key`; a done callback removes it (only if it is still the registered task) and retrieves its exception; `cancel_all()` cancels and awaits every running task (Dev Notes "Shared fetches")
  - [x] 3.2: `ModApiClient.__init__` (`:318-352`): `_version_fetches` (`:348`) becomes `SharedFetches[int, VersionListing]`; new `_all_mods_fetch: SharedFetches[None, list[ModDict]]` and `_game_versions_fetch: SharedFetches[None, dict[str, int]]`. `_version_fetch` (`:741-755`) becomes a one-line call of `self._version_fetches.get(version_tagid, lambda: self._refresh_version_listing(version_tagid))`. `close()` (`:360-369`) awaits `cancel_all()` of all three before closing the client; its docstring says "any mod database fetch still running"
  - [x] 3.3: `get_all_mods` and `get_game_versions`: when the cache is not used (cold, expired or `force_refresh`), `return await asyncio.shield(self._all_mods_fetch.get(None, self._fetch_all_mods))` (and the game version equivalent). A forced refresh therefore joins a running fetch (ADR-13 decision 6). Docstrings: concurrent callers share one request; a forced refresh joins a running fetch; a failure reaches every waiter and is not kept
  - [x] 3.4: `get_version_mod_ids` (`:780-824`): after the game version list resolves, check `_fresh_version_listing(tagid)` before starting the filtered fetch (replace `:811` with Dev Notes "The fresh-copy check"). Without it the existing `test_concurrent_callers_share_one_fetch` (`tests/test_mod_api.py:2365`) makes two filtered requests once the game version fetch is shared (found with the prototype)
  - [x] 3.5: Tests (Dev Notes "API tests", Task 3 rows), on the client with `asyncio` (not `TestClient`), red first

- [x] Task 4: E2E against the Docker dev stack (AC: 2, 3, 4, 5)
  - [x] 4.1: New `web/e2e/mod-database-urls.spec.ts` (Dev Notes "E2E"): every mod database route the pages call is stubbed with `page.route`, so the spec needs neither the mod database nor a game server and changes nothing. Rebuild the stack from this branch first (`just docker restart`), then `cd web && bunx playwright test e2e/mod-database-urls.spec.ts` with `VS_API_KEY_ADMIN` exported; also re-run `e2e/mod-detail-media.spec.ts` and `e2e/browse-game-version.spec.ts`. Do not start or stop the game server; no screenshots
  - [x] 4.2: Record in the Dev Agent Record that `GET /api/v1alpha1/mods` returned the same body before and after the run

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `just check` passes; the diff adds no lint or type suppression and no `cast` (it removes one); pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); web tests keep the 4 known skips (`VSS-hnl`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 5.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): see Dev Notes "Manual check"
  - [ ] 5.3: Story status `review`, `just sprint set 19-6-mod-database-data-is-checked review`, PR (base: Story 19.5's branch while its PR is open, otherwise `main`), PR link on `VSS-2zis`, `VSS-ce0h` and `VSS-0lkb`. The PR description lists "API contract changes" from this story

## Dev Notes

### The bugs (verified at b6ae2f2)

- **Unchecked URLs (`VSS-2zis`).** `lookup_mod` passes `mod["logofilename"]`, `mod["homepageurl"]` and `mod["sourcecodeurl"]` straight into `ModLookupResponse` (`services/mods.py:690`, `:693`, `:694`), and `_api_mod_to_browse_item` passes `mod["logo"]` (`routers/mods.py:238`). The normalizer only makes them `str | None` (`models/moddb.py:104-107`). The web puts the logo into `<img src>` without `referrerPolicy` in three places and the links into `<a href>` (`ModDetailPage.tsx:702-723`). Screenshots and the trailer already go through `services/mod_media.py` (Story 18.1); this story replaces Epic 18 ADR-1 decision 6 ("`logo_url` keeps passing through unchecked").
- **Malformed bodies are 500 (`VSS-ce0h`).** `get_all_mods` calls `response.json()` and `data.get(...)` with no guard (`services/mod_api.py:663-667`): HTML or an empty body raises `ValueError` (a `json.JSONDecodeError`), and `[]`, `"text"` or `null` raise `AttributeError`; neither is an `httpx.HTTPError`, so `GET /mods/browse` and `GET /mods/tags` answer 500. `_fetch_mods_by_version` catches the `ValueError` (`:858-866`) and then calls `data.get` unguarded (`:869`). `get_mod` (`:395-407`) and `get_game_versions` (`:964-981`, Story 18.3) are guarded, each with its own copy.
- **No shared fetch (`VSS-0lkb`).** `get_all_mods` (`:658-664`) and `get_game_versions` (`:944-952`) start their own request for every caller that finds the cache cold; the full listing is about 4 MB. Only the filtered listings share one fetch per tag (`_version_fetch`, `:741-755`, awaited shielded at `:776-777`). The bead text says Story 19.4 adds the game version fetch; ADR-13 puts it here (see "ADR against the code").

### URL rules (Task 1)

```python
MAX_LINK_LENGTH = 2048
"""Longest homepage or source URL the API passes on, in characters (Epic 19 ADR-12)."""


def external_link_url(url: str | None) -> str | None:
    """`url` unchanged when it is a well-formed https URL with a host, else None (ADR-12)."""
    if (
        not url
        or len(url) > MAX_LINK_LENGTH
        or _UNSAFE.search(url)
        or any(ch.isspace() for ch in url)
        or not url.startswith("https://")
    ):
        return None
    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError for a port that is not a number in range
    except ValueError:
        return None
    if not parts.hostname or "@" in parts.netloc or port == 0:
        return None
    return url
```

- **Logo:** the existing `mod_image_url` (`services/mod_media.py:63-65`): `https`, whole `netloc` in `MOD_MEDIA_HOSTS` (`:31`), no user info, no port, no trailing dot. Nothing new.
- **Links:** any host and any port (ADR-12 decision 3). `https://` is matched case-sensitively, as `_https_parts` does (`:54`); the mod database sends lower case. `@` anywhere in the `netloc` is user info (an empty `https://@x.com` too). `parts.hostname` is `None` for `https://`, `https:///path` and `https://:443/`. Reading `.port` raises for `:abc` and `:99999`; `port == 0` is refused because a browser refuses it too. An IPv6 literal (`https://[::1]/`) is kept: it is a well-formed `https` URL with a host.
- **Whitespace:** `_UNSAFE` (`:49`) covers ASCII control characters, space and backslash. The prototype showed `https://x.com /` (no-break space) passing that and `urlsplit`, so the rule also refuses any `str.isspace()` character (see "ADR against the code").
- **Length:** characters, `len(url) > 2048` is refused; exactly 2,048 is kept.
- **`""` becomes `null`** (ADR-12 consequences); 23 of the 60 most downloaded entries have `homepageurl: ""` and 16 have `sourcecodeurl: ""` (mod database facts), so the web, which already hides a falsy link, shows the same thing.
- Percent-encoded text is not decoded: `https://x.com%40y.com/` is kept (host `x.com%40y.com`; a browser does not treat `%40` as user info). The web puts it in `href` as is.

### Logging (Task 1)

```python
def checked_url(
    url: str | None, rule: Callable[[str | None], str | None], *, slug: str, field: str
) -> str | None:
    """`rule(url)`; a non-empty URL the rule drops is logged at debug level, without the URL."""
    kept = rule(url)
    if kept is None and url:
        logger.debug("mod_url_dropped", slug=slug, field=field)
    return kept
```

- **Event name** `mod_url_dropped`, fields `slug` and `field` (`logo_url`, `homepage_url`, `source_url`, the response field names). Never the URL (ADR-12 decision 6): it is author-controlled and can be long.
- **Empty and missing values are not logged:** they are the normal case for links (see above) and would fill the debug log on every lookup.
- **Browse** logs per item on the page (at most `page_size`, 100), at debug level only. The listing of 9,636 items is never walked (ADR-12 decision 2).
- `build_screenshots` keeps its own `mod_screenshot_dropped` event (`:96`); not changed.

### API documentation (Task 1)

- `ModLookupResponse.logo_url`: "URL of the mod's logo on the mod database CDN (`https`, `MOD_MEDIA_HOSTS`), or null when the entry has none or its URL is not allowed (Epic 19 ADR-12)."
- `homepage_url` / `source_url`: "The author's homepage (source code) URL when it is a well-formed `https` URL of at most 2,048 characters, otherwise null (an empty value is null)."
- `ModBrowseItem.logo_url`: same as the lookup's.

### Web (Task 1)

- `rg -n "logoUrl" web/src --glob '!*.test.*'` lists exactly three `<img src={mod.logoUrl}>` (`ModCard.tsx:142-147`, `InstallConfirmDialog.tsx:142-147`, `ModDetailPage.tsx:620-624`); the other hits are the types (`api/types.ts:209`, `:429`) and props passed to the dialog (`ModCard.tsx:286`, `ModDetailPage.tsx:217`, `:276`, `:759`). The `<img>` elements in `Sidebar.tsx:141-152` are the app's own logo from the same origin; `ModScreenshotGallery.tsx` already has the attribute (`:99`, `:161`, `:187`).
- Placement: right after `src`, as in `ModScreenshotGallery.tsx`. The web keeps trusting the API's values (ADR-12 decision 5); it does not re-check URLs.
- Story 19.3 sends `Referrer-Policy: no-referrer` for the page; the attribute still matters for the Vite dev server and a proxy that drops the header. The E2E therefore asserts the attribute as well as the missing `Referer`.
- The detail page's logo `<img>` has no test ID; tests find it through `mod-detail-logo` (`ModDetailPage.tsx:617`), as `ModDetailPage.test.tsx:234-235` does.

### The guarded fetch (Task 2)

```python
async def _get_json_object(
    self, url: str, *, params: dict[str, int] | None = None, require_200: bool = False
) -> dict[str, object]:
    """GET `url` and return its body as a JSON object (Epic 19 ADR-13 decision 1).

    Raises ExternalApiError for a timeout, a connection or other HTTP client error, an
    HTTP status other than 200 when `require_200`, a body that is not JSON, and a body
    that is JSON but not an object. Status rules beyond that are the caller's.
    """
    client = await self._get_client()
    endpoint = url.removeprefix(self.BASE_URL)
    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException as e:
        logger.error("mod_api_timeout", endpoint=endpoint)
        raise ExternalApiError("VintageStory mod API request timed out") from e
    except httpx.ConnectError as e:
        logger.error("mod_api_connection_error", endpoint=endpoint)
        raise ExternalApiError("Could not connect to VintageStory mod API") from e
    except httpx.HTTPError as e:
        logger.error("mod_api_error", endpoint=endpoint, error=str(e))
        raise ExternalApiError(f"VintageStory mod API error: {e}") from e
    if require_200 and response.status_code != 200:
        logger.warning("mod_api_http_error", endpoint=endpoint, status_code=response.status_code)
        raise ExternalApiError(f"VintageStory mod API returned HTTP {response.status_code}")
    try:
        body: object = response.json()
    except ValueError as e:
        logger.error("mod_api_invalid_body", endpoint=endpoint, http_status=response.status_code)
        raise ExternalApiError("VintageStory mod API returned invalid JSON") from e
    if not _is_json_object(body):
        logger.error("mod_api_invalid_body", endpoint=endpoint, http_status=response.status_code)
        raise ExternalApiError("VintageStory mod API returned an unexpected response")
    return body
```

- **The HTTP 200 check stays before the parse.** A first prototype parsed first and broke `test_get_game_versions_http_error` (`tests/test_mod_api.py:1901-1912`: a 503 with a text body must say `HTTP 503`, not "invalid JSON"). `require_200` keeps each fetcher's status rule (ADR-13 decision 2): `True` for `_fetch_mods_by_version` and `get_game_versions`, `False` for `get_mod` (reads `statuscode` "404" from a non-200 body) and `get_all_mods` (never checked the HTTP status).
- **Messages** are the ones the tests already assert: "timed out", "Could not connect", "VintageStory mod API error", "HTTP <n>", "invalid JSON", "unexpected response", "unexpected status" (the last is the fetchers'). `get_mod`'s "unreadable response (HTTP n)" text becomes "invalid JSON"; no test or caller reads it (`rg unreadable api/` finds only an unrelated test).
- **Log events** become one set with `endpoint` (`/mod/<slug>`, `/mods`, `/gameversions`; the `gameversion` tag is in `params`, not the path). No test asserts the old per-fetcher event names (`rg "mod_api_timeout|mod_api_json_error|mod_api_invalid_body" api/tests` finds none). The fetchers keep their own `unexpected_api_status*` and normalization error events. `get_mod` logs `slug` today; `endpoint` contains it.
- **Nothing malformed is cached (ADR-13 decision 4):** the cache attributes are written only after a successful parse and normalization, as today; every failure raises before that line.
- **Routes do not change (ADR-13 decision 3):** `ExternalApiError` is already 502 `EXTERNAL_API_ERROR` in browse (`routers/mods.py:458`), game versions (`:534`), tags (`:586`), lookup (`:687`), install (`:829`) and version change (`:1133`). The update check catches `ExternalApiError` from `get_mod` already (`services/mod_updates.py:526-531`).
- An `asyncio.TimeoutError` from `get_version_mod_ids`'s `asyncio.timeout` (`:807`) is not an `httpx` error and is not caught by the helper; unchanged.

### Shared fetches (Task 3)

```python
class SharedFetches[K, T]:
    """Running mod database fetches by key; callers that find one running share it.

    Epic 19 ADR-13 decision 5: the pattern of Story 18.3's filtered listings, used for the
    game version list and the full listing too. A finished task is removed, so a failure
    reaches every waiter and is not kept.
    """

    def __init__(self) -> None:
        self._tasks: dict[K, asyncio.Task[T]] = {}

    def get(self, key: K, fetch: Callable[[], Coroutine[Any, Any, T]]) -> asyncio.Task[T]:
        task = self._tasks.get(key)
        if task is None:
            task = asyncio.create_task(fetch())
            self._tasks[key] = task

            def finished(done: asyncio.Task[T]) -> None:
                if self._tasks.get(key) is done:
                    del self._tasks[key]
                if not done.cancelled():
                    # Retrieved, so a failure nobody awaited is not reported as lost
                    done.exception()

            task.add_done_callback(finished)
        return task

    async def cancel_all(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

- **One helper for all three (ADR-13 decision 5):** "one small helper holds the pattern for all three", so it replaces Story 18.3's `_version_fetch` body; `_version_fetch` stays as a one-line wrapper because `get_mods_by_version` (`:776-777`) and `get_version_mod_ids` call it.
- **Key `None`** for the two single fetches (`SharedFetches[None, ...]`); the filtered listings keep the tag ID.
- **Imports:** `Callable` and `Coroutine` from `collections.abc`, `Any` from `typing` (the module has `from __future__ import annotations`, `:7`). The prototype passed pyright strict with 0 errors and ruff apart from import order. No `cast`, no suppression.
- **Shielded waits:** every caller awaits `asyncio.shield(task)`, as Story 18.3 does: a cancelled request (a closed browser tab, or `get_version_mod_ids`'s 5-second `asyncio.timeout`) does not cancel the fetch others wait for; it finishes and fills the cache. The game version list is now also fetched in the background after that timeout, where today the timeout cancels the request; this is the intended effect of decision 5.
- **`force_refresh=True` joins (decision 6):** it skips the cache check and calls `get(None, ...)`, which returns the running task if there is one. No caller in `api/src` passes `force_refresh` today (`rg force_refresh api/src` finds only the two definitions), so this is client behaviour for tests and future callers.
- **`clear_browse_cache` / `clear_gameversions_cache`** (`:705-716`, `:1027-1034`) clear the cached values only; a running fetch is left to finish and fills the cache afterwards, as the filtered listing already does (`:709-710`). Docstrings say so for both.
- **`close()`** cancels and awaits all three helpers, then closes the client, so the lifespan shutdown leaves no pending task.
- **Router tests:** `TestClient` runs each request on its portal loop; with respx answering at once, each shared task finishes inside its request, and the done callback removes it, so nothing survives between requests (the prototype ran the whole API suite: 2858 passed).

### The fresh-copy check (Task 3)

Replace `return (await asyncio.shield(self._version_fetch(tagid))).mod_ids` (`:811`) with:

```python
listing = self._fresh_version_listing(tagid)
if listing is None:
    listing = await asyncio.shield(self._version_fetch(tagid))
return listing.mod_ids
```

While a caller waits for the shared game version list, another caller (`get_mods_by_version`) can fetch and cache the same tag's listing and finish; its task is then removed, so `_version_fetch` would start a second request. Today the existing test passes only because each caller's own game version request finishes later.

### API tests

`tests/` may read private members (`pyproject.toml:60-63`, `reportPrivateUsage = false`); use that to assert the cache attributes are unchanged. Fixtures under `api/tests/fixtures/moddb/` are captured data and are not changed (none has `logofilename`, `homepageurl` or `sourcecodeurl`); the bad-data entries are built in the test modules.

| Task | File | Test |
|---|---|---|
| 1 | `tests/test_mod_media.py`, new `TestExternalLinkUrl` (style of `TestModImageUrl`, `:36-80`) | Kept unchanged: `https://github.com/a/b`, `https://example.com:8443/x?y#z`, `https://[::1]/`, a 2,048-character URL. Rejected (parametrized): `None`, `""`, `http://example.com`, `HTTPS://example.com`, `//example.com`, `javascript:alert(1)`, `data:text/html,x`, `https://`, `https:///path`, `https://:443/`, `https://u:p@example.com`, `https://@example.com`, `https://example.com:abc`, `https://example.com:99999`, `https://example.com:0`, `https://[::1`, `https://example.com/a b`, ` https://example.com`, `https://example.com/\t`, `https://example.com/\n`, `https://example.com /`, `https:\\\\example.com`, `https://example.com/\\a`, a 2,049-character URL |
| 1 | same, new `TestCheckedUrl` | Returns the rule's value; a dropped non-empty URL logs `mod_url_dropped` with `slug` and `field` and without the URL text (`captured_logs`, strip ANSI as `:185-190` does); `None` and `""` log nothing; a kept URL logs nothing |
| 1 | `tests/test_mod_service.py` `TestModServiceLookupMod` (`:1358`, fixture `lookup_service` `:1362`) | Parametrized lookup with a synthetic entry (one release): CDN logo kept; each of `http://moddbcdn...`, `https://i.imgur.com/a.png`, `data:image/png;base64,AA==`, `javascript:alert(1)`, `not a url` gives `logo_url is None`; `https` homepage and source kept; `""`, `http://`, `javascript:`, `data:`, user info, a space, a backslash and 2,049 characters give `None`. The lookup still succeeds for every case. The existing null-everywhere test (`test_lookup_mod_with_null_in_every_field`, `:1811-1839`) stays as it is |
| 1 | `tests/test_mods_router.py` `TestLookupModEndpoint` (`:535`) | `GET /mods/lookup/<slug>` for an entry with `logofilename: "http://moddbcdn.vintagestory.at/x.png"`, `homepageurl: "javascript:alert(1)"`, `sourcecodeurl: ""`: 200 and the three fields `null` in the raw JSON; a second entry with a CDN logo and `https` links returns them unchanged |
| 1 | `tests/test_mods_router.py` `TestBrowseModsEndpoint` (`:1875`) | A listing with one CDN logo, one `http:` logo, one off-host logo and one `null`: `logo_url` is the CDN URL, `null`, `null`, `null`; status 200. Existing items with CDN logos (`:1833`, `:1865`) are unchanged |
| 2 | `tests/test_mod_api.py`, one new parametrized test per fetcher (`get_mod`, `get_all_mods`, `get_mods_by_version`, `get_game_versions`) | Bodies `b"<html>Not JSON</html>"`, `b""`, `b"[]"`, `b'"text"'`, `b"null"` (and `b"5"`) with HTTP 200 raise `ExternalApiError`. For the three cached ones: a good answer first, then the malformed one; the cached value and its time (`_browse_cache_time`, `_gameversions_cache_time`, `_version_listings[tag].fetched_at`) are unchanged. `get_all_mods` and `get_game_versions` reach the second request with `force_refresh=True`; the filtered listing with `BROWSE_CACHE_TTL = timedelta(0)` on the instance (as the 18.3 tests set `VERSION_FLAGS_WAIT`). Then a good answer: the call returns the new data (AC 8) |
| 2 | `tests/test_mods_router.py` | `GET /mods/browse` with `/api/mods` answering `[]` and then HTML: 502 `EXTERNAL_API_ERROR`, never 500 (red before Task 2: 500); `GET /mods/browse?version=1.21.3` with `/api/gameversions` answering `"text"`: 502; with the filtered listing answering `null`: 502; `GET /mods/tags` with `/api/mods` answering `[]`: 502; `GET /mods/lookup/<slug>` with `null`: 502. Then a good answer on the same client: 200 (AC 8). Follow `test_browse_mods_api_unavailable` (`:2134`) for the fixture |
| 3 | `tests/test_mod_api.py`, new class `TestSharedFetches` (client-level, `asyncio`, respx `side_effect` with an `asyncio.Event` gate as `test_slow_fetch_is_bounded_and_fills_cache`, `:2526-2555`) | Five concurrent cold `get_all_mods()` calls (`asyncio.gather`): one `/api/mods` request, five equal results. The same for `get_game_versions()` |
| 3 | same | Failure: gated answer `b"[]"`; four concurrent callers all get `ExternalApiError`; one request; the next call makes a second request and succeeds (not kept). For both caches |
| 3 | same | Forced refresh joins: one gated `get_all_mods()` running, then `get_all_mods(force_refresh=True)` while it waits: one request, both get the result. With no fetch running and a valid cache, `force_refresh=True` makes a request (existing `test_get_all_mods_force_refresh`, `:1658-1672`, still passes). The same for `get_game_versions` |
| 3 | same | Expired cache: a valid listing, then `BROWSE_CACHE_TTL = timedelta(0)` on the instance and three concurrent calls: one more request (AC 10 "cold or expired") |
| 3 | same | A cancelled waiter does not cancel the fetch: start one gated call, cancel it, start another, open the gate: the second gets the result, one request. `close()` with a gated fetch running for each helper returns without error and leaves no pending task |
| 3 | same | `SharedFetches` itself: a finished task is removed (a second `get` after completion starts a new task); a failed task nobody awaited is not reported as "Task exception was never retrieved" (install a recording handler with `asyncio.get_running_loop().set_exception_handler`, drop the task, `gc.collect()`, assert the handler saw nothing) |

### Existing tests that change (deliberately)

Found by running the whole API suite (2858 tests) and the three web test files against a throwaway prototype of Tasks 1 to 3, since discarded:

- None fails once the HTTP 200 check runs before the parse and the fresh-copy check is in `get_version_mod_ids`. Without the first, `tests/test_mod_api.py::TestModApiClientGameVersions::test_get_game_versions_http_error` (`:1901-1912`) fails; without the second, `TestModApiClientVersionListingCache::test_concurrent_callers_share_one_fetch` (`:2365-2382`) fails with two requests. Both tests are right; do not change them.
- Web: `ModCard.test.tsx`, `InstallConfirmDialog.test.tsx` and `ModDetailPage.test.tsx` (165 tests) pass with the attribute. Their logo fixtures use `https://mods.vintagestory.at/assets/...` (`ModCard.test.tsx:120`, `InstallConfirmDialog.test.tsx:38`), which the API would now drop; the web trusts the API, so they stay as they are.
- Environment note: in a fresh worktree without `.env`, set `VS_API_KEY_ADMIN` before `just test-api` (Story 18.2 saw 77 errors and 6 failures without it).
- Anything else that fails is a regression (AC 12): fix the code, not the test.

### Web tests

| Task | File | Test |
|---|---|---|
| 1 | `web/src/components/ModCard.test.tsx` (`:320-327`) | The logo `<img>` (`mod-card-logo-modwithlogo`) has `referrerpolicy="no-referrer"`; the placeholder test (`:329`) unchanged |
| 1 | `web/src/components/InstallConfirmDialog.test.tsx` (`:130-143`) | `install-dialog-logo` has `referrerpolicy="no-referrer"` |
| 1 | `web/src/features/mods/ModDetailPage.test.tsx` "header section" (`:225-240`) and "external links" (`:652-705`) | The logo `<img>` inside `mod-detail-logo` has `referrerpolicy="no-referrer"`. With `homepage_url: null`, `source_url: null` and `logo_url: null`, the placeholder shows, neither link renders and `mod-detail-moddb-link` still does (extend `does not render optional links when null`, `:693-704`, with the ModDB link) |

### E2E (`web/e2e/mod-database-urls.spec.ts`)

Style of `e2e/mod-detail-media.spec.ts` (header comment with requirements, `readOnly`, a synthetic lookup body, a CDN route that records `Referer`, a 1x1 PNG) and `e2e/browse-game-version.spec.ts` (`item`, `browseBody`, `stubBrowse`, `:42-88`); copy the helpers, do not import across specs. Header: Story 19.6, FR224-FR225, every mod database route is stubbed, so the spec needs no mod database and no game server and changes nothing; it carries no tag, so Story 19.7's CI job runs it.

- **Key:** load the page's key through Story 19.2's `/config.js` helper in `web/e2e/` (ADR-5 decision 8; Story 19.7 moves every spec to it). Add no `localStorage` init script.
- **Stubs:** `readOnly` (refuse every non-GET to `/api/`), `GET /api/v1alpha1/mods/browse` with two items, `e2e-logo` (`logo_url: "https://moddbcdn.vintagestory.at/e2e-logo.png"`) and `e2e-nologo` (`logo_url: null`); `/mods/gameversions` (`{versions: ["1.22.7"]}`) and `/mods/tags` (`{tags: []}`) so the browse page makes no mod database request; `/mods/lookup/e2e-logo` and `/mods/lookup/e2e-nologo` with the lookup body of `mod-detail-media.spec.ts` (`:54-97`), `e2e-logo` with the CDN logo and `homepage_url: "https://example.com/home"`, `source_url: "https://example.com/src"`, `e2e-nologo` with all three `null`; the CDN (`https://moddbcdn.vintagestory.at/**`) answering the PNG and recording each request's `referer` header.
- **Why the bad URLs are not in the stubs:** `page.route` acts on the browser's requests, not on the API's requests to the mod database, so an end-to-end check of the API's filtering would need a fake mod database. The router tests (Task 1) cover the filtering; the spec stubs what the API answers for a dropped URL (`null`) and checks what the admin sees.
- **Test 1 (AC 3, browse and dialog):** open `/game-server/mods/browse`; `mod-card-logo-e2e-logo` is visible with `referrerpolicy` `no-referrer`; `mod-card-placeholder-e2e-nologo` is visible; click `mod-card-install-e2e-logo`, `install-dialog-logo` has `referrerpolicy` `no-referrer`; cancel the dialog. Every recorded CDN request has no `referer`, and at least one was made.
- **Test 2 (AC 3, AC 4, detail):** open `/game-server/mods/browse/e2e-logo`; the `img` in `mod-detail-logo` has the attribute; `mod-detail-homepage-link` and `mod-detail-source-link` have the stubbed `href`; no CDN request has a `referer`.
- **Test 3 (AC 2, AC 5, detail):** open `/game-server/mods/browse/e2e-nologo`; `mod-detail-logo` contains no `img`; `mod-detail-homepage-link` and `mod-detail-source-link` have count 0; `mod-detail-moddb-link` is visible.
- No real state changes: compare `GET /api/v1alpha1/mods` (via `request`, admin key) before and after in the Dev Agent Record. Do not start or stop the game server. No screenshots.

### Manual check (Task 5.2)

On the Docker stack built from this branch: open the mod browser and two or three mod detail pages from the live mod database; logos load, placeholders show for mods without one, and in the browser's network panel a logo request has no `Referer`. Open a mod whose homepage or source is empty and one where it is set: the link appears only when set; "ModDB Page" is always there. Do not install anything; do not start or stop the game server; no screenshots (the page can show the server name). The maintainer ticks 5.2.

### Not changed (do not "fix" these here)

- `MOD_MEDIA_HOSTS`, `mod_image_url`, `trailer_link_url`, `build_screenshots` (Story 18.1).
- The description HTML and the images inside it (Story 19.3 handles `http:` images there); the "ModDB Page" link, which the web builds from `urlalias`.
- `get_version_mod_ids`'s bounded wait, retry pause and stale-copy fallback (Story 18.3), apart from the fresh-copy check.
- The download path of `ModApiClient` (`download_release_file` and the cache layout; Story 19.4).
- No route, status code or response field changes shape; no new error code.

### API contract changes

- `GET /api/v1alpha1/mods/lookup/{slug}` and `GET /api/v1alpha1/mods/browse`: `logo_url` is `null` unless it is an `https` URL on `moddbcdn.vintagestory.at`. Behavior change.
- `GET /api/v1alpha1/mods/lookup/{slug}`: `homepage_url` and `source_url` are `null` unless a well-formed `https` URL of at most 2,048 characters with a host and no user info; `""` becomes `null`. Behavior change.
- `GET /api/v1alpha1/mods/browse`, `/mods/tags`, `/mods/gameversions`, `/mods/lookup/{slug}`, and the install and version change routes: a mod database body that is not a JSON object is 502 `EXTERNAL_API_ERROR` (existing code); before, 500 for the listing and the filtered listing. Changed status.
- No field is added, removed or renamed. Concurrent cold requests now share one mod database request (no contract change).

### ADR against the code

- **ADR-13 decision 1** lists what the helper raises for but not where the HTTP status check sits. The two fetchers that check HTTP 200 do it before parsing, and a test pins the `HTTP 503` message for a non-JSON 503; the helper takes `require_200` and checks before the parse. Decision 2 is kept exactly.
- **ADR-13 decision 5** does not mention `get_version_mod_ids`. Sharing the game version fetch exposes that it starts a filtered fetch without looking for a copy cached meanwhile; the story adds that check (Task 3.4) so the 18.3 test keeps its one request.
- **ADR-12 decision 3** says "no control character, space or backslash". The story refuses any Unicode whitespace too, because a no-break space passed both `_UNSAFE` and `urlsplit` in the prototype. Stricter, not different.
- **ADR-12 decision 6** does not say whether an empty value is logged; the story logs only a non-empty dropped URL (see "Logging").
- **Bead `VSS-0lkb`** says Story 19.4 adds the shared game version fetch; ADR-13 (decision 5) and the epic put it in this story. The bead text is stale; nothing to do in 19.4.
- Everything else in ADR-12 and ADR-13 matches the code at b6ae2f2 (line numbers re-read).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/...`. Concurrency tests run on the client with `asyncio` and a gated respx `side_effect`, not through `TestClient`.
- Router tests use the existing class fixtures, which build the `ModService` on `tmp_path`; `git status --short` after `just test-api` must show nothing under `dev/`.
- No test reaches the live mod database; the E2E stubs every mod database route.

### Security Requirements

- No new endpoint; lookup and browse stay readable by both roles. The change narrows what reaches `src` and `href`: no `javascript:`, `data:` or `http:` URL from the mod database leaves the API in these fields, and logo requests send no referrer (no manager origin leaks to the CDN).
- Logs never contain a dropped URL (author-controlled).
- A malformed upstream body no longer produces a 500 with a stack trace in the log; it is a logged `ExternalApiError` and a 502.

### Development Commands

- `just test-api tests/test_mod_media.py tests/test_mod_api.py tests/test_mod_service.py tests/test_mods_router.py tests/test_edge_cases.py`, `just test-web src/components/ModCard.test.tsx src/components/InstallConfirmDialog.test.tsx src/features/mods/ModDetailPage.test.tsx`, `just typecheck-api`, `just lint-api`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 and 18.2 process notes). Fix import order with `ruff check --select I --fix` on the touched files.

### Previous Story Intelligence

- **18.1:** `services/mod_media.py` and its tests; the reviewer probed 20 hostile URLs and could not get one through; the same table style applies. URL rules were tightened after the prototype showed `urlsplit` accepting whitespace and an empty port; this story found the no-break space the same way.
- **18.3:** `_version_fetch`, shielded waits, the done callback that retrieves exceptions, `close()` cancelling fetches, the type guards. Its review L2 recorded the unshared game version fetch this story fixes. `get_version_mod_ids` must keep its bounded wait.
- **18.2 / 17.4:** router tests must not write into `dev/`; a completion note must be true of the code; `feat`/`fix`/`perf` subjects describe what an admin can see.
- **17.3:** a TanStack Query v5 hook-level `onError` replaces the client default; this story adds no hook.
- **17.2:** E2E that changes real state needs a snapshot guard and must restore the stack exactly; this story's E2E changes nothing.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`). Stories 19.1 to 19.5 land first; 19.4 also edits `services/mod_api.py` and `services/mods.py`.
- Planned commits, subjects from the change proposal's release notes (section 2):
  - Task 1: `fix(story-19.6/task-1): pass on only https logo, homepage and source links from the mod database` (VSS-2zis; API and web in one commit, so the referrer change is part of the same release note)
  - Task 2: `fix(story-19.6/task-2): answer 502, not 500, when the mod database sends a malformed response` (VSS-ce0h)
  - Task 3: `perf(story-19.6/task-3): fetch the mod list once when several requests arrive together` (VSS-0lkb)
  - Task 4: `test(story-19.6/task-4): check mod logos and links from the mod database in the browser`
  - Task 5: `docs(story-19.6): ...`

### Project Structure Notes

- New: `web/e2e/mod-database-urls.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mod_media.py`, `services/mod_api.py`, `services/mods.py`, `routers/mods.py`, `models/mods.py`; `api/tests/test_mod_media.py`, `test_mod_api.py`, `test_mod_service.py`, `test_mods_router.py`; `web/src/components/ModCard.tsx`, `InstallConfirmDialog.tsx`, `web/src/features/mods/ModDetailPage.tsx` and their three test files. No fixture file.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.6: Mod Database Data Is Checked]
- [Source: _bmad-output/planning-artifacts/prd.md] FR224, FR225, FR226, FR227
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-12, #ADR-13, "Mod database data", "Mod Database Facts"]
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md] (ADR-1, decision 6 replaced)
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (ADR-1 normalization, extended by ADR-13)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (section 2: API contract changes and release-note subjects; open question 7: `http:` links dropped)
- [Source: _bmad-output/implementation-artifacts/18-1-mod-detail-media-and-links.md], [18-3-game-version-badge-on-browse-cards.md]
- Beads: `VSS-2zis`, `VSS-ce0h`, `VSS-0lkb`, parent `VSS-fl9b`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), BMAD dev-story, non-interactive.

### Debug Log References

- Line numbers re-read at c4fd594 (after Stories 19.1 to 19.5): `services/mods.py` mod_media import at `:56`, the three fields at `:779-783`, docstring at `:652-653`; `routers/mods.py` `logo_url=` at `:239`; `services/mod_api.py` `_is_json_object`/`_is_json_array` at `:262-269`, `get_mod` at `:372`, `get_all_mods` at `:681`, `_version_fetch` at `:780`, `get_version_mod_ids` at `:819`, `_fetch_mods_by_version` at `:865`, `get_game_versions` at `:965`. The story's references otherwise matched.
- Red runs: Task 1, 15 API tests (service and router) and 3 web tests failed before the change, and `tests/test_mod_media.py` failed to import; Task 2, 10 client tests (`get_all_mods` all six bodies, the filtered listing for `[]`, `"text"`, `null`, `5`; `get_mod` and `get_game_versions` were already guarded) and 3 router tests (listing, filtered listing, tags: 500) failed; Task 3, the module failed to import `SharedFetches`, and with only `get_all_mods` put back to an unshared fetch 6 of the 10 `TestSharedFetches` tests failed.
- `just test-api -k "a or b"` cannot pass a quoted expression through the Justfile recipe; whole files were run instead.
- `ruff format --diff` on the touched files shows unrelated, pre-existing reformatting, so no formatter was run; the one long line was wrapped by hand.
- `TestSharedFetches.test_close_cancels_every_running_fetch` first passed a mixed list of tasks to `asyncio.gather`, which pyright rejected (the element type is a union of two `Task` types); it awaits the three tasks as separate arguments instead.
- E2E: game server checked not running (`ps` in `vintagestory-manager-dev` found no `VintagestoryServer`) before `just docker restart`; `GET /api/v1alpha1/mods` (Admin key) was saved before and after the Playwright run and the bodies are byte-identical (`cmp`). A read-only check of the live API after the rebuild: `GET /mods/browse?page_size=50` returned 50 items, 39 with a logo, none off the CDN; the `betterruins`, `carryon` and `smithingplus` lookups returned 200 (`carryon` has no homepage, so `homepage_url` is null).

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) from Epic 19, ADR-12, ADR-13, the three beads and the code at b6ae2f2, and validated against the create-story checklist. A throwaway prototype of Tasks 1 to 3 (`external_link_url`, the three fields, `_get_json_object`, `SharedFetches` for all three fetches, the fresh-copy check) and of the web attribute was run against the whole API suite (2858 passed), the three web test files (165 passed), pyright on the changed files (0 errors) and a scratch set of 15 client tests (malformed bodies for the listing and the lookup, concurrent cold calls with a joined forced refresh, a shared failure, a cancelled waiter), then discarded.

- Task 1: `external_link_url` and `checked_url` in `services/mod_media.py`; the lookup's `logo_url` (image rule), `homepage_url` and `source_url` (link rule) and the browse item's `logo_url` (image rule, per page item only) go through `checked_url`, which logs `mod_url_dropped` with `slug` and `field` at debug level for a non-empty dropped URL and never logs the URL. The model and route docstrings say when the values are null. The three logo `<img>` elements carry `referrerPolicy="no-referrer"` right after `src`.
- Task 2: `ModApiClient._get_json_object` holds the three `httpx` error branches, the optional HTTP 200 check (before the parse), the JSON parse and the object check, logging `mod_api_timeout`, `mod_api_connection_error`, `mod_api_error`, `mod_api_http_error` or `mod_api_invalid_body` with `endpoint`. `get_mod` (`require_200=False`), `_fetch_all_mods` (`False`), `_fetch_mods_by_version` (`True`) and `_fetch_game_versions` (`True`) use it; each keeps its `statuscode` rule and normalization and writes its cache only on success. `cast` is gone from `mod_api.py`. `get_mod`'s "unreadable response (HTTP n)" message is now "invalid JSON".
- Task 3: `SharedFetches[K, T]` (PEP 695) replaces the body of `_version_fetch` and shares the full listing and the game version list (key `None`). `get_all_mods` and `get_game_versions` await `asyncio.shield(...)` of the shared task whenever the cache is not used, so a forced refresh joins a running fetch. `get_version_mod_ids` checks for a fresh copy of the tag's listing after the game version list resolves. `close()` cancels and awaits all three. The `clear_*_cache` docstrings say a running fetch is left to finish and fills the cache.
- Task 4: `web/e2e/mod-database-urls.spec.ts` (3 tests) stubs browse, game versions, tags, both lookups and the CDN, loads the Admin key through `serveConfigKey` (Story 19.2) and refuses every non-GET. 13 passed with `mod-detail-media.spec.ts` and `browse-game-version.spec.ts` on the stack rebuilt from this branch. No screenshot was taken; the game server was not started or stopped.
- Task 5.1: `just check` passes: ruff clean, pyright 0 errors and the 3 known warnings (VSS-1ar), API 3334 passed, web 3349 passed and 4 skipped (VSS-hnl), script tests pass. No suppression and no `cast` added. `git status --short` shows nothing under `dev/`. `just changelog` lists the two Fixes and the Performance entry with the planned subjects.
- Task 5.2 (manual check) is left for the maintainer, as the story requires. Task 5.3: status `review` and sprint status set; the PR and the PR links on `VSS-2zis`, `VSS-ce0h` and `VSS-0lkb` are left to the orchestrator (this run does not push, open PRs or change beads).
- No existing test was changed apart from the three web tests that gained `referrerpolicy` assertions and the extended `does not render optional links when null` test, as the story plans.

### File List

- `api/src/vintagestory_api/services/mod_media.py`
- `api/src/vintagestory_api/services/mod_api.py`
- `api/src/vintagestory_api/services/mods.py`
- `api/src/vintagestory_api/routers/mods.py`
- `api/src/vintagestory_api/models/mods.py`
- `api/tests/test_mod_media.py`
- `api/tests/test_mod_api.py`
- `api/tests/test_mod_service.py`
- `api/tests/test_mods_router.py`
- `web/src/components/ModCard.tsx`
- `web/src/components/ModCard.test.tsx`
- `web/src/components/InstallConfirmDialog.tsx`
- `web/src/components/InstallConfirmDialog.test.tsx`
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `web/e2e/mod-database-urls.spec.ts` (new)
- `_bmad-output/implementation-artifacts/19-6-mod-database-data-is-checked.md`

## Change Log

- 2026-11-17: Story 19.6 created and validated (ready-for-dev).
- 2026-11-16: Tasks 1 to 4 and 5.1 implemented; status review. Manual check 5.2, the PR and the bead links of 5.3 remain.
