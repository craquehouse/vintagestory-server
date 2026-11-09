# Epic 14: Mod Updates Architecture

_Added during the Epic 14 course correction (2026-11-09). Story 14.0 verified each decision against the live mod database and a running server; see its story file for evidence._

## ADR-1: Detect Updates by Release Order

**Status:** Changed by Story 14.0

**Decision:** A release is newer than the installed one if it appears earlier in the mod database's release list, which is ordered newest first. Version strings are never compared.

**Rationale:** Mod versions are free-form. The detail page's current `!==` comparison reports any non-latest version as outdated, including a deliberate rollback.

**Story 14.0 findings:** The list is newest first by publish date, but publish order is not version order (CarryOn: `2.0.0-rc.1`, then `1.14.3`, then `2.0.0-pre.8`). One ModDB entry can hold releases for several modids, and a `modversion` can repeat across them.

**Rules:**
- Only releases whose `modidstr` equals the installed mod's modid are considered.
- The installed release is the one matching both `modidstr` and `modversion`; these matched the archive's `modinfo.json` in every sampled release.
- A version is a pre-release if its `modversion` contains `-` (for example `2.0.0-rc.1`). A stable install is only offered stable releases. A mod already on a pre-release is offered any newer release. Pre-releases remain available through version switching (ADR-2), with a warning.
- The offered release is the newest newer eligible compatible release, then the newest newer eligible not-verified release, otherwise none (`blocked`).

**Consequences:** If the installed release is not in the list, or the mod returns `"404"` (removed from ModDB), the status is `unknown`. Mods are looked up by their installed modid; `urlalias` does not resolve as a lookup key.

## ADR-2: One Version Change Operation

**Status:** Changed by Story 14.0

**Decision:** Update and rollback use one `ModService` operation that moves a mod to a given listed release. It replaces the Epic 5 `update(slug)` sequence, which removed the old version before installing the new one.

**Sequence:**
1. Resolve the release from the mod database
2. Use the cached file in `vsmanager/cache/mods/` if present and valid (ADR-3), otherwise download it there. Use only the final path component of ModDB's `filename`, and reject empty, `.` or `..` names
3. Validate the archive and confirm its `modinfo.json` `modid` and `version` match the requested release
4. Copy into the mods directory under a temporary name, then rename into place, keeping `.disabled` if the mod is disabled
5. Update and save mod state, then delete the old file if its name differs. Deleting it is required: if it fails, remove the new file, restore the original state, and report the change as failed
6. Mark a restart as pending if the server is running

A failure before step 4 completes leaves the original file and state untouched. Changes are serialized per mod; a concurrent request for the same mod returns 409.

**Story 14.0 findings:** Replacing a code mod under a running 1.22.7 server caused no errors; the new version loaded at restart. With two versions of the same modid present, the game warns "Multiple mods share the mod ID" and loads only one, while the API still reported the other. Hence the required delete in step 5.

## ADR-3: Rollback Source

**Status:** Changed by Story 14.0

**Decision:** Rollback uses the mod database's release list and the existing artifact cache. No extra retention policy is added, and cache eviction is unchanged.

**Consequences:** A release removed from the mod database can only be restored while its file is still cached. Filenames repeat within one ModDB entry, so a cached file is reused only after its archive `modid` and `version` match the target release; otherwise the release is downloaded again.

## ADR-4: Update Status Store

**Status:** Confirmed by Story 14.0, with each stored release also keeping its `modidstr`

**Decision:** Checks write `vsmanager/state/mod-updates.json` atomically. Per mod it holds the release list (versions and game version tags, in order), the computed status, the offered release and `checked_at`. It also records the alerts already sent.

**Rationale:** Status survives restarts (FR147). Storing the release list lets status be recomputed locally when the game version changes or a mod is installed, removed or switched, without calling the mod database.

## ADR-5: Scheduled Checks Reuse the Refresh Job

**Status:** Confirmed by Story 14.0. `ModApiClient.get_mod()` has no response cache, so the job makes one request per installed mod per interval, as it does today.

**Decision:** `mod_cache_refresh`, which already fetches every installed mod on `mod_list_refresh_interval` (default 14400 seconds), records update status. No new job or setting is added, and an interval of 0 disables it.

## ADR-6: Webhook Alerts

**Status:** Changed by Story 14.0

**Decision:** An Admin-only `mod_update_webhook_url` in API settings.
- **Reads:** return only whether it is configured; the URL is never returned, logged or exposed to Monitor.
- **Sending:** http or https only, a 10 second timeout, and no redirects followed.
- **Payload:** receiver-specific, because Discord does not document how it treats extra fields.
  - Discord URL (host `discord.com`, `discordapp.com`, `ptb.discord.com` or `canary.discord.com`, path starting `/api/webhooks/`): `{"content": <summary>, "allowed_mentions": {"parse": []}}`
  - Any other URL: `{"event": "mod_updates_available", "content": <summary>, "updates": [{"slug", "name", "installed", "offered", "compatibility"}]}`
  - Summary: one line per mod, `- {name}: {installed} → {offered} ({compatibility})`, truncated with "…and N more" to stay within Discord's 2000-character `content` limit. Mentions are suppressed because mod names come from ModDB.
- **Deduplication:** one alert per mod and version, recorded in the status store only after a 2xx response, so a failed delivery is retried on the next check. A 429 is not retried within the same check.
- **Failure:** delivery failures are logged without the URL and never fail the job.

**Consequences:** The URL is stored in plain text in `api-settings.json` on the data volume, the same trust boundary as the rest of the server's state.

## API Additions

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/mods/updates` | Admin, Monitor | Update status for installed mods |
| POST | `/mods/updates/check` | Admin | On-demand check |
| POST | `/mods/updates/apply-all` | Admin | Update all compatible mods |
| PUT | `/mods/{slug}/version` | Admin | Change version; body: `version`, `confirm` |

Literal routes are declared before `/{slug}` routes.

**New error codes:**
- `MOD_CONFIRMATION_REQUIRED`: the target is not verified, incompatible or older, and `confirm` is false
- `MOD_VERSION_CHANGE_IN_PROGRESS`: 409
- `MOD_VALIDATION_FAILED`: the archive is invalid or its modid doesn't match

The existing `MOD_VERSION_NOT_FOUND` covers unlisted releases.

## Frontend

- **Query key:** update status gets its own key under `mods` that cannot collide with a mod's detail key.
- **Invalidation:** version change and update all invalidate both installed mods and update status.
