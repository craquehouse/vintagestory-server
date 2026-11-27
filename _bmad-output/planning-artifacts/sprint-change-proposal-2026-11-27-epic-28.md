# Sprint Change Proposal: Mods From Outside the Mod Database (Epic 28)

**Date:** 2026-11-27
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (scope named by the maintainer; no question round)
**Scope classification:** Moderate
**Status:** Scope named by Matt (2026-11-27): install a mod that is not on the mod database from an uploaded file or an HTTPS link, mark such mods, and check GitHub and Forgejo releases for updates; tokens for private sources out of scope. He grouped the five beads under the epic bead `VSS-guzf` and asked for the epic to be planned and implemented, coming back to him only when his input is truly needed. Every decision below is the planner's, listed in section 5 for review.

## 1. Issue Summary

**Trigger:** Matt asked for a way to install mods that are not on mods.vintagestory.at, by posting the file or a link reachable over HTTPS (GitHub, Forgejo, S3). The beads `VSS-guzf.1` (API-100), `VSS-cxuu` (API-099), `VSS-guzf.2` (API-101), `VSS-guzf.3` (UI-105) and `VSS-guzf.4` (API-102) were filed the same day under `VSS-guzf`. No other open bead touches the mod code, so none is pulled in (backlog rule, 2026-11-17).

**Problem:** The only install is from the mod database (`POST /mods`). A mod from GitHub, a private build or a patched fork has to be copied into the mods folder by hand and picked up with Rescan (Epic 24). Such a file is then looked up in the mod database by its mod ID, so a fork of a database mod is offered the original's update, and "Update" replaces the fork.

**Evidence:** see the facts in `architecture/epic-28-mods-from-outside-the-mod-database.md` (code at `0da3d584`). In short: no source is recorded on a mod (`ModState`, `models/mods.py:63`); every mod is looked up (`_check_one`, `services/mod_updates.py:534`); no multipart parser is installed; nothing checks whether an address is private.

## 2. Impact Analysis

**Epic impact:** Epics 1 to 25 are done; none is invalidated. Epics 26 and 27 stay proposed. One new epic, Epic 28, with 5 stories (160 in all).

