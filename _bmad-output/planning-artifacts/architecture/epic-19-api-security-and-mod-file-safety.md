# Epic 19: API Security and Mod File Safety - Architecture Decisions

Decisions from the Epic 19 course correction (2026-11-17). Epic 19 has no preparation story. Each decision was checked by reading the code at commit `048fea9` (`main` after Epic 18, release `v0.1.0-rc.4`), and file and line references are to that commit; API paths are under `api/src/vintagestory_api/`. The mod database facts were checked on 2026-11-16 with unauthenticated requests to the public API. Where a story has to confirm something in a browser first, the ADR says so.

Decisions the maintainer made before planning are marked "maintainer decision" and are not reopened here: the scope of `VSS-9wv` (a warning plus no Admin key by default, a breaking change), and that a login (`VSS-2kdt`) is a separate follow-up.

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
- E2E: all 18 specs in `web/e2e/` take the Admin key from the test process's own `VS_API_KEY_ADMIN` (default `changeme`) for direct API calls. Six specs answer `/config.js` themselves with `page.route` (`layout-widths`, `mod-detail-media`, `settings-desktop-layout`, `settings-empty-values`, `settings-as-saved`, `monitor-password-redaction`). The other twelve rely on the stack's own `/config.js` handing the page the Admin key; their `localStorage.setItem('apiKey', ...)` init scripts have done nothing since Story 17.5. No GitHub workflow runs the E2E specs.

**`VS_GAME_VERSION`.** `Settings.game_version` (`config.py:24`) is read by nothing in `api/src` since `VSS-tpe`; compatibility uses the installed server version (`services/mods.py:101`, `:302`). It is still set in `docker-compose.yaml:22`, `docker-compose.dev.yaml:21` and `scripts/worktree-setup.sh:61`, and described in `.env.example:20-23` as "VintageStory game version to install", which is false: the version to install is chosen in the web UI. `Settings` has no `env_file` and reads only declared fields from the environment, so an environment variable without a field is ignored.

**Content-Security-Policy.**

- Nothing sets one. The API registers CORS, CORS logging and request context middleware (`main.py:186-200`); `web/index.html` has no CSP `<meta>`; `web/vite.config.ts` sets no headers.
- The built `index.html` has two scripts, both same-origin files: the module bundle (`/assets/index-*.js`) and the classic `<script src="/config.js">` (`web/index.html:13`). It has no inline script and no inline style. Styles are one linked stylesheet per chunk.
- The frontend is served by `register_frontend` (`main.py:246-278`): `/assets` as static files, `/config.js`, and `serve_spa` for every other path, which returns `index.html` for any path that is not a file (`:275-278`).
- FastAPI's `/docs` and `/redoc` are on (no `docs_url` in `FastAPI(...)`, `main.py:165-170`). They load Swagger UI from a CDN and use an inline script.
- In the image the web calls the API on its own origin (`VITE_API_BASE_URL=""`, `Dockerfile:28`), and both WebSockets are built from `window.location` (`web/src/hooks/use-console-websocket.ts:88`, `use-log-stream.ts:92`).
- Runtime style injection: `@xterm/xterm`, `sonner`, `react-style-singleton` (Radix scroll lock) and `next-themes` each create `<style>` elements (`createElement("style")` in their published builds). Mod descriptions are inserted as sanitized HTML (`ModDetailPage.tsx:785`) and keep inline `style` attributes and `<img>` from any host (`web/src/lib/mod-description.ts`). `web/src/styles/index.css:249` uses a `data:` SVG as an image.
- `next-themes` renders an inline `<script>` element through React. Whether a browser tries to run it in a client-rendered page was not established by reading; Story 19.2 confirms it.
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
- `get_game_versions` has no shared fetch: every request that finds the cache cold makes its own request (`:948-952`). The filtered listings share one fetch per tag (`_version_fetch`, `:741-755`, awaited with `asyncio.shield`, `:776-777`).

## Mod Database Facts (checked 2026-11-16)

