# Epic 18: Mod Media and Fixes - Architecture Decisions

Decisions from the Epic 18 course correction (2026-11-16). Epic 18 has no preparation story. Each decision was checked by reading the code at commit `574e125` (`main` after Epic 17), and file and line references are to that commit. The mod database facts were checked on 2026-11-16 with unauthenticated requests to the public API (`https://mods.vintagestory.at/api/...`). Where a story has to measure or confirm something first, the ADR says so.

## Mod Database Facts (checked 2026-11-16)

**Mod entry, `GET /api/mod/{slug}`.** Besides the fields the API already reads, an entry carries `screenshots` and `trailervideourl`. Seven named mods and the 45 most downloaded mods were fetched.

| Mod | Screenshots | `trailervideourl` |
|---|---|---|
| `betterruins` | 10 | `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM` |
| `expandedfoods` | 7 | `""` |
| `smithingplus` | 5 | `""` |
| `carryon` | 1 | `""` |
| `canjewelry` | 4 | `""` |
| `primitivesurvival` | 9 | `""` |
| `playercorpse` | 0 (`[]`) | `null` |

- Every screenshot object has exactly the keys `fileid`, `filename`, `mainfile`, `thumbnailfilename`, `created`. Across the 45 most downloaded mods (202 screenshots, 0 to 11 per mod, 7 mods with none), every `mainfile` and `thumbnailfilename` was an `https://moddbcdn.vintagestory.at/` URL, every `filename` a non-empty string and every `fileid` an int. No null thumbnail, `http:` URL or other host was seen. The API does not promise that, and the same API returns nulls elsewhere (Epic 17 ADR-1).
- Every thumbnail is the 55x60 pixel variant (`..._55_60.jpg`). One sampled thumbnail is 1,939 bytes; its full image is 554,970 bytes.
- The CDN serves images without a `Referer` header and with `access-control-allow-origin: *` and `cache-control: public, max-age=2592000`.
- `trailervideourl` across the same 45 mods: `""` 33 times, `null` 7 times, `https://www.youtube-nocookie.com/watch?v=<id>` 4 times, and once `https://apachegaming.net`, which is a website and not a video.
- `https://www.youtube-nocookie.com/watch?v=<id>` returns 404 when opened. The mod database's own page embeds `https://www.youtube-nocookie.com/embed/<id>` (200), and `https://www.youtube.com/watch?v=<id>` returns 200. The API value cannot be used as a link without rewriting it.
- The entry also has `logofile`, `logofiledb`, `issuetrackerurl`, `wikiurl`, `lastmodified` and `comments`, which the API does not read. They are not part of Epic 18.

**Listing, `GET /api/mods`.** 9,633 items, 4,248,716 bytes, 1.7 s. Each item has `assetid`, `author`, `comments`, `downloads`, `follows`, `lastreleased`, `logo`, `modid`, `modidstrs`, `name`, `side`, `summary`, `tags`, `trendingpoints`, `type`, `urlalias`. There are no releases and no game versions. None of the 209 distinct `tags` values parses as a version. 180 items have an empty `modidstrs`. `logo` is an `https://moddbcdn.vintagestory.at/` URL for 6,528 items and `null` for 3,105.

**Filtered listing, `GET /api/mods?gameversion=<tagid>`.** For the tag of 1.22.7 it returns 5,651 items, 2,544,049 bytes, 2.0 s, with the same keys per item. Every item's `modid` is an int and is in the unfiltered listing. `betterruins`, `carryon` and `expandedfoods` are in it; `playercorpse` (last tagged for 1.21.1) is not. The array form `?gameversions[]=<tagid>` returns 2,829 items, a subset of the first. Its meaning is not documented, so nothing here uses it.

**Game versions, `GET /api/gameversions`.** 247 tags, 15,804 bytes, each `{tagid, name, color}`.

## Content Security Policy and Image Loading (checked in the code)

