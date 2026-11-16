# Story 18.1: Mod Detail Page Media and Links

Status: done

<!-- Implements FR194-FR198. Beads: VSS-l4x (UI-083), VSS-tzl (UI-078). First story of Epic 18; stories are implemented in order 18.1, 18.2, 18.3, 18.4, each stacked on the previous. Governed by Epic 18 ADR-1 (media normalized in models/moddb.py, then filtered by an allow-list in services/mod_media.py) and ADR-2 (the trailer is a link, the gallery uses the existing Dialog, no new dependency), which extend Epic 17 ADR-1 (normalization at the boundary). Line references were verified at commit b9606f1 (branch epic-18-planning, on top of main 574e125) and must be re-checked at implementation time. Not in scope: VSS-z7e, VSS-do7 (18.2), VSS-4f3 (18.3), VSS-bgu, VSS-n2u (18.4); pre-existing VSS-1ar, VSS-hnl, VSS-6wj. No new npm or Python dependency. -->

## Story

As an **administrator**,
I want **to see a mod's screenshots and trailer on its detail page**,
so that **I can judge a mod before installing it without leaving the manager**.

## Acceptance Criteria

1. **Given** a mod with screenshots in the mod database (for example `betterruins`, 10)
   **When** I request `GET /api/v1alpha1/mods/lookup/{slug}`
   **Then** the response has `screenshots`, one item per screenshot in the mod database's order, each with exactly `image_url`, `thumbnail_url` and `filename`; a mod without screenshots has `screenshots: []`
   *(Covers FR194, FR197; `VSS-l4x`)*

2. **Given** a screenshot whose image URL is not `https` on `moddbcdn.vintagestory.at` (an `http:` URL, another host, a URL with user info or a port, an empty or missing URL), a null or non-object element, or a `screenshots` value that is missing, null or not a list
   **When** I look the mod up
   **Then** the response is 200, that screenshot is left out and the others keep their order; a screenshot with a missing or rejected thumbnail keeps its place and uses its image URL as the thumbnail; a dropped screenshot is logged at debug level with the mod slug
   *(Covers FR197)*

3. **Given** a mod whose trailer field is an `https` YouTube URL in an accepted form (`/watch?v=<id>`, `/embed/<id>` or `youtu.be/<id>` on the hosts of Dev Notes "URL rules"; for example `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`)
   **When** I look the mod up
   **Then** `trailer_url` is `https://www.youtube-nocookie.com/embed/<id>`, built from the ID alone (maintainer decision 2026-11-16; planned as `https://www.youtube.com/watch?v=<id>`); for `null`, `""`, a missing field, a non-string, an `http:` URL, a non-YouTube host (for example `https://apachegaming.net`) or a YouTube URL without a valid 11-character ID it is `null`, and the lookup is still 200
   *(Covers FR196, FR197)*

4. **Given** a mod with several screenshots
   **When** I open its detail page
   **Then** a Screenshots section between the header and the description shows one image, its position ("3 of 10"), Previous and Next, and a strip of thumbnails; choosing a thumbnail or Previous/Next changes the image and the position; Next on the last image goes to the first and Previous on the first goes to the last
   *(Covers FR194; `VSS-l4x`)*

5. **Given** the Screenshots section
   **When** I activate the current image (click, tap, Enter or Space)
   **Then** it opens larger in a dialog with the same position, Previous and Next, that I can step through and close; after closing, the section shows the image I was on in the dialog
   *(Covers FR194)*

6. **Given** a keyboard only
   **When** I tab to the gallery
   **Then** the current image, Previous, Next and every thumbnail can be focused and activated, Left and Right arrow keys move between images while focus is in the section and while the dialog is open (one step per key press), and Escape closes the dialog and returns focus to the current image in the section
   *(Covers FR195)*

7. **Given** a 390px wide touch screen, in the light and the dark theme
   **When** I open the detail page of a mod with screenshots
   **Then** nothing in the Screenshots section extends past the viewport, the page is no wider with the section than the same page without screenshots, Previous and Next are at least 44x44px targets in the section and in the dialog, every thumbnail is at least 44px in both directions, and the thumbnail strip scrolls inside itself
   *(Covers FR195. Narrower than the epic's "the page does not scroll sideways": see Dev Notes "ADR and epic against the code", item 3)*

8. **Given** the gallery
   **When** it renders
   **Then** every image has alt text built from its position and file name ("Screenshot 3 of 10: ToolRepair.png"), every `<img>` has `loading="lazy"` and `referrerPolicy="no-referrer"`, the strip uses the thumbnail files, only the current image's full-size file is requested (the others when they are selected), and no gallery image request carries a `Referer` header
   *(Covers FR195)*

9. **Given** a mod with no screenshots (for example `playercorpse`) or with one
   **When** I open its detail page
   **Then** with none there is no Screenshots section, and with one the section shows the image (which still opens in the dialog) without Previous, Next, position or thumbnail controls
   *(Covers FR194)*

10. **Given** a mod with a trailer
    **When** I open its detail page
    **Then** a "Watch trailer" link beside the other external links has the API's `trailer_url` as its `href`, `target="_blank"`, `rel="noopener noreferrer"`, an external-link icon and the screen reader text "(opens in a new tab)"; the page has no iframe and requests nothing from YouTube; a mod without a trailer has no such link
    *(Covers FR196)*

11. **Given** a mod description with links
    **When** I read it
    **Then** each link that opens in a new tab shows an external-link icon after it, and a screen reader hears "(opens in a new tab)" after the link's own text; anchors without an `href` are unchanged
    *(Covers FR198; `VSS-tzl`)*

12. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory
    *(Regression guard)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-18.1/task-N): ... ; feat/fix only for a change an admin can see, subject written for admins (Story 17.4 review L1). Red first. Every commit is green. -->

- [x] Task 1: The normalizer reads `screenshots` and `trailervideourl` + tests (AC: 1, 2, 3, 12)
  - [x] 1.1: `api/src/vintagestory_api/models/moddb.py`: add `SCREENSHOT_FIELDS: dict[str, FieldNormalizer]` (`mainfile` and `thumbnailfilename` `_as_optional_str`, `filename` `_as_str`, `fileid` `_as_optional_int`, `created` `_as_optional_str`) with a one-line docstring like `RELEASE_FIELDS` (`:104-114`). `MOD_FIELDS` (`:79-101`) gains `"screenshots": _as_screenshot_list` and `"trailervideourl": _as_optional_str`. Do not write a second copy of `_as_release_list` (`:67-76`) with its own `cast`: turn its body into one shared helper, `_as_object_list(value: object, fields: dict[str, FieldNormalizer]) -> list[dict[str, Any]]` (not a list gives `[]`; each element goes through `_normalize(item, fields)` (`:117-124`); `None` results, the non-objects, are dropped), and make `_as_release_list` and the new `_as_screenshot_list` one-line callers of it with `RELEASE_FIELDS` and `SCREENSHOT_FIELDS` (both tables are module globals read at call time, so their position below the functions is fine). The existing `cast(list[object], value)` moves into the helper; the file has four `cast(` calls before and four after. `normalize_release` (`:127-129`) is unchanged. Types only: no URL check in this module (ADR-1 decision 1)
  - [x] 1.2: Update the module docstring (`:1-22`): the rules line names three tables (`MOD_FIELDS`, `RELEASE_FIELDS`, `SCREENSHOT_FIELDS`) and says the normalizer checks types, not URLs (the URL policy is `services/mod_media.py`)
  - [x] 1.3: Tests in `api/tests/test_moddb_normalize.py` (Dev Notes "API tests", Task 1 rows) and the three changes to that file in "Existing tests that change"
  - [x] 1.4: Commit `refactor(story-18.1/task-1): normalize mod database screenshots and trailer field`

