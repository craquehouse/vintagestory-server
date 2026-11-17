# Sprint Change Proposal: API Security and Mod File Safety (Epic 19)

**Date:** 2026-11-17
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (batch, non-interactive; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Scope, grouping and the `VSS-9wv` decision approved by Matt, 2026-11-16. Reviewed by Matt on 2026-11-17 and revised the same day: the nine open questions are answered (section 5), `VSS-9wv` is its own story, and the seven follow-ups the first version reported were filed as beads and folded in. Six stories, eighteen beads. Revised a second time the same day: Matt decided the four observations the first revision reported, and they are written into the plan (a new Story 19.5 and ADR-10, and additions to Stories 19.1, 19.2, 19.3 and 19.7); seven stories, eighteen beads. The ADRs added in the revision (ADR-3, ADR-7, ADR-9, ADR-14) have not been reviewed yet.

## 1. Issue Summary

**Trigger:** Epic 18 is done and on `main` (`048fea9`, release `v0.1.0-rc.4`). The maintainer picked eleven open beads for the next epic, all follow-ups filed during Epic 15, Epic 17 and Epic 18 work: four about who can read secrets and keys, one about the missing Content-Security-Policy, four about mod files being overwritten, and two about mod database data passed on unchecked. Planning found seven more items in the same code; the maintainer filed them and added them to the epic so that they do not stay open: `VSS-3hs2`, `VSS-my4c`, `VSS-5mes`, `VSS-yhmt`, `VSS-uoxl`, `VSS-0lkb`, `VSS-wenx`.

**Problem:** The manager separates an Admin role from a read-only Monitor role, and several paths go around that separation: the config file viewer serves any file in any directory and redacts one key at one depth, and the default deployment hands the Admin key to anyone who can load the web page. The page that holds that key has no Content-Security-Policy, and the same origin serves documentation pages that load scripts from a CDN. Beside that, three of the four operations that place a mod file can replace another mod's file or report the refusal as a server error, a crash can leave files nothing recovers, the download cache can mix two mods' archives, URLs and response bodies from the mod database are trusted in places Epic 17 and Epic 18 did not reach, and the browser tests that would catch a regression in any of this run only on a developer's machine.

**Evidence** (code at commit `048fea9`; details and line references in `architecture/epic-19-api-security-and-mod-file-safety.md`):

- `ConfigFilesService.read_file` has no file type, suffix or size check (`services/config_files.py:179-227`), while `list_files` lists only `*.json` (`:172-174`). `read_text` is outside the `try` (`:213`), so a binary file or a directory is a 500 (`VSS-633`).
- `redact_secrets` changes only an object's own keys that equal `Password` (`services/game_config.py:215-248`); the nested case is pinned as a known limit by `test_nested_password_is_unchanged` (`VSS-sg1`).
- The three config file routes do not look at the role when choosing directories (`routers/config.py:393-538`); a Monitor key can list `Saves`, `Backups` and `Playerdata` and read the player files (`VSS-3hs2`).
- `Settings.game_version` (`config.py:24`) is read by nothing; `.env.example:20-23` says it chooses the version to install (`VSS-ms0`).
- `Settings.web_api_key` falls back to the Admin key (`config.py:31-36`) and `/config.js` serves it unauthenticated (`main.py:260-272`). Both compose files pass `VS_API_KEY` blank by default. The only start-up warning is for a key that matches no role (`main.py:103-108`) (`VSS-9wv`).
- No `Content-Security-Policy` is set by the API, `web/index.html` or the Vite configuration. The built page has only same-origin script files; four dependencies create `<style>` elements at run time (`VSS-3qb8`). Mod descriptions keep `<img>` from any address, `http:` included (`web/src/lib/mod-description.ts`) (`VSS-my4c`).
- `FastAPI(...)` sets no `docs_url`, `redoc_url` or `openapi_url` (`main.py:165-170`), so the documentation pages and the schema are served without a key and load scripts from a public CDN (`VSS-5mes`).
- `enable_mod` and `disable_mod` rename without checking the target or that their own file exists (`services/mods.py:749`, `:807`) (`VSS-40ja`, `VSS-yhmt`). `_apply_version_change` refuses a taken name with `ModVersionChangeFailedError`, a 500 (`:1008-1012`, `routers/mods.py:1137-1138`) (`VSS-macf`). `_place_install` compares names exactly (`:1283-1290`) (`VSS-52fy`).
- An install copies to `<name>.tmp`, and a same-name version change moves the installed file to `<name>.bak` first (`services/mods.py:1014-1023`, `:1297-1311`); a killed process leaves them, and the `.bak` can be the only copy of the mod (`VSS-uoxl`).
- `download_release_file` writes `cache/mods/<name>.tmp` and renames it to `cache/mods/<name>` (`services/mod_api.py:578-595`); the per-mod locks do not stop two different mods downloading the same file name at once, and an install does not require the archive's mod ID to be the one it resolved (`services/mods.py:1236-1244`) (`VSS-n0qv`).
- `logo_url`, `homepage_url` and `source_url` are passed through unchecked (`services/mods.py:690-694`, `routers/mods.py:238`); the three logo `<img>` elements have no `referrerPolicy` (`VSS-2zis`).
- `get_all_mods` calls `response.json()` and `data.get` unguarded (`services/mod_api.py:664-668`), and `_fetch_mods_by_version` calls `data.get` unguarded (`:869`) (`VSS-ce0h`). Neither `get_game_versions` nor `get_all_mods` shares a running fetch (`:948-952`, `:659-664`) (`VSS-ce0h`, `VSS-0lkb`).
- `.github/workflows/ci.yml` builds the image and never runs it; no job runs the 18 specs in `web/e2e/`. Fifteen specs carry a `localStorage` init script (17 occurrences) that the web stopped reading in Story 17.5 (`VSS-wenx`; the bead says twelve, the count in the code is fifteen).
- Mod database, checked 2026-11-16: every non-null listing `logo` (6,531 of 9,636) is an `https://moddbcdn.vintagestory.at/` URL; across the 60 most downloaded mods every non-empty `homepageurl` (33) and `sourcecodeurl` (44) is `https`.

**Scope decisions (made by the maintainer):**

| Decision | Choice |
|---|---|
| Items in scope | The eleven of 2026-11-16 (`VSS-633`, `VSS-sg1`, `VSS-9wv`, `VSS-ms0`, `VSS-3qb8`, `VSS-40ja`, `VSS-macf`, `VSS-52fy`, `VSS-n0qv`, `VSS-2zis`, `VSS-ce0h`) and the seven added on 2026-11-17 (`VSS-3hs2`, `VSS-my4c`, `VSS-5mes`, `VSS-yhmt`, `VSS-uoxl`, `VSS-0lkb`, `VSS-wenx`): 18 issues in 7 stories (Story 19.5 has no bead of its own) |
| Grouping (2026-11-17) | 19.1 `VSS-633` + `VSS-sg1` + `VSS-ms0` + `VSS-3hs2`; 19.2 `VSS-9wv`; 19.3 `VSS-3qb8` + `VSS-my4c` + `VSS-5mes`; 19.4 `VSS-40ja` + `VSS-macf` + `VSS-52fy` + `VSS-n0qv` + `VSS-yhmt` + `VSS-uoxl`; 19.5 no bead, rides with `VSS-uoxl` (second revision); 19.6 `VSS-2zis` + `VSS-ce0h` + `VSS-0lkb`; 19.7 `VSS-wenx`. Checked against the code: each added bead is in the files its story already edits, so the grouping stands as given |
| Order | 19.1 to 19.7. Dependencies found: 19.3 after 19.2, 19.5 directly after 19.4, 19.7 last |
| `VSS-9wv` | "A plus C": a start-up warning and documentation, and no Admin key for the web UI unless `VS_API_KEY` is set. C is a breaking change. Its own story since the review |
| Start-up reconcile of the mod state (Matt, 2026-11-17) | In scope as Story 19.5, with no bead of its own; it rides with `VSS-uoxl`. Called once at start-up after the working-file recovery; no endpoint, no button |
| Seeded `serverconfig.json` in CI (Matt, 2026-11-17) | In scope, Story 19.7: the settings specs run in CI; `@moddb`, `@game-server` and `@install` stay local-only |
| `Settings()` built three times in `main.py` (Matt, 2026-11-17) | In scope as part of Stories 19.2 and 19.3: one cached settings object and an app that tests can build with chosen settings. Service-level cleanup is out of scope; no bead |
| A hint for Monitor in the file browser (Matt, 2026-11-17) | In scope, Story 19.1: a short static note, no folder names or counts |
| `VSS-2kdt` (a login) | Not in scope: a separate follow-up |
| Preparation story | None |
| `VSS-1ar`, `VSS-hnl`, `VSS-6wj` | Not in scope: known items that predate this epic |

**Decisions made in planning** (in the ADR file):

| Question | Decision | ADR | Reviewed |
|---|---|---|---|
| With `VS_API_KEY` unset: refuse to start, or start and serve no key? | Start; `/config.js` serves an empty key and the web UI shows a set-up screen. The API supervises the game server, API-only use is valid, health probes keep passing, and the API already warns instead of refusing for a wrong `VS_API_KEY` | ADR-5 | Confirmed 2026-11-17 |
| What may the config file viewer serve? | `.json` regular files up to 2 MiB | ADR-1 | Confirmed |
| How are nested and other-named secrets redacted? | Recursively by key name (a declared fragment list plus `StartupCommands`) and two value rules; Admin gets files unchanged | ADR-2 | Confirmed |
| `VS_GAME_VERSION`: remove or repurpose? | Remove; setting it stays harmless | ADR-4 | Confirmed |
| CSP: where, which directives, enforced? | A response header from the API on the web UI's pages, enforced, with `VS_CSP_MODE` as the way out | ADR-6 | Confirmed |
| Which directories may each role list and read? | Roles other than Admin: the root files and `ModConfig` only (an allow-list); other directories are 403 | ADR-3 | New |
| What happens to `http:` images in descriptions under the policy? | The sanitizer replaces any image that is not `https:` or `data:image/` with a short text | ADR-6 decision 14 | New |
| `/docs`, `/redoc`, `/openapi.json`: key, switch or self-hosted assets? | Off unless the API runs in debug mode; no new setting | ADR-7 | New |
| Enable or disable with the mod's own file missing | 409 `MOD_FILE_MISSING`, state unchanged, the message says to remove and reinstall | ADR-9 | New |
| Leftover `.tmp` and `.bak` files | The manager's working files get their own suffixes and are recovered at start-up from the mod state; other `.tmp` and `.bak` files are reported and left alone | ADR-9 | New |
| Shared fetch for the full listing | One helper for the listing, the game version list and the filtered listings; a forced refresh joins a running fetch | ADR-13 | New |
| Where does the start-up reconcile go: a task of 19.4 or a story? | A story of its own, 19.5, directly after 19.4. Story 19.4 is at the six-task limit, the sync needs 19.4's recovery and suffixes first, and a change that removes state entries at start-up should have its own review. The existing `sync_state_with_disk` is made safe first: it would stop start-up on one unreadable archive and would remove entries for files that exist under a non-zip name | ADR-10 | Matt, 2026-11-17 (the decision to call it); placement by planning |
| What runs in CI? | The E2E tests that need nothing outside the stack; tests that need the live mod database, a game server or a real install are tagged and left out | ADR-14 | New |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 18 are done; none is invalidated. One new epic, Epic 19: API Security and Mod File Safety, with 7 stories. No resequencing.

**Story impact:** No existing story changes. Story 19.1 replaces Story 17.5's "top-level keys only" redaction. Story 19.2 changes Epic 15 ADR-5 (the web key no longer falls back to the Admin key). Story 19.4 extends Epic 18 ADR-4 and replaces its decision 6. Story 19.6 replaces Epic 18 ADR-1 decision 6.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR205-FR233; frontmatter |
| Epics | Add Epic 19; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-19-api-security-and-mod-file-safety.md` (facts, ADR-1 to ADR-14); index entry |
| UX spec | None. One new full-page message (no key configured) follows the existing empty-state pattern |
| Deployment and documentation | README, `.env.example`, both compose files and `scripts/worktree-setup.sh` change in Stories 19.1, 19.2 and 19.3 |
| CI | A new `e2e` job in `.github/workflows/ci.yml` (Story 19.7) |
| Beads | Epic `Epic 19: API Security and Mod File Safety` (`VSS-fl9b`) with the 18 in-scope issues as children |

**Technical impact:**

- Stories 19.1, 19.2, 19.3 and 19.6 change the API and the web. Stories 19.4 and 19.5 are API only. Story 19.7 changes the E2E specs, the Justfile and the CI workflow.
- No new dependencies.
- Configuration: `VS_API_KEY` becomes necessary for the web UI (breaking); `VS_CSP_MODE` is new and optional; `VS_GAME_VERSION` goes; the API documentation pages follow `VS_DEBUG`.
- The download cache is emptied once on the first start after Story 19.4, and start-up gains a recovery pass over the mods directory (19.4) followed by a reconcile of the mod state with it (19.5).
- `main.py` builds the app through a factory from one settings object (19.2, 19.3); no behaviour changes from that.
- CI gains a job that builds and starts the image and installs a browser.
- The maintainer's cluster deployment (another repository, not touched here) must set `VS_API_KEY` in the release that carries Story 19.2.

**API contract changes, all in `v1alpha1` unless noted (for the release notes).** Rows marked "revision" were added or changed on 2026-11-17.

| Story | Where | Change | Kind |
|---|---|---|---|
| 19.1 | `GET /config/files/{path}` | 400 `CONFIG_FILE_NOT_SUPPORTED` (new code) for a name that does not end in `.json`, a directory, a file that is not a regular file or not UTF-8 text. Before: 200 (text files), 404 or 500 | New error code, behavior change |
| 19.1 | `GET /config/files/{path}` | 413 `CONFIG_FILE_TOO_LARGE` (new code) above 2 MiB | New error code |
| 19.1 | `GET /config/files/{path}` | For roles other than Admin, more values are `"[redacted]"`: secret key names at any depth, `StartupCommands`, URLs with credentials, Discord webhook URLs. The redacted value replaces the whole value, whatever its type | Behavior change (Monitor only) |
| 19.1 | `GET /config/files/{path}` | A file with a byte order mark now parses instead of returning `_raw` | Behavior change |
| 19.1 (revision) | `GET /config/directories`, `GET /config/files`, `GET /config/files/{path}` | For roles other than Admin: the root listing of directories holds `ModConfig` only; any directory other than the root and `ModConfig` is 403 `FORBIDDEN` (existing code) for listing and reading. Before: 200 | Behavior change (Monitor only) |
| 19.1 | `VS_GAME_VERSION` | Removed from the settings, compose files and `.env.example`. Still accepted and ignored | Removed setting, not breaking |
| 19.2 | `GET /config.js`, `VS_API_KEY` | With `VS_API_KEY` unset or blank, serves `{"apiKey": ""}` instead of the Admin key; the web UI shows a set-up screen. Setting `VS_API_KEY` (to the Monitor or the Admin key) restores a working UI | **Breaking** |
| 19.2 | Start-up log | New warnings `web_api_key_is_admin_key` and `web_api_key_not_set` | Added |
| 19.3 | Web UI pages (`/` and every non-API path) | New headers `Content-Security-Policy` (enforced), `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`. Images over plain `http:` in mod descriptions are replaced by a text; the page cannot be framed | Behavior change |
| 19.3 | `VS_CSP_MODE` | New setting: `enforce` (default), `report-only`, `off` | Added setting |
| 19.3 (revision) | `/docs`, `/redoc`, `/openapi.json` | Served only when `VS_DEBUG=true`. Otherwise the paths return the web UI's page (or 404 without the frontend). Before: always served. Not part of `v1alpha1`; a client that fetched the schema from a production deployment loses it | Removed by default; see the note below |
| 19.4 | `POST /mods/{slug}/enable`, `POST /mods/{slug}/disable` | New error 409 `MOD_FILE_CONFLICT` when the target file name is taken. Before, the other file was replaced | New error on these routes, behavior change |
| 19.4 (revision) | `POST /mods/{slug}/enable`, `POST /mods/{slug}/disable` | New error 409 `MOD_FILE_MISSING` (new code) when the mod's own file is not in the mods directory. Before: 500 | New error code |
| 19.4 | `PUT /mods/{slug}/version` | A taken file name is 409 `MOD_FILE_CONFLICT`; before 500 `MOD_VERSION_CHANGE_FAILED`. The check also covers the `.disabled` form and the mod state | Changed status and code |
| 19.4 | `POST /mods`, and the three above | File names are compared ignoring letter case | Behavior change |
| 19.4 | `POST /mods/updates/apply-all` | Response shape unchanged; a file-name conflict is a `failed` item | None |
| 19.4 | Download cache and mods directory on disk | Cache layout `cache/mods/<fileid>/<name>`, old files removed at start. (revision) Working files are `<name>.vsm-tmp` and `<name>.vsm-bak` and are recovered at start-up. Not an API | Internal |
| 19.5 (second revision) | `GET /mods`, and every route that looks an installed mod up | No shape change. After a restart of the manager the installed mods are those in the mods directory: an archive added by hand is listed (no asset ID, no update record until the next check), and an entry whose file is gone is no longer listed, so its routes answer 404 `MOD_NOT_INSTALLED` | Behavior change at start-up |
| 19.1 (second revision) | Web UI | A note in the file browser for roles other than Admin. No API change | None |
| 19.6 | `GET /mods/lookup/{slug}`, `GET /mods/browse` | `logo_url` is `null` unless it is an `https` URL on `moddbcdn.vintagestory.at` | Behavior change |
| 19.6 | `GET /mods/lookup/{slug}` | `homepage_url` and `source_url` are `null` unless a well-formed `https` URL; `""` becomes `null` | Behavior change |
| 19.6 | `GET /mods/browse` and other mod routes | A mod database body that is not a JSON object is 502 `EXTERNAL_API_ERROR`; before 500 | Changed status |
| 19.7 | None | CI and tests only | None |

No response field is removed or renamed. **One breaking item,** unchanged by the revision: Story 19.2. Note on the documentation pages: they are outside the versioned API, so the plan does not mark their removal as breaking; if the maintainer wants it marked, the Story 19.3 commit takes a `!` and a line under Breaking Changes.

**Draft release-note text** (the commit subjects that produce it; `cliff.toml` prints the subject):

- Breaking Changes: `feat(api)!: the web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key`, with the footer `BREAKING CHANGE: /config.js serves no key when VS_API_KEY is unset or blank, and the web UI shows a set-up message. Set VS_API_KEY to VS_API_KEY_MONITOR for a read-only web UI or to VS_API_KEY_ADMIN for full access; anyone who can load the web UI receives that key.`
- Features: `feat(api): warn at start-up when the web UI is given the Admin key`; `feat(api): serve the web UI with a Content-Security-Policy (VS_CSP_MODE)`
- Fixes, Story 19.1: `fix(api): the config file viewer serves only .json files and no longer fails on binary files`; `fix(api): hide nested and other-named secrets in config files from Monitor keys`; `fix(api): Monitor keys can no longer list or read saves, backups and player data`; `fix(docker): VS_GAME_VERSION is no longer set or documented; it had no effect`
- Fixes, Story 19.3: `fix(web): mod description images that cannot be loaded securely show a note instead of a broken image`; `fix(api): serve the API documentation pages only when VS_DEBUG is on`
- Fixes, Story 19.4: `fix(api): enabling, disabling or changing the version of a mod can no longer replace another mod's file`; `fix(api): enabling or disabling a mod whose file is missing explains what to do instead of failing`; `fix(api): recover mod files left by an interrupted install or version change at start-up`; `fix(api): keep downloaded mod files apart when two mods use the same file name`
- Fixes, Story 19.6: `fix(api): pass on only https logo, homepage and source links from the mod database`; `fix(api): answer 502, not 500, when the mod database sends a malformed response`; `perf(api): fetch the mod list once when several requests arrive together`
- Story 19.5: `feat(api): pick up mods added or removed by hand when the manager starts`
- Story 19.1, the note: `feat(web): tell Monitor users that some folders are only shown to Admin keys`
- Story 19.7 has no release note (`ci` and `test` commits). The app factory work in Stories 19.2 and 19.3 is `refactor` and has none.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 19 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Seven stories, six tied to existing beads and one riding with `VSS-uoxl`. Effort medium, risk low to medium. |
| 2. Rollback | Not viable. Nothing completed has to be undone. |
| 3. MVP Review | Not needed. |

**Effort:** Medium. Three issues are size-m in beads (`VSS-9wv`, `VSS-3qb8`, `VSS-wenx`) and fifteen are size-s. Story 19.4 is the largest by count (six beads in the mod file code); Story 19.3 spans the API, the web and a browser spec.

**Risks:**

- Story 19.2: the breaking change. An upgraded deployment that does not set `VS_API_KEY` has a web UI that shows a set-up message. The API and the game server keep running, the page says what to set, and the release note is the first entry. The maintainer's own deployment needs its one-line change in the same release.
- Story 19.1: key-name redaction is a heuristic. It hides some harmless values from Monitor and misses a secret under an unrecognisable name with an unrecognisable value. The README says so.
- Story 19.1: the allow-list hides from Monitor any configuration a mod keeps outside `ModConfig/` and the root. Adding a directory is one constant.
- Story 19.3: an enforced policy can break a page in a browser the E2E run does not cover. `VS_CSP_MODE` is the way out without a new image; the WebSocket behaviour under `connect-src 'self'` and the next-themes script are confirmed in a browser before the policy is fixed.
- Story 19.3: `style-src 'unsafe-inline'` and `img-src https:` are weaker than a strict policy. The alternative breaks the terminal, toasts and description images.
- Story 19.3: a client that reads `/openapi.json` from a production deployment loses it.
- Story 19.4: size, six beads. They share one helper and one test fixture, and the tasks are at the project's limit of six.
- Story 19.4: start-up recovery moves and deletes files in the mods directory. It touches only files with the manager's own suffixes, decides from the mod state, and is tested for each point at which an operation can be interrupted.
- Story 19.4: the first start after the upgrade empties the download cache.
- Story 19.4: comparing file names without case refuses an install that a case-sensitive volume would have accepted (`foo.zip` beside `Foo.zip`). That is the bead's intent.
- Story 19.5: the sync removes state entries at start-up. It removes only an entry whose own file is not there, runs after the recovery of Story 19.4, and never deletes a file. When the mods directory itself does not exist the sync changes nothing (ADR-10 decision 10), so a volume that is not there yet does not empty the state.
- Stories 19.1, 19.2 and 19.3 are each at six tasks after the additions.
- Story 19.6: an author's `http:` homepage or source link is dropped. None was seen in the sample of 60.
- Story 19.7: CI covers only the tests that need nothing outside the stack. The mod database flows and the settings pages stay local-only; the tags make that visible.
- Stories 19.4 and 19.6 edit the same two service files, and Stories 19.1 and 19.2 the same configuration files; in parallel they would conflict.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** `lastUpdated: '2026-11-17'`; update entry "Added FR205-FR233 for Epic 19 (API Security and Mod File Safety)".

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 19: API Security and Mod File Safety

#### Secrets and Roles

- FR205: The config file viewer lists and serves only `.json` files under the server data directory, up to 2 MiB
- FR206: A config file request for anything else (another file type, a directory, a file that is too large or not UTF-8 text) is refused with a 4xx status and an error code, never a 500
- FR207: For every role other than Admin, config file content is redacted at every depth: values under secret key names, `StartupCommands`, URLs that contain credentials and Discord webhook URLs; Admin receives files unchanged
- FR208: Roles other than Admin can list and read only the root of the server data directory and `ModConfig`; any other directory (saves, backups, player data) is listed and read by Admin only
- FR209: `VS_GAME_VERSION` is removed from the settings and the documentation; a deployment that still sets it starts as before

#### The Web UI's Key

- FR210: When `VS_API_KEY` is unset or blank, the web UI is given no API key: the API starts, `/config.js` serves an empty key, and the web UI shows a set-up message and makes no API request
- FR211: The API logs a start-up warning whenever the web UI's key is the Admin key and whenever the web UI has no key, never logging a key
- FR212: The README, `.env.example` and the compose examples explain `VS_API_KEY`, recommend the Monitor key or an authenticating proxy for the web UI, the production example does not hand out the Admin key by default, and the release notes list the change as breaking with what to set

#### Content-Security-Policy and API Docs

- FR213: The web UI's pages are served with an enforced Content-Security-Policy that allows scripts from the manager's own origin only and forbids framing; it is not sent on API or health routes
- FR214: Every page of the web UI, including the console WebSocket, the mod gallery and mod description images, works under the policy in the light and dark themes with no policy violation
- FR215: `VS_CSP_MODE` switches the policy between enforced, report-only and off, and the web UI's pages also send `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`
- FR216: An image in a mod description that the policy would block (any address that is not https or an image data URL) is replaced by a short text with its alt text, with no request and no broken-image icon
- FR217: The API documentation pages and the OpenAPI schema (`/docs`, `/redoc`, `/openapi.json`) are served only when the API runs in debug mode

#### Mod Files

- FR218: Enabling or disabling a mod whose target file name is already used is refused with 409 `MOD_FILE_CONFLICT` and changes no file and no state
- FR219: A version change whose new file name is already used is refused with 409 `MOD_FILE_CONFLICT` instead of a 500, changes nothing, and in Update All is one failed item that does not stop the run
- FR220: File-name collisions for install, enable, disable and version change are detected ignoring letter case, so the result does not depend on the volume's filesystem
- FR221: The mod download cache keeps each release under its file ID with a temporary file per download, so mods whose releases share a file name never replace or mix each other's cached archives
- FR222: Enabling or disabling a mod whose own file is missing is refused with 409 `MOD_FILE_MISSING` and a message that says what to do, never a 500
- FR223: At start-up the manager recovers from an interrupted install or version change: its own working files are removed or put back so that every mod's file matches the mod state; files it did not create are reported and left alone

#### Mod Database Data

- FR224: The API passes on a mod's logo URL only when it uses https on the mod database's image host, and the web requests logo images without a referrer
- FR225: The API passes on a mod's homepage and source URLs only when they are well-formed https URLs; anything else is left out and never fails the lookup
- FR226: A mod database response that is not a JSON object is answered with 502 `EXTERNAL_API_ERROR` on every mod route, never a 500, and is not cached
- FR227: Requests that arrive while the mod listing or the game version list is not cached share one request to the mod database

#### E2E in CI

- FR228: CI builds the image, starts it without a game server but with a seeded fixture `serverconfig.json`, and runs the E2E tests against it on every pull request and push to `main`, keeping the report of a failed run
- FR229: E2E tests that need the live mod database, an installed game server or a real mod install are tagged and left out of CI; they still run locally. The settings specs run in CI against the seeded configuration
- FR230: No E2E spec sets an API key in `localStorage`; every spec gets its key through one shared `/config.js` helper

#### Decided on Review (Matt, 2026-11-17)

- FR231: At start-up, after recovering its own working files, the manager reconciles the mod state with the mods directory once: a mod archive added by hand gets an entry and an entry whose file is gone is removed, each change is logged, and there is no endpoint or button for it
- FR232: The start-up reconcile looks only at mod archives, skips with a warning an archive it cannot read or whose mod is already installed under another file, ignores working, `.tmp` and `.bak` files, and never stops the API from starting
- FR233: With a key whose role is not Admin, the web file browser shows a short static note that some folders are only shown to Admin keys, without folder names or counts
```

**FR to story map:**

| Story | Sprint key | FRs | Beads |
|---|---|---|---|
| 19.1 Secrets Stay with Admin | `19-1-secrets-stay-with-admin` | FR205, FR206, FR207, FR208, FR209, FR233 | `VSS-633`, `VSS-sg1`, `VSS-3hs2`, `VSS-ms0` |
| 19.2 The Web UI No Longer Gets the Admin Key | `19-2-web-ui-no-longer-gets-the-admin-key` | FR210, FR211, FR212 | `VSS-9wv` |
| 19.3 Content-Security-Policy and API Docs | `19-3-content-security-policy-and-api-docs` | FR213, FR214, FR215, FR216, FR217 | `VSS-3qb8`, `VSS-my4c`, `VSS-5mes` |
| 19.4 Mod Files Are Never Overwritten | `19-4-mod-files-are-never-overwritten` | FR218, FR219, FR220, FR221, FR222, FR223 | `VSS-40ja`, `VSS-macf`, `VSS-52fy`, `VSS-n0qv`, `VSS-yhmt`, `VSS-uoxl` |
| 19.5 The Mod State Matches the Mods Directory at Start-Up | `19-5-mod-state-matches-the-mods-directory` | FR231, FR232 | none of its own; rides with `VSS-uoxl` |
| 19.6 Mod Database Data Is Checked | `19-6-mod-database-data-is-checked` | FR224, FR225, FR226, FR227 | `VSS-2zis`, `VSS-ce0h`, `VSS-0lkb` |
| 19.7 E2E Runs in CI | `19-7-e2e-runs-in-ci` | FR228, FR229, FR230 | `VSS-wenx` |

The first version of this proposal numbered the FRs FR205 to FR222 for four stories; the revision renumbered them in story order. The second revision added FR231 to FR233 after FR230 instead of renumbering again, and changed the text of FR228 and FR229.

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** `lastUpdated: '2026-11-17'`; update entry "Added Epic 19 (7 stories) for API Security and Mod File Safety; FR205-FR233".

**FR Coverage Map:** rows FR205 to FR233 appended after FR204, each mapped to Epic 19.

**Story Summary:**

OLD:

```markdown
| **Total** | | **106** |
```

NEW:

```markdown
| Epic 19: API Security and Mod File Safety | 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7 | 7 |
| **Total** | | **113** |
```

### 4.3 Epic 19 Stories (appended to `epics.md`)

## Epic 19: API Security and Mod File Safety

**Goal:** Only the Admin role, and only someone the operator chose to give the Admin key to, can read secrets or act as Admin; every page the manager serves runs under a Content-Security-Policy; no mod operation can replace or lose a mod's file; nothing the mod database sends reaches a link, an image or a 500; and the browser tests run on every pull request.

**Architecture:** `architecture/epic-19-api-security-and-mod-file-safety.md` (ADR-1 to ADR-14, with the code facts at `048fea9` and the mod database facts checked on 2026-11-16). There is no preparation story. Story 19.3 confirms two browser behaviours before it settles the policy (ADR-6 decisions 7 and 12).

**Revised 2026-11-17** after the maintainer's review: seven follow-up beads found in planning were folded in, and `VSS-9wv` became its own story (19.2). Six stories, eighteen beads.

**Revised again 2026-11-17:** Matt decided four observations from the first revision, and each is written into a story: the mod state is reconciled with the mods directory at start-up (new Story 19.5, so the two later stories moved down one), CI seeds a `serverconfig.json` so the settings specs run (19.7), `main.py` uses one settings object and the app can be built with chosen settings in tests (19.2 and 19.3), and the file browser tells a role other than Admin that some folders are hidden (19.1). Seven stories, eighteen beads; Story 19.5 has no bead of its own.

**Order:** 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7.

**Dependencies:**

- Story 19.2 needs no other story's code. It comes second so the breaking change is on `main` early and the release that carries it can be prepared.
- Story 19.3 comes after 19.2: its E2E spec loads every page with a key through the `/config.js` helper Story 19.2 adds, and both stories edit `register_frontend` in `main.py` and `config.py`.
- Story 19.3 also builds on the app construction Story 19.2 introduces (ADR-5 decision 11, ADR-7 decision 6).
- Story 19.5 comes directly after 19.4: its sync runs after 19.4's start-up recovery and relies on 19.4's working-file suffixes, and it edits the same files (`services/mod_state.py`, `services/mods.py`, the start-up in `main.py`).
- Stories 19.4 and 19.6 need no other story's code. Both edit `services/mods.py` and `services/mod_api.py` in different places, so run them one after another.
- Story 19.7 comes last: it uses Story 19.2's helper and key handling, and puts the specs of Stories 19.2 and 19.3 into CI.
- Stories 19.1 and 19.2 both edit `config.py`, `.env.example` and the compose files (`VS_GAME_VERSION` in 19.1, `VS_API_KEY` in 19.2); run them one after another.

**Breaking change:** Story 19.2 stops handing the Admin key to the web UI when `VS_API_KEY` is unset (ADR-5). Every deployment that does not set `VS_API_KEY` must set it when it upgrades, including the maintainer's cluster deployment, which is configured in another repository and is not changed by this epic.

**Size:** Story 19.4 carries six beads, all in the mod file code. Its six tasks are at the project's limit; `create-story` should not add to them. That is why the start-up sync is Story 19.5 and not a seventh task.

### Current State

- A Monitor key can ask the config file viewer for any file under the server data directory; binary files and directories answer 500
- A Monitor key receives nested passwords and secrets under other key names in config files, can list `Saves`, `Backups` and `Playerdata`, and can read the player files
- `VS_GAME_VERSION` is documented and set in the compose files and does nothing
- With `VS_API_KEY` unset, anyone who can load the web UI receives the Admin key, and nothing tells the operator
- The web UI's pages have no Content-Security-Policy, and `/docs`, `/redoc` and `/openapi.json` are served to anyone, loading scripts from a public CDN
- Enabling or disabling a mod can replace another mod's file, and is a 500 when the mod's own file is gone; a version change refuses a taken name with a 500; the install check depends on the volume's case rules
- A crash during an install or version change leaves `.tmp` or `.bak` files that nothing recovers
- Two mods whose releases share a file name share one cache file, and two such downloads at once write one temporary file
- Logo, homepage and source URLs from the mod database reach `src` and `href` unchecked
- A mod database answer that is not a JSON object makes the mod browser answer 500, and several first requests each download the whole listing
- A mod file added or deleted by hand never reaches the Installed list: `sync_state_with_disk` exists and nothing calls it
- The E2E specs run only on a developer's machine, and fifteen of them carry an init script that does nothing

### Target State

- The config file viewer serves `.json` files only, and roles other than Admin see the root files and `ModConfig` only, with secrets redacted at every depth
- `VS_GAME_VERSION` is gone from the settings and the documentation
- The web UI gets a key only when `VS_API_KEY` names one; the API warns when that key is the Admin key and when there is none
- The web UI's pages are served with an enforced Content-Security-Policy and every page works under it; the API documentation pages are served only in debug mode
- Install, enable, disable and version change refuse a taken file name with 409 `MOD_FILE_CONFLICT`, ignoring case; a missing mod file is 409 `MOD_FILE_MISSING`; start-up recovers interrupted operations; the download cache is keyed by file ID
- The Installed list matches the mods directory after every start
- Only checked `https` URLs leave the API, a malformed mod database answer is a 502, and cold caches are filled by one request
- CI starts the built image with a seeded `serverconfig.json` and runs every E2E test that needs nothing outside it, the settings specs included

---

### Story 19.1: Secrets Stay with Admin

**Sprint key:** `19-1-secrets-stay-with-admin`
**Beads:** `VSS-633` (API-077, bug), `VSS-sg1` (API-078, bug), `VSS-3hs2` (API-089), `VSS-ms0` (API-070)
**FRs:** FR205, FR206, FR207, FR208, FR209, FR233

As an **operator who gives other people Monitor access**,
I want **secrets and player data to reach only the Admin role**,
So that **read-only access stays read-only**.

**Acceptance Criteria:**

**Given** a `.json` file in the root of the server data directory or under `ModConfig`
**When** I request `GET /api/v1alpha1/config/files/{path}` with an Admin or a Monitor key
**Then** the response is 200 with its content, and `GET /config/files` lists exactly the files that can be read this way

*(Covers FR205)*

**Given** a path whose name does not end in `.json` (a log, a zip, a text file), existing or not, in a directory the key's role may read
**When** I request it with either key
**Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED` and the file is not read

*(Covers FR205, FR206)*

**Given** a directory, a directory named `x.json`, a symlink `x.json` to a file of another type, or a `.json` file that is not UTF-8 text, in a directory the key's role may read
**When** I request it with either key
**Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED`, never a 500

*(Covers FR206)*

**Given** a `.json` file larger than 2 MiB
**When** I request it with either key
**Then** the response is 413 `CONFIG_FILE_TOO_LARGE` and the file is not read into memory

*(Covers FR206)*

**Given** a `.json` file that starts with a byte order mark, and one that is UTF-8 and not valid JSON or is nested too deeply to parse
**When** I request them
**Then** the first is parsed, and the second is 200 with `_raw` and `_parse_error`, the text only for Admin

*(Covers FR206)*

**Given** a config file with `{"Other": {"Password": "x"}}`, a list of objects with `Token` or `ApiKey` keys, and a key such as `bot_token` or `WebhookUrl`
**When** I read it with a Monitor key
**Then** each of those values is `"[redacted]"` at every depth, a `null` or `""` value stays as it is, and the secret is nowhere in the raw response body

*(Covers FR207)*

**Given** `serverconfig.json` with `StartupCommands` set, and a config file with a string value that is a URL with user info or a Discord webhook URL under any key name
**When** I read them with a Monitor key
**Then** those values are `"[redacted]"`

*(Covers FR207)*

**Given** the same files
**When** I read them with the Admin key
**Then** every value is returned unchanged

*(Covers FR207)*

**Given** a Monitor key
**When** I request `GET /api/v1alpha1/config/directories` for the root of the server data directory
**Then** the response lists `ModConfig` when it exists and no other directory; with the Admin key it lists every directory, as before

*(Covers FR208)*

**Given** a Monitor key
**When** I request the listing of, the files in, or a `.json` file in `Playerdata`, `Saves`, `Backups` or any directory other than `ModConfig`, in any letter case, existing or not
**Then** the response is 403 `FORBIDDEN` with a message that the directory needs the Admin role

*(Covers FR208)*

**Given** a Monitor key
**When** I read a `.json` file in the root or anywhere under `ModConfig`, and a symlink under `ModConfig` that resolves into another directory
**Then** the first is 200 with secrets redacted, and the second is 403 `FORBIDDEN`

*(Covers FR208)*

**Given** a Monitor key in the web UI
**When** I open the file browser
**Then** it shows the note "Some folders are only shown to Admin keys.", which names no folder and gives no count; with the Admin key, or while the role is not yet known, the note is not shown

*(Covers FR233)*

**Given** a deployment that still sets `VS_GAME_VERSION`
**When** the API starts
**Then** it starts as before; the variable is no longer a setting and is not in the compose files, `.env.example` or the worktree set-up script

*(Covers FR209)*

**Tasks:**

- [ ] Config file viewer: one predicate for the listing and the read; suffix, type, size and decoding checks; `CONFIG_FILE_NOT_SUPPORTED` and `CONFIG_FILE_TOO_LARGE` (Epic 19 ADR-1) (`VSS-633`)
- [ ] Recursive redaction by key name with `UNMANAGED_SECRET_KEYS`, `SECRET_KEY_FRAGMENTS` and the two value rules; replace `test_nested_password_is_unchanged` (ADR-2) (`VSS-sg1`)
- [ ] The role's directories: `MONITOR_CONFIG_DIRECTORIES`, filtered listings and 403 on the three config file routes, checked on the resolved path (ADR-3) (`VSS-3hs2`)
- [ ] Remove `Settings.game_version` and every `VS_GAME_VERSION` line; test that setting it is harmless; committed as `fix(docker):` (ADR-4) (`VSS-ms0`)
- [ ] Web: the static note in `FileManagerPanel` for a role other than Admin, from `useAuthMe()` as `SettingsPage` does; component tests for Monitor, Admin and the loading state; confirm the file browser shows a Monitor only what the API lists (ADR-3 decision 9; Matt, 2026-11-17)
- [ ] Tests for both roles with the raw response body checked; API documentation and README (what the Monitor role can read)

---

### Story 19.2: The Web UI No Longer Gets the Admin Key

**Sprint key:** `19-2-web-ui-no-longer-gets-the-admin-key`
**Beads:** `VSS-9wv` (API-079)
**FRs:** FR210, FR211, FR212
**Breaking change.**

As an **operator whose web UI can be reached by people who are not admins**,
I want **the web UI to receive a key only when I name one**,
So that **opening the page does not hand out the Admin key**.

**Acceptance Criteria:**

**Given** `VS_API_KEY` is unset or blank
**When** the API starts
**Then** it starts, `/healthz` and `/readyz` answer as before, it logs the warning `web_api_key_not_set` without any key, and `GET /config.js` serves `{"apiKey": ""}` with the same headers as before

*(Covers FR210, FR211)*

**Given** the web UI is loaded and `/config.js` serves no key
**When** the page opens
**Then** it shows a "No API key configured" screen that names `VS_API_KEY`, the Monitor key and the Admin key, and it makes no request to `/api/` and opens no WebSocket

*(Covers FR210)*

**Given** `VS_API_KEY` equals the Admin key
**When** the API starts
**Then** `/config.js` serves the Admin key and the API logs the warning `web_api_key_is_admin_key` without the key

*(Covers FR211)*

**Given** `VS_API_KEY` equals the Monitor key, or matches neither key
**When** the API starts
**Then** with the Monitor key `/config.js` serves it and neither new warning is logged; with a key that matches no role the existing `web_api_key_matches_no_role` warning is logged, as before

*(Covers FR211)*

**Given** the README, `.env.example` and both compose files
**When** I read how to give the web UI a key
**Then** they say the web UI needs `VS_API_KEY`, recommend the Monitor key or an authenticating proxy, say that anyone who can load the page receives that key, and the production compose example does not hand out the Admin key by default

*(Covers FR212)*

**Given** the dev stack started with `just docker start` and no `VS_API_KEY` in the environment
**When** I open the web UI or run the E2E specs
**Then** the page has the Admin key as before, because the dev compose file sets `VS_API_KEY` to the Admin key itself

*(Covers FR212)*

**Given** the API tests
**When** they need the app in one of the four `VS_API_KEY` states
**Then** they build the app with those settings through the app factory, and each start-up warning is asserted both ways: logged in its state and not logged in the others

*(Covers FR211)*

**Given** the commit that removes the fallback
**When** the release notes are generated with `just changelog`
**Then** the change is listed under Breaking Changes and its line says to set `VS_API_KEY` to the Monitor or the Admin key

*(Covers FR212)*

**Tasks:**

- [ ] `main.py`: an app factory that takes the settings, with the lifespan using the cached `get_settings()` instead of a new `Settings()` (ADR-5 decision 11; Matt, 2026-11-17)
- [ ] `Settings.web_api_key` without the fallback, one function for the four start-up states, the two new warnings, `/config.js` with an empty key; committed as `feat(api)!:` with a `BREAKING CHANGE:` footer and the subject of ADR-5 "Release" (`VSS-9wv`)
- [ ] Web: the "No API key configured" screen, shown before any request (ADR-5 decision 4)
- [ ] `docker-compose.dev.yaml` default, `docker-compose.yaml` comment, `.env.example`, README (ADR-5 decisions 6 and 7)
- [ ] E2E: one `/config.js` helper in `web/e2e/` and the empty-key spec, written to run without the mod database (ADR-5 decision 8)
- [ ] API tests for `/config.js` and the start-up log in the four states, each from an app built with those settings; `just changelog` checked for the breaking entry

---

### Story 19.3: Content-Security-Policy and API Docs

**Sprint key:** `19-3-content-security-policy-and-api-docs`
**Beads:** `VSS-3qb8` (INFRA-005), `VSS-my4c` (UI-102), `VSS-5mes` (API-088)
**FRs:** FR213, FR214, FR215, FR216, FR217

As an **operator**,
I want **every page the manager serves to run under a Content-Security-Policy**,
So that **an injected script cannot run on an origin that holds an API key**.

**Acceptance Criteria:**

**Given** the published image
**When** I request `/` or any web UI path
**Then** the response has `Content-Security-Policy` with exactly the directives of Epic 19 ADR-5 decision 3, and `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`

*(Covers FR213, FR215)*

**Given** the same image
**When** I request `/api/v1alpha1/...`, `/healthz` or `/readyz`
**Then** the response has no `Content-Security-Policy` header

*(Covers FR213)*

**Given** the Docker stack with the policy enforced
**When** I open the dashboard, the console, the mod browser, a mod detail page with a gallery and a description with images, the installed list, the settings and the version page, in the light and the dark theme
**Then** each page works as before, the browser reports no `securitypolicyviolation` event and no console error, and toasts, dialogs and the terminal are styled

*(Covers FR214)*

**Given** the console page with the policy enforced
**When** it connects
**Then** the console WebSocket and the log stream connect and carry data

*(Covers FR214)*

**Given** a page of the web UI with the policy enforced
**When** an inline script is injected into it, or the page is loaded inside a frame on another origin
**Then** the script does not run and the frame does not load

*(Covers FR213)*

**Given** a mod description with an image on any `https` host
**When** I open the mod's detail page
**Then** the image loads

*(Covers FR214)*

**Given** `VS_CSP_MODE=report-only`, `VS_CSP_MODE=off`, and an unknown value
**When** the API starts
**Then** with `report-only` the same policy is sent as `Content-Security-Policy-Report-Only`, with `off` neither header is sent, and an unknown value stops start-up with a message naming the setting

*(Covers FR215)*

**Given** the Vite dev server (`just dev-web`)
**When** I develop
**Then** no policy applies and hot reload works as before

*(Covers FR214)*

**Given** a mod description with an `<img>` whose address is `http:`, relative, or anything other than `https:` or a `data:image/` URL
**When** I open the mod's detail page
**Then** the image is replaced by the text "Image not shown" with its alt text, no request is made for it, no broken-image icon is shown, and the browser reports no policy violation

*(Covers FR216)*

**Given** the image started without `VS_DEBUG=true`
**When** I request `/docs`, `/redoc` or `/openapi.json`
**Then** none of them serves the API documentation or the schema, and no response from the manager loads a script from another origin

*(Covers FR217)*

**Given** the API started with `VS_DEBUG=true`
**When** I open `/docs`
**Then** the API documentation renders as before, without the web UI's policy

*(Covers FR217)*

**Given** the API tests
**When** they check the documentation paths and the RBAC test routes
**Then** they build one app with debug on and one with debug off through the app factory and assert both, and `main.py` no longer calls `Settings()` itself

*(Covers FR217)*

**Tasks:**

- [ ] `VS_CSP_MODE` in `Settings` with validation; the policy as one constant; the headers on `serve_spa` responses (Epic 19 ADR-6 decisions 1, 3, 9 and 10) (`VSS-3qb8`)
- [ ] Browser checks first: the WebSockets under `connect-src 'self'` and the next-themes inline script (ADR-6 decisions 7 and 12); record what was seen and any hash added
- [ ] Sanitizer: replace description images that are not `https:` or `data:image/` (ADR-6 decision 14) (`VSS-my4c`)
- [ ] `docs_url`, `redoc_url` and `openapi_url` off unless debug, set in the app factory; the CORS and RBAC-router `Settings()` calls in `main.py` moved to the same settings object; adapt `test_version.py`; the commit subject names the change for the release notes (ADR-7, decision 6; Matt, 2026-11-17) (`VSS-5mes`)
- [ ] API tests: the headers in each mode and on which routes, the documentation paths with debug off and on; `mod-description.test.ts` for the image rule
- [ ] E2E spec against the Docker stack with stubbed mod data: every page in both themes with no violation, and the blocked inline script (ADR-6 decision 13); README and `.env.example`

---

### Story 19.4: Mod Files Are Never Overwritten

**Sprint key:** `19-4-mod-files-are-never-overwritten`
**Beads:** `VSS-40ja` (API-082, bug), `VSS-macf` (API-083), `VSS-52fy` (API-085), `VSS-n0qv` (API-084), `VSS-yhmt` (API-091, bug), `VSS-uoxl` (API-092; stays open until Story 19.5, which rides with it)
**FRs:** FR218, FR219, FR220, FR221, FR222, FR223

As an **administrator**,
I want **no mod operation to replace or lose a mod's file, on any volume and after a crash**,
So that **the mods directory always holds what the Installed list says**.

**Acceptance Criteria:**

**Given** mod A is disabled as `Foo.zip.disabled` and another file `Foo.zip` is in the mods directory
**When** I enable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` with a message naming `Foo.zip`, both files have the same bytes as before, the mod state is unchanged and no restart is pending

*(Covers FR218)*

**Given** mod A is enabled as `Foo.zip` and a file `Foo.zip.disabled` is in the mods directory
**When** I disable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is changed

*(Covers FR218)*

**Given** no file is in the way
**When** I enable or disable a mod
**Then** it works as before, and enabling an enabled mod or disabling a disabled one is still a success that changes nothing

*(Covers FR218)*

**Given** an installed mod and a target release whose file name, or its `.disabled` form, is another file in the mods directory or another entry in the mod state
**When** I change the mod's version
**Then** the response is 409 `MOD_FILE_CONFLICT`, not 500 `MOD_VERSION_CHANGE_FAILED`, and the mod's file, the other file and the state are unchanged

*(Covers FR219)*

**Given** Update All, and one mod's new file name is taken
**When** the run reaches it
**Then** that mod is a `failed` item with the conflict message, and the run continues with the other mods

*(Covers FR219)*

**Given** a version change that fails to place the file or save state for another reason
**When** it is rolled back
**Then** the response is 500 `MOD_VERSION_CHANGE_FAILED`, as before

*(Covers FR219)*

**Given** a case-sensitive mods directory with `Foo.zip` installed
**When** I install, enable, disable or change to a version of another mod whose file would be `foo.zip` or `FOO.ZIP.disabled`
**Then** the response is 409 `MOD_FILE_CONFLICT`, the same answer a case-insensitive volume gives

*(Covers FR220)*

**Given** an installed mod `Foo_1.0.zip`
**When** I change it to a release whose file name differs from its own only in case
**Then** the change succeeds and exactly one file for the mod is in the directory afterwards, on a case-sensitive and on a case-insensitive volume

*(Covers FR220)*

**Given** a dangling symlink with the target name, or a mod state entry under the target name with no file
**When** I run any of the four operations
**Then** the response is 409 `MOD_FILE_CONFLICT`

*(Covers FR218, FR219, FR220)*

**Given** two mods whose releases have the same file name
**When** I download both, one after the other or at the same time
**Then** each is cached under its own file ID, neither replaces the other's copy, and each install places the archive of the mod that was asked for

*(Covers FR221)*

**Given** two downloads of the same release at the same time
**When** both finish
**Then** the cache holds one complete file and no temporary file is left

*(Covers FR221)*

**Given** a cache with files from before this story, and a temporary file left by a crash more than an hour ago
**When** the API starts and the next download finishes
**Then** the old files are removed at start and their number logged, eviction counts and evicts files in the new layout and removes emptied directories and the old temporary file

*(Covers FR221)*

**Given** an installed mod whose own file was removed from the mods directory by hand
**When** I enable or disable it
**Then** the response is 409 `MOD_FILE_MISSING` with a message naming the file and saying to remove the mod and install it again, never a 500, and the mod state is unchanged

*(Covers FR222)*

**Given** that mod
**When** I remove it through the manager
**Then** the removal succeeds

*(Covers FR222)*

**Given** a mods directory left by an interrupted install or version change: an unplaced working copy; a kept-aside original whose file is missing; a kept-aside original beside a new file that the mod state does not describe; and one beside a new file that it does
**When** the API starts
**Then** the working copy is deleted, the first two originals are put back, the last is deleted, each action is logged, and every mod's file matches its state

*(Covers FR223)*

**Given** files named `something.bak` or `something.tmp` that the manager did not create under its own suffixes
**When** the API starts
**Then** they are named in one warning and are neither deleted nor renamed

*(Covers FR223)*

**Given** a leftover working file for a name
**When** I install, enable, disable or change the version of a mod with that file name
**Then** the leftover does not cause a `MOD_FILE_CONFLICT`

*(Covers FR223)*

**Tasks:**

- [ ] The file-name helper (listing plus state, `casefold`, the mod's own file excluded) and `ModFileConflictError` with the operation in its message; use it in `_place_install` (Epic 19 ADR-8 decisions 1, 2 and 6) (`VSS-52fy`)
- [ ] `enable_mod` and `disable_mod`: the name check and the missing-file check; 409 `MOD_FILE_CONFLICT` and 409 `MOD_FILE_MISSING` on both routes (ADR-8, ADR-9 decisions 1 to 4) (`VSS-40ja`, `VSS-yhmt`)
- [ ] `_apply_version_change`: the name check, `same_file` ignoring case, 409 on the version route, `ModFileConflictError` in the Update All loop (ADR-8 decisions 4 and 7) (`VSS-macf`)
- [ ] Working files as `.vsm-tmp` and `.vsm-bak`, start-up recovery, the warning for old-style leftovers (ADR-9 decisions 5 to 8) (`VSS-uoxl`)
- [ ] Cache layout `cache/mods/<fileid>/<name>`, one path function, a temporary file per download, removal of the old layout at start, `CacheEvictionService` for the new layout (ADR-11) (`VSS-n0qv`)
- [ ] Tests for every case above with file bytes and state compared before and after, on a case-sensitive directory; confirm the web shows each message; API documentation of the changed errors

---

### Story 19.5: The Mod State Matches the Mods Directory at Start-Up

**Sprint key:** `19-5-mod-state-matches-the-mods-directory`
**Beads:** none of its own (Matt, 2026-11-17). It rides with `VSS-uoxl` (API-092), which Story 19.4 starts and this story finishes: close `VSS-uoxl` with its AAR when this story is done.
**FRs:** FR231, FR232

As an **administrator who sometimes adds or deletes mod files by hand**,
I want **the manager to bring its list of installed mods in line with the mods directory when it starts**,
So that **the Installed list shows what is really there**.

**Acceptance Criteria:**

**Given** a readable mod archive `New.zip` copied into the mods directory by hand, and another as `Off.zip.disabled`
**When** the API starts
**Then** both are in `GET /api/v1alpha1/mods` with the mod ID and version from their `modinfo.json`, the first enabled and the second disabled, and each addition is logged with its file name and mod ID

*(Covers FR231)*

**Given** a mod state entry whose file is no longer in the mods directory
**When** the API starts
**Then** the entry is gone from the Installed list and the removal is logged with its file name and mod ID

*(Covers FR231)*

**Given** a state entry whose file exists under a name that does not end in `.zip` or `.zip.disabled`
**When** the API starts
**Then** the entry stays

*(Covers FR231)*

**Given** a `.zip` in the mods directory that cannot be read or has no usable `modinfo.json`
**When** the API starts
**Then** start-up completes, the file is not added, it is not deleted, and one warning names it

*(Covers FR232)*

**Given** a `.zip` added by hand whose mod ID is already installed under another file
**When** the API starts
**Then** the existing entry stays, no second entry is added, and one warning names both files

*(Covers FR232)*

**Given** `.vsm-tmp`, `.vsm-bak`, `.tmp` and `.bak` files, a directory and a text file in the mods directory
**When** the API starts
**Then** none of them is added to the state, and none is changed by the sync

*(Covers FR232)*

**Given** an interrupted version change left a working file and a kept-aside original
**When** the API starts
**Then** Story 19.4's recovery runs first and the sync then sees the recovered file, so the mod is neither removed nor added twice

*(Covers FR231)*

**Given** the mods directory does not exist when the API starts
**When** the sync runs
**Then** no state entry is removed, and a warning says the directory was not found

*(Covers FR232)*

**Given** any start-up
**When** the sync has run
**Then** one summary line gives the numbers added, removed and skipped, also when all are zero, and the game server's auto-start comes after it

*(Covers FR231, FR232)*

**Given** the API
**When** I look for a way to run the sync again
**Then** there is no route and no button for it; it runs only at start-up

*(Covers FR231)*

**Tasks:**

- [ ] Make `sync_state_with_disk` safe: guard each import, decide removal by the entry's own file, skip a second file for an installed mod ID, one save (Epic 19 ADR-10 decisions 2 to 4 and 6)
- [ ] Logging: a line per addition, removal and skip, and the summary line (ADR-10 decision 5)
- [ ] Call it once in start-up, after the recovery of Story 19.4 and before the game server auto-start (ADR-10 decision 1)
- [ ] Tests from hand-built directories and states for every case above, including that start-up continues; README: mods added or removed by hand are picked up at the next restart

---

### Story 19.6: Mod Database Data Is Checked

**Sprint key:** `19-6-mod-database-data-is-checked`
**Beads:** `VSS-2zis` (API-081), `VSS-ce0h` (API-086), `VSS-0lkb` (API-090)
**FRs:** FR224, FR225, FR226, FR227

As an **administrator**,
I want **the manager to pass on only URLs it has checked and to treat a broken mod database answer as an upstream error**,
So that **a mod author's data or a mod database fault cannot misuse or break the pages I use**.

**Acceptance Criteria:**

**Given** a mod whose logo is an `https://moddbcdn.vintagestory.at/` URL
**When** I look it up or see it in the browse results
**Then** `logo_url` is that URL unchanged

*(Covers FR224)*

**Given** a mod whose logo is an `http:` URL, a URL on another host, a `data:` or `javascript:` URL, or not a URL
**When** I look it up or browse
**Then** the response is 200, `logo_url` is `null`, and the page shows the placeholder

*(Covers FR224)*

**Given** a mod logo on a browse card, the detail page or the install dialog
**When** the image is requested
**Then** the request carries no referrer

*(Covers FR224)*

**Given** a mod whose homepage or source URL is an `https` URL
**When** I look it up
**Then** `homepage_url` or `source_url` is that URL unchanged and the detail page shows the link

*(Covers FR225)*

**Given** a homepage or source value that is empty, an `http:`, `javascript:` or `data:` URL, has user info, has a space, control character or backslash, or is longer than 2,048 characters
**When** I look the mod up
**Then** the response is 200, the field is `null` and the detail page shows no such link; the "ModDB Page" link is unaffected

*(Covers FR225)*

**Given** the mod database answers the listing, a filtered listing, a mod lookup or the game version list with HTML, an empty body, `[]`, `"text"` or `null`
**When** a mod route needs that answer
**Then** the response is 502 `EXTERNAL_API_ERROR`, never 500, and the previous cached copy and its age are unchanged

*(Covers FR226)*

**Given** the mod database answers correctly on the next request
**When** I retry
**Then** the route works; nothing malformed was cached

*(Covers FR226)*

**Given** the game version cache is cold and several browse requests arrive together
**When** they are served
**Then** the mod database receives one `/api/gameversions` request, every request gets its result, and a failure reaches every waiting request and is not kept

*(Covers FR227)*

**Given** the mod listing cache is cold or expired and several browse requests arrive together
**When** they are served
**Then** the mod database receives one `/api/mods` request, every request gets its result, and a failure reaches every waiting request and is not kept

*(Covers FR227)*

**Given** a listing fetch is running
**When** a refresh is forced
**Then** it waits for the running fetch instead of starting a second one

*(Covers FR227)*

**Tasks:**

- [ ] `external_link_url` in `services/mod_media.py`; `mod_image_url` on `logo_url` in the lookup and the browse item; debug log without the URL (Epic 19 ADR-12 decisions 1 to 3 and 6) (`VSS-2zis`)
- [ ] Web: `referrerPolicy="no-referrer"` on the three logo images; confirm the placeholder and the missing links (ADR-12 decision 5)
- [ ] One guarded JSON fetch in `ModApiClient`, used by the four fetchers, each keeping its status rules (ADR-13 decisions 1 to 4) (`VSS-ce0h`)
- [ ] One shared in-flight fetch helper for the game version list, the full listing and the filtered listings (ADR-13 decisions 5 and 6) (`VSS-0lkb`)
- [ ] Tests: URL rules with a synthetic bad-data fixture for lookup and browse; each fetcher with the five malformed bodies and an unchanged cache; concurrent cold calls for both caches; API documentation of `null` for the three URL fields

---

### Story 19.7: E2E Runs in CI

**Sprint key:** `19-7-e2e-runs-in-ci`
**Beads:** `VSS-wenx` (TOOLS-007)
**FRs:** FR228, FR229, FR230

As a **maintainer**,
I want **the browser tests to run against the built image on every pull request**,
So that **a change that breaks the page is caught before it is merged**.

**Acceptance Criteria:**

**Given** a pull request or a push to `main`
**When** CI runs
**Then** an `e2e` job builds the image, starts a container from it with a data directory that holds only the seeded `serverconfig.json` fixture and with placeholder keys, waits for `/healthz`, runs the E2E tests that carry no tag, and fails the run when one fails

*(Covers FR228)*

**Given** the `e2e` job
**When** it starts the container
**Then** `VS_API_KEY` is set as Story 19.2 requires, no game server is installed or started, and no real key or instance data is in the workflow

*(Covers FR228)*

**Given** a failed `e2e` job
**When** I open the run
**Then** the Playwright report is attached as an artifact

*(Covers FR228)*

**Given** the E2E specs
**When** I read them
**Then** every test that needs the live mod database is tagged `@moddb`, every test that needs an installed game server `@game-server`, every test that installs or removes a real mod `@install`, and each tag is explained in one place

*(Covers FR229)*

**Given** the fixture `serverconfig.json` in the repository
**When** I read it
**Then** it holds made-up values only, and the CI job copies it to `serverdata/serverconfig.json` before the container starts

*(Covers FR228)*

**Given** the settings specs (`settings-desktop-layout`, `settings-empty-values`, `settings-as-saved`, `monitor-password-redaction`)
**When** they run against the seeded stack in CI
**Then** each test that passes there carries no tag and runs in CI, and any test that still needs an installed or running game server keeps `@game-server` with its reason

*(Covers FR229)*

**Given** the CI invocation
**When** it runs
**Then** it leaves out the three tags, includes the no-key spec of Story 19.2 and the policy spec of Story 19.3, and the same `just` recipe runs it on a developer's machine

*(Covers FR229)*

**Given** `just test-e2e-web` on a developer's machine with a game server installed
**When** it runs
**Then** it still runs every spec, tagged or not

*(Covers FR229)*

**Given** the E2E specs
**When** I search them for `localStorage.setItem('apiKey'`
**Then** there is no match, and every spec that loads a page gets its key through the helper of Story 19.2

*(Covers FR230)*

**Given** the workflow files
**When** `just lint-workflows` runs
**Then** it passes, and every action is pinned by commit like the existing jobs

*(Covers FR228)*

**Tasks:**

- [ ] Remove the dead `localStorage` init scripts from the fifteen specs and move every spec to the `/config.js` helper (Epic 19 ADR-14 decision 6) (`VSS-wenx`)
- [ ] The `serverconfig.json` fixture under `web/e2e/fixtures/` and its copy into the data directory, in the CI job and in the `just` recipe (ADR-14 decision 10; Matt, 2026-11-17)
- [ ] Tag the specs and tests (`@moddb`, `@game-server`, `@install`) after running each against the seeded stack with no game server; the settings specs lose their tag where they pass; record which tests run in CI (ADR-14 decisions 2, 3 and 10)
- [ ] A `just` recipe for the CI invocation; `api/tests/e2e/` in the same run (ADR-14 decisions 3 and 8)
- [ ] The `e2e` job in `.github/workflows/ci.yml`: cached image build, container start, health wait, Playwright install, report artifact; `just lint-workflows` (ADR-14 decisions 1 and 7)
- [ ] Documentation: how to run the CI subset locally and what the tags mean

### 4.4 Architecture (`architecture/epic-19-api-security-and-mod-file-safety.md`, new)

ADR numbers are in story order. The first version had nine ADRs and the first revision thirteen; the "was" column gives the first version's number.

| ADR | Was | Decision | Story |
|---|---|---|---|
| ADR-1 | ADR-1 | The config file viewer lists and serves only `.json` regular files up to 2 MiB; another suffix, a directory or non-UTF-8 content is 400 `CONFIG_FILE_NOT_SUPPORTED`, too large is 413 `CONFIG_FILE_TOO_LARGE`; a file that does not parse keeps the `_raw` form | 19.1 |
| ADR-2 | ADR-2 | For roles other than Admin, `redact_secrets` walks every depth and replaces the value of a key that is a secret setting, is in `UNMANAGED_SECRET_KEYS` (`StartupCommands`) or contains a fragment such as `password`, `token`, `secret`, `apikey`, `webhook`; plus URLs with user info and Discord webhook URLs. Admin gets files unchanged | 19.1 |
| ADR-3 | new | Roles other than Admin may list and read only the root of the server data directory and `ModConfig` (an allow-list, checked on the resolved path); listings are filtered and any other directory is 403 `FORBIDDEN`. Second revision: the web file browser shows a role other than Admin a static note that some folders are only shown to Admin keys (decision 9) | 19.1 |
| ADR-4 | ADR-4 | `VS_GAME_VERSION` is removed from the settings, compose files and documentation; setting it stays harmless | 19.1 |
| ADR-5 | ADR-3 | The web key has no fallback: with `VS_API_KEY` unset or blank the API starts, `/config.js` serves an empty key and the web UI shows a set-up screen; a warning at start-up when the web key is the Admin key and when there is none; the dev compose file sets the Admin key itself. Breaking, with the `feat(api)!:` subject carrying the instruction. Second revision: `main.py` uses the cached settings and builds the app through a factory so each start-up state is tested both ways (decision 11) | 19.2 |
| ADR-6 | ADR-5 | The API sends an enforced `Content-Security-Policy` on the web UI's pages only: `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `img-src 'self' data: https:`, `connect-src 'self'`, `frame-src 'none'`, `frame-ancestors 'none'`; with `nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options`; `VS_CSP_MODE` switches to report-only or off; the Vite dev server has no policy. New decision 14: the sanitizer replaces description images that are not `https:` or `data:image/` with a text | 19.3 |
| ADR-7 | new | `/docs`, `/redoc` and `/openapi.json` are served only when the API runs in debug mode; no new setting, no key in a URL, no vendored assets. Second revision: set in the app factory and tested with debug on and off; the last two `Settings()` calls in `main.py` go (decision 6) | 19.3 |
| ADR-8 | ADR-6 | One helper checks the names an operation will create against the directory listing and the mod state, ignoring case and excluding the mod's own file; install, enable, disable and version change all answer 409 `MOD_FILE_CONFLICT`; Update All records it as a failed item | 19.4 |
| ADR-9 | new | Enable or disable with the mod's own file missing is 409 `MOD_FILE_MISSING`. The manager's working files become `<name>.vsm-tmp` and `<name>.vsm-bak`; start-up deletes the first and restores or deletes the second according to the mod state; other `.tmp` and `.bak` files are reported and never touched; working files are never names the ADR-8 check looks at | 19.4 |
| ADR-10 | new (second revision) | `sync_state_with_disk` is made safe and called once at start-up, after ADR-9's recovery and before the game server auto-start: a readable `.zip` or `.zip.disabled` the state does not know is added, an entry whose own file is gone is removed, an unreadable archive or a second file for an installed mod ID is skipped with a warning, and a summary is always logged. No endpoint, no button (Matt, 2026-11-17) | 19.5 |
| ADR-11 | ADR-7 | The download cache is `cache/mods/<fileid>/<name>` with a temporary file per download; eviction follows the layout; the old flat files are removed once at start | 19.4 |
| ADR-12 | ADR-8 | `logo_url` goes through the Story 18.1 image rule; `homepage_url` and `source_url` through a new `https`-only link rule; anything else is `null`; logo images get `referrerPolicy="no-referrer"` | 19.6 |
| ADR-13 | ADR-9 | One helper fetches mod database JSON and raises `ExternalApiError` for a body that is not a JSON object, used by all four fetchers. Changed: one shared in-flight fetch for the game version list and for the full listing, and a forced refresh joins a running fetch | 19.6 |
| ADR-14 | new | A CI job builds the image, starts it without a game server and runs the E2E tests that carry no tag; `@moddb`, `@game-server` and `@install` tests are left out of CI and still run locally; all specs use the `/config.js` helper and the dead `localStorage` scripts go. Second revision: the job seeds a fixture `serverconfig.json`, so the settings specs run in CI (decision 10) | 19.7 |

The file also records the code facts and the mod database facts the decisions rest on.

### 4.5 Other Artifacts

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | `epic-19` (backlog), `epic-19-retrospective` (optional) and the seven story keys of section 4.1 (backlog), via `scripts/sprint-status.sh`. The three keys of the first version that no longer exist (`19-2-content-security-policy`, `19-3-mod-files-are-never-overwritten`, `19-4-mod-database-data-is-checked`) were removed on 2026-11-17 with the script's new `remove` command (Matt's decision) | Now |
| `sprint-status.yaml`, second revision | With the script: removed `19-5-mod-database-data-is-checked` and `19-6-e2e-runs-in-ci`; added `19-5-mod-state-matches-the-mods-directory`, `19-6-mod-database-data-is-checked` and `19-7-e2e-runs-in-ci` | Now |
| Beads | Epic `Epic 19: API Security and Mod File Safety` (`VSS-fl9b`); the 18 in-scope issues are its children; Story 19.5 has no bead and `VSS-uoxl` is closed with it, not with 19.4; close each with an AAR when its story is done | Now, and per story |
| `architecture/index.md` | Entry for the Epic 19 ADRs | Now |
| README, `.env.example`, compose files, `scripts/worktree-setup.sh`, `architecture/project-structure-boundaries.md` | `VS_GAME_VERSION` (19.1), `VS_API_KEY` (19.2), `VS_CSP_MODE` and the documentation pages (19.3) | Stories 19.1 to 19.3 |
| `.github/workflows/ci.yml`, `Justfile` | The `e2e` job and its recipe | Story 19.7 |
| The maintainer's cluster deployment (another repository) | Set `VS_API_KEY` | With the release that carries Story 19.2; not done by this epic's stories |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 19.1 to 19.7 from `epics.md` and the Epic 19 ADRs, 19.1 first |
| Developer (`dev-story`) | Implement each story; in 19.2, make the breaking change its own commit with the subject of ADR-5; in 19.3, do the two browser checks before fixing the policy; in 19.7, tag tests only after running them against a stack with no game server |
| Reviewer (`code-review`) | Delegated read-only review per story |
| Maintainer (Matt) | Reviews the four new ADRs; sets `VS_API_KEY` in the cluster deployment with the release; decides how the three stale sprint keys are removed |

**Open questions for the maintainer.** Answered 2026-11-17: 1 to 7 and 9 confirmed as defaulted; 8 changed to the alternative (`VSS-9wv` is its own story, 19.2).

1. **Start and serve no key (ADR-5).** Default: the API starts and the web UI shows a set-up screen. Alternative: refuse to start, which also stops the game server on upgrade. *Confirmed: default.*
2. **Which key the documentation recommends first.** Default: the README and `.env.example` show `VS_API_KEY` set to the Monitor key as the recommended example and the Admin key as the full-access choice with its warning. The production compose file keeps a blank default, so a first run shows the set-up screen until the operator chooses. *Confirmed: default.*
3. **A key that matches no role (ADR-5 decision 5).** Default: unchanged, it is served and warned about as today. *Confirmed: default.*
4. **Redaction list (ADR-2).** Default fragments: `password`, `passwd`, `secret`, `token`, `apikey`, `privatekey`, `accesskey`, `credential`, `webhook`, `authorization`; plus `StartupCommands`. The world seed is not treated as a secret. *Confirmed: default.*
5. **Config file size limit (ADR-1).** Default: 2 MiB. Not configurable. *Confirmed: default.*
6. **CSP mode and the extra headers (ADR-6).** Default: enforced, with `VS_CSP_MODE` as a switch, and `Referrer-Policy: no-referrer`, `nosniff` and `X-Frame-Options` on the same responses. *Confirmed: default.*
7. **`http:` homepage and source links (ADR-12).** Default: dropped. *Confirmed: default.*
8. **Story 19.1's size.** Default: one story, as grouped. Alternative: split the `VS_API_KEY` change (`VSS-9wv`) into its own story so the breaking commit has its own review. *Changed: split; it is Story 19.2.*
9. **Release.** The breaking change lands before the first stable release (`0.1.0-rc.4` today). Default: nothing special; it ships in the next pre-release or in `0.1.0`. *Confirmed: default.*

**Questions the revision raises.** Answered by Matt 2026-11-17: 1 changed (the removal is named in the release notes, without a breaking marker), 2 and 4 confirmed as defaulted, 3 confirmed with a follow-up bead (`VSS-hv60`), 5 resolved (a `remove` command was added to the script and the three stale keys removed).

1. **Removing `/docs` and `/openapi.json` by default (ADR-7).** Default: not marked as a breaking change, since the pages are outside the versioned API. Alternative: mark the commit breaking. *Answered: the commit is not marked breaking (`!`), but the release notes name the change: Story 19.3's commit subject for it is a `feat(api)` or `fix(api)` subject that says the API docs pages are served only with `VS_DEBUG=true`, so it appears under Features or Fixes.*
2. **Monitor's directories (ADR-3).** Default: the root files and `ModConfig` only. Alternative: add directories to the constant (for example `Macros`). *Confirmed: root and `ModConfig` only.*
3. **Old-style `.tmp` and `.bak` files (ADR-9 decision 7).** Default: named in a start-up warning and never touched, because the manager cannot tell its own old leftovers from an admin's files. Alternative: delete `.tmp` files whose name is a mod file name the state knows. *Confirmed: warn only. Follow-up `VSS-hv60` [UI-103]: show possibly unused files in the web UI with a confirmed cleanup (for example an age rule such as 7 days), designed when that bead is planned.*
4. **CI coverage (ADR-14).** Default: untagged tests only. Alternative: let CI also run `@moddb` tests against the live mod database, accepting failures when it is unavailable. *Confirmed: untagged tests only.*
5. **The stale sprint keys** (section 4.5). The script had no remove command; the planner did not edit the file by hand. *Resolved: `scripts/sprint-status.sh remove <key>` added with tests; the three stale keys removed with it.*

**Follow-ups found outside the scope.** The seven of the first version are in the epic as beads. The four the first revision listed were decided by Matt on 2026-11-17 and are in the plan:

1. `sync_state_with_disk` is called by nothing. *Matt, 2026-11-17: call it once at start-up, after ADR-9's recovery; no endpoint and no button. Story 19.5, ADR-10; no bead, rides with `VSS-uoxl`.*
2. The settings specs could run in CI with a seeded `serverconfig.json`. *Matt, 2026-11-17: do it in Story 19.7 (ADR-14 decision 10); `@moddb`, `@game-server` and `@install` stay local-only.* Recording mod database answers for the `@moddb` tests remains a follow-up without a bead.
3. `Settings()` is constructed three times in `main.py`. *Matt, 2026-11-17: Stories 19.2 and 19.3 switch `main.py` to the cached `get_settings()` where they touch it and build the app so tests can construct it with chosen settings (ADR-5 decision 11, ADR-7 decision 6). Service-level cleanup stays out of scope; no bead.*
4. The web shows a Monitor no hint that directories are hidden. *Matt, 2026-11-17: a short static note in the file browser, Story 19.1 (ADR-3 decision 9).*

Found in the second revision, reported, no beads created:

1. `scan_mods_directory` matches only `.zip` and `.zip.disabled`. A mod the manager installed under another file name keeps its entry (ADR-10 decision 4), but such a file added by hand is not picked up at start-up.
2. A mod added by the start-up sync has no mod database asset ID, so whatever uses `asset_id` treats it like a mod installed before that field existed.

**Success criteria:**

- A Monitor key gets 400 for `server-main.log`, 403 for anything in `Playerdata`, and no secret value from a config file with nested and other-named secrets; the raw body is checked
- No request to the config file viewer answers 500 for a binary file or a directory
- With `VS_API_KEY` unset, `/config.js` contains no key and the page shows the set-up screen; with it set to the Admin key the start-up log has the warning
- Every web UI page loads in both themes with the policy enforced and no violation; an injected inline script does not run; `/docs` is not served without debug mode
- Enabling, disabling, installing or changing a mod's version when the file name is taken returns 409 and leaves the other file byte for byte, on a case-sensitive directory; a missing mod file returns 409 `MOD_FILE_MISSING`
- A mods directory built to look like each interruption point is put right at start-up, and an admin's own `.bak` file is still there afterwards
- A mod archive copied into the mods directory is in the Installed list after a restart, a deleted one is gone, and an unreadable archive does not stop start-up
- A Monitor key sees the note in the file browser; an Admin key does not
- Two mods with the same release file name can be downloaded at the same time and each install places the right archive
- A mod with an `http:` or off-host logo shows the placeholder; a malformed mod database listing answers 502; several cold browse requests make one listing request
- A pull request runs the `e2e` job against the built image with the seeded configuration, the settings specs run in it, and no spec contains `localStorage.setItem('apiKey'`
- Each in-scope beads issue is closed with an AAR by its story
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: eleven beads chosen by the maintainer after Epic 18, and seven more found in planning and added on review. [x] 1.2 type: five bugs and thirteen hardening and tooling tasks. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete except the Admin key fallback of Epic 15 ADR-5, the top-level-only redaction of Story 17.5, and decision 6 of Epic 18 ADR-1 and ADR-4. [x] 2.5 no resequencing; order inside Epic 19 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR205-FR233 added, MVP unaffected. [x] 3.2 architecture: new Epic 19 ADRs. [N/A] 3.3 UX spec: no change. [!] 3.4 deployment: `VS_API_KEY` must be set by every deployment that uses the web UI, in the release that carries Story 19.2; CI gains a job |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1, 6.2 reviewed by Matt on 2026-11-17; this is the second revision, with his decisions on the four observations written in. [!] 6.3 the four new ADRs and the questions the revision raises are not reviewed yet; the stale sprint keys need a decision. [x] 6.4 handoff in section 5 |
