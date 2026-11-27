# Story 28.5: Mods from GitHub and Forgejo Releases Get Updates

Status: review

<!-- Implements FR365, FR366, Epic 28 ADR-7. Bead: VSS-guzf.4 (API-102), closes with this story after merge. Branch story/28-5-mods-from-github-and-forgejo-releases-get-updates, stacked on story/28-4-the-mods-page-adds-a-mod-from-a-file-or-a-link (PR #238); the PR targets main and merges after 28.4's. API, with a web label. -->

## Story

As an **administrator**,
I want **a mod I installed from a GitHub or Forgejo release to tell me when a newer release is out**,
so that **I can update it like a mod-database mod**.

## Acceptance Criteria

1. **Given** a `url` mod whose link is a release asset (`/{owner}/{repo}/releases/download/{tag}/{asset}`) **When** the update check runs **Then** the repo's latest release is fetched (GitHub's API on `github.com`, `/api/v1` on any other host), through Story 28.3's transport *(FR365; ADR-7)*
2. **Given** the latest release **Then** the asset is matched by name with version-like parts removed, else the only `.zip`; no match gives `unknown` / `release_asset_not_matched` *(ADR-7 decision 3)*
3. **Given** a newer tag (a leading `v` removed) **Then** `update_available` with `not_verified`; the same or older gives `up_to_date`; a tag that does not parse gives `unknown` / `version_unparsable` *(FR365)*
4. **Given** a lookup that fails **Then** the error is recorded as for a mod-database lookup and the check goes on
5. **Given** `PUT /mods/{slug}/version` with the offered version **Then** the matching asset is installed with replace through Story 28.3's download; an archive with another mod ID is refused with 422 `MOD_FILE_INVALID` and the installed mod is kept *(FR366)*
6. **Given** the Installed tab **Then** such a mod shows the update with the Update button, and Update all skips it as not verified; the webhook alert includes it
7. **Given** a link that is not a release asset **Then** its status stays `manual_install`
8. **(Quality gates.)** `just check` green; README documents release updates

## Tasks / Subtasks

- [x] Task 1: The release lookup and the check (AC: 1-4, 6, 7)
  - [x] 1.1: `services/mod_releases.py`: `parse_release_link`, `tag_version`, `asset_stem`/`match_asset`, `is_newer`, `release_lookup` (guarded transport, redirects checked per hop, 2 MB cap)
  - [x] 1.2: `mod_link.open_following` and `link_client` shared by downloads and lookups
  - [x] 1.3: `ModUpdateService`: release mods checked through an injected `release_lookup` (built from the settings on first use); `_release_status`; reason `release_asset_not_matched`; `StoredRelease.download_url`
- [x] Task 2: Applying the update (AC: 5)
  - [x] 2.1: `PUT /mods/{slug}/version` sends a release mod to `_update_release_mod` (only the offered version; 409 `MOD_CONFIRMATION_REQUIRED` with `not_verified` until confirmed; download and replace with `expect_modid`)
- [x] Task 3: Web label for `release_asset_not_matched`; README (AC: 6, 8)
- [x] Task 4: Validate and move the story to review (AC: 8)

## Dev Notes

- `parse_base_version` stays in `services/mod_updates.py`; `mod_releases.is_newer` imports it inside the function because `mod_updates` imports `mod_releases`.
- The web needs no new flow: an `update_available` status shows Update, and `useVersionChangeFlow` already confirms a 409 `MOD_CONFIRMATION_REQUIRED` with `not_verified`.
- Update all calls `change_version` only for `compatible` offers, so a release offer (`not_verified`) is skipped before any request.

### References

- `epics.md` "Story 28.5"; `architecture/epic-28-mods-from-outside-the-mod-database.md` ADR-7

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-27): exit 0; API 4403 passed, web 4001 passed.
- Live check (2026-11-27): `release_lookup` on `https://github.com/cli/cli/releases/download/v2.40.0/gh_2.40.0_windows_amd64.zip` read the latest release (`v2.106.0`, 22 assets) through the guarded transport and matched `gh_2.106.0_windows_amd64.zip`.

### Implementation decisions

- **One stored release per release mod**: the record holds the matched asset of the latest release (`modversion` the tag's version, `download_url`), or no release when nothing matched.
- **Only the offered version can be applied**, and only after confirming (it is not verified); any other version is 404 `MOD_VERSION_NOT_FOUND` ("check for updates first"). Rolling back a release mod is not offered.
- **The installed version is "no change"**, as for a mod-database mod.
- **The record is kept after an update**, so the mod reads up to date at once instead of "Not checked yet".
- **`expect_modid` on `install_archive`**: a release update refuses an archive of another mod ID before taking any lock, so it can never install a second mod.
- **Version comparison uses the base version** (`parse_base_version`, before any `-`), padded; `2.0.0-rc.1` is newer than `1.9.0`, and `1.1.0` newer than an installed `1.0.0-fork`.

### Completion Notes List

- 2026-11-27 (dev-story): Tasks 1 to 4 done. 48 new API tests in `test_mod_releases.py` (links, versions, asset matching, the lookup against GitHub and Forgejo shapes and its errors, the check's statuses, a failed lookup, non-release links, update all, and applying: confirmation, install keeping the disabled state, another mod ID refused, a version not offered, no change, a failed download) and 2 web tests.
- 2026-11-27 (create-story): created from Epic 28's Story 28.5 and ADR-7.

### File List

- `api/src/vintagestory_api/services/mod_releases.py` (new), `services/mod_link.py`, `services/mod_updates.py`, `services/mods.py`, `routers/mods.py`, `models/mod_updates.py`; `api/tests/test_mod_releases.py` (new) (Tasks 1, 2)
- `web/src/api/types.ts`, `web/src/components/ModUpdateCell.tsx`, `ModUpdateCell.test.tsx`; `README.md` (Task 3)
- this file; `sprint-status.yaml` (through `just sprint set`)

## Change Log

- 2026-11-27: Story 28.5 created (create-story).
- 2026-11-27: Story 28.5 implemented (dev-story): Tasks 1 to 4; status review.