- [x] Task 2: `screenshots` and `trailer_url` on the lookup response, behind the URL rules + tests (AC: 1, 2, 3, 12)
  - [x] 2.1: New `api/src/vintagestory_api/services/mod_media.py` (a pure helper module like `services/mod_release_selection.py`; no I/O, no client): `MOD_MEDIA_HOSTS`, `YOUTUBE_HOSTS`, `mod_image_url(url: str | None) -> str | None`, `trailer_watch_url(url: str | None) -> str | None` and `build_screenshots(screenshots: list[dict[str, Any]], slug: str) -> list[ModScreenshot]`, exactly as in Dev Notes "URL rules"
  - [x] 2.2: `api/src/vintagestory_api/models/mods.py`: new `ModScreenshot(BaseModel)` directly above `ModLookupResponse` (`:193`) with `image_url: str`, `thumbnail_url: str`, `filename: str` and docstrings (full-size image on the mod database CDN; the 55x60 thumbnail, or the image URL when the mod database gave no usable thumbnail; the uploaded file name, may be `""`). `ModLookupResponse` gains, after `last_released` (`:272-273`): `screenshots: list[ModScreenshot] = []` ("the entry's screenshots in mod database order; only `https` URLs on the mod database CDN, Epic 18 ADR-1") and `trailer_url: str | None = None` ("`https://www.youtube.com/watch?v=<id>` when the entry's trailer field names a YouTube video, else None; Epic 18 ADR-2"). Add `ModScreenshot` to the module docstring's list (`:8`). Careful: `ModBrowseItem` below has the same `created`/`last_released` lines (`:376`); the fields go in `ModLookupResponse` only
  - [x] 2.3: `api/src/vintagestory_api/services/mods.py` `lookup_mod` (`:536`): in the `ModLookupResponse(...)` call (`:660-680`), after `last_released=mod["lastreleased"]` (`:679`), add `screenshots=build_screenshots(mod["screenshots"], response_slug)` and `trailer_url=trailer_watch_url(mod["trailervideourl"])`; import both from `vintagestory_api.services.mod_media` with the other service imports (`:30-54`). `mod` is the normalized entry from `api_client.get_mod(slug)` (`:571`), so both keys always exist. Add one sentence to the docstring (`:539-561`). No other method changes; `logo_url` is not filtered (ADR-1 decision 6)
  - [x] 2.4: `api/src/vintagestory_api/routers/mods.py` `lookup_mod` docstring (`:589-602`): add `screenshots` and `trailer_url` to the field list. No code change in the router
  - [x] 2.5: New fixture `api/tests/fixtures/moddb/mod_betterruins.json` and its row in `api/tests/fixtures/moddb/README.md` (Dev Notes "The fixture")
  - [x] 2.6: Tests (Dev Notes "API tests", Task 2 rows) and the `test_mod_models.py` change in "Existing tests that change"
  - [x] 2.7: Commit `chore(story-18.1/task-2): add screenshots and trailer URL to the mod lookup response` (not `feat`: nothing an admin can see yet; the PR description cites "API contract changes")

- [x] Task 3: Screenshot gallery on the detail page + tests (AC: 4, 5, 6, 7, 8, 9, 12)
  - [x] 3.1: `web/src/api/types.ts`: new exported `ModScreenshot` interface (`imageUrl: string`, `thumbnailUrl: string`, `filename: string`, doc comments as in 2.2) above `ModLookupData` (`:173`); `ModLookupData` gains `screenshots: ModScreenshot[]` and `trailerUrl: string | null` after `lastReleased` (`:203`), both required (the API always sends them; `snakeToCamel` in `api/client.ts:46` maps the keys, nested ones too). Careful: `ModBrowseItem` has the same `lastReleased` line (`:415`). Fix the one typed literal this breaks (`src/api/mods.test.ts:584`, see "Existing tests that change")
  - [x] 3.2: New `web/src/components/ModScreenshotGallery.tsx` (Dev Notes "The gallery"), built from `Card`, `Button`, `Dialog` (`components/ui/dialog.tsx`), `lucide-react` icons and plain `<img>`. No new dependency, no document-level key listener
  - [x] 3.3: `web/src/features/mods/ModDetailPage.tsx`: after `<Separator />` (`:744`) and before the Description card (`:746-764`) render `<ModScreenshotGallery key={mod.slug} screenshots={screenshots} />` when the list is not empty, where `const screenshots = Array.isArray(mod.screenshots) ? mod.screenshots : [];` sits beside `sanitizedDescription` (`:561-564`) with a comment (media are optional: a response without the list shows no gallery, it does not fail the page; the guard at `:541-548` is not extended). Add "Story 18.1" to the header comment (`:1-39`)
  - [x] 3.4: Tests: new `web/src/components/ModScreenshotGallery.test.tsx` and additions to `web/src/features/mods/ModDetailPage.test.tsx` (Dev Notes "Web tests", Task 3 rows)
  - [x] 3.5: Commit `feat(story-18.1/task-3): show a mod's screenshots on its detail page`

- [x] Task 4: "Watch trailer" link + tests (AC: 10, 12)
  - [x] 4.1: `web/src/lib/mod-description.ts`: export `export const OPENS_IN_NEW_TAB = '(opens in a new tab)';` (used by the trailer link here and by the description hook in Task 5, so the two cannot drift)
  - [x] 4.2: `ModDetailPage.tsx` external links row (`:680-716`): after the Source link (`:704-715`) add, when `mod.trailerUrl` is set, an `<a>` with `href={mod.trailerUrl}`, `target="_blank"`, `rel="noopener noreferrer"`, the same classes as its siblings, `data-testid="mod-detail-trailer-link"`, the `ExternalLink` icon (already imported, `:49`; `aria-hidden="true"`), the text `Watch trailer` and `<span className="sr-only"> {OPENS_IN_NEW_TAB}</span>`. Add `flex-wrap gap-y-1` to the row's `className` (`:681`) so a fourth link wraps instead of widening the header. No `<iframe>`, no preconnect, no thumbnail from YouTube. The web does not re-check the URL (ADR-1 decision 5)
  - [x] 4.3: Tests in `ModDetailPage.test.tsx` `describe('external links')` (`:559`): with `trailer_url: 'https://www.youtube.com/watch?v=mJHZH_sThDM'` the link has that `href`, `target`, `rel`, and the accessible name `Watch trailer (opens in a new tab)` (`getByRole('link', { name: ... })`); with `trailer_url: null`, and with the field missing (the existing fixtures), there is no `mod-detail-trailer-link`; the rendered page contains no `iframe`. Extend "does not render optional links when null"
  - [x] 4.4: Commit `feat(story-18.1/task-4): link to a mod's trailer from its detail page`

- [x] Task 5: Description links show that they open in a new tab + tests (AC: 11, 12)
  - [x] 5.1: `web/src/lib/mod-description.ts` hook (`:21-30`): after setting `target` and `rel`, for an HTML link only (`node.namespaceURI === 'http://www.w3.org/1999/xhtml'`), append `<span class="sr-only" data-new-tab-note=""> (opens in a new tab)</span>` built with `node.ownerDocument.createElement('span')` and `textContent` (leading space, then `OPENS_IN_NEW_TAB`), unless the link's last element child already has `data-new-tab-note` (sanitizing sanitized output must not add a second note). Do not use `aria-label` (it would replace the link's own text) and do not set `innerHTML`. Update the module comment (`:1-11`). Details and what the prototype showed: Dev Notes "Description links"
  - [x] 5.2: `web/src/styles/index.css`, inside the existing `@layer components` block (`:209-245`): the `.mod-description a[target='_blank']::after` rule of Dev Notes "Description links". `ModDetailPage.tsx:754`: add `mod-description` to the description container's `className` (leave the other classes as they are)
  - [x] 5.3: Tests in `web/src/lib/mod-description.test.ts` `describe('links')` (`:120-156`) and one in `ModDetailPage.test.tsx` `describe('description section')` (`:381`) (Dev Notes "Web tests", Task 5 rows)
  - [x] 5.4: Commit `fix(story-18.1/task-5): show that mod description links open in a new tab`

