# Epic 19: API Security and Mod File Safety - Architecture Decisions

Decisions from the Epic 19 course correction (2026-11-17), revised the same day after the maintainer's review: seven follow-up beads were folded in (ADR-3, ADR-7, ADR-9, ADR-14 and parts of ADR-6 and ADR-13 are new), `VSS-9wv` became its own story, and the ADRs were renumbered in story order. Epic 19 has no preparation story. Each decision was checked by reading the code at commit `048fea9` (`main` after Epic 18, release `v0.1.0-rc.4`), and file and line references are to that commit; API paths are under `api/src/vintagestory_api/`. The mod database facts were checked on 2026-11-16 with unauthenticated requests to the public API. Where a story has to confirm something in a browser first, the ADR says so.

Decisions the maintainer made before planning are marked "maintainer decision" and are not reopened here: the scope of `VSS-9wv` (a warning plus no Admin key by default, a breaking change), and that a login (`VSS-2kdt`) is a separate follow-up. The maintainer answered the nine open questions of the proposal on 2026-11-17: every default stands, and `VSS-9wv` is split into its own story; the status lines say which ADR each answer confirms.

| Story | ADRs |
|---|---|
| 19.1 Secrets Stay with Admin | ADR-1, ADR-2, ADR-3, ADR-4 |
| 19.2 The Web UI No Longer Gets the Admin Key | ADR-5 |
| 19.3 Content-Security-Policy and API Docs | ADR-6, ADR-7 |
| 19.4 Mod Files Are Never Overwritten | ADR-8, ADR-9, ADR-11 |
| 19.5 The Mod State Matches the Mods Directory at Start-Up | ADR-10 |
| 19.6 Mod Database Data Is Checked | ADR-12, ADR-13 |
| 19.7 E2E Runs in CI | ADR-14 |

Second revision, same day: Matt decided the four observations the first revision reported (each marked "Matt, 2026-11-17" where it is written in): the start-up reconcile of the mod state (new ADR-10, new Story 19.5, later ADRs and stories renumbered), a seeded `serverconfig.json` in CI (ADR-14 decision 10), one cached settings object and an app that tests can construct (ADR-5 decision 11, ADR-7 decision 6), and a note for roles other than Admin in the file browser (ADR-3 decision 9).

## Facts Checked in the Code

**Config file viewer.**

- `GET /api/v1alpha1/config/files/{filename:path}` (`routers/config.py:471-538`) needs only an authenticated key (`RequireAuth`, `:485`) and passes the role to `ConfigFilesService.read_file` (`:515`).
- `read_file` (`services/config_files.py:179-227`) checks that the resolved path is inside the server data directory (`_safe_path`, `:67-102`, which resolves symlinks first) and that it exists (`:207`). It has no check for the file type, the suffix or the size. `list_files` lists only `*.json` (`:172-174`), so the listing and the read disagree about what the viewer serves.
- `safe_path.read_text(encoding="utf-8")` (`:213`) is outside the `try`. A file that is not UTF-8 raises `UnicodeDecodeError` and a directory raises `IsADirectoryError`; neither is caught, so both are a 500 for both roles. Only `json.JSONDecodeError` is caught (`:217`). A deeply nested JSON text raises `RecursionError` from `json.loads`, which is not caught either.
- A file that is UTF-8 and does not parse is returned as `{"_raw": <text>, "_parse_error": ...}`; a role other than Admin gets `_raw: "[redacted]"` (`:221`).
- `redact_secrets` (`services/game_config.py:238-248`) changes only an object's own keys, and only keys in `SECRET_SETTING_KEYS` (`:215-217`), which is derived from the managed settings' `secret` flag and holds one key, `Password`, compared without case (`is_secret_key`, `:228-230`). `null` and `""` stay (`has_secret_value`). `test_nested_password_is_unchanged` (`api/tests/test_routers_config.py:1474`) pins the nested case as a known limit.
- Epic 17 ADR-4 planned the redaction for `serverconfig.json` only; Story 17.5 applied it to every file the viewer reads (`services/config_files.py:9-12`).

**The web UI's key.**

- `Settings.api_key` is `VS_API_KEY` (`config.py:23`). `Settings.web_api_key` returns it, or the Admin key when it is unset or blank (`config.py:31-36`).
- `GET /config.js` is unauthenticated and serves `window.__VSM_CONFIG__ = {"apiKey": <web_api_key>};` with `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin` and `X-Content-Type-Options: nosniff` (`main.py:260-272`; Epic 15 ADR-5).
- At start-up the API warns when the web key matches neither role key (`web_api_key_matches_no_role`, `main.py:103-108`, using `web_api_key_has_a_role()`, `config.py:38-40`). It refuses to start only when the Admin key is missing (`config.py:178-182`). Nothing is logged when the web key is the Admin key.
- The same lifespan auto-starts the game server (`main.py:117-141`): the API process supervises the game server.
- `/healthz` and `/readyz` (`routers/health.py`) are unauthenticated and do not look at any key.
- The web reads `window.__VSM_CONFIG__?.apiKey || import.meta.env.VITE_API_KEY || ''` (`web/src/api/client.ts:29-33`) and sends it as `X-API-Key` on every request. With an empty key every request is a 401; no screen explains why.
- `docker-compose.yaml:21` and `docker-compose.dev.yaml:20` both pass `VS_API_KEY=${VS_API_KEY:-}`, so in both stacks the variable is set and blank unless the operator sets it. `.env.example:41-45` and `README.md:37`, `:75` document "default: the Admin key".
- E2E: all 18 specs in `web/e2e/` take the Admin key from the test process's own `VS_API_KEY_ADMIN` (default `changeme`) for direct API calls. Six specs answer `/config.js` themselves with `page.route` (`layout-widths`, `mod-detail-media`, `settings-desktop-layout`, `settings-empty-values`, `settings-as-saved`, `monitor-password-redaction`). The other twelve rely on the stack's own `/config.js` handing the page the Admin key. Fifteen specs still add a `localStorage.setItem('apiKey', ...)` init script, which has done nothing since Story 17.5. No GitHub workflow runs the E2E specs.

**How the app is built.** `main.py` constructs `Settings()` three times: in the lifespan (`:96`), at import for the CORS origins (`:177`) and at import to decide whether the RBAC test router is registered (`:219`). Requests use a fourth, cached one (`get_settings`, `middleware/auth.py:23-30`). `app` is created at import (`main.py:165-170`), so a test cannot build the app with settings of its choice; it can only override the `get_settings` dependency, which the lifespan and the import-time code do not use.

**`VS_GAME_VERSION`.** `Settings.game_version` (`config.py:24`) is read by nothing in `api/src` since `VSS-tpe`; compatibility uses the installed server version (`services/mods.py:101`, `:302`). It is still set in `docker-compose.yaml:22`, `docker-compose.dev.yaml:21` and `scripts/worktree-setup.sh:61`, and described in `.env.example:20-23` as "VintageStory game version to install", which is false: the version to install is chosen in the web UI. `Settings` has no `env_file` and reads only declared fields from the environment, so an environment variable without a field is ignored.

**Content-Security-Policy.**

