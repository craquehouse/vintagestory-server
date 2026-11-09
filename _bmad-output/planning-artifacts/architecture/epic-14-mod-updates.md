# Epic 14: Mod Updates Architecture

_Added during the Epic 14 course correction (2026-11-09). Story 14.0 verifies the assumptions marked below._

## ADR-1: Detect Updates by Release Order

**Decision:** A release is newer than the installed one if it appears earlier in the mod database's release list, which is ordered newest first. Version strings are never compared.

**Rationale:** Mod versions are free-form. The detail page's current `!==` comparison reports any non-latest version as outdated, including a deliberate rollback.

**Consequences:** If the installed version is not in the list, the status is `unknown`. The offered release is the newest newer compatible release, then the newest newer not-verified release, otherwise none (`blocked`). Story 14.0 verifies the ordering assumption.

## ADR-2: One Version Change Operation

**Decision:** Update and rollback use one `ModService` operation that moves a mod to a given listed release. It replaces the Epic 5 `update(slug)` sequence, which removed the old version before installing the new one.

**Sequence:**
1. Resolve the release from the mod database
2. Use the cached file in `vsmanager/cache/mods/` if present, otherwise download it there
3. Validate the archive and confirm its `modid` matches the installed mod
4. Copy into the mods directory under a temporary name, then rename into place, keeping `.disabled` if the mod is disabled
5. Update and save mod state, then delete the old file if its name differs
6. Mark a restart as pending if the server is running

A failure before step 4 completes leaves the original file and state untouched. Changes are serialized per mod; a concurrent request for the same mod returns 409.

## ADR-3: Rollback Source

**Decision:** Rollback uses the mod database's release list and the existing artifact cache. No extra retention policy is added, and cache eviction is unchanged.

**Consequences:** A release removed from the mod database can only be restored while its file is still cached.

## ADR-4: Update Status Store

**Decision:** Checks write `vsmanager/state/mod-updates.json` atomically. Per mod it holds the release list (versions and game version tags, in order), the computed status, the offered release and `checked_at`. It also records the alerts already sent.

**Rationale:** Status survives restarts (FR147). Storing the release list lets status be recomputed locally when the game version changes or a mod is installed, removed or switched, without calling the mod database.

## ADR-5: Scheduled Checks Reuse the Refresh Job

**Decision:** `mod_cache_refresh`, which already fetches every installed mod on `mod_list_refresh_interval` (default 14400 seconds), records update status. No new job or setting is added, and an interval of 0 disables it.

## ADR-6: Webhook Alerts

**Decision:** An Admin-only `mod_update_webhook_url` in API settings.
- **Reads:** return only whether it is configured; the URL is never returned, logged or exposed to Monitor.
- **Sending:** http or https only, a 10 second timeout, and no redirects followed.
- **Payload:** a Discord-compatible `content` message plus a structured `updates` list. Story 14.0 confirms this.
- **Deduplication:** one alert per mod and version, recorded in the status store.
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