- [ ] Task 6: E2E against the Docker dev stack and browser check (AC: 4-11)
  - [x] 6.1: New `web/e2e/mod-detail-media.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`, as Stories 17.4 and 17.8 did; it recreates the container, so if a game server is running in the dev stack ask the maintainer before restarting, and never start or stop the game server through the UI or the API); run with `cd web && bunx playwright test e2e/mod-detail-media.spec.ts` and the admin key exported from `.env` (`just test-e2e-web` stops the stack afterwards). Also re-run `e2e/mod-detail-bad-data.spec.ts` and `e2e/installed-mod-any-modid.spec.ts` (both open the detail page)
  - [x] 6.2: Record in the Dev Agent Record the page widths measured at 390px with and without screenshots (Dev Notes "ADR and epic against the code", item 3)
  - [ ] 6.3: Manual browser check (requires the user's confirmation before it is ticked, `project-context.md:160-161`): `betterruins` on the Docker stack in the light and the dark theme at desktop width and at 390px: gallery, dialog, trailer link, description link icons. No screenshots kept; do not start or stop the game server
  - [x] 6.4: Commit `test(story-18.1/task-6): e2e for the screenshot gallery, trailer link and description links`

- [ ] Task 7: Quality gate and review hand-off (AC: all)
  - [x] 7.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast` (`grep -c "cast(" api/src/vintagestory_api/models/moddb.py` is 4, as before; `services/mod_media.py` and the web code need none); after `just test-api`, `git status --short` shows nothing under `dev/`; `web/package.json`, `web/bun.lock`, `api/pyproject.toml` and `api/uv.lock` are unchanged
  - [ ] 7.2: Story status `review`, `just sprint set 18-1-mod-detail-media-and-links review`, PR against `main`; the PR description quotes the "API contract changes" section; PR link on `VSS-l4x` and `VSS-tzl`. Commit `docs(story-18.1/task-7): ...` for the story file

## Dev Notes

### Where things are today (verified at b9606f1)

- **API.** `ModApiClient.get_mod` passes the entry through `normalize_mod` (`models/moddb.py:132-134`). `_normalize` (`:117-124`) copies unknown keys unchanged, so `screenshots` and `trailervideourl` already reach `lookup_mod` exactly as the mod database sent them; nothing reads them. `lookup_mod` builds `ModLookupResponse` at `services/mods.py:660-680`; `logo_url=mod["logofilename"]` (`:673`) is passed through unchecked.
- **Mod database shape** (fetched 2026-11-16 for this story, `GET https://mods.vintagestory.at/api/mod/betterruins`): `screenshots` is a list of `{fileid, mainfile, filename, thumbnailfilename, created}`; `mainfile` is `https://moddbcdn.vintagestory.at/<name>_<hash>.jpg`, `thumbnailfilename` the same with `_55_60` before the extension; `filename` is the uploaded name and can contain spaces (`Timeline 1_01_02_04_26.jpg`, whose URL has `+` for the space); `trailervideourl` is `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`. Other mods send `""` or `null` for the trailer (Epic 18 architecture, "Mod Database Facts").
- **Web.** `ModDetailPage.tsx` renders header (`:601-742`), `<Separator />` (`:744`), Description (`:746-764`), Releases (`:766-`). The three external links are at `:680-716`, each `target="_blank" rel="noopener noreferrer"` with a leading icon and no screen reader note. The description is sanitized by `sanitizeModDescription` (`lib/mod-description.ts:41-43`), whose `afterSanitizeAttributes` hook (`:21-30`) sets `target="_blank"` and `rel` on every `<a>` with an `href` (HTML) or `xlink:href` (SVG). That hook is the only place Story 16.4 sets `target`; it is the place to mark the links.
- **Description styles: there are none.** The container's classes are `prose prose-sm prose-invert max-w-none` (`:754`), but `@tailwindcss/typography` is not installed (`web/package.json`, `web/src/styles/index.css`), so the `prose` classes do nothing, and Tailwind's preflight gives links `color: inherit; text-decoration: inherit`. A description link looks like plain text today. This story adds the icon and the note, not link styling (see "Not changed").
- **Components available:** `components/ui/dialog.tsx` (Radix Dialog; `DialogContent` is `sm:max-w-lg` with `p-6` by default and takes a `className`, `:49-83`), `components/ui/button.tsx` (sizes `icon` 36px, `icon-lg` 40px, `:23-29`; 44px is `className="size-11"`, as `InstalledModCard.tsx:81`), `lucide-react`. The theme is a `dark` class on `<html>` set by `next-themes` (`contexts/ThemeContext.tsx`, `defaultTheme="system"`), so Playwright's `page.emulateMedia({ colorScheme })` switches it in a fresh context.

### URL rules (`services/mod_media.py`)

```python
"""Which mod database media URLs the API passes on (Epic 18 ADR-1 and ADR-2).

A URL from the mod database is author-controlled data that the web puts into `src`
and `href`. `models/moddb.py` checks types; this module is the one place that
decides which URLs are allowed. Anything else becomes None and never fails a lookup.
"""

MOD_MEDIA_HOSTS = frozenset({"moddbcdn.vintagestory.at"})
YOUTUBE_HOSTS = frozenset({
    "www.youtube-nocookie.com", "youtube-nocookie.com",
    "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be",
})
_UNSAFE = re.compile(r"[\x00-\x20\x7f\\]")       # control characters, space, backslash
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def _https_parts(url: str | None, hosts: frozenset[str]) -> SplitResult | None:
    if not url or _UNSAFE.search(url) or not url.startswith("https://"):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    return parts if parts.netloc.lower() in hosts else None


def mod_image_url(url: str | None) -> str | None:
    """`url` unchanged when it is an https URL on the mod database CDN, else None."""
    return url if _https_parts(url, MOD_MEDIA_HOSTS) is not None else None


def trailer_watch_url(url: str | None) -> str | None:
    """`https://www.youtube.com/watch?v=<id>` for a YouTube video URL, else None."""
    parts = _https_parts(url, YOUTUBE_HOSTS)
    if parts is None:
        return None
    if parts.netloc.lower() == "youtu.be":
        video_id = parts.path.removeprefix("/")
    elif parts.path == "/watch":
        video_id = (parse_qs(parts.query).get("v") or [""])[0]
    elif parts.path.startswith("/embed/"):
        video_id = parts.path.removeprefix("/embed/")
    else:
        return None
    if not _VIDEO_ID.fullmatch(video_id):
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def build_screenshots(screenshots: list[dict[str, Any]], slug: str) -> list[ModScreenshot]:
    """The entry's screenshots whose image URL is allowed, in order (ADR-1 decision 3)."""
    result: list[ModScreenshot] = []
    for index, screenshot in enumerate(screenshots):
        image_url = mod_image_url(screenshot["mainfile"])
        if image_url is None:
            logger.debug("mod_screenshot_dropped", slug=slug, index=index)
            continue
        result.append(ModScreenshot(
            image_url=image_url,
            thumbnail_url=mod_image_url(screenshot["thumbnailfilename"]) or image_url,
            filename=screenshot["filename"],
        ))
    return result
```

This is the rule, not a suggestion; write it test-first from the tables in "API tests". Why each check is there (found with a throwaway prototype on Python 3.14.10, since discarded):

- **`urlsplit` alone is not a validator.** With only "scheme is https, hostname in the list, no user info, no port" the prototype accepted `" https://moddbcdn.vintagestory.at/a.jpg"` (leading space), `"https://moddbcdn.vintagestory.at/a.jpg\n"`, `"https://mod\tdbcdn.vintagestory.at/a"` (a tab inside the host, which `urlsplit` strips) and `"https://moddbcdn.vintagestory.at:/a"` (empty port, `parts.port` is None), each returned unchanged. Hence `_UNSAFE` (no ASCII control character, space or backslash anywhere) and the comparison of the whole `netloc`, not `hostname`: `netloc` equality rejects user info (`user@host`, `host@evil`), any port including the empty one and `:443`, and a trailing dot, in one test.
- **`startswith("https://")`**: `urlsplit` lowercases the scheme, so `HTTPS://...` would pass a `parts.scheme` check and be returned as given; the CDN sends lower case. The host is compared without case (ADR-1 decision 2).
- **The image URL is returned unchanged** when allowed (the web uses it as `src`); the trailer URL is never returned, only rebuilt from the ID, so nothing an author typed reaches `href`.
- **Trailer forms.** Accepted: `/watch?v=<id>` (other query parameters ignored; the first `v` wins), `/embed/<id>`, `youtu.be/<id>` (its query ignored). Not accepted, so `None`: `/shorts/`, `/live/`, `/v/`, playlists, a trailing slash after the ID, surrounding whitespace, `http:`. `www.youtube-nocookie.com/watch?v=<id>` itself returns 404 when opened (architecture facts), which is why the URL is rewritten.
- **`filename`** is passed through as text (`""` when the mod database sent none); React renders it as text in `alt`. It is never used to build a URL.
- **No cap on the number of screenshots** (0 to 11 seen across the 45 most downloaded mods). The lookup grows by about 250 bytes per screenshot; the Installed list's per-mod lookups (`lookupMod(slug, version)`) carry them too and ignore them.
- **Logging.** Debug level, event `mod_screenshot_dropped`, `slug` and `index` only; the rejected URL is not logged. A rejected trailer is not logged (33 of 45 mods send `""`).
- **pyright strict.** `mod["screenshots"]` is `Any` (`ModDict = dict[str, Any]`); pass it straight to `build_screenshots`, whose parameter is typed. `SplitResult`, `urlsplit` and `parse_qs` come from `urllib.parse`; `logger = structlog.get_logger()` as in the other services.

### The fixture (`api/tests/fixtures/moddb/mod_betterruins.json`)

The existing fixtures had screenshots and CDN URLs removed (`fixtures/moddb/README.md`), so none can test this story. Capture `GET https://mods.vintagestory.at/api/mod/betterruins` and trim it the way the README describes: keep the mod fields the README lists plus `screenshots` (all of them, with all five keys, unchanged) and `trailervideourl`; keep the first three releases with the README's release fields; drop `text`, `comments`, changelogs and the logo fields. It is public mod database data. Add the README row (source `betterruins`, capture date, "10 screenshots with CDN URLs and thumbnails; a file name with spaces; a `youtube-nocookie.com/watch` trailer URL") and amend the README sentence that says screenshots and CDN URLs were removed ("except in `mod_betterruins.json`"). If the entry has changed by then (another count, no trailer), keep what the mod database returns and make the tests read their expectations from the fixture's raw JSON rather than hard-coding 10; the synthetic cases below cover every rule regardless. Captured fixtures are not edited by hand; bad data is built in the tests.

### API tests

| Task | File | Tests |
|---|---|---|
| 1 | `tests/test_moddb_normalize.py` | New `SCREENSHOT_FIELDS` table test (the five keys). `screenshots`: each of `None`, `"x"`, `3`, `True`, `{}` gives `[]`; `[None, "x", 3, {"mainfile": "u"}]` keeps one item; `{}` as an element gives `{"mainfile": None, "thumbnailfilename": None, "filename": "", "fileid": None, "created": None}`; wrong types per field (`mainfile: 5` and `thumbnailfilename: []` give `None`, `filename: None` gives `""`, `fileid: "7"` and `True` give `None`); a valid item is unchanged; an unknown key inside a screenshot is kept; the input is not mutated; `normalize_mod` of the result changes nothing. `trailervideourl` is covered by adding it to `MOD_OPTIONAL_STR_FIELDS` (`:22-32`), which parametrizes the existing optional-text tests; note `""` stays `""` (it is a string), so `mod_media` handles it. `TestFixtures` (`:311-320`): add `betterruins` to the parametrized names once Task 2 adds the fixture |
| 2 | new `tests/test_mod_media.py` | `mod_image_url`, parametrized. Kept unchanged: `https://moddbcdn.vintagestory.at/a_55_60.jpg`, `https://MODDBCDN.vintagestory.at/a.jpg`, a path with `+` and with a query. `None` for: `None`, `""`, `http://moddbcdn.vintagestory.at/a.jpg`, `HTTPS://moddbcdn.vintagestory.at/a.jpg`, `//moddbcdn.vintagestory.at/a.jpg`, `https://i.imgur.com/a.png`, `https://moddbcdn.vintagestory.at.evil.example/a`, `https://evil.example/moddbcdn.vintagestory.at`, `https://user@moddbcdn.vintagestory.at/a`, `https://moddbcdn.vintagestory.at@evil.example/a`, `https://moddbcdn.vintagestory.at:443/a`, `https://moddbcdn.vintagestory.at:/a`, `https://moddbcdn.vintagestory.at./a`, a leading space, a trailing `\n`, a tab in the host, a space in the path, `https:\\moddbcdn.vintagestory.at/a`, `https://[::1/a` (the `ValueError` branch), `javascript:alert(1)`, `data:image/png;base64,AA==` |
| 2 | `tests/test_mod_media.py` | `trailer_watch_url`, parametrized. `https://www.youtube.com/watch?v=mJHZH_sThDM` for: `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`, `https://youtube-nocookie.com/embed/mJHZH_sThDM`, `https://www.youtube.com/watch?v=mJHZH_sThDM`, `https://youtube.com/watch?t=10s&v=mJHZH_sThDM`, `https://m.youtube.com/watch?v=mJHZH_sThDM&list=x`, `https://youtu.be/mJHZH_sThDM`, `https://youtu.be/mJHZH_sThDM?t=3`, `https://WWW.YouTube.com/embed/mJHZH_sThDM`. `None` for: `None`, `""`, `https://apachegaming.net`, `http://www.youtube.com/watch?v=mJHZH_sThDM`, `https://www.youtube.com.evil.example/watch?v=mJHZH_sThDM`, `https://www.youtube.com/watch` (no `v`), `?v=short`, a 12-character ID, an ID with `%0A`, `https://www.youtube.com/embed/mJHZH_sThDM/`, `https://www.youtube.com/shorts/mJHZH_sThDM`, `https://www.youtube.com/playlist?list=x`, `https://youtu.be/`, `https://vimeo.com/123`, a trailing `\n`, `javascript:alert(1)`. One test that the result never contains anything but the ID after the fixed prefix (`...watch?v=mJHZH_sThDM&v=aaaaaaaaaaa` gives the first ID only) |
| 2 | `tests/test_mod_media.py` | `build_screenshots`: all good, in order; an item with a rejected `mainfile` (`http:`, other host, `None`) is dropped and the rest keep their order; `thumbnailfilename` `None`, `http:` or another host gives `thumbnail_url == image_url`; `[]` gives `[]`; a dropped item logs `mod_screenshot_dropped` at debug level with `slug` and `index` (the `captured_logs` fixture, `tests/conftest.py:73`, a `StringIO`; if it does not record debug events as configured, assert through whatever an existing debug-log test in the suite uses, not by lowering the log level in the code) |
| 2 | `tests/test_mod_service.py` `TestModServiceLookupMod` (`:1357`) | With `mod_betterruins.json` served by respx on `https://mods.vintagestory.at/api/mod/betterruins`: `result.screenshots` has one item per raw screenshot, in raw order, the first item's three fields equal to the raw `mainfile`, `thumbnailfilename` and `filename`; `result.trailer_url == "https://www.youtube.com/watch?v=mJHZH_sThDM"`. Synthetic bad data (the fixture's dict with `screenshots` replaced): `[good, {"mainfile": "http://moddbcdn.vintagestory.at/x.jpg"}, {"mainfile": "https://i.imgur.com/x.png"}, None, "x", {**good, "thumbnailfilename": None}]` gives two items, the second with `thumbnail_url == image_url`; `screenshots` of `None`, `"x"` and a missing key each give `[]`; `trailervideourl` of `None`, `""`, `5`, `"https://apachegaming.net"` and a missing key each give `trailer_url is None`; none raises. An existing fixture without either key (`mod_carryon.json`) gives `[]` and `None` |
| 2 | `tests/test_mods_router.py` `TestLookupModEndpoint` (`:486`) | `GET /api/v1alpha1/mods/lookup/betterruins`: 200, `data.screenshots` is a list whose items have exactly the keys `image_url`, `thumbnail_url`, `filename`, and `data.trailer_url` is the watch URL; with the bad-data entry: 200 and the filtered list; an entry without either key: `screenshots == []` and `trailer_url is None` (the keys are present) |
| 2 | `tests/test_mod_models.py` `TestModLookupResponse` (`:391`) | `ModScreenshot` round-trips; `ModLookupResponse` defaults are `[]` and `None` |