- Nothing sets one. The API registers CORS, CORS logging and request context middleware (`main.py:186-200`); `web/index.html` has no CSP `<meta>`; `web/vite.config.ts` sets no headers.
- The built `index.html` has two scripts, both same-origin files: the module bundle (`/assets/index-*.js`) and the classic `<script src="/config.js">` (`web/index.html:13`). It has no inline script and no inline style. Styles are one linked stylesheet per chunk.
- The frontend is served by `register_frontend` (`main.py:246-278`): `/assets` as static files, `/config.js`, and `serve_spa` for every other path, which returns `index.html` for any path that is not a file (`:275-278`).
- FastAPI's `/docs` and `/redoc` are on (no `docs_url` in `FastAPI(...)`, `main.py:165-170`). They load Swagger UI from a CDN and use an inline script.
- In the image the web calls the API on its own origin (`VITE_API_BASE_URL=""`, `Dockerfile:28`), and both WebSockets are built from `window.location` (`web/src/hooks/use-console-websocket.ts:88`, `use-log-stream.ts:92`).
- Runtime style injection: `@xterm/xterm`, `sonner`, `react-style-singleton` (Radix scroll lock) and `next-themes` each create `<style>` elements (`createElement("style")` in their published builds). Mod descriptions are inserted as sanitized HTML (`ModDetailPage.tsx:785`) and keep inline `style` attributes and `<img>` from any host (`web/src/lib/mod-description.ts`). `web/src/styles/index.css:249` uses a `data:` SVG as an image.
- `next-themes` renders an inline `<script>` element through React. Whether a browser tries to run it in a client-rendered page was not established by reading; Story 19.3 confirms it.
- A local build (`web/dist/assets`) contains no `eval(` or `new Function(`.

**Mod files.**

- `enable_mod` and `disable_mod` call `old_path.rename(new_path)` with no check of the target (`services/mods.py:749`, `:807`). Both are synchronous and refuse only when the mod is busy.
- `_apply_version_change` refuses when `new_path.exists()` and the name is not the mod's own (`:1008-1012`). It raises `ModVersionChangeFailedError`, which `PUT /mods/{slug}/version` returns as 500 `MOD_VERSION_CHANGE_FAILED` (`routers/mods.py:1137-1138`). It checks one name only (not the enabled or disabled twin), follows symlinks, does not look at the mod state, and compares the name with the mod's own exactly (`same_file`, `:1008`).
- `_place_install` (Story 18.2, Epic 18 ADR-4) checks `<name>` and `<name>.disabled` in the directory (not following symlinks) and in the mod state, comparing names exactly (`:1283-1290`).
- `ModFileConflictError`'s message is written for an install ("Cannot install ...", `:191-200`). The Update All loop catches a fixed list of errors per mod (`services/mod_updates.py:422-438`); `ModFileConflictError` is not in it.
- The per-mod lock key is the mod ID in lower case (`_lock_key`, `:337-339`).

**Download cache.**

- `download_release_file` writes to `cache/mods/<safe_name>.tmp` and renames it to `cache/mods/<safe_name>` (`services/mod_api.py:578-595`). The key is the release's file name alone.
- `install_mod` holds the lock of the install mod ID while it downloads (`services/mods.py:1236-1237`), and `change_version` holds the mod's lock. Two different mods have two different locks, so two downloads of releases that share a file name can run at once, both writing the same `.tmp` file.
- After the download, `install_mod` reads the archive's `modinfo.json` to refuse a busy or installed mod (`:1240-1244`). It does not require the archive's mod ID to equal the one it resolved, so an install can place whatever archive is at the cache path. A version change does check (`_archive_matches`, `:1173-1179`, called at `:1149` and `:1154`).
- `_acquire_release_archive` builds the cache path itself (`services/mods.py:1147`), separately from the client.
- `CacheEvictionService` lists `*.zip` and `*.cs` directly under `cache/mods`, not in subdirectories (`services/cache_eviction.py:59`, `:105-110`). Nothing removes a `.tmp` file left by a crash.

**Mod database data.**

- `logo_url` is `mod["logofilename"]` on lookup (`services/mods.py:690`) and `mod["logo"]` on browse (`routers/mods.py:238`); `homepage_url` and `source_url` are `mod["homepageurl"]` and `mod["sourcecodeurl"]` (`services/mods.py:693-694`). The normalizer checks their type only (`models/moddb.py:103-106`). None goes through `services/mod_media.py`, which holds the image rule (`mod_image_url`, `:63-65`) Story 18.1 applies to screenshots.
- The web puts the logo in `<img src>` in three places without `referrerPolicy` (`web/src/components/ModCard.tsx:142`, `InstallConfirmDialog.tsx:142`, `features/mods/ModDetailPage.tsx:620`) and the two links in `<a href>` with `rel="noopener noreferrer"` (`ModDetailPage.tsx:702-723`). The gallery images already have `referrerPolicy="no-referrer"`.
- `get_mod` guards its body: not JSON and not an object are both `ExternalApiError` (`services/mod_api.py:395-407`). `get_game_versions` has the same guards since Story 18.3 (`:964-981`, `_is_json_object`, `_is_json_array`, `:261-269`).
- `get_all_mods` calls `response.json()` and `data.get(...)` with no guard (`:664-668`): a body that is not JSON raises `ValueError`, and a JSON array or string raises `AttributeError`; neither is an `httpx.HTTPError`, so both are a 500 on `GET /mods/browse`. `_fetch_mods_by_version` catches the `ValueError` (`:858-866`) and then calls `data.get` unguarded (`:869`).
- `get_all_mods` has no shared fetch either: every request that finds the 5-minute cache cold downloads the whole listing (`:659-664`).
- `get_game_versions` has no shared fetch: every request that finds the cache cold makes its own request (`:948-952`). The filtered listings share one fetch per tag (`_version_fetch`, `:741-755`, awaited with `asyncio.shield`, `:776-777`).

## Mod Database Facts (checked 2026-11-16)

- Listing, `GET /api/mods`: 9,636 items. `logo` is an `https://moddbcdn.vintagestory.at/` URL for 6,531 and `null` for 3,105. No other scheme or host.
- Entry, `GET /api/mod/{slug}`, for the 60 most downloaded mods: `logofilename` is an `https://moddbcdn.vintagestory.at/` URL for 55 and `null` for 5. `homepageurl` is an `https` URL for 33, `""` for 23 and `null` for 4. `sourcecodeurl` is an `https` URL for 44 and `""` for 16. No `http:` URL and no other scheme was seen. The API does not promise that.

## ADR-1: The Config File Viewer Serves JSON Files Only and Refuses the Rest with an Error Code

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-633`). Extends Epic 17 ADR-4. The maintainer confirmed the 2 MiB limit, not configurable, on 2026-11-17.

**Context:** see "Config file viewer" above. A Monitor key can request any path under the server data directory (logs, `Saves/`, `Playerdata/`, `Backups/`, `Mods/`). Since Story 17.5 the text of a file that does not parse is hidden from Monitor, but the request is served, whole files are read into memory whatever their size, and binary files and directories are a 500.

**Decision:**

1. **One predicate decides what the viewer serves,** used by `list_files` and `read_file`, so the listing and the read cannot disagree: a regular file whose name ends in `.json` (compared without case).
2. **The rule is the same for Admin and Monitor.** The viewer is a configuration viewer. Logs, saves and backups are not configuration, and an Admin has the console, the log stream and the volume for those.
3. **The suffix is checked on the requested name before the disk is touched,** and again on the resolved path. So a request for a name without the suffix gets the same answer whether or not the file exists, and a symlink `x.json` to a file of another type is refused.
4. **Order of checks and answers** (each sets `Cache-Control: no-store`, as today):

   | Case | Status | Code |
   |---|---|---|
   | Path leaves the server data directory | 400 | `CONFIG_PATH_INVALID` (unchanged) |
   | Name does not end in `.json` | 400 | `CONFIG_FILE_NOT_SUPPORTED` (new) |
   | Does not exist | 404 | `CONFIG_FILE_NOT_FOUND` (unchanged) |
   | Exists and is a directory, or not a regular file, or resolves to a name without the suffix | 400 | `CONFIG_FILE_NOT_SUPPORTED` |
   | Larger than `CONFIG_FILE_MAX_BYTES` (2 MiB, 2,097,152 bytes) | 413 | `CONFIG_FILE_TOO_LARGE` (new) |
   | Not UTF-8 text | 400 | `CONFIG_FILE_NOT_SUPPORTED` |
   | UTF-8 text that does not parse as JSON | 200 | `_raw` and `_parse_error`, as today |

5. **Size is checked with `stat` before the file is read.** 2 MiB is far above any `serverconfig.json` and above the mod configuration files seen so far; it is one constant.
6. **Decoding.** The file is read as bytes and decoded as `utf-8-sig`, so a file written with a byte order mark parses. `UnicodeDecodeError` is the 400 above.
7. **Parsing never raises past the service.** `RecursionError` from `json.loads` is treated like `JSONDecodeError`: the `_raw` form. Game and mod configuration files are often not strict JSON (comments, trailing commas), so the `_raw` form stays; only Admin receives the text.
8. **Any other `OSError` while reading** (permissions, a file removed between the checks) is 404 `CONFIG_FILE_NOT_FOUND` when the file is gone and otherwise a logged 500 with the standard error envelope; it is not hidden.
9. **Not decided here:** this ADR is about file types. Which directories a role may list and read is ADR-3, and what Monitor sees inside a file is ADR-2.
10. **Rejected: Admin may read any file type.** It keeps a second, untested path through binary and very large files for a need the console and log stream already meet. **Rejected: 415.** That status is about the request body's media type. **Rejected: an allow-list of directories.** Mod configuration lives where each mod puts it; the suffix and the role-based redaction are the rule.

**Consequences:**

- A request for a `.log`, `.vcdbs`, `.zip`, `.txt` or suffix-less path that was 200 or 500 is now 400. The web lists only `.json` files, so the UI does not ask for anything else.
- No request to this route can read more than 2 MiB into memory.
- Tests cover both roles for: a text file with another suffix, a binary file named `.json`, a directory, a directory named `x.json`, a symlink `x.json` to another type, a file one byte over the limit, a file with a byte order mark, and deeply nested JSON.

## ADR-2: Non-Admin Roles Get Config Files Redacted Recursively by Key Name

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-sg1`). Replaces the "top-level keys only" rule of Story 17.5; Epic 17 ADR-4 decisions 1, 2 and 4 to 6 stand. The maintainer confirmed the fragment list, `StartupCommands`, and that the world seed is not treated as a secret, on 2026-11-17.