- Nothing sets a `Content-Security-Policy`, `frame-src` or `img-src`. `web/index.html` has no CSP `<meta>` tag, `web/vite.config.ts` sets no headers, the `Dockerfile` and compose files contain no reverse proxy configuration, and the API registers only CORS, CORS logging and request context middleware (`main.py:186-200`). The only security headers the API sends are on `/config.js` (`main.py:263-271`).
- The mod logo is loaded straight from the CDN. The lookup returns `logo_url=mod["logofilename"]` (`services/mods.py`, `lookup_mod`) and the browse item returns `logo_url=mod["logo"]` (`routers/mods.py:197-230`). `ModDetailPage.tsx:609-614` and `ModCard.tsx:97-103` put the URL in `<img src>`. Nothing is proxied or checked.
- Mod descriptions keep `<img>` from any host. DOMPurify's defaults drop `<iframe>`, and `lib/mod-description.ts` also forbids `style` and form elements.

So gallery images load today without any configuration change. If a deployment puts a CSP in front of the app, it already has to allow `img-src https://moddbcdn.vintagestory.at` for logos. Epic 18 adds no other origin (ADR-2).

## ADR-1: Mod Media Is Normalized, Then Filtered by an Allow-List in the API

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.1. Extends Epic 17 ADR-1.

**Context:**

- Nothing in `api/src` or `web/src` reads `screenshots` or `trailervideourl` today.
- Epic 17 ADR-1 normalizes mod database data once, in `models/moddb.py` (`MOD_FIELDS`, `RELEASE_FIELDS`, `normalize_mod`, `normalize_release`). Unknown keys are copied unchanged, so `screenshots` reaches `lookup_mod` exactly as the mod database sent it.
- The web puts mod database URLs into `src` and `href`. A URL from the mod database is author-controlled data.

**Decision:**

1. **Types, in the normalizer.** `MOD_FIELDS` gains `screenshots` and `trailervideourl`. `screenshots` becomes a list of objects, with elements that are not objects dropped. A new `SCREENSHOT_FIELDS` table normalizes each one: `mainfile` and `thumbnailfilename` as optional text, `filename` as text, `fileid` as an optional int, `created` as optional text. `trailervideourl` is optional text. The normalizer checks types only, as it does for every other field.
2. **URL policy, in one function.** A new module `services/mod_media.py` holds the rule for a mod database image URL. The URL is kept only when it parses, its scheme is exactly `https`, its host is in `MOD_MEDIA_HOSTS` (one entry, `moddbcdn.vintagestory.at`, compared case-insensitively), and it has no user info and no port. Anything else is `None`.
3. **What happens to anything else.** A screenshot whose `mainfile` fails the rule is dropped from the list. A screenshot whose thumbnail fails or is missing keeps its place and uses the full image URL as its thumbnail. A dropped item is logged at debug level with the mod slug and never fails the lookup.
4. **API.** `ModLookupResponse` gains `screenshots: list[ModScreenshot]`, default `[]`, in mod database order. `ModScreenshot` has `image_url`, `thumbnail_url` and `filename`. The web types gain `screenshots: ModScreenshot[]` with `imageUrl`, `thumbnailUrl` and `filename`. The trailer field is ADR-2.
5. **The web trusts the API's list.** It renders `image_url` and `thumbnail_url` as given and does not repeat the check, so there is one definition of an allowed media URL.
6. **Not changed.** `logo_url` keeps passing through unchecked, as do images inside descriptions. Applying the allow-list to the logo is a follow-up, not part of `VSS-l4x`.

**Consequences:**

- The lookup response grows by about 250 bytes per screenshot (three strings each).
- Story 18.1 adds a fixture with the `betterruins` shape and a synthetic one with an `http:` URL, another host, a null thumbnail, a null element and a non-list `screenshots`.
- If the mod database moves its images to another host, the gallery is empty until `MOD_MEDIA_HOSTS` is updated. That is the cost of an allow-list, and it is a one-line change.

## ADR-2: The Trailer Is a Link, and the Gallery Uses Existing Components

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.1.

**Context:**

- The trailer value is a `youtube-nocookie.com/watch` URL that returns 404, an empty string, `null`, or any URL an author typed (see the facts above).
- An embedded player is an `<iframe>` to YouTube. It contacts Google when the admin opens the mod page, before any click. The app has no CSP today, so an embed would load, but any deployment that adds one would need `frame-src https://www.youtube-nocookie.com`.
- The web has Radix `Dialog` (`components/ui/dialog.tsx`), `Button` and `lucide-react` icons. It has no carousel library, and the maintainer approves new dependencies.

**Decision:**

