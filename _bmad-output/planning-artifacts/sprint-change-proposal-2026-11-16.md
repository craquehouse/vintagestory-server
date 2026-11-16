# Sprint Change Proposal: Mod Media and Fixes (Epic 18)

**Date:** 2026-11-16
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (batch, non-interactive; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Scope approved by Matt, 2026-11-16. The wording, the ADRs and the open questions in section 5 have not been reviewed yet.

## 1. Issue Summary

**Trigger:** Epic 17 is done and on `main` (`574e125`). The maintainer picked seven open beads for the next epic: two features Epic 17 left out as "new capabilities, not corrections" (`VSS-l4x`, `VSS-4f3`), one older phone task (`VSS-bgu`), and four follow-ups filed during Epic 16 and Epic 17 reviews (`VSS-tzl`, `VSS-z7e`, `VSS-do7`, `VSS-n2u`). The screenshot gallery (`VSS-l4x`) is the one the maintainer wants most.

**Problem:** The mod detail page shows less than the mod database's own page, and a browse card gives no hint about the installed game version, so an admin opens mods one by one to find usable ones. Beside that, an install can overwrite another mod's file, a version change can leave "Unknown" in the Installed list, and the Installed list cannot be sorted below 1024px and scrolls inside itself at 1024px with a long name.

**Evidence** (code at commit `574e125`, mod database checked on 2026-11-16; details and line references in `architecture/epic-18-mod-media-and-fixes.md`):

- `GET https://mods.vintagestory.at/api/mod/{slug}` returns `screenshots` and `trailervideourl`. Nothing in `api/src` or `web/src` reads them (`VSS-l4x`). Samples: `betterruins` 10 screenshots and a trailer, `expandedfoods` 7, `smithingplus` 5, `carryon` 1, `playercorpse` 0. All 202 screenshot URLs across the 45 most downloaded mods are `https://moddbcdn.vintagestory.at/` URLs; thumbnails are 55x60 pixels.
- The trailer value is not usable as it stands. `https://www.youtube-nocookie.com/watch?v=<id>` returns 404, and one of the 45 mods has `https://apachegaming.net` in the field.
- The app sets no Content-Security-Policy anywhere, and loads mod logos straight from the CDN, so gallery images load without configuration.
- `lib/mod-description.ts` gives every description link `target="_blank"` and nothing marks it (`VSS-tzl`).
- `_place_install` renames the download over any file of the same name (`services/mods.py:1261`), and its cleanup deletes that file and its state entry (`:1299`, `:1301`) (`VSS-z7e`).
- `_prepare_version_change` builds the entry's releases (`services/mods.py:1078`) and drops them; only installs store an update record (`routers/mods.py:704`) (`VSS-do7`). `VersionChangeResult` is serialized whole (`routers/mods.py:1071`).
- The listing (`/api/mods`, 9,633 items, 4.2 MB) has no per-release data. `/api/mods?gameversion=<tagid>` returns the 5,651 entries with a release tagged for 1.22.7 in one request (2.5 MB, 2.0 s). `ModApiClient.get_mods_by_version` calls it uncached, and the browse filter pays that on every page change (`VSS-4f3`).
- The installed mod cards follow `preferences.installedModsSort`, which only the table headers can change (`VSS-bgu`). With a 63-character name the table needs 1183px in an 816px container at 1024px (`VSS-n2u`).

**Scope decisions (made by the maintainer before the workflow ran):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-l4x`, `VSS-4f3`, `VSS-z7e`, `VSS-do7`, `VSS-tzl`, `VSS-bgu`, `VSS-n2u` (7 issues, 4 stories) |
| Grouping | As proposed by the maintainer, unchanged: 18.1 `VSS-l4x` + `VSS-tzl`, 18.2 `VSS-z7e` + `VSS-do7`, 18.3 `VSS-4f3`, 18.4 `VSS-bgu` + `VSS-n2u` |
| Order | 18.1 first (the gallery). Then 18.2, 18.3, 18.4 |
| Preparation story | None. The mod database was probed during planning and the results are in the ADR file |
| New dependencies | None. A carousel library needs maintainer approval, so the gallery is built from existing components (ADR-2) |
| `VSS-1ar`, `VSS-hnl`, `VSS-6wj` | Not in scope: known items that predate this epic |
| Anything else found while planning | Reported as follow-ups in section 5; no beads created by this workflow |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 17 are done; none is invalidated. One new epic, Epic 18: Mod Media and Fixes, with 4 stories. No resequencing.

**Story impact:** No existing story changes. Story 18.1 extends Epic 17 ADR-1's normalizer. Story 18.2 completes Story 17.4 (update record) for version changes and closes a gap Story 17.3 listed as not changed. Story 18.3 supersedes Epic 10 ADR-2 for browse cards and replaces decision 6 of Epic 16 ADR-2. Story 18.4 changes acceptance criterion 2 of Story 17.8 for rows with long names.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR194-FR204; frontmatter |
| Epics | Add Epic 18; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-18-mod-media-and-fixes.md` (facts, ADR-1 to ADR-6); index entry |
| UX spec | None. The gallery follows the existing breakpoints and 44px touch targets |
| Beads | Epic `Epic 18: Mod Media and Fixes` with the 7 in-scope issues as children |

**Technical impact:**

- Stories 18.1 and 18.3 change the API and the web. Story 18.2 is API only. Story 18.4 is web only.
- No new dependencies, no configuration, no deployment change.
- The web starts loading up to 11 thumbnails (about 2 KB each) and one full image (about 0.5 MB in the sample) per mod detail page, from the same CDN that serves logos.
- The API holds up to three more filtered listings in memory (about 5,600 small dictionaries each).

**API contract changes, all in `v1alpha1` (for the release notes):**

| Story | Endpoint | Change | Kind |
|---|---|---|---|
| 18.1 | `GET /mods/lookup/{slug}` | New `screenshots`: list of `{image_url, thumbnail_url, filename}`, `[]` when none | Added field |
| 18.1 | `GET /mods/lookup/{slug}` | New `trailer_url`: a `https://www.youtube.com/watch?v=<id>` URL or `null` | Added field |
| 18.2 | `POST /mods` | New error: 409 `MOD_FILE_CONFLICT` when a file with the download's name, or its `.disabled` form, is already in the mods directory. Before, the install succeeded and overwrote the file | New error code, behavior change |
| 18.2 | `PUT /mods/{slug}/version`, `POST /mods/updates/apply-all` | Response unchanged. A completed change now stores that mod's update record, so `GET /mods/updates` reports its status at once | Side effect only |
| 18.3 | `GET /mods/browse` | New `game_version` (string or `null`) beside `mods` and `pagination` | Added field |
| 18.3 | `GET /mods/browse` | New `has_release_for_game_version` (`true`, `false` or `null`) on every item | Added field |
| 18.3 | `GET /mods/browse?version=...` | Results for a version filter are cached for up to 5 minutes, like unfiltered results | Behavior change |

No field is removed or renamed and no existing error code changes.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 18 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Four stories tied to existing beads. Effort small to medium, risk low. |
| 2. Rollback | Not viable. Nothing completed has to be undone. |
| 3. MVP Review | Not needed. |

**Effort:** Small to medium. Two issues are size-m in beads (`VSS-l4x`, `VSS-4f3`) and five are size-s. Story 18.1 is the largest: two API fields, a gallery with a dialog, and tests at two widths.

**Risks:**

- Story 18.1: the allow-list has one host. If the mod database moves its images, galleries are empty until the constant changes. Accepted; the alternative is passing author-controlled URLs to `src`.
- Story 18.1: the trailer link opens `youtube.com`, because the privacy-enhanced domain has no watch page. See open question 1.
- Story 18.2: mods whose releases share a file name can no longer both be installed. They could not safely before; now the admin is told why.
- Story 18.3: "No release for 1.22.7" can be read as "incompatible". The wording avoids that word and the flag's meaning is in ADR-3, but it is the item most worth a look by the maintainer (open question 2).
- Story 18.3: the mod database's filtered listing is a second large request. It is fetched at most once per 5 minutes per version and a failure degrades to no indicator.
- Story 18.4: the Name column's minimum width depends on column widths that have not been measured one by one. The story measures first.
- Stories 18.1, 18.2 and 18.3 edit the same three files in different places; in parallel they would conflict.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** `lastUpdated: '2026-11-16'`; update entry "Added FR194-FR204 for Epic 18 (Mod Media and Fixes)".

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 18: Mod Media and Fixes

#### Mod Detail Page

- FR194: The mod detail page shows the mod's screenshots from the mod database as a gallery with thumbnails, previous and next, and a larger view; the gallery is hidden when the mod has no screenshots
- FR195: The gallery works with the keyboard and on touch screens, gives each image alt text from its file name, loads images lazily, and fits phone widths in the light and dark themes
- FR196: A mod with a trailer video has a link on its detail page that opens the trailer in a new tab; no video player is embedded
- FR197: The API passes on only screenshot URLs that use https on the mod database's image host, and only trailer URLs that name a YouTube video; anything else is left out and never fails the lookup
- FR198: Links in a mod description are marked as opening in a new tab, visibly and for screen readers

#### Install and Version Change

- FR199: Installing a mod whose file name is already used in the mods directory, enabled or disabled, is refused with 409 and changes no file and no state
- FR200: After a version change, the mod's stored update record comes from that change's own lookup, so the Installed list shows a real status for the new version without waiting for the next update check

#### Mod Browser

- FR201: Mod browser cards show whether the mod has a release tagged for the installed game version, from one cached request per game version and never a request per card
- FR202: When the installed game version is unknown or the mod database cannot answer, cards show no game version indicator and browsing works as before

#### Installed Mods

- FR203: The installed mod cards have a sort control (name, version or status, ascending or descending) that uses the same saved preference as the table headers
- FR204: At 1024px and wider, the installed mods table fits its container when a mod has a long name: nothing scrolls sideways and the enable toggle and remove action are on screen
```

**FR to story map:**

| Story | Sprint key | FRs | Beads |
|---|---|---|---|
| 18.1 Mod Detail Page Media and Links | `18-1-mod-detail-media-and-links` | FR194, FR195, FR196, FR197, FR198 | `VSS-l4x`, `VSS-tzl` |
| 18.2 Install and Version Change Keep Files and Records Right | `18-2-install-and-version-change-keep-records-right` | FR199, FR200 | `VSS-z7e`, `VSS-do7` |
| 18.3 Game Version Badge on Browse Cards | `18-3-game-version-badge-on-browse-cards` | FR201, FR202 | `VSS-4f3` |
| 18.4 Installed Mods List at Every Width | `18-4-installed-mods-list-at-every-width` | FR203, FR204 | `VSS-bgu`, `VSS-n2u` |

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** `lastUpdated: '2026-11-16'`; update entry "Added Epic 18 (4 stories) for Mod Media and Fixes; FR194-FR204".

**FR Coverage Map**, appended after FR193:

```markdown
| FR194 | Epic 18 | Screenshot gallery on the mod detail page |
| FR195 | Epic 18 | Gallery keyboard, touch, alt text, lazy loading, phones |
| FR196 | Epic 18 | Trailer link, no embedded player |
| FR197 | Epic 18 | Only allow-listed media URLs leave the API |
| FR198 | Epic 18 | Description links marked as opening in a new tab |
| FR199 | Epic 18 | Install refuses a file-name collision with 409 |
| FR200 | Epic 18 | Update record stored after a version change |
| FR201 | Epic 18 | Game version indicator on browse cards, no per-card request |
| FR202 | Epic 18 | No indicator when the version or data is unknown |
| FR203 | Epic 18 | Sort control for installed mod cards |
| FR204 | Epic 18 | Installed mods table fits at 1024px with a long name |
```

**Story Summary:**

OLD:

```markdown
| **Total** | | **102** |
```

NEW:

```markdown
| Epic 18: Mod Media and Fixes | 18.1, 18.2, 18.3, 18.4 | 4 |
| **Total** | | **106** |
```

### 4.3 Epic 18 Stories (appended to `epics.md`)

## Epic 18: Mod Media and Fixes

**Goal:** Admins can see a mod's screenshots and trailer before installing it and tell from a browse card whether it has a release for their game version, and installing, changing versions and the Installed list behave correctly in the cases Epic 17 left open.

**Architecture:** `architecture/epic-18-mod-media-and-fixes.md` (ADR-1 to ADR-6, with the mod database facts checked on 2026-11-16). There is no preparation story. Story 18.4 measures the table's columns before it settles the Name column's width.

**Order:** Story 18.1 first, because the maintainer wants the gallery most. Then 18.2 (it holds the only bug, `VSS-z7e`, P2), 18.3 and 18.4.

**Dependencies:** No story needs another's code. Stories 18.1, 18.2 and 18.3 each edit `routers/mods.py`, `models/mods.py` and `web/src/api/types.ts` in different places, so run them one after another or expect small merge conflicts. Story 18.4 is web only and touches none of their files.

### Current State

- The mod detail page shows the logo and description only; the mod database's screenshots and trailer are dropped by the API
- Description links open in a new tab with nothing to say so
- Installing a mod whose file name another installed mod already uses replaces that mod's file, and a failed import then deletes it
- After a version change to a release newer than the last update check, the Installed list shows "Unknown" until the next check
- Browse cards say nothing about the installed game version
- Below 1024px the installed mod cards can only be re-sorted by widening the window to reach the table headers
- At 1024px a long mod name makes the installed mods table scroll inside itself, with the toggle and remove button off screen

### Target State

- A mod's screenshots and trailer link are on its detail page, from URLs the API has checked
- Description links show that they open in a new tab
- An install never overwrites another mod's file, and a version change leaves a correct update status behind
- Browse cards show whether the mod has a release for the installed game version, without a request per card
- The Installed list can be sorted and fits its container at every width

---

### Story 18.1: Mod Detail Page Media and Links

**Sprint key:** `18-1-mod-detail-media-and-links`
**Beads:** `VSS-l4x` (UI-083), `VSS-tzl` (UI-078)
**FRs:** FR194, FR195, FR196, FR197, FR198

As an **administrator**,
I want **to see a mod's screenshots and trailer on its detail page**,
So that **I can judge a mod before installing it without leaving the manager**.

**Acceptance Criteria:**

**Given** a mod with screenshots in the mod database (for example `betterruins`, 10)
**When** I request `GET /api/v1alpha1/mods/lookup/{slug}`
**Then** the response has `screenshots`, one item per screenshot in the mod database's order, each with `image_url`, `thumbnail_url` and `filename`

*(Covers FR194, FR197)*

**Given** a screenshot whose image URL is not `https` on `moddbcdn.vintagestory.at`, a null element, or a `screenshots` value that is not a list
**When** I look the mod up
**Then** the response is 200, that screenshot is left out, and a screenshot with a missing or rejected thumbnail uses its image URL as the thumbnail

*(Covers FR197)*

**Given** a mod whose trailer field is a YouTube URL in any accepted form (for example `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`)
**When** I look the mod up
**Then** `trailer_url` is `https://www.youtube.com/watch?v=<id>`; for an empty, null or any other URL (for example `https://apachegaming.net`) it is `null`

*(Covers FR196, FR197)*

**Given** a mod with several screenshots
**When** I open its detail page
**Then** a Screenshots section shows one image, its position ("3 of 10"), Previous and Next, and a strip of thumbnails; choosing a thumbnail or Previous/Next changes the image

*(Covers FR194)*

**Given** the Screenshots section
**When** I activate the current image
**Then** it opens larger in a dialog that I can step through and close

*(Covers FR194)*

**Given** a keyboard only
**When** I tab to the gallery
**Then** every thumbnail and control can be focused and activated, Left and Right move between images in the section and in the dialog, and Escape closes the dialog and returns focus to the gallery

*(Covers FR195)*

**Given** a 390px wide touch screen, in the light and the dark theme
**When** I open the detail page of a mod with screenshots
**Then** the page does not scroll sideways, Previous and Next are at least 44px targets, and the thumbnail strip scrolls inside itself

*(Covers FR195)*

**Given** the gallery
**When** it renders
**Then** each image has alt text built from its file name, images are lazy-loaded, only the current image's full-size file is requested, and no request carries a referrer

*(Covers FR195)*

**Given** a mod with no screenshots (for example `playercorpse`) or with one
**When** I open its detail page
**Then** with none there is no Screenshots section, and with one there are no Previous, Next or thumbnail controls

*(Covers FR194)*

**Given** a mod with a trailer
**When** I open its detail page
**Then** a "Watch trailer" link opens the video in a new tab with `rel="noopener noreferrer"`, and the page loads no iframe and nothing from YouTube

*(Covers FR196)*

**Given** a mod description with links
**When** I read it
**Then** each link shows an external-link icon, and a screen reader hears "(opens in a new tab)" after the link's own text

*(Covers FR198)*

**Tasks:**

- [ ] `SCREENSHOT_FIELDS`, `screenshots` and `trailervideourl` in `models/moddb.py` (Epic 18 ADR-1 decision 1)
- [ ] `services/mod_media.py`: the image URL allow-list and the trailer rewrite (ADR-1 decision 2, ADR-2 decision 2); `ModScreenshot`, `screenshots` and `trailer_url` on `ModLookupResponse`; web types
- [ ] Gallery component from `Dialog`, `Button` and plain `<img>`; no new dependency (ADR-2 decisions 5 and 6) (`VSS-l4x`)
- [ ] "Watch trailer" link beside the other external links (ADR-2 decisions 1 and 4)
- [ ] Mark description links in `lib/mod-description.ts` and the description's styles (`VSS-tzl`)
- [ ] Tests: normalizer and URL rules with a `betterruins`-shaped fixture and a synthetic bad-data fixture; component tests for navigation, none, one, keyboard and the dialog; `mod-description.test.ts` for the link marking
- [ ] E2E against a stubbed mod with several screenshots at desktop and 390px; browser check of `betterruins` in both themes

---

### Story 18.2: Install and Version Change Keep Files and Records Right

**Sprint key:** `18-2-install-and-version-change-keep-records-right`
**Beads:** `VSS-z7e` (API-075, bug), `VSS-do7` (API-076)
**FRs:** FR199, FR200

As an **administrator**,
I want **installing or changing one mod never to damage another mod or leave a wrong status behind**,
So that **I can trust the Installed list after every operation**.

**Acceptance Criteria:**

**Given** mod A is installed as `Foo.zip`
**When** I install mod B, whose release file is also named `Foo.zip`
**Then** the response is 409 `MOD_FILE_CONFLICT` with a message naming `Foo.zip`, A's file has the same bytes as before, A's state entry is unchanged, and no `.tmp` file is left

*(Covers FR199)*

**Given** mod A is disabled, so its file is `Foo.zip.disabled`
**When** I install mod B, whose release file is named `Foo.zip`
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is placed

*(Covers FR199)*

**Given** a file named like the download exists in the mods directory but belongs to no known mod, or the mod state has an entry under that file name with no file
**When** I install the mod
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is placed or removed

*(Covers FR199)*

**Given** a download whose `modinfo.json` cannot be read, with a file name another mod uses
**When** I install it
**Then** the response is 409 `MOD_FILE_CONFLICT`

*(Covers FR199)*

**Given** no file-name collision, and the import or state save fails after the file is placed
**When** the install cleans up
**Then** only the newly placed file and its own state entry are removed, as today

*(Covers FR199)*

**Given** an installed mod whose stored update record does not list a release the mod database now has
**When** I change the mod to that release from its detail page
**Then** `GET /api/v1alpha1/mods/updates` reports a real status for it ("up to date" or an offered update), not `unknown` with reason `installed_release_not_listed`, without an update check

*(Covers FR200)*

**Given** a version change through `PUT /api/v1alpha1/mods/{slug}/version`
**When** it succeeds
**Then** the response has exactly the keys `slug`, `previous_version`, `version`, `filename`, `compatibility`, `changed` and `pending_restart`, as before

*(Covers FR200)*

**Given** Update All changes several mods
**When** it finishes
**Then** each changed mod's stored record comes from its own change

*(Covers FR200)*

**Given** storing the record fails, or the version change fails or is rolled back, or the requested version is already installed
**When** the request ends
**Then** a storing failure does not fail the version change, and in the other cases the stored record is untouched

*(Covers FR200)*

**Tasks:**

- [ ] `ModFileConflictError` and the check at the start of `_place_install` (Epic 18 ADR-4) (`VSS-z7e`)
- [ ] `ErrorCode.MOD_FILE_CONFLICT`, 409 on `POST /mods`; route docstring and API documentation
- [ ] Confirm the web shows the API's message for a failed install; no other web change
- [ ] `PreparedVersionChange.releases`, the `record_releases` parameter of `change_version`, and `ModUpdateService.record_releases` with `record_install` delegating to it (ADR-5) (`VSS-do7`)
- [ ] Pass the recorder from the version change route and the Update All route
- [ ] Tests: the four collision cases with file bytes and state compared before and after; a failing import after a clean placement; the version change record cases, including the response key set

---

### Story 18.3: Game Version Badge on Browse Cards

**Sprint key:** `18-3-game-version-badge-on-browse-cards`
**Beads:** `VSS-4f3` (UI-068)
**FRs:** FR201, FR202

As an **administrator**,
I want **each mod browser card to tell me whether the mod has a release for my game version**,
So that **I do not open mod after mod to find the ones I can use**.

**Acceptance Criteria:**

**Given** a game server is installed and its version has a tag in the mod database
**When** I request `GET /api/v1alpha1/mods/browse`
**Then** the response has `game_version` set to the installed version, and every item has `has_release_for_game_version` `true` or `false`

*(Covers FR201)*

**Given** two browse requests within the cache lifetime, for any pages, sorts or filters
**When** they are served
**Then** the mod database receives at most one filtered listing request for the installed version and no request per mod

*(Covers FR201)*

**Given** a card whose flag is `true`
**When** I see it
**Then** it shows "Has a release for 1.22.7" (with the installed version), and a card whose flag is `false` shows "No release for 1.22.7"; neither uses the words "Compatible" or "Incompatible"

*(Covers FR201)*

**Given** no game server is installed, or the installed version has no tag in the mod database
**When** I browse
**Then** the response is 200 with `game_version: null` and every flag `null`, and the cards show no game version indicator

*(Covers FR202)*

**Given** the mod database fails or times out on the filtered listing
**When** I browse
**Then** the response is 200; the flags come from the last copy for that version when one exists and are `null` otherwise

*(Covers FR202)*

**Given** I install a different game server version
**When** I browse again
**Then** the flags and `game_version` are for the new version on the next request, without restarting the API

*(Covers FR201)*

**Given** I pick a game version in the browse filter
**When** I change pages
**Then** the filtered listing is served from the same cache, and the cards' flags still refer to the installed version

*(Covers FR201)*

**Tasks:**

- [ ] Cache filtered listings per tag ID in `ModApiClient`, with the `modid` set, a three-entry limit and the browse cache lifetime (Epic 18 ADR-3 decisions 1 and 2) (`VSS-4f3`)
- [ ] Browse route: resolve the installed version, fetch concurrently when cold, fall back as ADR-3 decision 5 says; `has_release_for_game_version` and `game_version` in the models
- [ ] Web types and the card indicator (ADR-3 decision 9); remove `getBrowseCardCompatibility` and its test
- [ ] Tests: route cases for true, false, no server, untagged version, failure with and without an earlier copy, and a changed version; client cache tests for lifetime and the entry limit; `ModCard` tests for the three states
- [ ] Browser check on the dev stack: `carryon` shows the badge and `playercorpse` shows "No release" on 1.22.7

---

### Story 18.4: Installed Mods List at Every Width

**Sprint key:** `18-4-installed-mods-list-at-every-width`
**Beads:** `VSS-bgu` (UI-077), `VSS-n2u` (UI-086)
**FRs:** FR203, FR204

As an **administrator**,
I want **to sort my installed mods and reach every control at any window width**,
So that **the list is as usable on a tablet or a small laptop as on a wide screen**.

**Acceptance Criteria:**

**Given** a viewport narrower than 1024px
**When** I open Installed mods
**Then** a sort control above the cards shows the current sort column (Name, Version or Status) and direction

*(Covers FR203)*

**Given** the sort control
**When** I choose another column or flip the direction
**Then** the cards reorder at once, and the choice is still there after a reload

*(Covers FR203)*

**Given** I sorted the cards by Version descending
**When** I widen the window to 1024px or more
**Then** the table is sorted by Version descending with its header showing it, and a sort made on a table header is the cards' sort when I narrow the window again

*(Covers FR203)*

**Given** a viewport of 1024px or wider
**When** I open Installed mods
**Then** there is no separate sort control; the table headers sort as today

*(Covers FR203)*

**Given** a 1024px viewport, sidebar expanded or collapsed, and a mod with a 63-character name and an offered pre-release update
**When** I open Installed mods
**Then** the table does not scroll inside its container, the page does not scroll sideways, the name wraps, and the mod's enable toggle and remove button are inside the viewport

*(Covers FR204)*

**Given** a viewport of 1440px or wider, or only mods with short names
**When** I open Installed mods
**Then** each row is on one line, as today

*(Covers FR204)*

**Given** the other tables in the app (Scheduled Jobs, Version)
**When** this story is done
**Then** their cells still do not wrap

*(Covers FR204)*

**Tasks:**

- [ ] Sort control in `ModTable` above the cards, writing `installedModsSort` through `setInstalledModsSort` (Epic 18 ADR-6, sort) (`VSS-bgu`)
- [ ] Extend `layout_widths.mjs` to record each column's width at 1024px; keep the before numbers
- [ ] Wrap the Name column through its column `meta.className`, applied to body cells too; choose the minimum width from the measurements; stack the Available cell only if the numbers require it (ADR-6, long names) (`VSS-n2u`)
- [ ] Tests: `ModTable.test.tsx` for the control and the shared preference; `layout-widths.spec.ts` now expects no scrolling element at 1024px in both sidebar states
- [ ] Record the after measurements in the story file

### 4.4 Architecture (`architecture/epic-18-mod-media-and-fixes.md`, new)

| ADR | Decision | Story |
|---|---|---|
| ADR-1 | Screenshots and the trailer field go through the Epic 17 normalizer for types, then one function in the API keeps only `https` URLs on `moddbcdn.vintagestory.at`; a screenshot with a rejected image URL is dropped, a rejected thumbnail falls back to the image URL, and the lookup never fails over it | 18.1 |
| ADR-2 | The trailer is a link, not an embed: the API accepts only YouTube URLs, extracts the video ID and returns `https://www.youtube.com/watch?v=<id>`; the gallery is built from the existing `Dialog` and buttons with no carousel library; no CSP consequence | 18.1 |
| ADR-3 | The browse card flag comes from `/api/mods?gameversion=<tagid>` for the installed version, cached per tag ID for 5 minutes and matched by numeric `modid`; `null` and no indicator when the version is unknown or the request fails; supersedes Epic 10 ADR-2 for cards and replaces Epic 16 ADR-2 decision 6 | 18.3 |
| ADR-4 | `_place_install` refuses before writing anything when `<name>` or `<name>.disabled` exists or is in the mod state; 409 `MOD_FILE_CONFLICT` | 18.2 |
| ADR-5 | `change_version` takes an optional recorder and calls it with the lookup's releases after a completed change; `VersionChangeResult` and the response do not change | 18.2 |
| ADR-6 | The card sort control writes the existing `installedModsSort` preference; the long-name table is fixed by wrapping the Name column, not by a wider breakpoint (the 1183px table would need a 1391px viewport, past `xl`) | 18.4 |

The file also records the mod database facts and the CSP check the decisions rest on.

### 4.5 Other Artifacts

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | Add `epic-18` (backlog), `epic-18-retrospective` (optional) and stories `18-1` to `18-4` (backlog), via `scripts/sprint-status.sh` | Now |
| Beads | Create epic `Epic 18: Mod Media and Fixes` (`VSS-5w8`); parent the 7 in-scope issues to it; close each with an AAR when its story is done | Now, and per story |
| `architecture/index.md` | Entry for the Epic 18 ADRs | Now |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 18.1 to 18.4 from `epics.md` and the Epic 18 ADRs, 18.1 first |
| Developer (`dev-story`) | Implement each story; in 18.4, record the column measurements before choosing the Name column's minimum width |
| Reviewer (`code-review`) | Delegated read-only review per story |
| Maintainer (Matt) | Reviews this proposal and answers the open questions below; can overturn any recommended default at story creation |

**Open questions for the maintainer** (each has a default the stories use unless overturned):

1. **Trailer link target.** Default: `https://www.youtube.com/watch?v=<id>`, a normal video page. Alternative: `https://www.youtube-nocookie.com/embed/<id>` opened in a new tab, which stays on the privacy-enhanced domain and shows a bare full-window player.
2. **Card wording and the `false` case.** Default: "Has a release for 1.22.7" as a badge and "No release for 1.22.7" as muted text. Alternative: show only the positive badge and nothing for `false`.
3. **Install collision status.** Default: 409 `MOD_FILE_CONFLICT`. The bead allowed 409 or 422.
4. **Swipe in the gallery.** Default: not required; Previous and Next are 44px targets. A swipe gesture would be hand-written, since no gesture library is installed.
5. **Removing `getBrowseCardCompatibility`.** Default: Story 18.3 deletes it and its test, since nothing else calls it.

**Follow-ups found outside the scope** (reported, no beads created):

1. `enable_mod` and `disable_mod` rename the mod file without checking that the target name is free (`services/mods.py:730`, `:788`). Same overwrite as `VSS-z7e`, by another route.
2. A version change's file-name refusal is 500 `MOD_VERSION_CHANGE_FAILED` (`services/mods.py:979-982`). After Story 18.2 the same situation on install is 409 `MOD_FILE_CONFLICT`; the two could be aligned.
3. `logo_url` on lookup and browse is passed to `<img src>` without the allow-list of ADR-1, and logo requests send a referrer naming the instance's origin to the CDN.
4. The app sets no Content-Security-Policy. If one is added it needs `img-src https://moddbcdn.vintagestory.at` plus whatever description images are to be allowed; descriptions load images from any host today.
5. The download cache stores archives by file name only (`cache/mods/<name>`), so two mods with the same release file name replace each other's cached copy. `_archive_matches` catches the wrong archive on reuse, so the cost is a repeated download.
6. `ModApiClient` does not read `issuetrackerurl` or `wikiurl`, which the mod database's page links to.
7. The Version column sorts as text in the table and the cards, so `1.10.0` sorts before `1.9.0`. Story 18.4 exposes the same sort on the cards and does not change it.
8. `agentdocs/vintagestory-modapi.md` does not describe `screenshots`, `trailervideourl` or the two game version filter forms (`gameversion` and `gameversions[]` return different sets: 5,651 and 2,829 for 1.22.7).

**Success criteria:**

- `betterruins` shows its 10 screenshots and a working trailer link on its detail page; `playercorpse` shows no Screenshots section
- No request for a mod detail page reaches YouTube until the trailer link is clicked
- Installing a mod whose file name is taken returns 409 and leaves the other mod's file byte for byte
- A version change to a release newer than the last check shows a real status in the Installed list at once
- Browse cards show the game version indicator with at most one filtered listing request per 5 minutes
- At 1024px the installed mods table does not scroll inside itself with the Story 17.8 long-name fixture, and the cards can be sorted
- Each in-scope beads issue is closed with an AAR by its story
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: seven beads chosen by the maintainer after Epic 17. [x] 1.2 type: two deferred features and five follow-ups from reviews. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete except Epic 10 ADR-2 for cards and Epic 16 ADR-2 decision 6. [x] 2.5 no resequencing; order inside Epic 18 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR194-FR204 added, MVP unaffected. [x] 3.2 architecture: new Epic 18 ADRs. [N/A] 3.3 UX spec: no change. [N/A] 3.4 deployment, CI and monitoring: no change |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [!] 6.1, 6.2 written without interactive review. [!] 6.3 scope approved by Matt on 2026-11-16 before the workflow ran; approval of this document is pending. [x] 6.4 handoff in section 5 |