**Context:** `redact_secrets` covers one key name at one depth. Mod configuration files under `ModConfig/` hold bot tokens, API keys and webhook URLs under names the manager cannot know in advance, and `serverconfig.json` has `StartupCommands`, free text that can hold a command with a password.

**Decision:**

1. **The walk is recursive.** `redact_secrets` visits every object and array at every depth. If the walk cannot finish (nesting too deep for it), the whole content is replaced by `"[redacted]"`: it fails closed.
2. **A key is secret when** any of these holds, compared after `casefold()` and after removing `_`, `-`, `.` and spaces:
   - it is a managed setting marked `secret` (today `Password`), as before;
   - it is in `UNMANAGED_SECRET_KEYS`, a second declared set for `serverconfig.json` keys that are not managed settings. It starts with `StartupCommands`;
   - it contains one of `SECRET_KEY_FRAGMENTS`: `password`, `passwd`, `secret`, `token`, `apikey`, `privatekey`, `accesskey`, `credential`, `webhook`, `authorization`.
3. **What is replaced.** The whole value of a secret key, whatever its type, becomes the string `"[redacted]"`. `null` and `""` stay, since they hold no secret (unchanged rule, `has_secret_value`).
4. **Two value rules, for secrets under other key names.** A string value anywhere is replaced when it is a URL with user info (`scheme://user:pass@host`) or a Discord webhook URL (host `discord.com` or `discordapp.com` with a path starting `/api/webhooks/`).
5. **The rule applies to every file the viewer serves,** not only to files under `ModConfig/`. The same key names mean the same thing wherever a file is.
6. **Admin gets every file unchanged.** Redacted stays the default: `read_file` reveals only when the Admin role is passed (Epic 17 ADR-4 decision 4).
7. **The `_raw` rule stays.** A file that does not parse cannot be redacted by structure, so only Admin gets its text.
8. **`GET /config/game` does not change.** It lists managed settings only.
9. **The lists are constants in `services/game_config.py`,** beside `SECRET_SETTING_KEYS`, with one function that answers "is this key secret".
10. **Rejected: making `ModConfig/` Admin-only.** It takes every mod's configuration away from Monitor (FR22) and does nothing for a secret in a file elsewhere. **Rejected: guessing secrets from how random a value looks.** It hides seeds, IDs and hashes and still misses short passwords.

**Consequences:**

- A Monitor key no longer receives nested passwords, tokens, API keys or webhook URLs under recognisable names, or `StartupCommands`.
- Some harmless values are hidden from Monitor (a key such as `TokenBucketSize`). That direction of error is accepted.
- A secret under a name the fragments do not match (`Key1`) with a value the value rules do not match is still sent to Monitor. The README says what the Monitor role can read.
- `test_nested_password_is_unchanged` is replaced by tests for nesting in objects and arrays, each fragment, both value rules, `StartupCommands`, and the raw response body for both roles.

## ADR-3: Roles Other Than Admin See the Root Config Files and `ModConfig` Only

**Status:** Accepted (Epic 19 revision, 2026-11-17). Implemented by Story 19.1 (`VSS-3hs2`). Matt confirmed root and `ModConfig` only, 2026-11-17, and added the note for roles other than Admin (decision 9) the same day.

**Context:**

- `GET /config/directories` (`routers/config.py:393-429`) and `GET /config/files` (`:432-468`) take any authenticated key and do not look at the role. `list_directories` returns every subdirectory, hidden ones included (`services/config_files.py:104-139`).
- After ADR-1 a Monitor key can still list `Saves`, `Backups`, `Playerdata`, `Logs` and `Mods`, and read every `.json` file in them. `Playerdata/` holds the player list, bans and the whitelist: personal data about players. It is not a secret in the sense of ADR-2, so redaction by key name does not cover it.
- The files a Monitor needs for troubleshooting are the server's own configuration in the root of the server data directory (`serverconfig.json`, `servermagicnumbers.json`) and the mods' configuration under `ModConfig/`.

**Decision:**

1. **An allow-list for roles other than Admin.** They may list and read the root of the server data directory and the `ModConfig` directory with everything under it. `MONITOR_CONFIG_DIRECTORIES` is one constant holding `ModConfig`.
2. **Admin may list and read every directory,** as today, within ADR-1's `.json` rule.
3. **The check is on the resolved path.** The first part of the path relative to the server data directory, compared with `casefold()`, must be in the allow-list, or the path must be a file directly in the root. A symlink in `ModConfig` that resolves into `Saves` is therefore refused.
4. **Listings are filtered, requests are refused.** For a role other than Admin, `GET /config/directories` for the root returns only the allowed directories that exist. Asking for the listing of, or a file in, any other directory is 403 `FORBIDDEN` (the existing code) with a message that the directory needs the Admin role. It is the same answer whether or not the directory or file exists.
5. **Order of checks:** path containment (400 `CONFIG_PATH_INVALID`), then the role's directories (403), then ADR-1's checks.
6. **Redacted is the default here too:** the service methods apply the allow-list unless the Admin role is passed.
7. **The web needs no rule of its own** for what it lists. The file browser shows what the API lists.
8. **Rejected: a deny-list** (`Saves`, `Backups`, `Playerdata`). A directory the game or a mod adds later would be open until someone noticed. **Rejected: redacting player files for Monitor.** There is nothing left worth showing in them.
9. **A note for roles other than Admin (Matt, 2026-11-17).** When the key's role is not Admin, the file browser (`web/src/features/settings/FileManagerPanel.tsx`) shows one short static line, "Some folders are only shown to Admin keys." It names no folder and gives no count, and it is shown whether or not anything is hidden. The role comes from the hook the web already uses for this, `useAuthMe()` (`web/src/api/hooks/use-auth-me.ts`; `SettingsPage.tsx:35-36` hides the Admin-only tabs with it). While the role is loading or unknown the note is not shown; with the Admin role it never is.

**Consequences:**