API tests use respx; none calls the live mod database. No test here installs a mod or touches the update store, so nothing writes under `dev/` (check with `git status --short` anyway).

### The gallery (`web/src/components/ModScreenshotGallery.tsx`)

Props: `{ screenshots: ModScreenshot[] }` (the page does not render it for an empty list, and the component returns `null` for an empty list anyway). State: `index` (0-based) and `open` (dialog).

**Decisions**

- **Thumbnail strip uses `thumbnailUrl`, at its native 55x60px.** The planning finding stands: thumbnails are only 55x60 (about 2 KB each), full images about 0.5 MB each. Scaled full images in the strip would look better but would fetch every full-size file on page load (about 5 MB for `betterruins`) and break AC 8 ("only the current image's full-size file is requested"). At native size nothing is upscaled, and 55x60 already exceeds the 44px touch target. Each thumbnail is a `<button type="button" className="shrink-0 ...">` holding `<img width={55} height={60} className="h-[60px] w-[55px] object-cover">`. When the API fell back to the image URL (no usable thumbnail) the same box shows the full image scaled down; that case is rare and needs no special code.
- **`referrerPolicy="no-referrer"` on every gallery `<img>`** (current image, dialog image, thumbnails), as ADR-2 decision 6 says. The CDN serves images without a `Referer` (architecture facts), and without the attribute each request would tell the CDN the manager's origin. The mod logo (`ModDetailPage.tsx:609-614`, `ModCard`) keeps the browser default; that is follow-up 3 of the change proposal, not this story.
- **`loading="lazy"` on every `<img>`, written before `src` in the JSX** (React sets attributes in prop order, and some browsers start the fetch when `src` is set). Only one full-size `<img>` exists in the section: the current one. The dialog's `<img>` has the same URL as the current image, so it comes from the browser cache.
- **Wrap-around, no disabled buttons.** Next on the last image goes to the first, Previous on the first to the last; arrow keys do the same. A button that becomes disabled while focused loses keyboard focus in some browsers, and wrap-around avoids the case.
- **Keys are handled on the section and on the dialog content, never on `document`.** `onKeyDown` on the section's root element handles `ArrowLeft`/`ArrowRight` when focus is inside it; a second `onKeyDown` on `DialogContent` handles them in the dialog. Ignore the event when `altKey`, `ctrlKey`, `metaKey` or `shiftKey` is set (Alt+Left is "back") and when there is one image; call `preventDefault()` when handled (otherwise the arrow also scrolls the strip). **Pitfall:** React synthetic events bubble through portals to the React parent. If `<Dialog>` is rendered inside the element that has the section's `onKeyDown`, one key press in the dialog steps twice. Return a fragment with the section and the `<Dialog>` as siblings, and test "one step per key press in the dialog".
- **Dialog.** `Dialog open={open} onOpenChange={setOpen}` with the current-image button as `DialogTrigger asChild`, so Radix returns focus to it on close (Escape, the close button, the overlay). `DialogContent` gets a `className` that widens it and trims the padding (for example `sm:max-w-5xl p-3 sm:p-4`; `cn` lets it override the defaults at `dialog.tsx:65`), a `DialogTitle` and `DialogDescription` (both required by Radix for accessibility; `sr-only`, the title is the image's alt text, the description "Use the left and right arrow keys to move between screenshots."), the image (`max-h-[80vh] w-full object-contain`), and a row with Previous, the position and Next. The dialog shares `index` with the section, which gives AC 5's "the section shows the image I was on". No thumbnail strip in the dialog. `components/ui/dialog.tsx` is not changed.
- **Layout.** `Card` with `CardHeader`/`CardTitle className="text-lg"` "Screenshots" (like the Description card). The current image sits in a fixed-ratio box so the page does not jump when images of different shapes load: a `<button type="button">` (`block w-full aspect-video overflow-hidden rounded-md bg-muted`, visible focus ring) holding the `<img className="h-full w-full object-contain">` and `<span className="sr-only">View larger</span>`. Below it: Previous (`Button variant="outline" size="icon" className="size-11"`, `aria-label="Previous screenshot"`, `ChevronLeft`), the position (`aria-live="polite"`, "3 of 10"), Next (same, `aria-label="Next screenshot"`, `ChevronRight`). Then the strip: `flex gap-2 overflow-x-auto` with a little padding so focus rings are not clipped. The selected thumbnail has `aria-current="true"` and a ring; when `index` changes, the selected thumbnail is scrolled into view with `scrollIntoView({ block: 'nearest', inline: 'nearest' })` from an effect (jsdom has no `scrollIntoView`; the tests define it, as `ModDetailPage.test.tsx:798` and `BrowseTab.test.tsx:1398` do).
- **Themes.** Only theme tokens (`bg-muted`, `text-muted-foreground`, `border`, `ring-ring`, `ring-primary`), no literal colors, so the section follows the light and dark themes like the cards around it.
- **Alt text.** One helper, `screenshotAlt(index, count, filename)`: `Screenshot 3 of 10: ToolRepair.png`, or `Screenshot 3 of 10` when the file name is empty. Used for the current image, the dialog image and each thumbnail (a thumbnail button's accessible name is its image's alt; no `aria-label` on it).
- **One screenshot.** The current image and the dialog only: no Previous, Next, position or strip, in the section and in the dialog; arrow keys do nothing.
- **Another mod.** The page passes `key={mod.slug}`, so going from one mod's page to another's starts at the first image; the component also clamps `index` to the list's length.
- **Swipe** is not required (change proposal, open question 4); the strip scrolls with a finger and Previous/Next are 44px.
- **Failed image.** Not handled beyond the browser's default (the alt text shows in the box). No retry, no placeholder.

**Test ids:** `mod-screenshots` (the card), `mod-screenshot-current` (the button), `mod-screenshot-image`, `mod-screenshot-position`, `mod-screenshot-prev`, `mod-screenshot-next`, `mod-screenshot-thumbnails` (the strip), `mod-screenshot-thumb-<index>` (0-based), `mod-screenshot-dialog` (on `DialogContent`), `mod-screenshot-dialog-image`, `mod-screenshot-dialog-position`, `mod-screenshot-dialog-prev`, `mod-screenshot-dialog-next`.

### Description links (`VSS-tzl`)

The hook, after Task 5 (shape, not final text):

```ts
if (isLink) {
  node.setAttribute('target', '_blank');
  node.setAttribute('rel', 'noopener noreferrer');
  // HTML links only: an SVG <a> cannot hold an HTML <span>
  if (node.namespaceURI === HTML_NAMESPACE && !node.lastElementChild?.hasAttribute('data-new-tab-note')) {
    const note = node.ownerDocument.createElement('span');
    note.className = 'sr-only';
    note.setAttribute('data-new-tab-note', '');
    note.textContent = ` ${OPENS_IN_NEW_TAB}`;
    node.appendChild(note);
  }
}
```

What the prototype showed (DOMPurify 3.3.1, jsdom; discarded):

- Appending a child inside `afterSanitizeAttributes` works: `<a href="https://x.example">Lib <b>bold</b></a>` became `<a href=... target="_blank" rel="noopener noreferrer">Lib <b>bold</b><span class="sr-only"> (opens in a new tab)</span></a>`. The appended span is itself visited by the sanitizer and kept (`span`, `class` and `data-*` attributes are allowed by DOMPurify's defaults). Assert the `data-new-tab-note` attribute survives; if a DOMPurify setting drops it, use a second class (`new-tab-note`) as the marker instead.
- An image link (`<a><img></a>`) gets the span after the image. A link without an `href`, and one whose `javascript:` `href` was removed, get nothing (the existing test at `:149-155` still holds).
- `#section`, `mailto:` and relative links also get `target="_blank"` today (Story 16.4), so they get the note and the icon too: the marking follows `target`, which is what is true of the link.
- An SVG link keeps `target`/`rel` and gets no span (and `::after` does not render on SVG elements). It is not marked; accepted, since SVG links in descriptions are rare.
- Without the marker check, sanitizing twice appended two notes. The page sanitizes once, but the sanitizer should be safe to re-apply; the check also covers an author who pastes the same markup.
- All 17 existing `mod-description.test.ts` tests and all 87 `ModDetailPage.test.tsx` tests passed with the hook change (they assert elements and attributes, not exact link `textContent`).

The visible icon is CSS, so it needs no extra element and nothing a screen reader would read (`content: ''`):

```css
/* Story 18.1: links in a mod description open in a new tab; show it (VSS-tzl) */
.mod-description a[target='_blank']::after {
  content: '';
  display: inline-block;
  width: 0.75em;
  height: 0.75em;
  margin-left: 0.2em;
  background-color: currentColor;
  -webkit-mask: var(--external-link-icon) center / contain no-repeat;
  mask: var(--external-link-icon) center / contain no-repeat;
}
```

with `--external-link-icon` a `url("data:image/svg+xml,...")` of the `lucide` external-link icon (three stroked paths, `viewBox='0 0 24 24'`, `fill='none'`, `stroke='black'`, `stroke-width='2'`; copy the path data from `web/node_modules/lucide-react/dist/esm/icons/external-link.mjs` and percent-encode `<`, `>` and `#`). `currentColor` makes it follow the link's color in both themes. Put the custom property on `.mod-description` or inline the URL twice; either is fine. jsdom cannot check CSS, so the unit test asserts the class and the E2E test asserts the computed `::after` style.

### Web tests

| Task | File | Tests |
|---|---|---|
| 3 | new `src/components/ModScreenshotGallery.test.tsx` | With five screenshots: shows `1 of 5`, the first `imageUrl` in `mod-screenshot-image` and five thumbnails whose `src` is each `thumbnailUrl`; Next, Previous and a thumbnail click change image and position; Next on the last wraps to the first, Previous on the first to the last; the selected thumbnail has `aria-current="true"`; exactly one `<img>` in the section has an `imageUrl` as `src` (AC 8); every `<img>` has `loading="lazy"` and `referrerpolicy="no-referrer"`; alt texts (`Screenshot 2 of 5: b.png`; an empty file name gives `Screenshot 2 of 5`). Keyboard (`userEvent`): Tab reaches the current image, Previous, Next and each thumbnail; `{ArrowRight}`/`{ArrowLeft}` with focus on a thumbnail and on Next move one step; with Alt held nothing moves; Enter and Space on the current image open the dialog. Dialog: opens with the same image and position; its Next and `{ArrowRight}` move exactly one step (the portal pitfall); `{Escape}` closes it, focus is back on `mod-screenshot-current`, and the section shows the image the dialog was on. One screenshot: image and dialog work, no `mod-screenshot-prev`, `-next`, `-position`, `-thumbnails`, and arrow keys change nothing. Empty list: renders nothing |
| 3 | `src/features/mods/ModDetailPage.test.tsx` | New `describe('screenshots (Story 18.1)')` with `mockModDetailResponse` (`:64`) spread plus `screenshots` (snake_case keys, as the fetch mock returns raw API JSON): the section is rendered after the header and before `mod-detail-description-card` (compare DOM order); `screenshots: []` and a response without the key (every existing fixture) render no `mod-screenshots` and no error state |
| 3 | `src/api/mods.test.ts` | In the `lookupMod` tests around `:584`: a response with `screenshots: [{ image_url, thumbnail_url, filename }]` and `trailer_url` comes back as `imageUrl`, `thumbnailUrl`, `filename` and `trailerUrl` |
| 4 | `src/features/mods/ModDetailPage.test.tsx` | Task 4.3 |
| 5 | `src/lib/mod-description.test.ts` | A link gets one trailing `span.sr-only[data-new-tab-note]` with text ` (opens in a new tab)`, and the link's `textContent` is `CarryOn Lib (opens in a new tab)`; a link around an image gets it after the image; anchors without `href` and with a removed `javascript:` `href` get none; an SVG link gets none and keeps `target`/`rel`; sanitizing the output again leaves exactly one note; the note's text comes from the exported `OPENS_IN_NEW_TAB`; the shared `DOMPurify` instance still adds nothing (extend "hook isolation", `:183-189`) |
| 5 | `src/features/mods/ModDetailPage.test.tsx` | In `describe('description section')` (`:381`): the container has the class `mod-description`, and a description link is found by `getByRole('link', { name: 'CarryOn Lib (opens in a new tab)' })` |

### E2E (`web/e2e/mod-detail-media.spec.ts`)

Style of `e2e/mod-detail-bad-data.spec.ts` (detail page, `page.route` for one lookup) and `e2e/layout-widths.spec.ts` (`readOnly` at `:72-88`: the admin key through `/config.js` and every non-GET API request refused; `horizontalOverflow` and `boxOf` at `:196-221`; viewport loops). Header comment with requirements as in those files. Reads only: nothing is installed, changed or removed, so no snapshot guard is needed; the game server is neither started nor stopped; no screenshot is taken.

Stubs (all with `page.route`):

- `GET /api/v1alpha1/mods/lookup/e2emediamod` (regex with an optional query, as `mod-detail-bad-data.spec.ts:85-87`): a full lookup body in snake_case (copy the field list from `layout-widths.spec.ts:143-172` and add `install_mod_id`, one release, `screenshots` and `trailer_url`; `description: '<p>See the <a href="https://example.com/docs">Docs</a>.</p>'`). Three variants selected per test: ten screenshots plus `trailer_url: 'https://www.youtube.com/watch?v=mJHZH_sThDM'`; none and `trailer_url: null`; one. Screenshot URLs are `https://moddbcdn.vintagestory.at/e2e-<n>.png` and `.../e2e-<n>_55_60.png`.
- `https://moddbcdn.vintagestory.at/**`: fulfilled with a small PNG built in the spec (a `Buffer` from base64), recording each request's URL and `referer` header. The test does not depend on the CDN.
- A recorder (`page.on('request')`) for any URL whose host contains `youtube`, `ytimg` or `google`.

Tests:

1. **Desktop (1440x900), several screenshots.** `mod-screenshots` is visible between `mod-detail-header` and `mod-detail-description-card`; position `1 of 10`; Next gives `2 of 10`; clicking `mod-screenshot-thumb-4` gives `5 of 10`; with focus on that thumbnail `ArrowLeft` gives `4 of 10`; `mod-screenshot-current` focused and Enter opens `mod-screenshot-dialog` showing `4 of 10`; `ArrowRight` gives `5 of 10` (one step); Escape hides the dialog, `mod-screenshot-current` is focused, and the section shows `5 of 10`. Each control receives focus by `Tab` from the current image (press Tab and assert `toBeFocused` for Previous, Next and the first thumbnail). Afterwards: the recorded full-size requests (URLs without `_55_60`) are exactly the images that were shown (1, 2, 4, 5), no recorded CDN request has a `referer` header, nothing was requested from YouTube, and `page.locator('iframe')` has count 0.
2. **Trailer and description links (same stub).** `mod-detail-trailer-link` has the `href`, `target="_blank"`, `rel="noopener noreferrer"` and is found by `getByRole('link', { name: 'Watch trailer (opens in a new tab)' })`. In `mod-detail-description`, `getByRole('link', { name: 'Docs (opens in a new tab)' })` exists, and its `::after` (`getComputedStyle(element, '::after')`) has a mask image containing `data:image/svg+xml` and a width greater than 0. The link is not clicked (no new tab, no request to example.com).
3. **None and one.** With no screenshots and no trailer: `mod-detail-page` is visible, `mod-screenshots` and `mod-detail-trailer-link` have count 0. With one: `mod-screenshot-image` is visible; `mod-screenshot-prev`, `-next`, `-position` and `-thumbnails` have count 0; the dialog opens and closes.
4. **Phone (390x844, `hasTouch: true`), one test that runs the checks with `colorScheme: 'light'` and then `'dark'`** (`page.emulateMedia` and a reload; assert `<html>` has, or has not, the class `dark`, so the test fails if the theme did not switch). First load the no-screenshots variant and record the document's `scrollWidth`; then the ten-screenshot variant: its `scrollWidth` is not larger; the box of `mod-screenshots` lies inside `[0, 390]`; `mod-screenshot-prev` and `-next` are at least 44x44; the first thumbnail is at least 44x44; `mod-screenshot-thumbnails` has `scrollWidth > clientWidth` and a computed `overflow-x` of `auto`; `tap()` on Next changes the position; `tap()` on the current image opens the dialog, whose Previous and Next are at least 44x44 and whose box lies inside the viewport. Keep the position text's computed color from the light pass and check the dark pass's differs (the section follows the theme).
5. **Live mod (no stub for the lookup), `betterruins`.** Wait for the lookup response as `mod-detail-bad-data.spec.ts:58-65` does: status 200; every `screenshots[].image_url` and `thumbnail_url` starts with `https://moddbcdn.vintagestory.at/`; `trailer_url` is `null` or matches `^https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}$`; if the list is not empty `mod-screenshots` is visible, otherwise it is absent (the database changes; do not hard-code 10). Needs network access to the public mod database, like the other detail-page specs.

No instance-specific value (server name, key) appears in the spec or its output.

### Existing tests that change (deliberately)

Found by running both suites against a throwaway prototype of Tasks 1, 2, 3 (types and a page stub) and 5 (the hook), since discarded: API 2679 passed, 3 failed; web typecheck 1 error; web tests 3185 passed, 4 skipped (`VSS-hnl`), and 75 failed in one file until the page read the list tolerantly (below).

- `api/tests/test_moddb_normalize.py::TestFieldTables::test_mod_fields` (`:63-70`): the expected set gains `"screenshots"`; add `"trailervideourl"` to `MOD_OPTIONAL_STR_FIELDS` (`:22-32`), which also feeds the parametrized optional-text tests. (Task 1)
- `api/tests/test_moddb_normalize.py::TestNormalizeModRules::test_empty_entry_has_every_field_with_its_default` (`:85-96`): passes as it is, but add `assert mod["screenshots"] == []`. (Task 1)
- `api/tests/test_moddb_normalize.py::TestNormalizeProperties::test_unknown_keys_kept` (`:240-252`): its example of an unknown mod key is `"screenshots": [{"fileid": 1}]`, which is now a known field and comes back with the four other keys filled in. Use another key the API does not read (for example `"wikiurl": "https://example.com"`); the release part of the test (`"mainfile": ""` on a release is still unknown there) is unchanged. (Task 1)
- `api/tests/test_mod_models.py::TestModLookupResponse::test_serialization_for_api_response` (`:478`): the exact dict gains `"screenshots": []` and `"trailer_url": None`. (Task 2)
- `web/src/api/mods.test.ts:584`: the typed `ApiResponse<ModLookupData>` literal needs `screenshots: []` and `trailerUrl: null` (the only typecheck error). (Task 3)
- **`web/src/features/mods/ModDetailPage.test.tsx`, no change needed, but only because of Task 3.3.** Its fixtures (`:64-113`, `:115-`, and the inline ones) are raw API JSON without `screenshots`. With `mod.screenshots.length` read directly, 75 of its 87 tests failed with a `TypeError` in render. With `Array.isArray(mod.screenshots) ? mod.screenshots : []` all 87 pass unchanged. Do not "fix" this by adding the field to every fixture and reading it directly: a missing optional list must not take the page down, and the existing guard (`:541-548`) says the same about the required ones.
- Not related: Story 17.4 saw `InstallConfirmDialog`, `QuickInstallButton`, `SettingField` and `GameConfigPanel` each fail one test under load in a full `vitest run` and pass alone. They did not fail in this story's prototype runs; if they fail in `just check`, re-run before suspecting this story.
- Anything else that fails is a regression (AC 12): fix the code, not the test.

### ADR and epic against the code

1. **ADR-1 decision 2, "the URL is kept only when it parses, its scheme is exactly `https`, its host is in `MOD_MEDIA_HOSTS`, and it has no user info and no port".** Implemented literally with `urllib.parse.urlsplit` this accepts URLs with leading whitespace, a trailing newline, control characters inside the host and an empty port (see "URL rules"). The story keeps the ADR's intent and adds the `_UNSAFE` check, the literal `https://` prefix and the `netloc` comparison. Stricter than the ADR's wording, never looser.
2. **ADR-2, "the description container's CSS draws an external-link icon after it".** There is no description CSS: the container's `prose` classes come from a plugin that is not installed. The story adds a `mod-description` class and one rule in `styles/index.css`. It does not install `@tailwindcss/typography` (a new dependency) and does not add link styling.
3. **Epic AC "at 390px ... the page does not scroll sideways".** The detail page's header was never fitted to phones: it is a non-wrapping `flex gap-6` row (`ModDetailPage.tsx:602`) of a 128px logo (`:606`, `flex-shrink-0`), the info column and a `w-64` install card (`:223`, `:398`), inside `p-4` (`Layout.tsx:49`). At 390px the content is 358px wide, and logo plus gaps plus the install card's content already need more before the info column gets any width, so the header overflows today, with or without this story. This was calculated from the classes, not measured; Task 6.2 measures it. Stories 16.5 and 17.8 did not touch this page, and no bead covers it. Fitting the header is outside `VSS-l4x` and `VSS-tzl`, so AC 7 is written for what this story adds: the Screenshots section stays inside the viewport and the page is no wider with it than without it. The Screenshots card is a block child of the page container (`space-y-6`), so the header's overflow does not widen it. If Task 6.2 finds the page does fit at 390px, the E2E test's "not wider than without screenshots" check already asserts the stronger statement. Reported as a follow-up.
4. **ADR-2 decision 5, arrow keys "in the card and in the dialog".** Correct, with the React portal pitfall described in "The gallery": the two handlers must not be nested in the React tree.
5. **ADR-2 decision 6, thumbnails "shown at their native 55x60".** Followed; see the decision in "The gallery".
6. ADR line references checked and correct at b9606f1: `lib/mod-description.ts:21-30`, `ModDetailPage.tsx:609-614`, `components/ui/dialog.tsx`.

### Not changed (do not "fix" these here)

- `logo_url` on lookup and browse is not put through the allow-list, and logo `<img>`s get no `referrerPolicy` (ADR-1 decision 6; change proposal follow-up 3). Images inside descriptions still load from any host.
- The three existing external links (ModDB Page, Homepage, Source, `:682-715`) keep their markup; only the new trailer link gets the screen reader note. `homepage_url` and `source_url` are not validated.
- The description gets no typography or link styling beyond the icon; `prose prose-sm prose-invert` stays on the container; no typography plugin.
- The detail page's header layout at phone widths (item 3 above), apart from `flex-wrap` on the links row.
- `components/ui/dialog.tsx` and `components/ui/button.tsx`. The dialog's own close button stays as it is (smaller than 44px; tapping the overlay also closes).
- `ModBrowseItem`, browse cards and `GET /mods/browse`: no media there. `routers/mods.py` changes only in a docstring, so Stories 18.2 and 18.3 can edit it without conflict.
- No embed, no YouTube thumbnail, no swipe gesture, no carousel library, no Content-Security-Policy.
- `agentdocs/vintagestory-modapi.md` (it already lists `screenshots`, `:64`, `:276`; describing `trailervideourl` there is change proposal follow-up 8).
- `sanitizeModDescription`'s configuration (`FORBID_TAGS`) and which links get `target="_blank"`.

### API contract changes

`v1alpha1`, both additive; cite these in the PR description and the release note.

- `GET /api/v1alpha1/mods/lookup/{slug}`: new field `screenshots`, a list of `{ "image_url": string, "thumbnail_url": string, "filename": string }` in mod database order, `[]` when the mod has none. Only `https` URLs on `moddbcdn.vintagestory.at` are passed on; `thumbnail_url` equals `image_url` when the mod database gave no usable thumbnail.
- `GET /api/v1alpha1/mods/lookup/{slug}`: new field `trailer_url`, `"https://www.youtube-nocookie.com/embed/<id>"` or `null` (maintainer decision 2026-11-16; planned as `https://www.youtube.com/watch?v=<id>`).
- No new error code, no changed status code, no change to any other endpoint. A lookup never fails because of media data.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/mod/{slug}`; the only live request in this story is the one-time fixture capture (Task 2.5) and the E2E live test.
- Captured fixtures are not edited by hand; bad data is built in the tests from a fixture's dict.
- After Task 2 and before Task 3 the API sends the fields and the web ignores them; every commit is green.
- No test reads a private member (`reportPrivateUsage`); `_https_parts`, `_UNSAFE` and `_VIDEO_ID` are tested through the three public functions.
- Web component tests use `@testing-library/user-event` (already a dev dependency) for keys, Tab order and focus.

### Security Requirements

- Mod database URLs are author-controlled. After this story the only media URLs that reach `src` are ones `mod_image_url` allowed, and the only trailer `href` is one the API built from an 11-character ID. The web renders them through React attributes (escaped) and does not re-validate, so there is one definition of an allowed URL (ADR-1 decision 5).
- Gallery images are requested with `referrerPolicy="no-referrer"`; the trailer link has `rel="noopener noreferrer"`. Nothing is requested from YouTube until the admin clicks the link.
- The description note is built with `createElement` and `textContent`, never from a string of HTML, and is added after DOMPurify has cleaned the link's attributes. The sanitizer's forbidden tags are unchanged.
- No new endpoint; `GET /mods/lookup/{slug}` keeps its auth (Admin and Monitor). The new fields are public mod database data. Rejected URLs are not logged.

### Development Commands

- `just test-api tests/test_moddb_normalize.py tests/test_mod_media.py tests/test_mod_models.py`, `just test-api tests/test_mod_service.py tests/test_mods_router.py`, `just test-web src/components/ModScreenshotGallery.test.tsx src/features/mods/ModDetailPage.test.tsx src/lib/mod-description.test.ts src/api/mods.test.ts`, `just typecheck`, `just lint`, `just check`.
- In a fresh worktree `just test-api` needs `VS_API_KEY_ADMIN` set (the settings refuse an empty key; the main checkout gets it from `.env`).
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **17.1 (Epic 17 ADR-1):** normalization happens once, at the boundary, by table; callers read fields directly. `_as_screenshot_list` and `_as_release_list` share one helper. pyright strict, baseline 0 errors and 3 pre-existing warnings in tests (`VSS-1ar`).
- **17.2:** `just format-api` must not be used. E2E cleanup needs a snapshot guard when real state changes; this story changes none.
- **17.3:** a hook-level `onError` on a TanStack Query v5 mutation replaces the client default, so such a hook must call `handleApiError` itself. This story adds no mutation and no query (the gallery reads `useModDetail`'s data), so there is no new error path; a failed lookup shows the existing error state.
- **17.4:** tests must not write into `dev/`; a `feat`/`fix` subject must describe something an admin can see (its review L1: an additive API field was committed as `feat`), hence `refactor`/`chore` for Tasks 1 and 2 here; a completion note must be true of the code; assertions on labels should be anchored so they cannot pass against the old source; with spec files running in parallel (`fullyParallel: true`), a spec must only clean up what it created (this spec creates nothing).
- **17.8:** layout checks measure boxes and `scrollWidth` in the browser rather than trusting class names; 44px targets are `h-11`/`size-11`/`min-h-11`. Its helpers in `layout-widths.spec.ts` are the model for test 4.
- **16.4:** introduced `lib/mod-description.ts` with a private DOMPurify instance so the hook cannot leak; keep it private (the "hook isolation" test).

### Git Intelligence

- Base: `b9606f1` (`docs(epic-18): plan epic 18 mod media and fixes`) on `main` `574e125`. Release notes come from commit subjects (`cliff.toml`, `RELEASING.md`). Planned: Task 1 `refactor`, Task 2 `chore`, Task 3 `feat` (show a mod's screenshots on its detail page), Task 4 `feat` (link to a mod's trailer from its detail page), Task 5 `fix` (show that mod description links open in a new tab), Task 6 `test`, Task 7 `docs`.
- Stories 18.2 and 18.3 also edit `models/mods.py` and `web/src/api/types.ts` (other classes) and are stacked on this one.

### Latest Technical Information

- No new libraries. Installed: `@radix-ui/react-dialog` ^1.1.15 (focus trap, Escape, focus return to the trigger), `dompurify` ^3.3.1 (`afterSanitizeAttributes` runs once per element after its attributes are cleaned; nodes appended in the hook are sanitized in the same pass), `lucide-react` ^1.0.0, React 19.3 (`referrerPolicy` and `loading` are plain `<img>` props), Tailwind 4 (`size-11` is 44px; `sr-only` is built in). Python: `urllib.parse.urlsplit` is lenient by design (it strips some control characters and never validates), which is why "URL rules" does not rely on it alone.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/mod_media.py`, `api/tests/test_mod_media.py`, `api/tests/fixtures/moddb/mod_betterruins.json`, `web/src/components/ModScreenshotGallery.tsx`, `web/src/components/ModScreenshotGallery.test.tsx`, `web/e2e/mod-detail-media.spec.ts`.
- Modified: `api/src/vintagestory_api/models/moddb.py`, `models/mods.py`, `services/mods.py`, `routers/mods.py` (docstring); `api/tests/test_moddb_normalize.py`, `test_mod_models.py`, `test_mod_service.py`, `test_mods_router.py`, `api/tests/fixtures/moddb/README.md`; `web/src/api/types.ts`, `web/src/api/mods.test.ts`, `web/src/features/mods/ModDetailPage.tsx`, `ModDetailPage.test.tsx`, `web/src/lib/mod-description.ts`, `mod-description.test.ts`, `web/src/styles/index.css`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.1: Mod Detail Page Media and Links]
- [Source: _bmad-output/planning-artifacts/prd.md] FR194-FR198
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md] Mod Database Facts; Content Security Policy and Image Loading; ADR-1; ADR-2 (and its "Related, same story" note for `VSS-tzl`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-1] normalization at the boundary
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-16.md] API changes table (18.1), open questions 1 (trailer target) and 4 (swipe), follow-ups 3, 4 and 8
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] 44px minimum touch targets (`:515`, `:1180`)
- [Source: _bmad-output/implementation-artifacts/17-4-installed-status-is-right-everywhere.md] structure, Completion Notes, Senior Developer Review
- [Source: _bmad-output/implementation-artifacts/17-8-layout-at-tablet-and-phone-widths.md] layout measurement in E2E
- Beads: `VSS-l4x`, `VSS-tzl`, parent `VSS-5w8`
- `project-context.md` - critical implementation rules (no suppressions; manual test tasks need the user's confirmation, `:160-161`)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), BMAD dev-story, non-interactive.

### Debug Log References

- `captured_logs` (`tests/conftest.py`) configures a DEBUG filtering logger, so it records debug events; its console renderer colors keys and values, so `test_mod_media.py` strips ANSI codes before matching `slug=` and `index=`.
- `ruff format` on the changed API files also reformatted unrelated lines (the files were not formatted at the configured width). Those hunks were reverted; one slipped into the Task 1 commit (`test_moddb_normalize.py`, one assert) and was restored in the Task 2 commit, so the branch's net diff has no formatting churn.
- jsdom's accessible-name computation trims each child element's text, so a leading space inside an `sr-only` span is dropped (`Watch trailer(opens in a new tab)`), while Chromium keeps it. See the deviations below.
- E2E: the dialog's Previous measured 41.8px (44 x 0.95) during the `zoom-in-95` open animation; the phone test waits for the dialog's animations to finish before measuring.
- Task 6.2, page widths at 390px (document `scrollWidth`, `e2e/mod-detail-media.spec.ts` phone test): light theme 674px without screenshots and 674px with; dark theme 674px and 674px. The page already overflows at 390px (the header, Dev Notes "ADR and epic against the code" item 3, now measured); the Screenshots section adds no width.

### Completion Notes List

- Story created 2026-11-16 from Epic 18, ADR-1 and ADR-2, the two beads and the code at b9606f1: the normalizer, the lookup model, service and route, the detail page, the description sanitizer and its tests, the dialog and button components, the styles, and the E2E specs of Stories 17.1, 17.4 and 17.8. The live `betterruins` entry was fetched once to confirm the screenshot shape. The tests that change were found by running both suites against a throwaway prototype (normalizer fields, `mod_media.py`, response fields, web types with a page stub, and the description hook), since discarded.

- Implemented 2026-11-16. Task 1: `SCREENSHOT_FIELDS`, `screenshots` and `trailervideourl` in `MOD_FIELDS`, one shared `_as_object_list` helper behind `_as_release_list` and `_as_screenshot_list`; still four `cast(` calls in `models/moddb.py`. Task 2: `services/mod_media.py` as specified in "URL rules", with the trailer target kept in one constant, `TRAILER_WATCH_URL`; `ModScreenshot` and the two `ModLookupResponse` fields; `lookup_mod` fills them; router docstring only. Task 3: `ModScreenshotGallery` (the `Dialog` root wraps the Card and `DialogContent`, which are siblings, so the two `onKeyDown` handlers are not nested); the page reads `screenshots` tolerantly. Task 4: "Watch trailer" link with `OPENS_IN_NEW_TAB`; the links row wraps. Task 5: the sanitizer hook appends the note to HTML links once; the `.mod-description` CSS draws the icon.
- The `betterruins` fixture was captured once (unauthenticated, generic User-Agent) and matches planning: 10 screenshots, `youtube-nocookie.com/watch` trailer, 61 releases (first 3 kept). Tests still read counts and URLs from the fixture's raw JSON.
- Deviation 1 (Task 4.2): the trailer link renders `Watch trailer{' '}<span className="sr-only">{OPENS_IN_NEW_TAB}</span>` instead of a leading space inside the span. The separating space is a text node before the span; in the `inline-flex` link a whitespace-only text node is not rendered, so nothing visible changes, and the accessible name is `Watch trailer (opens in a new tab)` in jsdom and in Chromium (both asserted exactly).
- Deviation 2 (Task 5.3, page test): the description note keeps the story's shape (leading space inside the span; the link's `textContent` is exactly `CarryOn Lib (opens in a new tab)`). jsdom computes the name without that space, so the `ModDetailPage.test.tsx` test finds the link by `/^CarryOn Lib ?\(opens in a new tab\)$/` and asserts the exact `textContent`; the E2E test asserts the exact name `Docs (opens in a new tab)` in Chromium, which passes.
- Deviation 3 (Task 5.3): "sanitizing the output again leaves exactly one note" is asserted by note count and text, not string equality: DOMPurify re-adds `target`/`rel` and the attribute order changes on the second pass.
- Tests: API 2786 passed (was 2707 before Task 2; new `test_mod_media.py` 62 tests). Web 3291 passed, 4 skipped (`VSS-hnl`), new `ModScreenshotGallery.test.tsx` 18 tests. E2E: `mod-detail-media.spec.ts` 5 passed; `mod-detail-bad-data.spec.ts` and `installed-mod-any-modid.spec.ts` 5 passed, against the dev stack rebuilt from this branch (no game server running; none started or stopped; reads only).
- `just check` green: 0 Pyright errors, the 3 known warnings (`VSS-1ar`). No lint or type suppression, no new dependency, nothing written under `dev/`.
- Not done here: Task 6.3 (manual browser check in both themes) needs the maintainer's confirmation (`project-context.md:160-161`) and stays unticked. Task 7.2's PR and the PR links on `VSS-l4x` and `VSS-tzl` are left to the maintainer (no PR opened, beads unchanged).
- Maintainer decision 2026-11-16 (after review): the trailer link targets the privacy-enhanced `https://www.youtube-nocookie.com/embed/<id>` page instead of `youtube.com/watch` (its `/watch` path is a 404; `/embed/<id>` was checked live: 200). `TRAILER_WATCH_URL` and `trailer_watch_url` were renamed `TRAILER_EMBED_URL` and `trailer_link_url`; the API, web and E2E tests expect the embed URL (red first, then the constant changed). The Dev Notes code sample and test tables keep the planned names. ADR-2 and the change proposal record the amendment.