1. **Link, not embed.** The detail page shows a "Watch trailer" link when the API returns a trailer URL. Nothing from YouTube loads until the admin clicks it.
2. **The API rewrites the URL.** `services/mod_media.py` accepts an `https` URL whose host is `www.youtube-nocookie.com`, `youtube-nocookie.com`, `www.youtube.com`, `youtube.com`, `m.youtube.com` or `youtu.be`, in the forms `/watch?v=<id>`, `/embed/<id>` and `youtu.be/<id>`, where the ID matches `^[A-Za-z0-9_-]{11}$`. It returns `https://www.youtube.com/watch?v=<id>`, built from the ID alone. Everything else, including `https://apachegaming.net`, gives `None`.
3. **API.** `ModLookupResponse` gains `trailer_url: str | None` (`trailerUrl` in the web types).
4. **Link attributes.** `target="_blank"`, `rel="noopener noreferrer"`, an external-link icon and the "(opens in a new tab)" text for screen readers, the same marking Story 18.1 gives description links.
5. **Gallery from existing components, no new dependency.** A "Screenshots" card between the header and the description, hidden when the list is empty. It shows one current image with Previous and Next buttons and a position such as "3 of 10", and a strip of thumbnail buttons. Activating the current image opens it in a `Dialog`, which gives focus trapping and Escape. Left and Right arrow keys move between images in the card and in the dialog. Previous and Next are 44px targets, so touch works without a gesture library. Swipe gestures are not required.
6. **Loading.** Thumbnails come from `thumbnail_url` (about 2 KB each, shown at their native 55x60). Only the current image loads its `image_url` (about 0.5 MB in the sample); the others load when selected. Every `<img>` has `loading="lazy"`, `referrerPolicy="no-referrer"` and alt text built from `filename` ("Screenshot 3 of 10: ToolRepair.png").
7. **Rejected: shadcn's Embla carousel.** It is a new runtime dependency for a feature that needs a current index and two buttons.

**Consequences:**

- No CSP consequence. `img-src https://moddbcdn.vintagestory.at` is already needed for logos, and no `frame-src` is needed.
- Clicking the trailer link opens `youtube.com`, not the privacy-enhanced domain, because that domain has no watch page. The click is the admin's choice and sends no referrer. The alternative target, `https://www.youtube-nocookie.com/embed/<id>` opened as a page, is an open question for the maintainer.
- A mod whose trailer field holds a non-video URL shows no trailer link. Its Homepage link is unaffected.

**Related, same story (`VSS-tzl`).** `lib/mod-description.ts:21-30` adds `target="_blank"` to every description link. The same hook appends a visually hidden `(opens in a new tab)` span to each such link, and the description container's CSS draws an external-link icon after it. `aria-label` is not used, because it would replace the link's own text for screen readers. No separate decision is needed.

## ADR-3: The Game Version Flag on Browse Cards Comes from One Cached, Filtered Listing

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.3. Supersedes Epic 10 ADR-2 (Conservative Compatibility Badge) for browse cards and replaces decision 6 of Epic 16 ADR-2 ("Browse cards are unchanged"). Epic 16 ADR-2 decisions 1 to 5 stand.

**Context:**

- The listing has no per-release data (facts above), so a card cannot work out compatibility from it. Epic 10 ADR-2 answered that with a fixed "not verified" for cards. Today `getBrowseCardCompatibility()` (`web/src/lib/mod-compatibility.ts:38`) is called only by its own test, and `ModCard` shows no compatibility information.
- The mod database answers "which entries have any release tagged for version X" in one request (5,651 of 9,633 for 1.22.7).
- `ModApiClient.get_all_mods` caches the listing in memory for 5 minutes (`BROWSE_CACHE_TTL`, `services/mod_api.py:278`, `:593-628`). `get_game_versions` caches the name-to-tag map for 1 hour (`:279`, `:767`). `get_mods_by_version` is not cached (`:665-755`). The browse route already calls it when the admin picks a version in the filter (`routers/mods.py:326-337`), so each such request, including each page change, costs 2.5 MB and about 2 s.
- The installed game version comes from `ModService.game_version()` (`services/mods.py:351-353`), which calls `installed_game_version` (`services/mod_updates.py:542-548`), which reads the `current_version` file on every call (`services/server.py:511-520`). It is `None` when no server is installed.