- A Monitor key can no longer learn the names of saves and backups or read player data through the manager.
- A mod that keeps configuration outside `ModConfig/` and the root is readable by Admin only. Adding a directory is a one-line change.
- A Monitor user is told that the list is not everything, without learning what is missing.
- Tests cover both roles for each of the three routes: root, `ModConfig`, a nested `ModConfig` path, `Playerdata` in another letter case, a missing forbidden directory, and a symlink out of `ModConfig`.

## ADR-4: `VS_GAME_VERSION` Is Removed

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-ms0`).

**Context:** see "`VS_GAME_VERSION`" above. The setting does nothing, and `.env.example` describes it as choosing the game version to install, which it does not.

**Decision:**

1. **Remove it.** `Settings.game_version` goes, with the lines in `docker-compose.yaml`, `docker-compose.dev.yaml`, `.env.example` and `scripts/worktree-setup.sh`, and the rows in `architecture/project-structure-boundaries.md`.
2. **Setting it stays harmless.** `Settings` reads only declared fields from the environment, so a deployment that still sets `VS_GAME_VERSION` starts as before. A test sets it and constructs `Settings` to pin that. This is why the removal is not a breaking change.
3. **`test_mod_service.py:2141`** sets the variable to prove compatibility ignores it; the test keeps its meaning and its docstring is adjusted.
4. **The commit is `fix(docker):`** with a subject for users ("VS_GAME_VERSION is no longer set or documented; it had no effect"), so the removal is in the release notes.
5. **Rejected: giving it a purpose** (for example the channel preselected in the installer). Nobody asked for that feature, the version browser already defaults sensibly, and an environment variable that sets a form's initial selection would be the only one of its kind.

**Consequences:** One fewer documented variable that does nothing. No behaviour changes.

## ADR-5: The Web UI Gets a Key Only When `VS_API_KEY` Names One

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.2 (`VSS-9wv`), a story of its own since the maintainer's review. Changes Epic 15 ADR-5: the key no longer falls back to the Admin key. The scope is a maintainer decision (2026-11-16, "A plus C"); decisions 3 and 4 below were left to planning. The maintainer confirmed on 2026-11-17: the API starts and serves no key (decision 3), a key that matches no role is handled as today (decision 5), the documentation recommends the Monitor key first and the production example stays blank (decisions 6 and 7), and the change ships in the next pre-release or `0.1.0` with nothing special.

**Context:** see "The web UI's key" above. In the default deployment `/config.js` hands the Admin key to anyone who can load the page, and with it the game server password and every Admin action. That undoes the Monitor redaction of Story 17.5 and ADR-2 for anyone who can reach the web origin, and nothing tells the operator.

**Decision:**

1. **No fallback (maintainer decision, C).** `Settings.web_api_key` is `VS_API_KEY` when it is set and not blank, and otherwise the empty string. The Admin key is served only when `VS_API_KEY` is set to it explicitly.
2. **A warning whenever the web key is the Admin key (maintainer decision, A).** At start-up the API logs `web_api_key_is_admin_key` at warning level, with a hint that anyone who can load the web UI receives the Admin key and that `VS_API_KEY` can be the Monitor key, or the web origin put behind an authenticating proxy. The key is never logged.
3. **With `VS_API_KEY` unset or blank, the API starts and `/config.js` serves no key.** The body is `window.__VSM_CONFIG__ = {"apiKey": ""};` with the same headers as today, and the API logs `web_api_key_not_set` at warning level with the same hint. It does not refuse to start. Reasons:
   - The API process supervises the game server and auto-starts it (`main.py:117-141`). Refusing to start over a web UI setting takes the game server down on an image upgrade: a restart loop under Compose's `restart: unless-stopped`, `CrashLoopBackOff` in a cluster.
   - Using the API without the web UI is a valid deployment: scripts and monitoring send `X-API-Key` and never load the page. Refusing to start would force such a deployment to publish a key at `/config.js` that it has no use for, the opposite of this change.
   - `/healthz` and `/readyz` do not depend on any key, so probes keep passing and the operator finds a running service and a page that says what to set, instead of an exited container and a log to read.
   - It matches what the API already does: a `VS_API_KEY` that matches no role warns and starts (`main.py:103-108`). Only a missing Admin key refuses (`config.py:178-182`), a state in which nothing can work.
   - First run with only the Admin key set gives a running server and a page with the instruction.
4. **The web shows a full-page message when it has no key.** When `window.__VSM_CONFIG__?.apiKey` and `VITE_API_KEY` are both empty, the app renders a "No API key configured" screen instead of the router: it says to set `VS_API_KEY` on the server to the Monitor key (read-only) or the Admin key (full access) and restart, and that anyone who can open the page receives that key. Under the Vite dev server it also names `VITE_API_KEY` in `web/.env`. It makes no API request and opens no WebSocket. It has no field to enter a key; that is `VSS-2kdt`.
5. **Start-up states,** from one function that replaces `web_api_key_has_a_role()`:

   | `VS_API_KEY` | `/config.js` serves | Start-up log |
   |---|---|---|
   | unset or blank | `""` | warning `web_api_key_not_set` |
   | equals the Admin key | the Admin key | warning `web_api_key_is_admin_key` |
   | equals the Monitor key (and not the Admin key) | the Monitor key | none |
   | anything else | that value, as today | warning `web_api_key_matches_no_role`, as today |

6. **Documentation.** `README.md`, `.env.example`, `docker-compose.yaml` and `docker-compose.dev.yaml` say that the web UI needs `VS_API_KEY`, recommend the Monitor key or an authenticating proxy in front of the web origin, and say what setting it to the Admin key means.
7. **The dev stack keeps a working Admin UI.** `docker-compose.dev.yaml` changes its default to `VS_API_KEY=${VS_API_KEY:-${VS_API_KEY_ADMIN:-changeme}}`, so `just docker start` and the twelve E2E specs that rely on the stack's key behave as before; the stack logs the Admin key warning, which is correct for it. `docker-compose.yaml` keeps `${VS_API_KEY:-}`, with its comment changed: the production example does not hand out the Admin key by default. `scripts/worktree-setup.sh` already writes `VS_API_KEY`.
8. **E2E.** Story 19.2 adds one helper in `web/e2e/` that answers `/config.js` with a chosen key, and a new spec that answers it with an empty key and expects the message and no request to `/api/`. Story 19.7 moves every spec to the helper and removes the dead `localStorage` init scripts (ADR-14).
9. **This is a breaking change.** See "Release" below.
10. **Rejected: refusing to start** (reasons in decision 3). **Rejected: serving the Monitor key when `VS_API_KEY` is unset and a Monitor key exists.** It still hands out a key nobody asked to publish, and a UI that silently became read-only is harder to diagnose than a page that says what to set. **Rejected: a key field in the browser.** Out of scope (`VSS-2kdt`).
11. **One settings object, and an app that tests can construct (Matt, 2026-11-17).** Where Story 19.2 touches `main.py` it uses the cached `get_settings()` instead of a new `Settings()` (the lifespan at `:96`), and it builds the app through a function that takes the settings (an app factory; the module still exposes `app` built from `get_settings()` for the server). A test can then build the app with `VS_API_KEY` unset, set to the Admin key, the Monitor key or another value, and assert the warning and `/config.js` for each state both ways. Story 19.3 finishes the two import-time uses (ADR-7 decision 6). Replacing `Settings()` in the services is not part of this epic.

**Release:**

- The commit that makes the change is `feat(api)!:` with a `BREAKING CHANGE:` footer. `cliff.toml` prints the commit subject, not the footer, under **Breaking Changes**, so the subject has to carry the instruction: `feat(api)!: the web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key`.
- Every deployment that does not set `VS_API_KEY` today has to set it in the same upgrade, or its web UI shows the message. That includes the maintainer's cluster deployment, which is configured in a separate repository, does not set `VS_API_KEY` today and relies on an internal-only gateway. That repository is not changed by this epic; the change is one environment variable and belongs in the same release.
- While the version is `0.x` a breaking change bumps the minor version (`RELEASING.md`). The current version is `0.1.0-rc.4`, so the change lands before the first stable release.

**Consequences:**

- The default deployment no longer publishes the Admin key. An operator who wants the old behaviour sets one variable and sees a warning on every start.
- An upgraded deployment that sets nothing has a web UI that shows a set-up message until the variable is set. The API, the game server and API clients are unaffected.
- Whatever key `VS_API_KEY` names is still handed to anyone who can load the page. The login that ends that is `VSS-2kdt`.
- API tests cover `/config.js` and the start-up log for the four states of decision 5.

## ADR-6: A Content-Security-Policy Header on the Web UI's Pages, Enforced

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.3 (`VSS-3qb8`, `VSS-my4c`). The maintainer confirmed on 2026-11-17: enforced, with `VS_CSP_MODE`, and the three other headers. Decision 14 was added in the revision.

**Context:** see "Content-Security-Policy" above. The page holds an API key in `window.__VSM_CONFIG__`, renders mod descriptions written by mod authors, and has no policy that would stop an injected script.

**Decision:**

1. **The API sets the header, on the frontend's responses only.** `register_frontend` adds it to every `serve_spa` response, since any path can return `index.html`. It is not a global middleware: `/docs` and `/redoc`, where they are served (ADR-7), need a CDN and an inline script, and JSON responses gain nothing from it.
2. **Not a `<meta>` tag.** `frame-ancestors` is ignored in a `<meta>` policy, report-only mode does not exist there, and `index.html` is shared with the Vite dev server.
3. **The policy:**

   ```
   default-src 'self';
   script-src 'self';
   style-src 'self' 'unsafe-inline';
   img-src 'self' data: https:;
   font-src 'self';
   connect-src 'self';
   frame-src 'none';
   object-src 'none';
   base-uri 'self';
   form-action 'self';
   frame-ancestors 'none'
   ```

4. **`script-src 'self'`** is the directive that matters: no inline script, no `eval`, no other origin. Both scripts in `index.html` are same-origin files, so the classic `/config.js` script is compatible as it is.
5. **`style-src` allows `'unsafe-inline'`.** xterm.js, sonner, Radix's scroll lock and next-themes create `<style>` elements at run time, and mod descriptions keep inline `style` attributes. A nonce would need the static `index.html` rewritten per response and libraries that accept one (xterm.js and sonner do not). An injected style is a much smaller risk than an injected script.
6. **`img-src 'self' data: https:`.** Logos and screenshots come from `https://moddbcdn.vintagestory.at`, and descriptions load images from any host, so a host list would break descriptions. `data:` covers the icon in `index.css` and data images in descriptions. Images over plain `http:` in descriptions stop loading; decision 14 says what the page shows instead.
7. **`connect-src 'self'`** covers the API and, in current browsers, the WebSockets to the same host (`/api/v1alpha1/console/ws` and the log stream), because `'self'` matches `ws:` and `wss:` for the page's host. Story 19.3 confirms the console and log stream in a browser with the policy enforced; if a supported browser refuses them, the fallback is to add `ws:` and `wss:` sources for the request's host.
8. **`frame-src 'none'` and `frame-ancestors 'none'`.** The trailer is a link (Epic 18 ADR-2), so the app embeds nothing, and the admin UI has no reason to be framed. `X-Frame-Options: DENY` is sent as well for older browsers.
9. **Two more headers on the same responses:** `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. With the second, no request the page starts (logos, description images, links) carries the manager's address.
10. **Enforced by default, with one setting.** `VS_CSP_MODE` is `enforce` (default), `report-only` (the same policy in `Content-Security-Policy-Report-Only`) or `off`; any other value fails start-up validation like the other settings. There is no `report-uri`: the project has no collector, and a report endpoint would be an unauthenticated write. Report-only alone would protect nothing, since nobody reads the browser console of a working page; the setting exists so an operator can get out of trouble without a new image.
11. **The Vite dev server (`just dev-web`) gets no policy.** Its pages are served by Vite, which needs inline scripts and a WebSocket for hot reload. The policy is tested where it is served: the Docker stack.
12. **The inline script of next-themes** is checked in the browser by the story. If the browser reports a violation for it, the story adds that script's hash to `script-src` and records the hash and the next-themes version; it does not add `'unsafe-inline'` to `script-src`.
13. **How it is tested.** An API test for the header in each mode and for its absence on `/api/...`, `/healthz` and, in debug mode, `/docs`. An E2E spec against the Docker stack that opens the dashboard, the console (WebSocket connected), the mod browser, a mod detail page with a gallery and a description with images, the installed list, the settings and the version page, in both themes, collects `securitypolicyviolation` events and console errors and expects none; and a control that injects an inline script and expects it blocked. The spec stubs the mod database answers it needs, so it runs in CI (ADR-14).
14. **Description images the policy would block are replaced by the sanitizer (`VSS-my4c`).** In the DOMPurify hook of `web/src/lib/mod-description.ts`, an `<img>` whose `src` is not an `https:` URL or a `data:image/` URL is replaced by a short muted text built from its `alt` ("Image not shown: `<alt>`", or "Image not shown" without one). The rule does not depend on how the page itself is served, the URL is not rewritten to `https` (that would be a guess), and no request is made for the image. This keeps a broken-image icon and a policy violation out of the page.
15. **Rejected: a host list for images,** which breaks description images. **Rejected: a nonce-based policy** (decision 5). **Rejected: report-only as the default** (decision 10).

**Consequences:**

- An injected script does not run, and the page cannot be framed.
- `img-src https:` still lets a page that is already compromised leak data in an image URL, and `'unsafe-inline'` styles remain. The policy does not replace the login of `VSS-2kdt`.
- A deployment whose proxy injects scripts or styles from another origin into the page breaks until the proxy is changed or `VS_CSP_MODE` is set. A proxy that adds its own policy narrows this one; both apply.
- A new dependency that needs another origin, `eval` or an inline script fails the E2E spec, which is the intended signal.

## ADR-7: The API Documentation Pages Are Served Only in Debug Mode

**Status:** Accepted (Epic 19 revision, 2026-11-17). Implemented by Story 19.3 (`VSS-5mes`). Matt, 2026-11-17: not marked breaking, but the release notes must name it, so its commit is a `feat(api)` or `fix(api)` subject saying the docs pages need `VS_DEBUG=true`.

**Context:**

- `FastAPI(...)` is created without `docs_url`, `redoc_url` or `openapi_url` (`main.py:165-170`), so `/docs`, `/redoc` and `/openapi.json` are served to anyone who can reach the API, without a key. The two pages load their scripts and styles from a public CDN and use an inline script.
- The schema is not secret (the repository is public), but the pages make every deployment load third-party scripts on an origin that also serves a page holding an API key, and they are the one part of the origin ADR-6's policy does not cover.
- The API already gates development-only routes on `VS_DEBUG` at start-up (`main.py:219-221`, the RBAC test router). The dev stack sets `VS_DEBUG=true` (`docker-compose.dev.yaml:22`); the production example defaults it to `false`.
- `api/tests/test_version.py:24` reads `/openapi.json`.

**Decision:**

1. **Off unless debug.** `docs_url`, `redoc_url` and `openapi_url` are `None` unless `Settings().debug` is true when the app is created. There is no new setting.
2. **In debug mode they are served as today,** from the CDN and without ADR-6's policy, which stays on the web UI's pages only. Debug mode is for development.
3. **What a request gets when they are off.** In the image, `/docs`, `/redoc` and `/openapi.json` fall through to the web UI's fallback and return the app's page, with ADR-6's headers; without the built frontend they are 404.
4. **The README says** that the API documentation is at `/docs` when `VS_DEBUG=true`.
5. **Rejected: requiring a key.** A browser opening `/docs` cannot send `X-API-Key`; it would need the key in the URL or a cookie, which is the login of `VSS-2kdt`. **Rejected: serving the assets from the image.** It adds vendored files to keep current and still serves the pages to everyone. **Rejected: a separate `VS_API_DOCS` setting.** One more variable for something a developer already gets from debug mode.
6. **Built through the app factory (Matt, 2026-11-17).** The documentation routes are set where the app is constructed from its settings (ADR-5 decision 11), so a test builds one app with debug on and one with it off and asserts the three paths in each. Story 19.3 also moves the two remaining import-time `Settings()` calls in `main.py` (`:177` for CORS, `:219` for the RBAC test router) to the same settings object; the RBAC router gets the same two-way test.

**Consequences:**

- The default deployment serves no page that loads scripts from another origin, so every HTML page it serves is under ADR-6's policy.
- A client that fetched `/openapi.json` from a production deployment no longer can; it is available from a debug instance. This is listed with the API contract changes.
- Tests: the three paths with debug off and on, each from an app built with those settings; `test_version.py` builds its app in debug mode or reads the version another way.

## ADR-8: One File-Name Check for Every Mod File Operation

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.4 (`VSS-40ja`, `VSS-macf`, `VSS-52fy`). Extends Epic 18 ADR-4 and replaces its decision 6.

**Context:** see "Mod files" above. Four operations put a file name into the mods directory: install, version change, enable and disable. One checks fully and exactly (install), one checks partly and answers 500 (version change), two do not check.

**Decision:**

1. **One helper answers "is this name taken by something else".** Given the names an operation will create and the mod's own current file name (none for an install), it raises `ModFileConflictError` when any of the names, compared with `casefold()`, matches an entry in the mods directory listing or a key in the mod state, other than the mod's own file.
2. **The directory is listed, not probed.** Comparing against `iterdir()` names finds a file that differs only in case on a case-sensitive volume and a dangling symlink, and gives the same answer on every filesystem.
3. **Names checked per operation:**

   | Operation | Names that must be free |
   |---|---|
   | Install | `<name>`, `<name>.disabled` (as Epic 18 ADR-4, now without case) |
   | Enable | the file name without `.disabled` |
   | Disable | the file name with `.disabled` |
   | Version change | `<new name>` and `<new name>.disabled`, except the mod's own file |

4. **A version change whose new name equals the mod's own name ignoring case** takes the existing same-file path (the old file is kept aside as `.bak`, `services/mods.py:1016`): `same_file` compares with `casefold()`. Otherwise, on a volume that ignores case, the new file would replace the old one and the step that deletes the old file (`:1044`) would delete the new one.
5. **Checked before anything is written, with no `await` after it.** All four placements are synchronous, so nothing can create the file between the check and the rename (Epic 18 ADR-4 decision 3).
6. **One error.** `ModFileConflictError` gains the operation, so its message reads "Cannot install", "Cannot enable", "Cannot disable" or "Cannot change the version of" `'<slug>'`: "a file named `<name>` already exists in the mods directory." Every route answers 409 `MOD_FILE_CONFLICT`:
   - `POST /mods` (unchanged, now also for a name that differs only in case);
   - `POST /mods/{slug}/enable` and `/disable` (new; before, the rename replaced the file);
   - `PUT /mods/{slug}/version` (was 500 `MOD_VERSION_CHANGE_FAILED`; that code stays for real failures to place the file or save state).
7. **Update All.** `ModFileConflictError` is added to the errors the loop catches per mod (`services/mod_updates.py:422-438`), so one mod's conflict is a `failed` item with the message and the run continues. Without that the new error would abort the run.
8. **Nothing is changed on a refusal:** no rename, no `.tmp`, no state change, no pending restart.
9. **Working files are not names.** The helper looks only at the final names of decision 3. The manager's temporary and backup files, and the case of a mod whose own file is missing, are ADR-9.

**Consequences:**

- No mod operation can replace another mod's file, and the answer no longer depends on whether the volume ignores case.
- The web shows the API's message for each of the four operations; Story 19.4 confirms that for enable, disable and version change.
- Tests compare the other file's bytes and the mod state before and after, for each operation, for the exact name, a name that differs in case, the `.disabled` twin, a state entry without a file and a dangling symlink, and run on a case-sensitive directory.

## ADR-9: A Missing Mod File Is an Error with a Code, and Start-Up Recovers Interrupted Operations

**Status:** Accepted (Epic 19 revision, 2026-11-17). Implemented by Story 19.4 (`VSS-yhmt`, `VSS-uoxl`). Matt confirmed warn-only for other `.tmp` and `.bak` files, 2026-11-17; a visible indication and cleanup is follow-up `VSS-hv60`. `VSS-uoxl` stays open until Story 19.5 (ADR-10), which rides with it and runs directly after this recovery.

**Context:**

- `enable_mod` and `disable_mod` rename the mod's own file without checking that it exists (`services/mods.py:749`, `:807`). When the file was removed by hand, `rename` raises `FileNotFoundError`, which no route catches: a 500. `sync_state_with_disk` exists (`services/mod_state.py:492`) and nothing in `api/src` calls it, so the state can name a file that is gone.
- `_place_install` copies to `<name>.tmp` and renames (`:1297-1311`). `_apply_version_change` copies to `<new name>.tmp`, and for a release with the mod's own file name first moves the installed file to `<name>.bak` (`:1014-1023`), which is deleted only after the state is saved (`:1049-1055`). The cleanup paths run on `OSError`; a process that is killed in between leaves the `.tmp` or `.bak` file. No code removes them later.
- A `.bak` file can be the only good copy of a mod: after the installed file was moved aside and before the new one was renamed into place.
- An admin can keep files of their own named `something.bak` or `something.tmp` in the mods directory. The manager cannot tell those from its own leftovers by name.
- ADR-8's check compares the names an operation will create, `<name>` and `<name>.disabled`. A leftover `<name>.tmp` or `<name>.bak` is never one of those, so it does not make a name "taken".

**Decision, missing file (`VSS-yhmt`):**

1. **Checked before the rename.** `enable_mod` and `disable_mod` raise a new `ModFileMissingError` when the mod's own file is not a regular file in the mods directory. The check sits beside ADR-8's, before anything is written.
2. **409 `MOD_FILE_MISSING`** (new code) on both routes, with a message that says what to do: "Cannot enable '`<slug>`': its file `<name>` is no longer in the mods directory. Remove the mod and install it again." 409 because the request is valid and the server's state is in the way, as for `MOD_FILE_CONFLICT`; 404 `MOD_NOT_INSTALLED` would say the mod is unknown, and the Installed list shows it.
3. **Nothing is changed.** The state entry stays, so the admin can remove the mod through the manager; `remove_mod` already skips a file that is not there (`services/mods.py:857-858`).
4. **Idempotent cases stay first:** enabling an enabled mod and disabling a disabled one still succeed without touching the file.

**Decision, leftovers (`VSS-uoxl`):**

5. **The manager's working files get their own suffixes.** From this story the temporary copy is `<name>.vsm-tmp` and the kept-aside original is `<name>.vsm-bak`. Nothing else in the mods directory uses those suffixes, so the manager can clean up without guessing.
6. **Recovery runs once at start-up,** before any mod operation, with the mod state as the source of truth:
   - every `*.vsm-tmp` is deleted: it is an unplaced copy and the download cache still has the source;
   - for each `<name>.vsm-bak`: if `<name>` is missing, the backup is renamed back to `<name>`; if `<name>` exists and its `modinfo.json` version equals the state's version for that file, the backup is deleted (the change completed); otherwise the backup replaces `<name>` (the change did not complete, so the state still describes the original).
   - each action is logged with the file name; a failure is logged and does not stop start-up.
7. **Old-style leftovers are reported, not removed.** `*.tmp` and `*.bak` files in the mods directory, which an earlier version may have left and an admin may have put there, are logged once at start-up at warning level with their names. The manager never deletes or restores them.
8. **The name check and the cleanup agree.** ADR-8's helper looks only at the final names an operation will create. Working files are never such a name, are cleared before the first operation, and a leftover one from the same name is overwritten by the next copy; so a leftover cannot cause a `MOD_FILE_CONFLICT`, and the story has a test for that.
9. **Rejected: deleting every `.tmp` and `.bak` at start-up.** It would delete an admin's own backup, and a `.bak` can be the only copy of an installed mod. **Rejected: only listing leftovers for the admin.** The state after a crash would stay wrong until someone read the log.

**Consequences:**

- Enabling or disabling a mod whose file is gone gives an answer the admin can act on.
- After a crash during an install or version change, the next start leaves each mod's file matching its state and no working file behind.
- Tests kill the operation at each step (after the copy, after the move aside, after the rename, after the state save) by building the directory by hand, then run recovery and compare files and state.

## ADR-10: The Mod State Is Reconciled with the Mods Directory Once at Start-Up

**Status:** Accepted (Matt, 2026-11-17). Implemented by Story 19.5, which has no bead of its own and rides with `VSS-uoxl`. No endpoint and no button.

**Context:**

- `ModStateManager.sync_state_with_disk` (`services/mod_state.py:492-547`) adds a state entry for each mod file in the directory that the state does not know and removes each entry whose file is not found. Nothing in `api/src` calls it, so a mod copied into the directory by hand never appears in the Installed list, and an entry whose file was deleted by hand stays (the case ADR-9 answers with `MOD_FILE_MISSING`).
- It finds files with `scan_mods_directory` (`:465-490`), which returns regular files whose names end in `.zip` or `.zip.disabled`. The manager's working files (`<name>.vsm-tmp`, `<name>.vsm-bak`) and other `.tmp` and `.bak` files do not end that way, so the scan already leaves them out.
- As written it is not safe to call at start-up:
  - `import_mod` (`:507`) is not guarded. One archive that cannot be read raises and would stop the API from starting.
  - Removal is decided by "not in the scan" (`:531`), not by "the file is gone". An entry for a file the manager installed under a name the scan does not match (a release file that is not a `.zip`) would be removed although its file is there.
  - A file added by hand whose mod ID is already installed would become a second entry for that mod ID. Operations look a mod up by ID (`get_mod_by_slug`, `:149`), and with two copies the game loads one and the API reports the other (Story 14.0).
  - It logs a line per change at info level, and a summary only when something changed.

**Decision:**

1. **Called once, in the API's start-up,** after ADR-9's recovery of the manager's working files and before the game server is auto-started. It is not called per request, on a timer or from a route.
2. **What is added.** A regular file in the mods directory whose name ends in `.zip` or `.zip.disabled` (the existing scan), that the state does not know and whose `modinfo.json` can be read, gets a state entry: enabled unless the name ends in `.disabled`, version and mod ID from the archive, `installed_at` the time of the sync, no mod database asset ID.
3. **What is skipped,** each with one warning naming the file and never failing start-up:
   - an archive that cannot be read or has no usable `modinfo.json`;
   - a file whose mod ID is already in the state under another file (compared like the lock key); the entry the state has stays, and the warning says two files claim the mod;
   - anything the scan does not match is not looked at, which covers `.vsm-tmp`, `.vsm-bak`, `.tmp`, `.bak`, directories and other file types.
4. **What is removed.** A state entry whose file does not exist in the mods directory, checked per entry by its own file name and not by membership in the scan. An entry whose file is there stays whatever its name.
5. **Logging.** One line per entry added and per entry removed, with the file name and mod ID, and always one summary line with the numbers added, removed and skipped, also when all are zero.
6. **One save,** after all changes, and only when something changed. A failure to save is logged and does not stop start-up; the next start tries again.
7. **No restart flag and no update check.** The sync runs before the game server starts. A mod it adds has no stored update record and shows "Not checked yet" until the next check, as any mod without one does (Story 17.4).
8. **ADR-9 stays.** Between restarts a file can still be removed by hand, so `MOD_FILE_MISSING` remains the answer for that window.
9. **Why a story of its own.** Story 19.4 is at the six-task limit, the sync needs Story 19.4's recovery and suffixes in place first, and a change that deletes state entries at start-up deserves its own review.
10. **A missing mods directory changes nothing.** When the directory does not exist the sync removes no entry and logs a warning; a volume that is not there yet must not empty the state.

**Consequences:**

- A mod copied into the mods directory appears in the Installed list after the next restart of the manager, and an entry whose file was deleted disappears.
- Start-up reads `modinfo.json` from each archive the state does not know. With nothing new, it lists the directory and checks each entry's file.
- No API changes shape; the Installed list's content can change after a restart.
- Tests build a directory and a state by hand: a new enabled and a new disabled archive, an unreadable archive, a second file for an installed mod ID, a ghost entry, an entry for a non-zip file that exists, working files and `.bak` files, and an empty directory; each asserts the state, the log lines and that start-up continues.

## ADR-11: The Download Cache Is Keyed by File ID

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.4 (`VSS-n0qv`).

**Context:** see "Download cache" above. The cache key is the release's file name, the per-mod locks do not cover two different mods, and an install does not require the archive to be the mod it resolved. So two different mods whose releases share a file name can replace each other's cached copy, and two such downloads at once write one temporary file.

**Decision:**

1. **Layout.** A release is cached at `cache/mods/<fileid>/<safe_name>`. The mod database's file ID is what the download URL takes (`/download?fileid=<id>`), so it names one file of one mod; the mod ID adds nothing to the key. Keeping the file name as the last path part keeps `DownloadResult.filename = path.name` and every caller of it.
2. **One function gives the path.** `ModApiClient` exposes the cache path for a file ID and file name; `download_release_file` and `_acquire_release_archive` both use it, and `services/mods.py:1147` stops building the path itself.
3. **A temporary file per download.** Each download writes to its own uniquely named `.tmp` file in the target directory and renames it into place, so two downloads of the same file never share a temporary file, whatever locks are held.
4. **Eviction follows the layout.** `CacheEvictionService` finds `*.zip` and `*.cs` in the subdirectories, removes a directory it has emptied, and removes `.tmp` files older than one hour (longer than `DOWNLOAD_TIMEOUT`, 120 s).
5. **Files from the old layout are deleted once.** When the client is created, regular files directly under `cache/mods` are removed and their number is logged. They are cache; nothing reads that layout any more, and with eviction disabled (`VS_MOD_CACHE_MAX_SIZE_MB=0`) they would otherwise stay for ever.
6. **The install's own archive check is not changed.** `install_mod` still does not require the archive's mod ID to equal the one it resolved (an archive may name its mod ID differently from the mod database; the install checks that ID and goes on, `services/mods.py:1238-1244`). The file ID key is what removes the wrong-archive case: the path an install reads can only hold the file it asked for.
7. **Rejected: a key of mod ID plus file name.** The mod ID is not known for every download path in the same spelling, and the file ID is already unique. **Rejected: one global download lock.** It would make every install wait for any other download.

**Consequences:**

- Two mods with the same release file name each keep their own cached copy, and concurrent downloads cannot mix bytes.
- The first start after the upgrade empties the old cache; the next install or version change of each mod downloads again.
- Tests: two file IDs with one file name give two paths; two concurrent downloads of one file ID both end with a complete file; eviction counts, evicts and tidies the new layout; the old files are removed at start.

## ADR-12: Logo, Homepage and Source URLs Go Through the URL Policy Module

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.6 (`VSS-2zis`). Replaces Epic 18 ADR-1 decision 6 ("`logo_url` keeps passing through unchecked"). The maintainer confirmed on 2026-11-17 that `http:` homepage and source links are dropped.

**Context:** see "Mod database data" above. Three author-controlled URLs reach `src` and `href` unchecked, and logo requests carry a referrer.

**Decision:**

1. **Logo: the image rule.** `logo_url` on the lookup and on each browse item is `mod_image_url(...)`: kept only as an `https` URL on `MOD_MEDIA_HOSTS`, otherwise `null`. The web already draws a placeholder for a mod without a logo.
2. **Browse checks the items it returns,** in the function that builds a browse item, not the 9,636 items of the cached listing.
3. **Homepage and source: a link rule.** A new `external_link_url` in `services/mod_media.py` keeps a URL only when it starts with `https://`, has no control character, space or backslash, parses, has a host and no user info, and is at most 2,048 characters. Any host and any port are allowed. Anything else, including `""`, is `null`.
4. **`https` only.** No `http:` homepage or source URL was seen in the sample. An author's `http:` link is dropped; the "ModDB Page" link is always there.
5. **The web trusts the API's values,** as for screenshots (Epic 18 ADR-1 decision 5), and adds `referrerPolicy="no-referrer"` to the three logo `<img>` elements. Story 19.3 also sends `Referrer-Policy: no-referrer` for the page; the attribute covers the Vite dev server and a proxy that drops the header.
6. **A dropped URL is logged at debug level** with the mod slug and the field name, never the URL, and never fails a lookup or a browse request.

