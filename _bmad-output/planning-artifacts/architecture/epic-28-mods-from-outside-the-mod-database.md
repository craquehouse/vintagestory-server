# Epic 28: Mods From Outside the Mod Database - Architecture Decisions

Decisions from the Epic 28 course correction (2026-11-27). Epic 28 has no preparation story. Each fact below was checked by reading the code at commit `0da3d584` (`main`). API paths are under `api/src/vintagestory_api/`, web paths under `web/src/`.

The maintainer named the scope on 2026-11-27: install a mod that is not on the mod database by uploading its file or by giving an HTTPS link (GitHub or Forgejo release asset, S3 object or presigned URL), mark such mods in the mod list, and check GitHub and Forgejo releases for updates. Tokens for private sources are out of scope. He asked for the epic to be planned and implemented without further questions unless one is truly needed, so every ADR below is a planner decision (status "Accepted (planner)"), listed for review in the proposal's section 5.

| Story | Bead | ADRs |
|---|---|---|
| 28.1 Each Installed Mod Records Where It Came From | `VSS-guzf.1` (API-100) | ADR-1, ADR-2 |
| 28.2 A Mod Can Be Installed by Uploading Its File | `VSS-cxuu` (API-099) | ADR-3, ADR-4 |
| 28.3 A Mod Can Be Installed from an HTTPS Link | `VSS-guzf.2` (API-101) | ADR-4, ADR-5 |
| 28.4 The Mods Page Adds a Mod from a File or a Link | `VSS-guzf.3` (UI-105) | ADR-6 |
| 28.5 Mods from GitHub and Forgejo Releases Get Updates | `VSS-guzf.4` (API-102) | ADR-7 |

## Facts Checked in the Code

**Installs.**

- `ModService.install_mod` (`services/mods.py:1498`) is the only install. It resolves the mod ID through the mod database, holds that mod ID's lock (`_hold`, `:479`; Epic 17 ADR-3), downloads into the cache, checks the archive's own `modinfo.json` mod ID, and calls `_place_install` (`:1586`). `_place_install` refuses a taken file name (`_refuse_taken_names`, `:449`, case-insensitive, Epic 19 ADR-8), copies through a `.vsm-tmp` working file and a rename, imports the archive (`ModStateManager.import_mod`), saves a `ModState`, and asks for a restart when the server runs.
- `POST /mods` (`routers/mods.py:807`) runs the install inside the request (no background job) and stores the update record from the install's lookup (`record_install`, Story 17.4).
- A version change swaps the file with a backup and restores the original on failure (`_apply_version_change`, `services/mods.py:1299`), keeping the enabled state (`.disabled` suffix).
- `ModStateManager.read_modinfo` (`services/mod_state.py:306`) reads and validates an archive's `modinfo.json` (keys case-insensitive, zip member paths checked) without caching or a fallback; `import_mod` (`:250`) caches it, with a filename fallback.
- Only `.zip` and `.zip.disabled` names are mod archives for the sync and the scan (`is_archive_name`, `services/mod_state.py:742`). `.cs` files and folders are never tracked (Epic 24 ADR-3).

**Mod state and the "local mod".**

- `ModState` (`models/mods.py:63`) holds `filename`, `slug` (the `modinfo.json` mod ID), `version`, `enabled`, `installed_at` and `asset_id` (0 when unknown). Nothing records where the file came from. `ModInfo` (`:92`) adds the cached metadata; `ModService.list_mods` (`services/mods.py:670`) builds it.
- The start-up sync and `POST /mods/rescan` add archives found in the mods folder (`sync_state_with_disk`, `services/mod_state.py:565`; Epic 24).
- The update check looks every installed mod up in the mod database (`ModUpdateService._check_one`, `services/mod_updates.py:534`) and fills in a missing asset ID (`fill_asset_id`, Epic 24 ADR-1). A mod the database does not know gets `unknown` / `not_in_database` (`build_status_items`, `:217`).
- The web shows a `not_in_database` mod as a "Local mod" with no mod database link and no Update button (`isLocalMod`, `components/InstalledModParts.tsx:35`; `ModUpdateCell.tsx:115`; Epic 24 ADR-1 decision 4).
- A mod ID that is also on the mod database is treated as that mod: the check offers the database's releases. A patched fork with the same mod ID would be offered the original's update, and "Update" would replace the fork.

**Transport.**

- The API has no multipart parser: `python-multipart` is not a dependency (`api/pyproject.toml`), so FastAPI's `UploadFile` and `Form` are not available.
- The web client always sends JSON (`apiClient`, `api/client.ts:180`).
- `httpx` 0.28.1 and `httpcore` 1.0.9 are installed. `httpcore.AsyncConnectionPool` takes a `network_backend` (public `httpcore.AsyncNetworkBackend`, `httpcore.AnyIOBackend`); `httpx.AsyncHTTPTransport` does not expose it.
- Nothing in `api/src` checks whether an address is private (no `ipaddress` use).
- `VS_MOD_DB_URL` allows plain HTTP only with `VS_DEBUG=true`, for tests (`config.py:30`, Epic 20 ADR-9).