**Decision:**

1. **Cache filtered listings by tag ID.** `ModApiClient` keeps the result of `get_mods_by_version` per tag ID, with the fetch time and the set of numeric `modid` values in it. The lifetime is `BROWSE_CACHE_TTL`. At most three tag IDs are kept, the oldest dropped first. `clear_browse_cache` clears them too. The existing version filter is served from the same cache.
2. **One set lookup per page.** For each browse request the route reads the installed game version, maps it to a tag ID with `get_game_versions`, and asks the client for that version's `modid` set. Each item on the page gets `modid in the set`. Matching uses the numeric `modid`, which both listings carry for every item; 180 listing items have no mod ID string.
3. **No per-card request,** from the API or from the web.
4. **Invalidation.** The cache key is the tag ID of the version read on each request. When the admin installs another game version, the next browse request asks for another key. Nothing has to be cleared.
5. **Unknown version or failed lookup.** The flag is `null` for every item when no server is installed, when the installed version has no tag in the mod database, or when the filtered listing cannot be fetched and no earlier copy for that tag exists. An expired copy is used when the refresh fails. The browse request itself still succeeds; only a failure of the main listing is a 502, as today.
6. **Cold cache.** When both caches are cold the route fetches the listing and the filtered listing concurrently, so the first page costs about the slower of the two requests (2.0 s measured) and not their sum.
7. **API.** `ModBrowseItem` gains `has_release_for_game_version: bool | None`. `ModBrowseResponse` gains `game_version: str | None`, the version the flags refer to, `null` when the flags are `null`. Web types: `hasReleaseForGameVersion` and `gameVersion`.
8. **What the flag means.** "At least one release of this mod database entry is tagged for exactly this game version." It is not the release an install would pick (Epic 17 ADR-2), it is not per mod ID for an entry with several, and a mod tagged only for 1.22.6 is `false` on 1.22.7 even if it works.
9. **What the card shows.** `true`: a small badge "Has a release for 1.22.7". `false`: muted text "No release for 1.22.7". `null`: nothing. The card never uses the words "Compatible" or "Incompatible" and never the `CompatibilityBadge` component. The detail page and the install dialog stay the place where compatibility of a specific release is judged.
10. **Epic 10 ADR-2's rule survives in a narrower form.** With no data the card makes no claim. `getBrowseCardCompatibility()` and its test are removed.
11. **Rejected: a lookup per card** (up to 9,633 requests). **Rejected: the web calling the filtered browse endpoint itself and intersecting,** which needs a second paged request per page and duplicates the paging logic. **Rejected: the array form `gameversions[]`,** whose meaning is unknown.

**Consequences:**

- A browse page can say whether a mod has a release for the installed version without a request per mod.
- Memory: up to three filtered listings of about 5,600 small dictionaries each, beside the 9,633-item listing already held.
- Version-filtered browsing becomes up to 5 minutes stale, the same as unfiltered browsing, and stops costing a 2.5 MB request per page change.
- Story 18.3 tests the route with a stubbed client for `true`, `false`, no installed server, a version without a tag, a failed filtered listing with and without an earlier copy, and a changed installed version.

## ADR-4: Install Refuses a File-Name Collision

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.2.

**Context:**

- `_place_install` (`services/mods.py:1234`) copies the archive to `<name>.tmp` and then calls `temp_path.rename(dest_path)` (`:1261`). A rename replaces an existing file of that name.
- If the import or the state save then fails, the cleanup deletes `dest_path` (`:1299`) and removes the state entry for that file name (`:1301`). After a collision both of those belong to the other mod.
- Story 17.3 refuses an install when the archive's own mod ID is installed (`install_mod`, step 6). It does not cover two different mod IDs whose release files share a name, or an archive whose `modinfo.json` cannot be read.
- A disabled mod's file is `<name>.disabled` (`disable_mod`, `:785`). Installing a file called `<name>` beside it would leave two files that become the same name on enable.
- `_apply_version_change` already refuses the same situation: when the new file name exists and is not the mod's own file it raises `ModVersionChangeFailedError` with "`<name>` already exists in the mods directory" (`:979-982`), which the router returns as 500 `MOD_VERSION_CHANGE_FAILED`.

**Decision:**