**Consequences:**

- No field of the mod responses can carry a `javascript:`, `data:` or `http:` URL into `src` or `href`.
- If the mod database moves its images to another host, logos become placeholders until `MOD_MEDIA_HOSTS` changes, as for screenshots.
- `homepage_url` and `source_url` are `null` where they were `""`.

## ADR-13: One Guarded Fetch for Mod Database JSON, and Shared Fetches for the Listing and the Game Version List

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.6 (`VSS-ce0h`, `VSS-0lkb`). Extends Epic 17 ADR-1. Decision 5 covers the full listing since the revision.

**Context:** see "Mod database data" above. Two of four fetchers guard their bodies, each in its own copy; the browse listing, the most used, does not.

**Decision:**

1. **One helper in `ModApiClient`** performs a GET and returns the body as a JSON object or raises `ExternalApiError`: for a timeout, a connection or other HTTP client error, a body that is not JSON, and a body that is JSON and not an object. `get_mod`, `get_all_mods`, `_fetch_mods_by_version` and `get_game_versions` use it.
2. **Each fetcher keeps its own rules** for the HTTP status and the `statuscode` string, which differ today (`get_mod` reads the body of any HTTP status; the two that check for HTTP 200 keep doing so). The helper does not change them.
3. **Routes do not change.** `ExternalApiError` is already 502 `EXTERNAL_API_ERROR` on every mod route, so a malformed mod database body becomes 502 where it was 500.
4. **Nothing malformed is cached.** A failed fetch leaves the previous cache entry and its time as they were.
5. **One fetch at a time for the game version list and for the full listing (`VSS-0lkb`).** `get_game_versions` and `get_all_mods` each keep their running fetch as a task, and every caller that finds the cache cold awaits that task, shielded, as `_version_fetch` does for the filtered listings (`:741-755`, `:776-777`). One small helper holds the pattern for all three. A failed fetch is reported to every waiter and is not kept.
6. **`force_refresh=True` joins a fetch that is already running** instead of starting a second one; a fetch in flight is as fresh as a new one. With no fetch running it starts one, as today.