- Listing, `GET /api/mods`: 9,636 items. `logo` is an `https://moddbcdn.vintagestory.at/` URL for 6,531 and `null` for 3,105. No other scheme or host.
- Entry, `GET /api/mod/{slug}`, for the 60 most downloaded mods: `logofilename` is an `https://moddbcdn.vintagestory.at/` URL for 55 and `null` for 5. `homepageurl` is an `https` URL for 33, `""` for 23 and `null` for 4. `sourcecodeurl` is an `https` URL for 44 and `""` for 16. No `http:` URL and no other scheme was seen. The API does not promise that.

## ADR-1: The Config File Viewer Serves JSON Files Only and Refuses the Rest with an Error Code

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-633`). Extends Epic 17 ADR-4.

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
9. **Not changed:** `list_directories` still lists every subdirectory, and the Monitor role can still read every `.json` file. What Monitor sees inside them is ADR-2.
10. **Rejected: Admin may read any file type.** It keeps a second, untested path through binary and very large files for a need the console and log stream already meet. **Rejected: 415.** That status is about the request body's media type. **Rejected: an allow-list of directories.** Mod configuration lives where each mod puts it; the suffix and the role-based redaction are the rule.

**Consequences:**

- A request for a `.log`, `.vcdbs`, `.zip`, `.txt` or suffix-less path that was 200 or 500 is now 400. The web lists only `.json` files, so the UI does not ask for anything else.
- No request to this route can read more than 2 MiB into memory.
- Tests cover both roles for: a text file with another suffix, a binary file named `.json`, a directory, a directory named `x.json`, a symlink `x.json` to another type, a file one byte over the limit, a file with a byte order mark, and deeply nested JSON.

## ADR-2: Non-Admin Roles Get Config Files Redacted Recursively by Key Name

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-sg1`). Replaces the "top-level keys only" rule of Story 17.5; Epic 17 ADR-4 decisions 1, 2 and 4 to 6 stand.

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

## ADR-3: The Web UI Gets a Key Only When `VS_API_KEY` Names One

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.1 (`VSS-9wv`). Changes Epic 15 ADR-5: the key no longer falls back to the Admin key. The scope is a maintainer decision (2026-11-16, "A plus C"); decisions 3 and 4 below were left to planning.

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
8. **E2E.** One helper in `web/e2e/` answers `/config.js` with a chosen key; the six specs that carry their own copy use it, and the dead `localStorage.setItem('apiKey', ...)` init scripts are removed from the specs the story touches. A new spec answers `/config.js` with an empty key and expects the message and no request to `/api/`.
9. **This is a breaking change.** See "Release" below.
10. **Rejected: refusing to start** (reasons in decision 3). **Rejected: serving the Monitor key when `VS_API_KEY` is unset and a Monitor key exists.** It still hands out a key nobody asked to publish, and a UI that silently became read-only is harder to diagnose than a page that says what to set. **Rejected: a key field in the browser.** Out of scope (`VSS-2kdt`).

**Release:**

- The commit that makes the change is `feat(api)!:` with a `BREAKING CHANGE:` footer. `cliff.toml` prints the commit subject, not the footer, under **Breaking Changes**, so the subject has to carry the instruction: `feat(api)!: the web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key`.
- Every deployment that does not set `VS_API_KEY` today has to set it in the same upgrade, or its web UI shows the message. That includes the maintainer's cluster deployment, which is configured in a separate repository, does not set `VS_API_KEY` today and relies on an internal-only gateway. That repository is not changed by this epic; the change is one environment variable and belongs in the same release.
- While the version is `0.x` a breaking change bumps the minor version (`RELEASING.md`). The current version is `0.1.0-rc.4`, so the change lands before the first stable release.

**Consequences:**

- The default deployment no longer publishes the Admin key. An operator who wants the old behaviour sets one variable and sees a warning on every start.
- An upgraded deployment that sets nothing has a web UI that shows a set-up message until the variable is set. The API, the game server and API clients are unaffected.
- Whatever key `VS_API_KEY` names is still handed to anyone who can load the page. The login that ends that is `VSS-2kdt`.
- API tests cover `/config.js` and the start-up log for the four states of decision 5.

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

## ADR-5: A Content-Security-Policy Header on the Web UI's Pages, Enforced

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.2 (`VSS-3qb8`).