1. **Check before anything is written.** At the start of `_place_install`, before the copy, the install is refused when `mods_dir/<name>` or `mods_dir/<name>.disabled` exists (including a dangling symlink), or when the mod state has an entry under either file name.
2. **Nothing is touched.** The check is before the temporary copy and before the `try` blocks, so no cleanup runs and the existing file and state entry are left exactly as they were.
3. **No await.** `_place_install` is synchronous and runs under the install lock (Epic 17 ADR-3), so nothing can create the file between the check and the rename.
4. **Error.** A new `ModFileConflictError`, returned by `POST /mods` as 409 with the new code `MOD_FILE_CONFLICT` and a message that names the file: "Cannot install '`<slug>`': a file named `<name>` already exists in the mods directory."
5. **Why 409.** The request is valid and conflicts with what is on the server, like `MOD_ALREADY_INSTALLED` on the same route. The wording mirrors the version change's refusal. Its status does not: 500 says the server failed, and here the admin can act (remove or rename the other file).
6. **Not changed:** the version change's own refusal stays 500 `MOD_VERSION_CHANGE_FAILED`, and `enable_mod` and `disable_mod` still rename without checking the target (`:730`, `:788`). Both are follow-ups.

**Consequences:**

- Installing a mod can no longer overwrite or delete another mod's file.
- The admin sees which file is in the way. Mods whose releases share a file name cannot both be installed through the manager until one file is renamed by hand; that was already broken, silently.
- Tests: another mod's file with the download's name, its `.disabled` form, a state entry without a file, and a failing import after a clean placement (the cleanup still removes only the new file).

## ADR-5: A Version Change Hands Its Lookup to a Recorder

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.2. Completes Story 17.4 for version changes.

**Context:**

- An install stores the new mod's update record from its own lookup. `InstallResult.releases` carries the releases (`services/mods.py:221-247`), and the route calls `update_service.record_install(result.slug, result.releases)` (`routers/mods.py:704`). The route builds its response field by field, so `releases` is not sent.
- A version change does not. `_prepare_version_change` fetches the entry and builds `releases = [StoredRelease.from_api(r) ...]` (`services/mods.py:1078`), uses them, and drops them.
- The stored list can be older than the release an admin picks on the detail page. The Installed list then shows "Unknown" (reason `installed_release_not_listed`) until the next check.
- `VersionChangeResult` is a frozen dataclass (`services/mods.py:198-209`) that the route serializes whole with `asdict(result)` (`routers/mods.py:1071`). Any field added to it becomes part of the API response.
- `ModUpdateService` already depends on `ModService` (`mod_source=get_mod_service()`, `services/mod_updates.py:564-567`), so `ModService` cannot hold the update service without a cycle. The routes compose the two.
- Update All calls `change_version` through a callable the route passes in (`routers/mods.py:164`, `ChangeVersion`, `services/mod_updates.py:263`).

**Decision:**

1. **`VersionChangeResult` does not change,** and neither does `asdict(result)`. The response of `PUT /mods/{slug}/version` keeps exactly its seven keys, and a test asserts the key set.
2. **`PreparedVersionChange` carries the releases.** It is internal and never serialized. It gains `releases: list[StoredRelease]`, every release of the entry as `_prepare_version_change` already builds them.
3. **A recorder parameter.** `ModService.change_version` gains a keyword-only `record_releases: Callable[[str, list[StoredRelease]], None] | None = None`. After `_apply_version_change` returns, and still inside the mod's lock, it calls `record_releases(slug, prepared.releases)`.
4. **`ModUpdateService.record_releases(modid, releases)`** stores the record, clears the mod's lookup error and saves, and never raises. It is the body of today's `record_install`, which becomes a thin wrapper that converts the raw releases first.
5. **Both callers pass it.** The version change route passes `update_service.record_releases`. The Update All route passes `change_version` with the recorder bound.
6. **Only a completed change records.** A request for the version already installed makes no lookup (`changed: false`) and records nothing. A change that fails or is rolled back records nothing.
7. **A recorder failure never fails the change.** The mod then keeps its previous record until the next check, as after a failed `record_install`.
8. **Rejected: a `releases` field on `VersionChangeResult`.** It would be serialized into the response, a few hundred releases for some mods, unless every `asdict` call site remembered to drop it. **Rejected: a wrapper return type,** which changes every caller and test of `change_version` for one optional side effect. **Rejected: `ModService` holding the update service,** because of the dependency cycle.