**Consequences:**

- No body the mod database can send makes a mod route answer 500.
- A cold start with several browser tabs makes one `/api/gameversions` request and one `/api/mods` request (about 4 MB) instead of one per tab.
- Tests feed each fetcher an HTML body, an empty body, `[]`, `"text"` and `null`, and assert `ExternalApiError` and an unchanged cache; for the game version list and for the full listing, a test with several concurrent cold calls asserts one request, that a failure reaches all of them and that the next call fetches again.

## ADR-14: CI Runs the E2E Specs That Need Nothing Outside the Stack

**Status:** Accepted (Epic 19 revision, 2026-11-17). Implemented by Story 19.7 (`VSS-wenx`). Matt confirmed untagged tests only, 2026-11-17, and added the seeded `serverconfig.json` (decision 10) the same day. Comes last: it uses Story 19.2's key helper and runs Story 19.3's policy spec.

**Context:**

- `.github/workflows/ci.yml` has four jobs: API tests, web tests and build, release scripts (with `just lint-workflows`, actionlint) and a Docker image build that does not run the image. No job runs `web/e2e/` (18 specs) or `api/tests/e2e/`.
- `just test-e2e-web` builds and starts the dev Compose stack, waits for `/healthz`, runs Playwright and stops the stack (`Justfile:63-90`). `web/playwright.config.ts` already has CI settings (`forbidOnly`, two retries, one worker) and takes the stack's address from `E2E_BASE_URL`.
- Fifteen specs still add a `localStorage.setItem('apiKey', ...)` init script (17 occurrences), which the web stopped reading in Story 17.5.
- The specs differ in what they need. Some stub every API answer with `page.route`. Some read the live mod database through the stack (browse, mod detail, install). Some need a game server that is installed or has run (`settings-*`, `monitor-password-redaction`, `file-browser-navigation`). `mod-install-release` and `installed-status` install real mods.
- A fresh stack in CI has no game server, and installing one downloads the game from the vendor on every run.

