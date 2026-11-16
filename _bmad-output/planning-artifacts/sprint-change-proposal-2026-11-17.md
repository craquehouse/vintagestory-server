# Sprint Change Proposal: API Security and Mod File Safety (Epic 19)

**Date:** 2026-11-17
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (batch, non-interactive; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Scope, grouping and the `VSS-9wv` decision approved by Matt, 2026-11-16. The wording, the ADRs and the open questions in section 5 have not been reviewed yet.

## 1. Issue Summary

**Trigger:** Epic 18 is done and on `main` (`048fea9`, release `v0.1.0-rc.4`). The maintainer picked eleven open beads for the next epic, all follow-ups filed during Epic 15, Epic 17 and Epic 18 work: four about who can read secrets and keys, one about the missing Content-Security-Policy, four about mod files being overwritten, and two about mod database data passed on unchecked.

**Problem:** The manager separates an Admin role from a read-only Monitor role, and three paths go around that separation: the config file viewer serves any file and redacts one key at one depth, and the default deployment hands the Admin key to anyone who can load the web page. The page that holds that key has no Content-Security-Policy. Beside that, three of the four operations that place a mod file can replace another mod's file or report the refusal as a server error, the download cache can mix two mods' archives, and URLs and response bodies from the mod database are trusted in places Epic 17 and Epic 18 did not reach.

**Evidence** (code at commit `048fea9`; details and line references in `architecture/epic-19-api-security-and-mod-file-safety.md`):

- `ConfigFilesService.read_file` has no file type, suffix or size check (`services/config_files.py:179-227`), while `list_files` lists only `*.json` (`:172-174`). `read_text` is outside the `try` (`:213`), so a binary file or a directory is a 500 (`VSS-633`).
- `redact_secrets` changes only an object's own keys that equal `Password` (`services/game_config.py:215-248`); the nested case is pinned as a known limit by `test_nested_password_is_unchanged` (`VSS-sg1`).
- `Settings.web_api_key` falls back to the Admin key (`config.py:31-36`) and `/config.js` serves it unauthenticated (`main.py:260-272`). Both compose files pass `VS_API_KEY` blank by default. The only start-up warning is for a key that matches no role (`main.py:103-108`) (`VSS-9wv`).
- `Settings.game_version` (`config.py:24`) is read by nothing; `.env.example:20-23` says it chooses the version to install (`VSS-ms0`).
- No `Content-Security-Policy` is set by the API, `web/index.html` or the Vite configuration. The built page has only same-origin script files; four dependencies create `<style>` elements at run time (`VSS-3qb8`).
- `enable_mod` and `disable_mod` rename without checking the target (`services/mods.py:749`, `:807`) (`VSS-40ja`). `_apply_version_change` refuses a taken name with `ModVersionChangeFailedError`, a 500 (`:1008-1012`, `routers/mods.py:1137-1138`) (`VSS-macf`). `_place_install` compares names exactly (`:1283-1290`) (`VSS-52fy`).
- `download_release_file` writes `cache/mods/<name>.tmp` and renames it to `cache/mods/<name>` (`services/mod_api.py:578-595`); the per-mod locks do not stop two different mods downloading the same file name at once, and an install does not require the archive's mod ID to be the one it resolved (`services/mods.py:1236-1244`) (`VSS-n0qv`).
- `logo_url`, `homepage_url` and `source_url` are passed through unchecked (`services/mods.py:690-694`, `routers/mods.py:238`); the three logo `<img>` elements have no `referrerPolicy` (`VSS-2zis`).
- `get_all_mods` calls `response.json()` and `data.get` unguarded (`services/mod_api.py:664-668`), and `_fetch_mods_by_version` calls `data.get` unguarded (`:869`); `get_game_versions` has no shared fetch (`:948-952`) (`VSS-ce0h`).
- Mod database, checked 2026-11-16: every non-null listing `logo` (6,531 of 9,636) is an `https://moddbcdn.vintagestory.at/` URL; across the 60 most downloaded mods every non-empty `homepageurl` (33) and `sourcecodeurl` (44) is `https`.

**Scope decisions (made by the maintainer before the workflow ran):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-633`, `VSS-sg1`, `VSS-9wv`, `VSS-ms0`, `VSS-3qb8`, `VSS-40ja`, `VSS-macf`, `VSS-52fy`, `VSS-n0qv`, `VSS-2zis`, `VSS-ce0h` (11 issues, 4 stories) |
| Grouping | As approved, unchanged: 19.1 `VSS-633` + `VSS-sg1` + `VSS-9wv` + `VSS-ms0`, 19.2 `VSS-3qb8`, 19.3 `VSS-40ja` + `VSS-macf` + `VSS-52fy` + `VSS-n0qv`, 19.4 `VSS-2zis` + `VSS-ce0h` |
| Order | 19.1, 19.2, 19.3, 19.4. Planning found one dependency, which agrees with it: 19.2 after 19.1 |
| `VSS-9wv` | "A plus C": a start-up warning and documentation, and no Admin key for the web UI unless `VS_API_KEY` is set. C is a breaking change |
| `VSS-2kdt` (a login) | Not in scope: a separate follow-up |
| Preparation story | None |
| `VSS-1ar`, `VSS-hnl`, `VSS-6wj` | Not in scope: known items that predate this epic |
| Anything else found while planning | Reported as follow-ups in section 5; no beads created by this workflow |

**Decisions made in planning** (in the ADR file, open to the maintainer's review):

| Question | Decision | ADR |
|---|---|---|
| With `VS_API_KEY` unset: refuse to start, or start and serve no key? | Start; `/config.js` serves an empty key and the web UI shows a set-up screen. The API supervises the game server, API-only use is valid, health probes keep passing, and the API already warns instead of refusing for a wrong `VS_API_KEY` | ADR-3 |
| What may the config file viewer serve? | `.json` regular files up to 2 MiB, the same for every role | ADR-1 |
| How are nested and other-named secrets redacted? | Recursively by key name (a declared fragment list plus `StartupCommands`) and two value rules; Admin gets files unchanged | ADR-2 |
| `VS_GAME_VERSION`: remove or repurpose? | Remove; setting it stays harmless | ADR-4 |
| CSP: where, which directives, enforced? | A response header from the API on the web UI's pages, enforced, with `VS_CSP_MODE` as the way out | ADR-5 |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 18 are done; none is invalidated. One new epic, Epic 19: API Security and Mod File Safety, with 4 stories. No resequencing.

**Story impact:** No existing story changes. Story 19.1 changes Epic 15 ADR-5 (the web key no longer falls back to the Admin key) and replaces Story 17.5's "top-level keys only" redaction. Story 19.3 extends Epic 18 ADR-4 and replaces its decision 6. Story 19.4 replaces Epic 18 ADR-1 decision 6.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR205-FR222; frontmatter |
| Epics | Add Epic 19; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-19-api-security-and-mod-file-safety.md` (facts, ADR-1 to ADR-9); index entry |
| UX spec | None. One new full-page message (no key configured) follows the existing empty-state pattern |
| Deployment and documentation | README, `.env.example`, both compose files and `scripts/worktree-setup.sh` change in Stories 19.1 and 19.2 |
| Beads | Epic `Epic 19: API Security and Mod File Safety` with the 11 in-scope issues as children |

**Technical impact:**

- Stories 19.1 and 19.4 change the API and the web. Story 19.2 changes the API and adds an E2E spec. Story 19.3 is API only.
- No new dependencies.
- Configuration: `VS_API_KEY` becomes necessary for the web UI (breaking); `VS_CSP_MODE` is new and optional; `VS_GAME_VERSION` goes.
- The download cache is emptied once on the first start after Story 19.3.
- The maintainer's cluster deployment (another repository, not touched here) must set `VS_API_KEY` in the release that carries Story 19.1.

**API contract changes, all in `v1alpha1` unless noted (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 19.1 | `GET /config.js`, `VS_API_KEY` | With `VS_API_KEY` unset or blank, serves `{"apiKey": ""}` instead of the Admin key; the web UI shows a set-up screen. Setting `VS_API_KEY` (to the Monitor or the Admin key) restores a working UI | **Breaking** |
| 19.1 | Start-up log | New warnings `web_api_key_is_admin_key` and `web_api_key_not_set` | Added |
| 19.1 | `GET /config/files/{path}` | 400 `CONFIG_FILE_NOT_SUPPORTED` (new code) for a name that does not end in `.json`, a directory, a file that is not a regular file or not UTF-8 text. Before: 200 (text files), 404 or 500 | New error code, behavior change |
| 19.1 | `GET /config/files/{path}` | 413 `CONFIG_FILE_TOO_LARGE` (new code) above 2 MiB | New error code |
| 19.1 | `GET /config/files/{path}` | For roles other than Admin, more values are `"[redacted]"`: secret key names at any depth, `StartupCommands`, URLs with credentials, Discord webhook URLs. The redacted value replaces the whole value, whatever its type | Behavior change (Monitor only) |
| 19.1 | `GET /config/files/{path}` | A file with a byte order mark now parses instead of returning `_raw` | Behavior change |
| 19.1 | `VS_GAME_VERSION` | Removed from the settings, compose files and `.env.example`. Still accepted and ignored | Removed setting, not breaking |
| 19.2 | Web UI pages (`/` and every non-API path) | New headers `Content-Security-Policy` (enforced), `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`. Images over plain `http:` in mod descriptions no longer load; the page cannot be framed | Behavior change |
| 19.2 | `VS_CSP_MODE` | New setting: `enforce` (default), `report-only`, `off` | Added setting |
| 19.3 | `POST /mods/{slug}/enable`, `POST /mods/{slug}/disable` | New error 409 `MOD_FILE_CONFLICT` when the target file name is taken. Before, the other file was replaced | New error on these routes, behavior change |
| 19.3 | `PUT /mods/{slug}/version` | A taken file name is 409 `MOD_FILE_CONFLICT`; before 500 `MOD_VERSION_CHANGE_FAILED`. The check also covers the `.disabled` form and the mod state | Changed status and code |
| 19.3 | `POST /mods`, and the three above | File names are compared ignoring letter case | Behavior change |
| 19.3 | `POST /mods/updates/apply-all` | Response shape unchanged; a file-name conflict is a `failed` item | None |
| 19.3 | Download cache on disk | Layout `cache/mods/<fileid>/<name>`; old files removed at start. Not an API | Internal |
| 19.4 | `GET /mods/lookup/{slug}`, `GET /mods/browse` | `logo_url` is `null` unless it is an `https` URL on `moddbcdn.vintagestory.at` | Behavior change |
| 19.4 | `GET /mods/lookup/{slug}` | `homepage_url` and `source_url` are `null` unless a well-formed `https` URL; `""` becomes `null` | Behavior change |
| 19.4 | `GET /mods/browse` and other mod routes | A mod database body that is not a JSON object is 502 `EXTERNAL_API_ERROR`; before 500 | Changed status |

No response field is removed or renamed.

**Draft release-note text** (the commit subjects that produce it; `cliff.toml` prints the subject):

- Breaking Changes: `feat(api)!: the web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key`, with the footer `BREAKING CHANGE: /config.js serves no key when VS_API_KEY is unset or blank, and the web UI shows a set-up message. Set VS_API_KEY to VS_API_KEY_MONITOR for a read-only web UI or to VS_API_KEY_ADMIN for full access; anyone who can load the web UI receives that key.`
- Features: `feat(api): warn at start-up when the web UI is given the Admin key`; `feat(api): serve the web UI with a Content-Security-Policy (VS_CSP_MODE)`
- Fixes: `fix(api): the config file viewer serves only .json files and no longer fails on binary files`; `fix(api): hide nested and other-named secrets in config files from Monitor keys`; `fix(docker): VS_GAME_VERSION is no longer set or documented; it had no effect`; `fix(api): enabling, disabling or changing the version of a mod can no longer replace another mod's file`; `fix(api): keep downloaded mod files apart when two mods use the same file name`; `fix(api): pass on only https logo, homepage and source links from the mod database`; `fix(api): answer 502, not 500, when the mod database sends a malformed response`

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 19 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Four stories tied to existing beads. Effort medium, risk low to medium. |
| 2. Rollback | Not viable. Nothing completed has to be undone. |
| 3. MVP Review | Not needed. |

**Effort:** Medium. Two issues are size-m in beads (`VSS-9wv`, `VSS-3qb8`) and nine are size-s. Story 19.1 is the largest: four beads across the API, the web, the compose files and the documentation.

**Risks:**

- Story 19.1: the breaking change. An upgraded deployment that does not set `VS_API_KEY` has a web UI that shows a set-up message. The API and the game server keep running, the page says what to set, and the release note is the first entry. The maintainer's own deployment needs its one-line change in the same release.
- Story 19.1: key-name redaction is a heuristic. It hides some harmless values from Monitor and misses a secret under an unrecognisable name with an unrecognisable value. The README says so.
- Story 19.1: size. Four beads in one story; see the note in the epic.
- Story 19.2: an enforced policy can break a page in a browser the E2E run does not cover. `VS_CSP_MODE` is the way out without a new image; the WebSocket behaviour under `connect-src 'self'` and the next-themes script are confirmed in a browser before the policy is fixed.
- Story 19.2: `style-src 'unsafe-inline'` and `img-src https:` are weaker than a strict policy. The alternative breaks the terminal, toasts and description images.
- Story 19.3: the first start after the upgrade empties the download cache.
- Story 19.3: comparing file names without case refuses an install that a case-sensitive volume would have accepted (`foo.zip` beside `Foo.zip`). That is the bead's intent.
- Story 19.4: an author's `http:` homepage or source link is dropped. None was seen in the sample of 60.
- Stories 19.3 and 19.4 edit the same two service files; in parallel they would conflict.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** `lastUpdated: '2026-11-17'`; update entry "Added FR205-FR222 for Epic 19 (API Security and Mod File Safety)".

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 19: API Security and Mod File Safety

#### Secrets and Keys

- FR205: The config file viewer lists and serves only `.json` files under the server data directory, up to 2 MiB, by the same rule for every role
- FR206: A config file request for anything else (another file type, a directory, a file that is too large or not UTF-8 text) is refused with a 4xx status and an error code, never a 500
- FR207: For every role other than Admin, config file content is redacted at every depth: values under secret key names, `StartupCommands`, URLs that contain credentials and Discord webhook URLs; Admin receives files unchanged
- FR208: When `VS_API_KEY` is unset or blank, the web UI is given no API key: the API starts, `/config.js` serves an empty key, and the web UI shows a set-up message and makes no API request
- FR209: The API logs a start-up warning whenever the web UI's key is the Admin key and whenever the web UI has no key, never logging a key
- FR210: The README, `.env.example` and the compose examples explain `VS_API_KEY`, recommend the Monitor key or an authenticating proxy for the web UI, and the production example does not hand out the Admin key by default
- FR211: `VS_GAME_VERSION` is removed from the settings and the documentation; a deployment that still sets it starts as before

#### Content-Security-Policy

- FR212: The web UI's pages are served with an enforced Content-Security-Policy that allows scripts from the manager's own origin only, forbids framing, and is not sent on API, health or API documentation routes
- FR213: Every page of the web UI, including the console WebSocket, the mod gallery and mod description images, works under the policy in the light and dark themes with no policy violation
- FR214: `VS_CSP_MODE` switches the policy between enforced, report-only and off, and the web UI's pages also send `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`

#### Mod Files

- FR215: Enabling or disabling a mod whose target file name is already used is refused with 409 `MOD_FILE_CONFLICT` and changes no file and no state
- FR216: A version change whose new file name is already used is refused with 409 `MOD_FILE_CONFLICT` instead of a 500, changes nothing, and in Update All is one failed item that does not stop the run
- FR217: File-name collisions for install, enable, disable and version change are detected ignoring letter case, so the result does not depend on the volume's filesystem
- FR218: The mod download cache keeps each release under its file ID with a temporary file per download, so mods whose releases share a file name never replace or mix each other's cached archives

#### Mod Database Data

- FR219: The API passes on a mod's logo URL only when it uses https on the mod database's image host, and the web requests logo images without a referrer
- FR220: The API passes on a mod's homepage and source URLs only when they are well-formed https URLs; anything else is left out and never fails the lookup
- FR221: A mod database response that is not a JSON object is answered with 502 `EXTERNAL_API_ERROR` on every mod route, never a 500, and is not cached
- FR222: Requests that arrive while the game version list is not cached share one request to the mod database
```

**FR to story map:**

| Story | Sprint key | FRs | Beads |
|---|---|---|---|
| 19.1 Secrets Stay with Admin | `19-1-secrets-stay-with-admin` | FR205, FR206, FR207, FR208, FR209, FR210, FR211 | `VSS-633`, `VSS-sg1`, `VSS-9wv`, `VSS-ms0` |
| 19.2 Content-Security-Policy | `19-2-content-security-policy` | FR212, FR213, FR214 | `VSS-3qb8` |
| 19.3 Mod Files Are Never Overwritten | `19-3-mod-files-are-never-overwritten` | FR215, FR216, FR217, FR218 | `VSS-40ja`, `VSS-macf`, `VSS-52fy`, `VSS-n0qv` |
| 19.4 Mod Database Data Is Checked | `19-4-mod-database-data-is-checked` | FR219, FR220, FR221, FR222 | `VSS-2zis`, `VSS-ce0h` |

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** `lastUpdated: '2026-11-17'`; update entry "Added Epic 19 (4 stories) for API Security and Mod File Safety; FR205-FR222".

**FR Coverage Map:** rows FR205 to FR222 appended after FR204, each mapped to Epic 19.

**Story Summary:**

OLD:

```markdown
| **Total** | | **106** |
```

NEW:

```markdown
| Epic 19: API Security and Mod File Safety | 19.1, 19.2, 19.3, 19.4 | 4 |
| **Total** | | **110** |
```

### 4.3 Epic 19 Stories (appended to `epics.md`)

## Epic 19: API Security and Mod File Safety

**Goal:** Only the Admin role, and only someone the operator chose to give the Admin key to, can read secrets or act as Admin; the web UI's pages run under a Content-Security-Policy; no mod operation can replace another mod's file; and nothing the mod database sends reaches a link, an image or a 500.

**Architecture:** `architecture/epic-19-api-security-and-mod-file-safety.md` (ADR-1 to ADR-9, with the code facts at `048fea9` and the mod database facts checked on 2026-11-16). There is no preparation story. Story 19.2 confirms two browser behaviours before it settles the policy (ADR-5 decisions 7 and 12).

**Order:** 19.1, 19.2, 19.3, 19.4. Story 19.1 first: it holds the two P2 items (`VSS-633`, `VSS-9wv`) and the breaking change, which should be on `main` early so the release that carries it can be prepared.

**Dependencies:**

- Story 19.2 comes after 19.1: its E2E spec loads every page with a key and uses the `/config.js` helper Story 19.1 adds, and both stories edit `register_frontend` in `main.py` and `config.py`.
- Stories 19.3 and 19.4 need no other story's code. Both edit `services/mods.py` and `services/mod_api.py` in different places, so run them one after another.
- Story 19.4's logo rule does not depend on Story 19.2's `img-src`, which allows any `https` image.

**Breaking change:** Story 19.1 stops handing the Admin key to the web UI when `VS_API_KEY` is unset (ADR-3). Every deployment that does not set `VS_API_KEY` must set it when it upgrades, including the maintainer's cluster deployment, which is configured in another repository and is not changed by this epic.

**Size:** Story 19.1 carries four beads and touches the API, the web, the compose files and the documentation. The grouping is the maintainer's; `create-story` should keep its tasks to the six listed and may propose a split if the story file grows past that.

### Current State

- A Monitor key can ask the config file viewer for any file under the server data directory; binary files and directories answer 500
- A Monitor key receives nested passwords and secrets under other key names in config files
- With `VS_API_KEY` unset, anyone who can load the web UI receives the Admin key, and nothing tells the operator
- `VS_GAME_VERSION` is documented and set in the compose files and does nothing
- The web UI's pages have no Content-Security-Policy
- Enabling or disabling a mod can replace another mod's file; a version change refuses the same case with a 500; the install check depends on the volume's case rules
- Two mods whose releases share a file name share one cache file, and two such downloads at once write one temporary file
- Logo, homepage and source URLs from the mod database reach `src` and `href` unchecked
- A mod database answer that is not a JSON object makes the mod browser answer 500

### Target State

- The config file viewer serves `.json` files only, to every role, and refuses the rest with an error code
- Roles other than Admin get secrets redacted at every depth of a config file
- The web UI gets a key only when `VS_API_KEY` names one; the API warns when that key is the Admin key and when there is none
- `VS_GAME_VERSION` is gone from the settings and the documentation
- The web UI's pages are served with an enforced Content-Security-Policy and every page works under it
- Install, enable, disable and version change refuse a taken file name with 409 `MOD_FILE_CONFLICT`, ignoring case, and the download cache is keyed by file ID
- Only checked `https` URLs leave the API, and a malformed mod database answer is a 502

---

### Story 19.1: Secrets Stay with Admin

**Sprint key:** `19-1-secrets-stay-with-admin`
**Beads:** `VSS-633` (API-077, bug), `VSS-sg1` (API-078, bug), `VSS-9wv` (API-079), `VSS-ms0` (API-070)
**FRs:** FR205, FR206, FR207, FR208, FR209, FR210, FR211

As an **operator who gives other people Monitor access or the web UI's address**,
I want **secrets and the Admin key to reach only the Admin role**,
So that **read-only access stays read-only**.

**Acceptance Criteria:**

**Given** a `.json` file under the server data directory
**When** I request `GET /api/v1alpha1/config/files/{path}` with an Admin or a Monitor key
**Then** the response is 200 with its content, and `GET /config/files` lists exactly the files that can be read this way

*(Covers FR205)*

**Given** a path whose name does not end in `.json` (a log, a save, a zip), existing or not
**When** I request it with either key
**Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED` and the file is not read

*(Covers FR205, FR206)*

**Given** a directory, a directory named `x.json`, a symlink `x.json` to a file of another type, or a `.json` file that is not UTF-8 text
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

**Given** `VS_API_KEY` is unset or blank
**When** the API starts
**Then** it starts, `/healthz` and `/readyz` answer as before, it logs the warning `web_api_key_not_set` without any key, and `GET /config.js` serves `{"apiKey": ""}` with the same headers as before

*(Covers FR208, FR209)*

**Given** the web UI is loaded and `/config.js` serves no key
**When** the page opens
**Then** it shows a "No API key configured" screen that names `VS_API_KEY`, the Monitor key and the Admin key, and it makes no request to `/api/` and opens no WebSocket

*(Covers FR208)*

**Given** `VS_API_KEY` equals the Admin key
**When** the API starts
**Then** `/config.js` serves the Admin key and the API logs the warning `web_api_key_is_admin_key` without the key

*(Covers FR209)*

**Given** `VS_API_KEY` equals the Monitor key, or matches neither key
**When** the API starts
**Then** with the Monitor key `/config.js` serves it and neither new warning is logged; with a key that matches no role the existing `web_api_key_matches_no_role` warning is logged, as before

*(Covers FR209)*

**Given** the README, `.env.example` and both compose files
**When** I read how to give the web UI a key
**Then** they say the web UI needs `VS_API_KEY`, recommend the Monitor key or an authenticating proxy, say that anyone who can load the page receives that key, and the production compose example does not hand out the Admin key by default

*(Covers FR210)*

**Given** the dev stack started with `just docker start` and no `VS_API_KEY` in the environment
**When** I open the web UI or run the E2E specs
**Then** the page has the Admin key as before, because the dev compose file sets `VS_API_KEY` to the Admin key itself

*(Covers FR210)*

**Given** a deployment that still sets `VS_GAME_VERSION`
**When** the API starts
**Then** it starts as before; the variable is no longer a setting and is not in the compose files, `.env.example` or the worktree set-up script

*(Covers FR211)*

**Tasks:**

- [ ] Config file viewer: one predicate for the listing and the read; suffix, type, size and decoding checks; `CONFIG_FILE_NOT_SUPPORTED` and `CONFIG_FILE_TOO_LARGE` (Epic 19 ADR-1) (`VSS-633`)
- [ ] Recursive redaction by key name with `UNMANAGED_SECRET_KEYS`, `SECRET_KEY_FRAGMENTS` and the two value rules; replace `test_nested_password_is_unchanged` (ADR-2) (`VSS-sg1`)
- [ ] `Settings.web_api_key` without the fallback, the start-up states and warnings, `/config.js` with an empty key; committed as `feat(api)!:` with a `BREAKING CHANGE:` footer and the subject of ADR-3 "Release" (`VSS-9wv`)
- [ ] Web: the "No API key configured" screen; E2E: one `/config.js` helper, the empty-key spec, and the dev compose default (ADR-3 decisions 4, 7 and 8)
- [ ] Documentation: README, `.env.example`, both compose files, API documentation of the changed errors (ADR-3 decision 6)
- [ ] Remove `Settings.game_version` and every `VS_GAME_VERSION` line; test that setting it is harmless; committed as `fix(docker):` (ADR-4) (`VSS-ms0`)

---

### Story 19.2: Content-Security-Policy

**Sprint key:** `19-2-content-security-policy`
**Beads:** `VSS-3qb8` (INFRA-005)
**FRs:** FR212, FR213, FR214

As an **operator**,
I want **the web admin's pages served with a Content-Security-Policy**,
So that **an injected script cannot run in a page that holds an API key**.

**Acceptance Criteria:**

**Given** the published image
**When** I request `/` or any web UI path
**Then** the response has `Content-Security-Policy` with exactly the directives of Epic 19 ADR-5 decision 3, and `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`

*(Covers FR212, FR214)*

**Given** the same image
**When** I request `/api/v1alpha1/...`, `/healthz`, `/readyz` or `/docs`
**Then** the response has no `Content-Security-Policy` header, and `/docs` still renders

*(Covers FR212)*

**Given** the Docker stack with the policy enforced
**When** I open the dashboard, the console, the mod browser, a mod detail page with a gallery and a description with images, the installed list, the settings and the version page, in the light and the dark theme
**Then** each page works as before, the browser reports no `securitypolicyviolation` event and no console error, and toasts, dialogs and the terminal are styled

*(Covers FR213)*

**Given** the console page with the policy enforced
**When** it connects
**Then** the console WebSocket and the log stream connect and carry data

*(Covers FR213)*

**Given** a page of the web UI with the policy enforced
**When** an inline script is injected into it, or the page is loaded inside a frame on another origin
**Then** the script does not run and the frame does not load

*(Covers FR212)*

**Given** a mod description with an image on any `https` host
**When** I open the mod's detail page
**Then** the image loads

*(Covers FR213)*

**Given** `VS_CSP_MODE=report-only`, `VS_CSP_MODE=off`, and an unknown value
**When** the API starts
**Then** with `report-only` the same policy is sent as `Content-Security-Policy-Report-Only`, with `off` neither header is sent, and an unknown value stops start-up with a message naming the setting

*(Covers FR214)*

**Given** the Vite dev server (`just dev-web`)
**When** I develop
**Then** no policy applies and hot reload works as before

*(Covers FR213)*

**Tasks:**

- [ ] `VS_CSP_MODE` in `Settings` with validation; the policy as one constant; the headers on `serve_spa` responses (Epic 19 ADR-5 decisions 1, 3, 9 and 10) (`VSS-3qb8`)
- [ ] API tests: the header in each mode, on SPA paths, and its absence on API, health and docs routes
- [ ] Browser checks first: the WebSockets under `connect-src 'self'` and the next-themes inline script (ADR-5 decisions 7 and 12); record what was seen and any hash added
- [ ] E2E spec against the Docker stack: every page in both themes with no violation, and the blocked inline script; the framing refusal by header test or in a browser (ADR-5 decision 13)
- [ ] Documentation: README section on the policy, `VS_CSP_MODE`, and what a proxy in front has to respect; `.env.example`

---

### Story 19.3: Mod Files Are Never Overwritten

**Sprint key:** `19-3-mod-files-are-never-overwritten`
**Beads:** `VSS-40ja` (API-082, bug), `VSS-macf` (API-083), `VSS-52fy` (API-085), `VSS-n0qv` (API-084)
**FRs:** FR215, FR216, FR217, FR218

As an **administrator**,
I want **no mod operation to replace another mod's file, on any volume**,
So that **the mods directory always holds what the Installed list says**.

**Acceptance Criteria:**

**Given** mod A is disabled as `Foo.zip.disabled` and another file `Foo.zip` is in the mods directory
**When** I enable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` with a message naming `Foo.zip`, both files have the same bytes as before, the mod state is unchanged and no restart is pending

*(Covers FR215)*

**Given** mod A is enabled as `Foo.zip` and a file `Foo.zip.disabled` is in the mods directory
**When** I disable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is changed

*(Covers FR215)*

**Given** no file is in the way
**When** I enable or disable a mod
**Then** it works as before, and enabling an enabled mod or disabling a disabled one is still a success that changes nothing

*(Covers FR215)*

**Given** an installed mod and a target release whose file name, or its `.disabled` form, is another file in the mods directory or another entry in the mod state
**When** I change the mod's version
**Then** the response is 409 `MOD_FILE_CONFLICT`, not 500 `MOD_VERSION_CHANGE_FAILED`, and the mod's file, the other file and the state are unchanged

*(Covers FR216)*

**Given** Update All, and one mod's new file name is taken
**When** the run reaches it
**Then** that mod is a `failed` item with the conflict message, and the run continues with the other mods

*(Covers FR216)*

**Given** a version change that fails to place the file or save state for another reason
**When** it is rolled back
**Then** the response is 500 `MOD_VERSION_CHANGE_FAILED`, as before

*(Covers FR216)*

**Given** a case-sensitive mods directory with `Foo.zip` installed
**When** I install, enable, disable or change to a version of another mod whose file would be `foo.zip` or `FOO.ZIP.disabled`
**Then** the response is 409 `MOD_FILE_CONFLICT`, the same answer a case-insensitive volume gives

*(Covers FR217)*

**Given** an installed mod `Foo_1.0.zip`
**When** I change it to a release whose file name differs from its own only in case
**Then** the change succeeds and exactly one file for the mod is in the directory afterwards, on a case-sensitive and on a case-insensitive volume

*(Covers FR217)*

**Given** a dangling symlink with the target name, or a mod state entry under the target name with no file
**When** I run any of the four operations
**Then** the response is 409 `MOD_FILE_CONFLICT`

*(Covers FR215, FR216, FR217)*

**Given** two mods whose releases have the same file name
**When** I download both, one after the other or at the same time
**Then** each is cached under its own file ID, neither replaces the other's copy, and each install places the archive of the mod that was asked for

*(Covers FR218)*

**Given** two downloads of the same release at the same time
**When** both finish
**Then** the cache holds one complete file and no temporary file is left

*(Covers FR218)*

**Given** a cache with files from before this story, and a temporary file left by a crash more than an hour ago
**When** the API starts and the next download finishes
**Then** the old files are removed at start and their number logged, eviction counts and evicts files in the new layout and removes emptied directories and the old temporary file

*(Covers FR218)*

**Tasks:**

- [ ] The file-name helper (listing plus state, `casefold`, the mod's own file excluded) and `ModFileConflictError` with the operation in its message (Epic 19 ADR-6 decisions 1, 2 and 6) (`VSS-52fy`)
- [ ] Use it in `enable_mod` and `disable_mod`; 409 on both routes (`VSS-40ja`)
- [ ] Use it in `_apply_version_change`, with `same_file` ignoring case; 409 on the version route; `ModFileConflictError` in the Update All loop (ADR-6 decisions 4 and 7) (`VSS-macf`)
- [ ] Cache layout `cache/mods/<fileid>/<name>`, one path function, a temporary file per download, removal of the old layout at start (ADR-7 decisions 1, 2, 3 and 5) (`VSS-n0qv`)
- [ ] `CacheEvictionService` for the new layout, emptied directories and old temporary files (ADR-7 decision 4)
- [ ] Tests for every case above with file bytes and state compared before and after; confirm the web shows the message for enable, disable and version change; API documentation of the changed errors

---

### Story 19.4: Mod Database Data Is Checked

**Sprint key:** `19-4-mod-database-data-is-checked`
**Beads:** `VSS-2zis` (API-081), `VSS-ce0h` (API-086)
**FRs:** FR219, FR220, FR221, FR222

As an **administrator**,
I want **the manager to pass on only URLs it has checked and to treat a broken mod database answer as an upstream error**,
So that **a mod author's data or a mod database fault cannot misuse or break the pages I use**.

**Acceptance Criteria:**

**Given** a mod whose logo is an `https://moddbcdn.vintagestory.at/` URL
**When** I look it up or see it in the browse results
**Then** `logo_url` is that URL unchanged

*(Covers FR219)*

**Given** a mod whose logo is an `http:` URL, a URL on another host, a `data:` or `javascript:` URL, or not a URL
**When** I look it up or browse
**Then** the response is 200, `logo_url` is `null`, and the page shows the placeholder

*(Covers FR219)*

**Given** a mod logo on a browse card, the detail page or the install dialog
**When** the image is requested
**Then** the request carries no referrer

*(Covers FR219)*

**Given** a mod whose homepage or source URL is an `https` URL
**When** I look it up
**Then** `homepage_url` or `source_url` is that URL unchanged and the detail page shows the link

*(Covers FR220)*

**Given** a homepage or source value that is empty, an `http:`, `javascript:` or `data:` URL, has user info, has a space, control character or backslash, or is longer than 2,048 characters
**When** I look the mod up
**Then** the response is 200, the field is `null` and the detail page shows no such link; the "ModDB Page" link is unaffected

*(Covers FR220)*

**Given** the mod database answers the listing, a filtered listing, a mod lookup or the game version list with HTML, an empty body, `[]`, `"text"` or `null`
**When** a mod route needs that answer
**Then** the response is 502 `EXTERNAL_API_ERROR`, never 500, and the previous cached copy and its age are unchanged

*(Covers FR221)*

**Given** the mod database answers correctly on the next request
**When** I retry
**Then** the route works; nothing malformed was cached

*(Covers FR221)*

**Given** the game version cache is cold and several browse requests arrive together
**When** they are served
**Then** the mod database receives one `/api/gameversions` request, every request gets its result, and a failure reaches every waiting request and is not kept

*(Covers FR222)*

**Tasks:**

- [ ] `external_link_url` in `services/mod_media.py`; `mod_image_url` on `logo_url` in the lookup and the browse item; debug log without the URL (Epic 19 ADR-8 decisions 1 to 3 and 6) (`VSS-2zis`)
- [ ] Web: `referrerPolicy="no-referrer"` on the three logo images; confirm the placeholder and the missing links (ADR-8 decision 5)
- [ ] One guarded JSON fetch in `ModApiClient`, used by the four fetchers, each keeping its status rules (ADR-9 decisions 1 to 4) (`VSS-ce0h`)
- [ ] Shared in-flight fetch for the game version list (ADR-9 decision 5)
- [ ] Tests: URL rules with a synthetic bad-data fixture for lookup and browse; each fetcher with the five malformed bodies and an unchanged cache; concurrent cold calls; API documentation of `null` for the three URL fields

### 4.4 Architecture (`architecture/epic-19-api-security-and-mod-file-safety.md`, new)

| ADR | Decision | Story |
|---|---|---|
| ADR-1 | The config file viewer lists and serves only `.json` regular files up to 2 MiB, by one rule for every role; another suffix, a directory or non-UTF-8 content is 400 `CONFIG_FILE_NOT_SUPPORTED`, too large is 413 `CONFIG_FILE_TOO_LARGE`; a file that does not parse keeps the `_raw` form | 19.1 |
| ADR-2 | For roles other than Admin, `redact_secrets` walks every depth and replaces the value of a key that is a secret setting, is in `UNMANAGED_SECRET_KEYS` (`StartupCommands`) or contains a fragment such as `password`, `token`, `secret`, `apikey`, `webhook`; plus URLs with user info and Discord webhook URLs. Admin gets files unchanged | 19.1 |
| ADR-3 | The web key has no fallback: with `VS_API_KEY` unset or blank the API starts, `/config.js` serves an empty key and the web UI shows a set-up screen; a warning at start-up when the web key is the Admin key and when there is none; the dev compose file sets the Admin key itself. Breaking, with the `feat(api)!:` subject carrying the instruction | 19.1 |
| ADR-4 | `VS_GAME_VERSION` is removed from the settings, compose files and documentation; setting it stays harmless | 19.1 |
| ADR-5 | The API sends an enforced `Content-Security-Policy` on the web UI's pages only: `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `img-src 'self' data: https:`, `connect-src 'self'`, `frame-src 'none'`, `frame-ancestors 'none'`; with `nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options`; `VS_CSP_MODE` switches to report-only or off; the Vite dev server has no policy | 19.2 |
| ADR-6 | One helper checks the names an operation will create against the directory listing and the mod state, ignoring case and excluding the mod's own file; install, enable, disable and version change all answer 409 `MOD_FILE_CONFLICT`; Update All records it as a failed item | 19.3 |
| ADR-7 | The download cache is `cache/mods/<fileid>/<name>` with a temporary file per download; eviction follows the layout; the old flat files are removed once at start | 19.3 |
| ADR-8 | `logo_url` goes through the Story 18.1 image rule; `homepage_url` and `source_url` through a new `https`-only link rule; anything else is `null`; logo images get `referrerPolicy="no-referrer"` | 19.4 |
| ADR-9 | One helper fetches mod database JSON and raises `ExternalApiError` for a body that is not a JSON object, used by all four fetchers; the game version list has one shared in-flight fetch | 19.4 |

The file also records the code facts and the mod database facts the decisions rest on.

### 4.5 Other Artifacts

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | Add `epic-19` (backlog), `epic-19-retrospective` (optional) and stories `19-1` to `19-4` (backlog), via `scripts/sprint-status.sh` | Now |
| Beads | Create epic `Epic 19: API Security and Mod File Safety` (`VSS-fl9b`); parent the 11 in-scope issues to it; close each with an AAR when its story is done | Now, and per story |
| `architecture/index.md` | Entry for the Epic 19 ADRs | Now |
| README, `.env.example`, compose files, `scripts/worktree-setup.sh`, `architecture/project-structure-boundaries.md` | `VS_API_KEY`, `VS_CSP_MODE`, `VS_GAME_VERSION` | Stories 19.1 and 19.2 |
| The maintainer's cluster deployment (another repository) | Set `VS_API_KEY` | With the release that carries Story 19.1; not done by this epic's stories |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 19.1 to 19.4 from `epics.md` and the Epic 19 ADRs, 19.1 first |
| Developer (`dev-story`) | Implement each story; in 19.1, make the breaking change its own commit with the subject of ADR-3; in 19.2, do the two browser checks before fixing the policy |
| Reviewer (`code-review`) | Delegated read-only review per story |
| Maintainer (Matt) | Reviews this proposal and answers the open questions below; can overturn any default at story creation; sets `VS_API_KEY` in the cluster deployment with the release |

**Open questions for the maintainer** (each has a default the stories use unless overturned):

1. **Start and serve no key (ADR-3).** Default: the API starts and the web UI shows a set-up screen. Alternative: refuse to start, which also stops the game server on upgrade.
2. **Which key the documentation recommends first.** Default: the README and `.env.example` show `VS_API_KEY` set to the Monitor key as the recommended example and the Admin key as the full-access choice with its warning. The production compose file keeps a blank default, so a first run shows the set-up screen until the operator chooses.
3. **A key that matches no role (ADR-3 decision 5).** Default: unchanged, it is served and warned about as today. Alternative: serve no key and show the set-up screen with a second message.
4. **Redaction list (ADR-2).** Default fragments: `password`, `passwd`, `secret`, `token`, `apikey`, `privatekey`, `accesskey`, `credential`, `webhook`, `authorization`; plus `StartupCommands`. The world seed is not treated as a secret. Additions or removals are one constant.
5. **Config file size limit (ADR-1).** Default: 2 MiB. Not configurable.
6. **CSP mode and the extra headers (ADR-5).** Default: enforced, with `VS_CSP_MODE` as a switch, and `Referrer-Policy: no-referrer`, `nosniff` and `X-Frame-Options` on the same responses, which goes slightly beyond the bead. Alternative: the CSP header alone, or no switch.
7. **`http:` homepage and source links (ADR-8).** Default: dropped. Alternative: allow `http:` as well as `https:` for these two links only.
8. **Story 19.1's size.** Default: one story, as grouped. Alternative: split the `VS_API_KEY` change (`VSS-9wv`) into its own story so the breaking commit has its own review.
9. **Release.** The breaking change lands before the first stable release (`0.1.0-rc.4` today). Default: nothing special; it ships in the next pre-release or in `0.1.0`.

**Follow-ups found outside the scope** (reported, no beads created):

1. `/docs`, `/redoc` and `/openapi.json` are served without authentication (FastAPI defaults, `main.py:165-170`), and the documentation pages load scripts from a public CDN. Not a secret leak; worth a decision on whether the published image should serve them.
2. `get_all_mods` has no shared in-flight fetch either: several first requests each download the 4 MB listing (`services/mod_api.py:642-664`). Same pattern as the game version list in `VSS-ce0h`, which names only that list.
3. Enabling or disabling a mod whose own file is missing from the mods directory fails with an unhandled `FileNotFoundError` (`services/mods.py:749`, `:807`), a 500.
4. A crash between the copy and the rename in `_place_install` or `_apply_version_change` leaves `<name>.tmp` or `<name>.bak` in the mods directory; no code was found that removes them.
5. The twelve E2E specs that still carry `localStorage.setItem('apiKey', ...)` init scripts; Story 19.1 removes them only from the specs it touches. And no workflow runs the E2E specs.
6. `Settings()` is constructed three times at import and start-up (`main.py:96`, `:177`, `:219`); not a defect, noticed while tracing the key.
7. `GET /config/directories` lists every subdirectory of the server data directory to Monitor, including `Saves`, `Backups` and `Playerdata`, although the viewer can no longer read anything but `.json` in them.
8. `Playerdata/*.json` (player names and IDs, ban and whitelist entries) stays readable by Monitor; it is personal data, not a secret, and is not redacted by ADR-2.
9. The world seed in `serverconfig.json` stays readable by Monitor (open question 4).
10. After Story 19.2, the description sanitizer could drop `http:` images itself so a broken image icon is not shown.

**Success criteria:**

- With `VS_API_KEY` unset, `/config.js` contains no key and the page shows the set-up screen; with it set to the Admin key the start-up log has the warning
- A Monitor key gets 400 for `server-main.log` and no secret value from a config file with nested and other-named secrets; the raw body is checked
- No request to the config file viewer answers 500 for a binary file or a directory
- Every web UI page loads in both themes with the policy enforced and no violation; an injected inline script does not run
- Enabling, disabling, installing or changing a mod's version when the file name is taken returns 409 and leaves the other file byte for byte, on a case-sensitive directory
- Two mods with the same release file name can be downloaded at the same time and each install places the right archive
- A mod with an `http:` or off-host logo shows the placeholder; a malformed mod database listing answers 502
- Each in-scope beads issue is closed with an AAR by its story
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: eleven beads chosen by the maintainer after Epic 18. [x] 1.2 type: four bugs and seven hardening tasks from reviews and planning. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete except the Admin key fallback of Epic 15 ADR-5, the top-level-only redaction of Story 17.5, and decision 6 of Epic 18 ADR-1 and ADR-4. [x] 2.5 no resequencing; order inside Epic 19 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR205-FR222 added, MVP unaffected. [x] 3.2 architecture: new Epic 19 ADRs. [N/A] 3.3 UX spec: no change. [!] 3.4 deployment: `VS_API_KEY` must be set by every deployment that uses the web UI, in the release that carries Story 19.1 |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [!] 6.1, 6.2 written without interactive review. [!] 6.3 scope approved by Matt on 2026-11-16 before the workflow ran; approval of this document is pending. [x] 6.4 handoff in section 5 |