### File List

New:
- `api/src/vintagestory_api/services/mod_media.py`
- `api/tests/test_mod_media.py`
- `api/tests/fixtures/moddb/mod_betterruins.json`
- `web/src/components/ModScreenshotGallery.tsx`
- `web/src/components/ModScreenshotGallery.test.tsx`
- `web/e2e/mod-detail-media.spec.ts`

Modified:
- `api/src/vintagestory_api/models/moddb.py`
- `api/src/vintagestory_api/models/mods.py`
- `api/src/vintagestory_api/services/mods.py`
- `api/src/vintagestory_api/routers/mods.py` (docstring)
- `api/tests/test_moddb_normalize.py`
- `api/tests/test_mod_models.py`
- `api/tests/test_mod_service.py`
- `api/tests/test_mods_router.py`
- `api/tests/fixtures/moddb/README.md`
- `web/src/api/types.ts`
- `web/src/api/mods.test.ts`
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `web/src/lib/mod-description.ts`
- `web/src/lib/mod-description.test.ts`
- `web/src/styles/index.css`
- `_bmad-output/implementation-artifacts/18-1-mod-detail-media-and-links.md`

## Senior Developer Review (AI)

**Date:** 2026-11-16
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `6285da4..9051973`
**Outcome:** Approve → resolved