**Decision:**

1. **A new `e2e` job in `ci.yml`,** on the same triggers as the other jobs. It builds the image with the build cache the `docker` job already fills, loads it, starts one container from it with an empty data directory and placeholder keys in the job's `env` (an Admin key, a Monitor key, and `VS_API_KEY` set to the Admin key, as Story 19.2 requires for a working page), waits for `/healthz`, installs Playwright's Chromium, and runs the suite. No game server is installed or started.
2. **Specs say what they need with Playwright tags.** `@moddb`: needs the live mod database. `@game-server`: needs a game server that is installed or has run. `@install`: installs or removes a real mod. A spec or a single test carries the tags that apply; a test with no tag needs only the stack.
3. **CI runs the untagged tests,** with `--grep-invert` on the three tags. The tagged tests still run locally with `just test-e2e-web`, as today. A `just` recipe holds the CI invocation so the same command runs on a developer's machine.
4. **Why not the live mod database in CI.** A pull request would fail when the mod database is slow or down, and the job would send its traffic on every push. **Why not a game server in CI.** It is a large download from the vendor per run; the settings specs get what they need from a seeded file instead (decision 10).
5. **New specs in this epic are written to run in CI:** the no-key spec (Story 19.2) and the policy spec (Story 19.3) stub the mod database answers they need.
6. **Every spec gets its key through the helper of Story 19.2,** and the dead `localStorage` init scripts are removed from all fifteen specs.
7. **The job is required like the others,** and uploads the Playwright report as an artifact when it fails. Actions are pinned by commit, as in the rest of the workflow, and `just lint-workflows` passes.
8. **`api/tests/e2e/`** (one health test) runs in the same job against the same container.
9. **Rejected: recording mod database answers** for the tagged specs. It is the right next step and a larger piece of work than this bead; it is a follow-up.
10. **A seeded `serverconfig.json` (Matt, 2026-11-17).** Before the container starts, the job copies a fixture `serverconfig.json` into the data directory at `serverdata/serverconfig.json`. The fixture is a file in the repository under `web/e2e/fixtures/`: a configuration as the game writes it, with made-up values and no data from any real server. The game settings are read from that file alone (`services/game_config.py:470-511`), so the specs that only need the settings to exist can run without a game server: `settings-desktop-layout`, `settings-empty-values`, `settings-as-saved` and `monitor-password-redaction`. The story runs each against the seeded stack; a test that passes carries no tag, and a test that turns out to need an installed or running game server keeps `@game-server` with a one-line reason. The fixture's values are what the specs expect of a fresh server (for example an empty password where `settings-empty-values` needs one). `@moddb`, `@game-server` and `@install` stay local-only.

**Consequences:**

- Every pull request starts the built image and drives the web UI in a browser: the page loads with a key, the no-key screen, the policy, the layouts and the stubbed flows.
- The settings pages are covered in CI through the seeded file. The mod database flows, real installs and anything that needs a running game server stay local-only.
- The job adds an image build (cached) and a browser download to each run.