**Consequences:**

- After a version change the Installed list shows a real status for the new version at once.
- The stored record's `checked_at` for that mod is the time of the change. `last_full_check` and the notified versions are untouched, so webhook alerts behave as before.
- No API shape changes. The effect is visible in `GET /mods/updates`.

## ADR-6: The Installed List Keeps One Sort Preference, and the Name Column Wraps

**Status:** Accepted (Epic 18 planning). Implemented by Story 18.4. Changes acceptance criterion 2 of Story 17.8 ("the table is unchanged at 1024px or wider") for rows with long names.

**Context, sort (`VSS-bgu`):**

- `ModTable` renders the table from `lg` (`LG_UP_QUERY`, `(min-width: 64rem)`, `hooks/use-media-query.ts:17`) and the cards below it (`ModTable.tsx:131`, `:369-418`). Story 17.8 moved the switch from `md` to `lg`, so the cards now cover phones and tablets.
- Both layouts render `table.getRowModel().rows`. The sort state is `preferences.installedModsSort` (`ModTable.tsx:150-153`), a `{column, direction}` pair with columns `name`, `version` and `enabled`, kept in the `vs_ui_prefs` cookie (`contexts/PreferencesContext.tsx:28-34`, `:51`, `:196`).
- Only the table headers can change it.

**Decision, sort:**

1. **Same preference.** A sort control above the cards calls `setInstalledModsSort`. There is no second preference and no URL state. Sorting in one layout is the sort in the other.
2. **Where.** `ModTable` renders it, only when the cards are shown, since `ModTable` owns the layout switch and the sort handlers.
3. **Controls.** The existing `Select` (`components/ui/select.tsx`) for the column, with Name, Version and Status (the `enabled` column), and a button that flips the direction and names the result in its label ("Sort ascending" or "Sort descending"). Both are 44px tall below `lg`, like the toolbar buttons.

**Context, long names (`VSS-n2u`).** Story 17.8 measured the page with a 63-character mod name and an offered pre-release update (`_bmad-output/implementation-artifacts/17-8-browser/layout_widths.after.json`):

| Viewport | Sidebar | Table needs | Container | Result |
|---|---|---|---|---|
| 1024 | expanded | 1183 | 816 | scrolls inside itself |
| 1024 | collapsed | 1183 | 912 | scrolls inside itself |
| 1440 | expanded | 1232 | 1232 | fits |
| 1440 | collapsed | 1328 | 1328 | fits |

- The page outside the container takes 208px with the sidebar expanded (184 left, 24 right) and 112px collapsed.
- Every cell is `whitespace-nowrap` (`components/ui/table.tsx:71`, `:84`), so the row is as wide as its longest name.
- The same table with five short names and no offered update needed 751px (`VSS-dp1`).

**Decision, long names:**

1. **Wrap the Name column.** The Name cell gets `whitespace-normal` and `break-words` with a minimum width, set through the column's `meta.className` in `ModTable`, which the story applies to body cells as well as headers (today only headers, `ModTable.tsx:372-376`). `components/ui/table.tsx` does not change, so the other tables keep their behavior.
2. **Rejected: a wider breakpoint.** The 1183px table needs a 1391px viewport with the sidebar expanded and 1295px collapsed. Tailwind's `xl` (1280px) gives containers of 1072px and 1168px, both too narrow. `2xl` (1536px) would fit, and would put every laptop below 1536px on the cards. The width needed also still depends on the longest installed name, so any fixed breakpoint is a guess.
3. **Measured in the story, not assumed.** The other six columns were not measured one by one. Story 18.4 extends `layout_widths.mjs` to record each column's width, and passes when the table container does not scroll at 1024px with the sidebar expanded (816px) for the Story 17.8 fixture. If the other columns leave less than the Name column's minimum, the Available cell may also stack its offered version above the Update button; the story records the numbers and what it changed.
4. **`LG_UP_QUERY` does not change.**

**Consequences:**

- At 1024px and wider, a row with a long name is taller and no longer wider than its container. Rows with short names look as they do today.
- Tablet and phone users can reorder the cards, and the order follows them to the table.