## ADR-1: Each Mod Records Its Source

**Status:** Accepted (planner)

**Decision:**

1. **Fields.** `ModState` gains `source: Literal["moddb", "folder", "upload", "url"]` and `source_url: str | None = None`. `ModInfo` and `GET /mods` carry both (`source`, `source_url`).
2. **Who sets it.** An install from the mod database: `moddb`. The start-up sync and rescan: `folder`. An upload: `upload`. A link: `url`, with `source_url`. A version change keeps the source (only `moddb` and `folder` mods can change version; ADR-7 adds `url`).
3. **Existing state files.** An entry without `source` reads as `moddb` when `asset_id > 0`, otherwise `folder`. Nothing is rewritten at load; the field is saved with the next write. The two defaults behave as today (ADR-2), so a wrong guess changes nothing.
4. **No credentials kept.** `source_url` is the link without its query string, fragment and user info. A presigned S3 link carries its signature in the query, so the stored URL can be shown and logged. ADR-7 needs only the path.

## ADR-2: Uploaded and Linked Mods Are Not Looked Up in the Mod Database

**Status:** Accepted (planner)

**Decision:**

1. **The update check skips them.** A mod with source `upload` or `url` is never looked up, so no asset ID is filled in and no database release is offered. Its status is `unknown` with the new reason `manual_install`. ADR-7 replaces this for `url` mods from GitHub or Forgejo releases.
2. **Folder mods keep today's behaviour.** A `folder` mod is still looked up; if the database knows its mod ID it gets updates, otherwise it is a local mod (Epic 24).
3. **The web.** A mod with source `upload` or `url` has no mod database link and no database lookup for its compatibility (its mod ID may name a different database mod). Its update cell reads "Uploaded file" or "Installed from a link" (the link's host in the tooltip). Its compatibility reads "Not verified", with the message "Not from the mod database".
4. **Update all and alerts** follow from the status: `unknown` is never offered, so neither touches these mods.

## ADR-3: The Upload Is the Request Body

**Status:** Accepted (planner)

**Decision:**

1. **Route.** `POST /mods/upload?filename=<name>&replace=<bool>`, Admin only. The body is the file (`application/zip` or `application/octet-stream`). No multipart, so no new dependency, and the size limit applies while reading.
2. **Size.** `VS_MOD_UPLOAD_MAX_MB` (default 200, at least 1). A `Content-Length` over the limit is refused before reading; the stream is counted and stopped at the limit. Answer 413 `MOD_FILE_TOO_LARGE`.
3. **Working file.** The body is written to a working file in `{cache_dir}/incoming/`, deleted on every exit. A leftover from a crash is deleted at start-up (with the other working files).
4. **The name.** The base name only; it must end in `.zip` (any case), be at most 255 characters, have no path separators or control characters and not start with a dot. Otherwise 422 `MOD_FILE_INVALID`. *(As implemented in Story 28.2, after its review: `.zip` in lowercase only, since `is_archive_name` and the game on Linux load only that, and at most 255 bytes in UTF-8, the volume's limit. A failure to write the file is 500 `MOD_FILE_WRITE_FAILED`.)*
5. **The archive.** It must be a zip with a readable `modinfo.json` that has a mod ID and a version (`read_modinfo`). Otherwise 422 `MOD_FILE_INVALID`, saying which. The rest of the archive is never extracted.

## ADR-4: One Install Path for Files, with Replace

**Status:** Accepted (planner)

**Decision:**

1. **Shared install.** `ModService.install_archive(path, filename, source, source_url, replace)` installs a validated archive from ADR-3 or ADR-5 under its mod ID's lock (`_hold`), refusing a busy mod (409 `MOD_OPERATION_IN_PROGRESS`).
2. **Not installed.** Placed like `_place_install`: taken names refused (409 `MOD_FILE_CONFLICT`), working copy and rename, import, state saved with the source.
3. **Installed, no replace.** 409 `MOD_ALREADY_INSTALLED`, with the installed version and source in the detail, so the web can offer a replace.
4. **Installed, replace.** The installed file is swapped like a version change: backup, new file placed (keeping the enabled state), state saved with the new source, original restored on failure. The mod's update record is removed. This is how a patched fork replaces a mod-database mod, and how a newer file replaces an older upload.
5. **Response.** As `POST /mods` (`slug`, `version`, `filename`, `compatibility`, `pending_restart`), plus `source`, `replaced` and `previous_version`. `compatibility` is `not_verified` (ADR-2 decision 3).
6. **Restart.** A pending restart when the server runs, as for every install.

## ADR-5: Fetching a Link Safely

**Status:** Accepted (planner)

**Decision:**

1. **Route.** `POST /mods/install-from-url` with `{url, replace}`, Admin only. It runs in the request, like `POST /mods`.
2. **Scheme.** `https` only, checked on the link and on every redirect (at most 5). Plain `http` only with `VS_DEBUG=true`, as for `VS_MOD_DB_URL`. A link with a user name or password is refused. 422 `MOD_URL_INVALID`.
3. **Addresses checked when connecting.** A transport wraps `httpcore.AsyncConnectionPool` with a network backend that resolves the host, refuses the connection when any resolved address is not global (private, loopback, link-local, multicast, reserved or unspecified), and connects to the address it checked. TLS still verifies the host name. Checked per connection, so a redirect or a DNS change between hops cannot reach an internal address. 422 `MOD_URL_BLOCKED`, naming the host but not the address.
4. **LAN hosts.** `VS_MOD_URL_PRIVATE_HOSTS` (comma-separated host names, default empty) lists hosts allowed to resolve to private addresses, for a self-hosted Forgejo on the LAN. Loopback, link-local and unspecified addresses stay blocked for every host.
5. **No proxy from the environment** (`trust_env=False`), so `HTTPS_PROXY` cannot route around the check.
6. **Limits.** Connect 10 s, read 30 s, the whole download 300 s; the size limit of ADR-3 decision 2, from `Content-Length` and while streaming. A non-2xx answer, a timeout or a connection error is 502 `DOWNLOAD_FAILED`.
7. **The name.** `Content-Disposition`'s file name, else the last path segment of the final URL; if neither passes ADR-3 decision 4, `{modid}_{version}.zip`.
8. **Then** the archive is checked as ADR-3 decision 5 and installed through ADR-4 with source `url` and the link (ADR-1 decision 4).

## ADR-6: The Add Dialog

**Status:** Accepted (planner)

**Decision:**

1. **Where.** An "Add from file or link" button on the Installed tab, Admin only, next to Rescan.
2. **The dialog** has two tabs: "File" (a file picker that also accepts a dropped `.zip`) and "Link" (an HTTPS URL field). One Install button; a spinner while the request runs (a fetch body has no upload progress).
3. **Upload client.** `apiClient` gains a raw body option that sends a `Blob` as is, with its content type, and no JSON transform; the upload uses it.
4. **Errors** show in the dialog with the API's message. `MOD_ALREADY_INSTALLED` shows "<name> <version> is already installed (<source>)" and a "Replace it" button that resends with `replace=true`.
5. **Success** closes the dialog, shows a toast with the mod's name and version (and the restart note when pending), and invalidates the mods and updates queries.
6. **Phones.** The dialog is full width under 640 px, targets 44 px.

## ADR-7: Updates from GitHub and Forgejo Releases

**Status:** Accepted (planner)

**Decision:**

1. **Which links.** A `url` mod whose link path is `/{owner}/{repo}/releases/download/{tag}/{asset}`: on `github.com` a GitHub release, on any other host a Forgejo (or Gitea) release. Other links (S3, plain URLs) keep `manual_install`.
2. **Latest release.** GitHub: `https://api.github.com/repos/{owner}/{repo}/releases/latest`. Forgejo: `https://{host}/api/v1/repos/{owner}/{repo}/releases/latest`. Both skip drafts and pre-releases. Fetched with ADR-5's transport (address checks, `VS_MOD_URL_PRIVATE_HOSTS`), no token.
3. **Which asset.** Among the release's `.zip` assets, the one whose name, with version-like parts removed, equals the installed asset's name treated the same way; if none matches and the release has exactly one `.zip`, that one; otherwise no offer (`unknown`, reason `release_asset_not_matched`).
4. **Which version.** The tag without a leading `v`, compared with the installed `modinfo.json` version by `parse_base_version` (Epic 14). Newer: `update_available`, compatibility `not_verified`. Same or older: `up_to_date`. A tag that does not parse: `unknown`, reason `version_unparsable`.
5. **Where.** In the existing update check: `_check_one` sends a release `url` mod to the release lookup instead of the mod database. A failed lookup is recorded as today. GitHub allows 60 unauthenticated requests an hour; the check makes one per release mod.
6. **Applying.** `PUT /mods/{slug}/version` for a `url` mod with a stored release offer installs the offered asset through ADR-5 with replace, refusing an archive whose mod ID differs from the installed one (422 `MOD_FILE_INVALID`). The web's Update button and its confirmation for `not_verified` work unchanged. Update all skips the offer as `not_verified`, as for every such offer. The webhook alert includes it.