**Context:** see "Content-Security-Policy" above. The page holds an API key in `window.__VSM_CONFIG__`, renders mod descriptions written by mod authors, and has no policy that would stop an injected script.

**Decision:**

1. **The API sets the header, on the frontend's responses only.** `register_frontend` adds it to every `serve_spa` response, since any path can return `index.html`. It is not a global middleware: `/docs` and `/redoc` need a CDN and an inline script, and JSON responses gain nothing from it.
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
6. **`img-src 'self' data: https:`.** Logos and screenshots come from `https://moddbcdn.vintagestory.at`, and descriptions load images from any host, so a host list would break descriptions. `data:` covers the icon in `index.css` and data images in descriptions. Images over plain `http:` in descriptions stop loading.
7. **`connect-src 'self'`** covers the API and, in current browsers, the WebSockets to the same host (`/api/v1alpha1/console/ws` and the log stream), because `'self'` matches `ws:` and `wss:` for the page's host. Story 19.2 confirms the console and log stream in a browser with the policy enforced; if a supported browser refuses them, the fallback is to add `ws:` and `wss:` sources for the request's host.
8. **`frame-src 'none'` and `frame-ancestors 'none'`.** The trailer is a link (Epic 18 ADR-2), so the app embeds nothing, and the admin UI has no reason to be framed. `X-Frame-Options: DENY` is sent as well for older browsers.
9. **Two more headers on the same responses:** `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. With the second, no request the page starts (logos, description images, links) carries the manager's address.
10. **Enforced by default, with one setting.** `VS_CSP_MODE` is `enforce` (default), `report-only` (the same policy in `Content-Security-Policy-Report-Only`) or `off`; any other value fails start-up validation like the other settings. There is no `report-uri`: the project has no collector, and a report endpoint would be an unauthenticated write. Report-only alone would protect nothing, since nobody reads the browser console of a working page; the setting exists so an operator can get out of trouble without a new image.
11. **The Vite dev server (`just dev-web`) gets no policy.** Its pages are served by Vite, which needs inline scripts and a WebSocket for hot reload. The policy is tested where it is served: the Docker stack.
12. **The inline script of next-themes** is checked in the browser by the story. If the browser reports a violation for it, the story adds that script's hash to `script-src` and records the hash and the next-themes version; it does not add `'unsafe-inline'` to `script-src`.
13. **How it is tested.** An API test for the header in each mode and for its absence on `/api/...`, `/healthz` and `/docs`. An E2E spec against the Docker stack that opens the dashboard, the console (WebSocket connected), the mod browser, a mod detail page with a gallery and a description with images, the installed list, the settings and the version page, in both themes, collects `securitypolicyviolation` events and console errors and expects none; and a control that injects an inline script and expects it blocked.
14. **Rejected: a host list for images,** which breaks description images. **Rejected: a nonce-based policy** (decision 5). **Rejected: report-only as the default** (decision 10).

**Consequences:**

- An injected script does not run, and the page cannot be framed.
- `img-src https:` still lets a page that is already compromised leak data in an image URL, and `'unsafe-inline'` styles remain. The policy does not replace the login of `VSS-2kdt`.
- A deployment whose proxy injects scripts or styles from another origin into the page breaks until the proxy is changed or `VS_CSP_MODE` is set. A proxy that adds its own policy narrows this one; both apply.
- A new dependency that needs another origin, `eval` or an inline script fails the E2E spec, which is the intended signal.

## ADR-6: One File-Name Check for Every Mod File Operation

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.3 (`VSS-40ja`, `VSS-macf`, `VSS-52fy`). Extends Epic 18 ADR-4 and replaces its decision 6.

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
9. **Not changed:** a mod whose own file is missing when it is enabled or disabled still fails as today; that is not a conflict and is not part of these beads.

**Consequences:**

- No mod operation can replace another mod's file, and the answer no longer depends on whether the volume ignores case.
- The web shows the API's message for each of the four operations; Story 19.3 confirms that for enable, disable and version change.
- Tests compare the other file's bytes and the mod state before and after, for each operation, for the exact name, a name that differs in case, the `.disabled` twin, a state entry without a file and a dangling symlink, and run on a case-sensitive directory.

## ADR-7: The Download Cache Is Keyed by File ID

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.3 (`VSS-n0qv`).

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

## ADR-8: Logo, Homepage and Source URLs Go Through the URL Policy Module

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.4 (`VSS-2zis`). Replaces Epic 18 ADR-1 decision 6 ("`logo_url` keeps passing through unchecked").

**Context:** see "Mod database data" above. Three author-controlled URLs reach `src` and `href` unchecked, and logo requests carry a referrer.

**Decision:**

1. **Logo: the image rule.** `logo_url` on the lookup and on each browse item is `mod_image_url(...)`: kept only as an `https` URL on `MOD_MEDIA_HOSTS`, otherwise `null`. The web already draws a placeholder for a mod without a logo.
2. **Browse checks the items it returns,** in the function that builds a browse item, not the 9,636 items of the cached listing.
3. **Homepage and source: a link rule.** A new `external_link_url` in `services/mod_media.py` keeps a URL only when it starts with `https://`, has no control character, space or backslash, parses, has a host and no user info, and is at most 2,048 characters. Any host and any port are allowed. Anything else, including `""`, is `null`.
4. **`https` only.** No `http:` homepage or source URL was seen in the sample. An author's `http:` link is dropped; the "ModDB Page" link is always there.
5. **The web trusts the API's values,** as for screenshots (Epic 18 ADR-1 decision 5), and adds `referrerPolicy="no-referrer"` to the three logo `<img>` elements. Story 19.2 also sends `Referrer-Policy: no-referrer` for the page; the attribute covers the Vite dev server and a proxy that drops the header.
6. **A dropped URL is logged at debug level** with the mod slug and the field name, never the URL, and never fails a lookup or a browse request.