**Story impact:** No existing story changes. Story 28.1 narrows Epic 24's local mod (ADR-2) to `folder` mods; uploaded and linked mods get their own label.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | FR354 to FR366; frontmatter |
| Epics | Epic 28; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-28-mods-from-outside-the-mod-database.md` (facts, ADR-1 to ADR-7); index entry |
| UX spec | No text change. The dialog follows `InstallConfirmDialog` and the Installed tab's toolbar |
| CI | No new job. Story 28.4 adds E2E checks to the CI set |
| Deployment and documentation | README: installing from a file or a link; `VS_MOD_UPLOAD_MAX_MB`, `VS_MOD_URL_PRIVATE_HOSTS`; updates from release links |
| Beads | Epic bead `VSS-guzf` gets the story map |

**Technical impact:**

- No new dependency: the upload is the request body (ADR-3), the address check is an `httpcore` network backend (ADR-5).
- The first request that downloads from an address an administrator types. ADR-5 checks every connection's resolved address, refuses redirects off HTTPS and ignores proxies from the environment.
- Two new settings, two new routes, one changed route (`PUT /mods/{slug}/version` for release mods).

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 28.1 | `GET /mods` | `source`, `source_url` on each mod | New fields |
| 28.1 | `GET /mods/updates` | reason `manual_install` | New value |
| 28.2 | `POST /mods/upload` | New, Admin | New route |
| 28.2 | `VS_MOD_UPLOAD_MAX_MB` | Default 200 | Configuration |
| 28.3 | `POST /mods/install-from-url` | New, Admin | New route |
| 28.3 | `VS_MOD_URL_PRIVATE_HOSTS` | Default empty | Configuration |
| 28.5 | `GET /mods/updates` | reason `release_asset_not_matched`; release mods get offers | New value |
| 28.5 | `PUT /mods/{slug}/version` | Also updates a release mod | Behaviour |

**Draft release-note text** (commit subjects; git-cliff removes the story scope):

- Features:
  - `feat(api): record where each installed mod came from`
  - `feat(web): mark uploaded mods and mods installed from a link`
  - `feat(api): install a mod by uploading its file`
  - `feat(api): install a mod from an HTTPS link`
  - `feat(web): add a mod from a file or a link on the Installed tab`
  - `feat(api): check GitHub and Forgejo releases for updates to mods installed from them`
- Fixes:
  - `fix(api): stop offering mod database updates to uploaded and linked mods`

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 28 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Five stories, one per bead. Effort medium to high; risk medium (28.3 fetches arbitrary links) |
| 2. Rollback | Not viable. Nothing completed has to be undone |
| 3. MVP Review | Not needed |

**Risks:**

- **Story 28.3: reaching internal services (SSRF).** A link could point at the Docker host, a metadata service or the LAN. ADR-5 checks the resolved address of every connection, including after redirects and DNS changes, and ignores proxy variables. Tests cover each address class, a redirect to a blocked host and a host that resolves to both a public and a private address.
- **Story 28.3: a self-hosted Forgejo on the LAN.** The address check would block it. `VS_MOD_URL_PRIVATE_HOSTS` allows named hosts to use private addresses; loopback and link-local stay blocked.
- **Story 28.2: large uploads.** The body is streamed to disk with the limit counted, never held in memory.
- **Story 28.2: replacing a database mod.** ADR-4 refuses unless `replace` is set, and the swap keeps a backup until the state is saved.
- **Story 28.5: GitHub's rate limit.** 60 unauthenticated requests an hour. One request per release mod per check; a limited answer is recorded as a failed lookup, as today.
- **Story 28.5: guessing the right asset.** ADR-7's name match can miss; then the status says `release_asset_not_matched` rather than offering a wrong file, and an archive with another mod ID is refused.

## 4. Detailed Change Proposals

The PRD FRs, the epic and its stories (with acceptance criteria) are in `prd.md` (FR354 to FR366) and `epics.md` ("Epic 28"). The decisions are in the architecture file.

**Beads:** `VSS-guzf`'s description gets the story map: `VSS-guzf.1` → 28.1, `VSS-cxuu` → 28.2, `VSS-guzf.2` → 28.3, `VSS-guzf.3` → 28.4, `VSS-guzf.4` → 28.5. Each closes with an AAR after its story merges.

## 5. Implementation Handoff

**Planner decisions not reviewed yet:**

- Four sources (`moddb`, `folder`, `upload`, `url`), with `folder` keeping Epic 24's behaviour, and old entries read by asset ID (ADR-1).
- The stored link drops its query string, so a presigned URL's signature is never kept (ADR-1 decision 4).
- The upload is the raw request body, not multipart (ADR-3); limit `VS_MOD_UPLOAD_MAX_MB`, default 200.
- Zip archives only; `.cs` and `.dll` files are not accepted (the manager tracks only zips).
- A replace is opt-in (`replace=true`) and swaps like a version change (ADR-4).
- Link installs run inside the request, like mod database installs, with a 300-second limit (ADR-5).
- `VS_MOD_URL_PRIVATE_HOSTS` for LAN hosts; plain HTTP only with `VS_DEBUG` (ADR-5).
- Release updates through the existing update check and `PUT /mods/{slug}/version`, offered as `not_verified`, so Update all skips them (ADR-7).

**Scope:** Moderate. Direct implementation by the dev workflow (`create-story`, `dev-story`), one story at a time; code review delegated per the `code-review-delegation` memory.

**On approval:** add the five stories to `sprint-status.yaml` and the story map to `VSS-guzf`; then create Story 28.1.

**Success criteria:** the five beads closed with AARs; `just check` and the CI E2E set pass on each PR; on a throwaway container, an uploaded zip and a GitHub release link install and show as such, and a link to a private address is refused.

**Backlog change (projected):** closes 5 plus the epic bead; all five were opened for this epic on 2026-11-27.