**Summary:** No HIGH or MEDIUM finding. All 12 acceptance criteria met with discriminating tests. The reviewer probed the URL validation with 20 hostile inputs beyond the story's tables (userinfo, ports, look-alike and suffix hosts, encoded separators, `javascript:`/`data:`, control characters) and could not get one through; the rebuilt trailer URL takes only an 11-character ID. Reviewer re-ran `just test-api` (2786 passed), `just test-web` (3291 passed, 4 skipped), `just lint` and `just typecheck` (0 errors, the 3 known warnings); nothing written under `dev/`.

### Action Items

- [x] [Low] L1 `mod-description.ts`: the idempotency check looked only at the link's last child, so a mod author's own `<span data-new-tab-note>` inside a link suppressed the screen reader note (fixed, 3f96136: every marked span inside a link is removed before the one real note is appended; a second pass still gives one note; new unit test with both author-marker positions)
- [x] [Low] L2 `mod-detail-media.spec.ts`: the exact full-size request check depended on Chromium's lazy-load distance (fixed, 1cafa38: the section is scrolled into view before the poll)
- [x] [Low] L3 bookkeeping: `sprint-status.yaml` is not in the File List and task 7.2 is partial (not changed: the project keeps `sprint-status.yaml` out of File Lists; task 7.2's PR is opened by the controller)
- Nits not changed: a weak `"debug" in output` substring next to stronger assertions; `step` computed from render-time state (safe with React's synchronous discrete events).

After the fixes: `mod-description.test.ts` and the mods feature tests 235 passed; `just lint-web` and `just typecheck-web` clean; on the stack rebuilt from this branch (`just docker restart`, no game server running, none started or stopped) `mod-detail-media.spec.ts` and `mod-detail-bad-data.spec.ts` 7 passed.

## Change Log

- 2026-11-16: Story 18.1 created (ready-for-dev).
- 2026-11-16: Validated against the create-story checklist: every cited path and line re-read at b9606f1; the URL rule tightened after the prototype showed `urlsplit` accepting whitespace, control characters and an empty port; AC 7 scoped to the Screenshots section because the page header already overflows at 390px; the tolerant read of `screenshots` added after 75 detail-page tests failed without it; the `test_unknown_keys_kept` example, the exact-dict model test and the one typed web literal listed; the missing description styles and the React portal key-event pitfall recorded.
- 2026-11-16: Implemented Tasks 1-6 (6.3 manual check left for the maintainer); quality gate green; status review.
- 2026-11-16: Code review (GLM-5.3-Flash): approved, three low findings; L1 and L2 fixed, L3 not changed. Status done.
- 2026-11-16: Maintainer chose the youtube-nocookie embed URL as the trailer target; AC 3 and the API contract changes amended, code and tests changed.