**Consequences:**

- No field of the mod responses can carry a `javascript:`, `data:` or `http:` URL into `src` or `href`.
- If the mod database moves its images to another host, logos become placeholders until `MOD_MEDIA_HOSTS` changes, as for screenshots.
- `homepage_url` and `source_url` are `null` where they were `""`.

## ADR-9: One Guarded Fetch for Mod Database JSON, and a Shared Game Version Fetch

**Status:** Accepted (Epic 19 planning). Implemented by Story 19.4 (`VSS-ce0h`). Extends Epic 17 ADR-1.

**Context:** see "Mod database data" above. Two of four fetchers guard their bodies, each in its own copy; the browse listing, the most used, does not.

**Decision:**

1. **One helper in `ModApiClient`** performs a GET and returns the body as a JSON object or raises `ExternalApiError`: for a timeout, a connection or other HTTP client error, a body that is not JSON, and a body that is JSON and not an object. `get_mod`, `get_all_mods`, `_fetch_mods_by_version` and `get_game_versions` use it.
2. **Each fetcher keeps its own rules** for the HTTP status and the `statuscode` string, which differ today (`get_mod` reads the body of any HTTP status; the two that check for HTTP 200 keep doing so). The helper does not change them.
3. **Routes do not change.** `ExternalApiError` is already 502 `EXTERNAL_API_ERROR` on every mod route, so a malformed mod database body becomes 502 where it was 500.
4. **Nothing malformed is cached.** A failed fetch leaves the previous cache entry and its time as they were.
5. **One fetch of the game version list at a time.** `get_game_versions` keeps the running fetch as a task and every caller that finds the cache cold awaits that task, shielded, as `_version_fetch` does for the filtered listings (`:741-755`, `:776-777`). A failed fetch is reported to every waiter and is not kept.
6. **Not changed:** the browse listing's own cold-cache behaviour (several first requests each fetch the 4 MB listing) is the same pattern and is reported as a follow-up; the bead names only the game version list.

**Consequences:**

- No body the mod database can send makes a mod route answer 500.
- A cold start with several browser tabs makes one `/api/gameversions` request.
- Tests feed each fetcher an HTML body, an empty body, `[]`, `"text"` and `null`, and assert `ExternalApiError` and an unchanged cache; a test with several concurrent cold calls asserts one request, and that a failure reaches all of them and the next call fetches again.
