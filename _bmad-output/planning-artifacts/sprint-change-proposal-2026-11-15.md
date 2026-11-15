# Sprint Change Proposal: Mod Data Correctness and Fixes (Epic 17)

**Date:** 2026-11-15
**Author:** Matt
**Workflow:** correct-course (batch; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Approved by Matt, 2026-11-15

## 1. Issue Summary

**Trigger:** A production bug. On `v0.1.0-rc.3`, opening C&N Jewelry (`canjewelry`) in the mod browser shows "Failed to load mod details": the lookup returns 500 because three of the mod's 179 releases have `"fileid": null` in the mod database (`VSS-a0r`, P1). Fifteen other open bugs and small fixes in beads, most of them found in the Epic 14 and Epic 16 reviews, describe wrong or unsafe behavior of the same kind.

**Problem:** The manager trusts the mod database's data more than it should and is loose about which release and which mod an operation applies to. A null field makes a mod impossible to open, Install can pick a different mod ID or a pre-release, operations on one mod can overlap, and installed status differs between views. Beside the mod work, a Monitor key can read the game server password, two settings do not behave as shown, and a few navigation and layout defects remain from Epic 16.

**Evidence** (code at commit `ebca566`; details and line references in `architecture/epic-17-mod-data-fixes.md`):

- `services/mods.py` builds releases with `r.get("fileid", 0)`; the default applies only to a missing key, so a null reaches `ModRelease.file_id: int` and fails validation (`VSS-a0r`). The same `.get(key, default)` pattern is used for every other mod database field in lookup, browse, sort and search.
- `ModDetailError` in `ModDetailPage.tsx` shows only a message, with no Back to Browse (`VSS-fv7`).
- `ModApiClient.download_mod` takes `releases[0]` or matches `modversion` across every mod ID of the entry: `instruments` installs `vsinstrumentsbase` (`VSS-jhf`), and `carryon` installs `2.0.0-rc.1` (`VSS-43b`). The detail page labels `releases[0]` "(Latest)" and preselects it.
- Only `change_version` takes the per-mod lock; install, enable, disable and remove do not (`VSS-8wg`). `import_mod` validates `modinfo.json` without the key normalization `read_modinfo` applies (`VSS-0jl`).
- `ModCard` compares only the browse slug with installed mod IDs (`VSS-49n`). The update status has no record for a mod installed after the last check and shows "Unknown" (`VSS-br2`).
- `GET /config/game` and `GET /config/files/...` need only an authenticated key and return the `Password` value (`VSS-qed`).
- `get_api_settings_service` never passes a scheduler callback, so a changed interval waits for a restart (`VSS-8bl`). `SettingField` renders `Boolean(null)` as Disabled (`VSS-2le`).
- `ModsPage.getActiveTab` reports Installed on a detail page, so the Installed tab is a no-op there (`VSS-2oz`). `parsePage` accepts any positive page (`VSS-nhb`).
- The installed mods table needs 751px in a 560px container at a 768px viewport (`VSS-dp1`); the Settings tab list is about 518px wide at 390px (`VSS-uni`); the Game Settings title row spans the full width beside a 1280px panel (`VSS-143`).

**Scope decisions (made by the maintainer before the workflow ran):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-a0r`, `VSS-fv7`, `VSS-jhf`, `VSS-43b`, `VSS-8wg`, `VSS-0jl`, `VSS-49n`, `VSS-br2`, `VSS-qed`, `VSS-8bl`, `VSS-2le`, `VSS-2oz`, `VSS-nhb`, `VSS-dp1`, `VSS-uni`, `VSS-143` (16 issues, 8 stories) |
| Preparation story | None. The decisions are in the Epic 17 ADRs, written from the code; the two open questions are settled inside their stories |
| Open question, Story 17.5 | Redact the password for Monitor, or make the endpoints Admin-only. Recommended default: redact (ADR-4) |
| Open question, Story 17.6 | VintageStory's default for `EntitySpawning`. Recommended default: on, per `agentdocs/vs-serverconfig-commands.md`; confirmed in the story against a generated server config |
| Order | 17.1 first (production bug; `v0.1.0-rc.4` is expected right after it). 17.2 then 17.3, back to back, because both change the install code. The rest in any order |
| Features `VSS-4f3`, `VSS-l4x`, `VSS-2bp`, `VSS-bgu`, `VSS-2n2`, `VSS-bhw`, `VSS-29p`, `VSS-7ap`, `VSS-glz` | Not in scope: new capabilities, not corrections |
| Tooling and CI `VSS-4ac`, `VSS-djg`, `VSS-870`, `VSS-1eb`, `VSS-as6`, `VSS-ms0` | Not in scope: no user-visible behavior |
| Test-only `VSS-37a`, `VSS-3mr` | Not in scope: they stay under the Web UI Test Coverage epic (`VSS-029`) |
| `VSS-o8s` (slash in a directory name) | Not in scope: POSIX file names cannot contain a slash, so it cannot occur on the server |
| `VSS-zws` (does the game overwrite config edits) | Not in scope: an unverified question, not a known defect; it needs an investigation on a running server first |

## 2. Impact Analysis

**Epic impact:** Epics 1-14 are done, every Epic 16 story is done and Epic 15 is finishing; none is invalidated. One new epic, Epic 17: Mod Data Correctness and Fixes, with 8 stories. No resequencing.

**Story impact:** No existing story changes. Story 17.2 extends Epic 14 ADR-1's release rules to a first install and replaces the default mod ID in Epic 16 ADR-2 decision 2. Story 17.3 widens the per-mod serialization of Epic 14 ADR-2. Story 17.7 keeps Epic 16 ADR-1's Browse tab precedence. Story 17.8 follows Epic 16 ADR-3 and the UX spec's tablet rules.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR177-FR193; frontmatter |
| Epics | Add Epic 17; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-17-mod-data-fixes.md` (ADR-1 to ADR-5); index entry |
| UX spec | None. Story 17.8 implements the tablet rules it already describes |
| Beads | Epic `Epic 17: Mod Data Correctness and Fixes` with the 16 in-scope issues as children |

**Technical impact:**

- API and web. Stories 17.1 to 17.6 change the API; 17.7 and 17.8 are web only.
- API contract changes, all in `v1alpha1`: `ModRelease.file_id` becomes nullable (17.1); the lookup response gains `install_mod_id` and `latest_version` changes meaning to "what a plain install picks" (17.2); 409 `MOD_OPERATION_IN_PROGRESS` replaces `MOD_VERSION_CHANGE_IN_PROGRESS` and applies to five routes (17.3); browse items gain `mod_ids` (17.4); game settings gain `secret`, `configured` and `default`, and Monitor responses lose the password (17.5, 17.6).
- No new dependencies.
- Test strategy unchanged. Story 17.1 adds null-heavy mod database fixtures; Story 17.3 adds concurrency tests.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 17 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Eight stories of small fixes, each tied to existing beads. Effort small to medium, risk low to medium. |
| 2. Rollback | Not viable. The defects predate the recent epics; nothing completed has to be undone. |
| 3. MVP Review | Not needed. |

**Effort:** Small to medium. Sixteen issues, all size-s in beads. Stories 17.1, 17.2 and 17.3 are larger than their issues suggest, because each applies one rule across several call sites.

**Risks:**

- Story 17.1 touches every place mod database data is read. The normalizers must not change values that are already valid; the existing mod tests and fixtures guard that.
- Story 17.2 changes what `latest_version` means. The Installed list and update detection do not use it, but any external API client reading it sees a different value for mods whose newest release is a pre-release or another mod ID.
- Story 17.3 renames a 409 error code. The web does not branch on it; an external client might.
- Story 17.5 changes what a Monitor key receives. That is the purpose, and it is the one change in this epic that removes data from a response.
- Stories 17.2 and 17.3 edit the same functions; running them in parallel would conflict.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-15'`; update entry "Added FR177-FR193 for Epic 17 (Mod Data Correctness and Fixes)".

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 17: Mod Data Correctness and Fixes

#### Mod Data and Install

- FR177: Mod lookup, browsing, sorting, tag listing and update checks succeed when the mod database returns null for any field of a mod or release; a null takes the field's default, and a release without a file ID is listed with a null file ID
- FR178: The mod detail page's error state offers Back to Browse, returning to the browse state the page was opened from
- FR179: Installing a mod considers only releases whose mod ID is the mod being installed, with or without a named version
- FR180: Installing without a named version picks the newest stable release of that mod ID that has a downloadable file; a pre-release is installed only when its version is named or the mod ID has no stable release
- FR181: The install version list shows only the releases of the mod ID that will be installed, and "(Latest)" marks the release that an install without a named version picks
- FR182: Install, enable, disable, remove and version change for the same mod never run at the same time; a request that arrives while another is running is refused with 409 and changes nothing
- FR183: A mod archive whose `modinfo.json` uses capitalized top-level keys (for example `ModID`, `Version`) is imported with its real mod ID and version
- FR184: Mod browser cards show a mod as installed when any mod ID of its database entry is installed
- FR185: A newly installed mod has an update status in the Installed list without waiting for the next update check; a mod with no update data shows "Not checked yet", not "Unknown"

#### Access and Settings

- FR186: A Monitor key never receives the game server password: game settings report only whether a password is set, and the config file viewer redacts it; Admin access is unchanged
- FR187: Changing a refresh interval setting reschedules its job without restarting the API; setting it to 0 stops the job and raising it from 0 starts it
- FR188: A boolean game setting with no value in the server config shows the game's default, marked as the default, or "Not set" when the default is not known; it is never shown as Disabled because it is missing

#### Navigation and Layout

- FR189: On a mod detail page, Browse is the active Mods tab and the Installed tab opens the Installed list
- FR190: A browse link whose page is beyond the results opens the last page (page 1 when there are no results) without adding a history entry
- FR191: At tablet widths (768-1023px) the installed mods list fits the screen without horizontal scrolling
- FR192: On phones, the Settings tab list does not make the page scroll horizontally
- FR193: On wide screens, the Game Settings title row is aligned with the centered settings panel
```

**FR to story map:**

| Story | FRs | Beads |
|---|---|---|
| 17.1 Mod Detail Pages Cannot Fail on Bad Data | FR177, FR178 | `VSS-a0r`, `VSS-fv7` |
| 17.2 Install Picks the Right Release | FR179, FR180, FR181 | `VSS-jhf`, `VSS-43b` |
| 17.3 Mod Operations Are Safe Against Each Other | FR182, FR183 | `VSS-8wg`, `VSS-0jl` |
| 17.4 Installed Status Is Right Everywhere | FR184, FR185 | `VSS-49n`, `VSS-br2` |
| 17.5 Monitor Keys Cannot Read the Server Password | FR186 | `VSS-qed` |
| 17.6 Settings Behave as Saved | FR187, FR188 | `VSS-8bl`, `VSS-2le` |
| 17.7 Mods Navigation | FR189, FR190 | `VSS-2oz`, `VSS-nhb` |
| 17.8 Layout at Tablet and Phone Widths | FR191, FR192, FR193 | `VSS-dp1`, `VSS-uni`, `VSS-143` |

### 4.2 Epics Structure (`epics.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-15'`; update entry "Added Epic 17 (8 stories) for Mod Data Correctness and Fixes; FR177-FR193".

**FR Coverage Map**, appended after FR176:

```markdown
| FR177 | Epic 17 | Nulls in mod database data cannot fail a request |
| FR178 | Epic 17 | Back to Browse on the mod detail error state |
| FR179 | Epic 17 | Install considers only the requested mod ID |
| FR180 | Epic 17 | Install picks the newest stable release |
| FR181 | Epic 17 | "(Latest)" matches what install picks |
| FR182 | Epic 17 | One operation per mod at a time, 409 otherwise |
| FR183 | Epic 17 | Case-insensitive `modinfo.json` keys on import |
| FR184 | Epic 17 | Browse cards recognize any installed mod ID |
| FR185 | Epic 17 | Update status for a newly installed mod |
| FR186 | Epic 17 | Monitor keys never receive the server password |
| FR187 | Epic 17 | Interval settings reschedule their jobs |
| FR188 | Epic 17 | Unset boolean settings show the game default |
| FR189 | Epic 17 | Mods tabs work on a mod detail page |
| FR190 | Epic 17 | Out-of-range browse page is clamped |
| FR191 | Epic 17 | Installed mods fit tablet widths |
| FR192 | Epic 17 | Settings tabs fit phones |
| FR193 | Epic 17 | Game Settings title row aligned with the panel |
```

**Story Summary:**

OLD:

```markdown
| **Total** | | **94** |
```

NEW:

```markdown
| Epic 17: Mod Data Correctness and Fixes | 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8 | 8 |
| **Total** | | **102** |
```

### 4.3 Epic 17 Stories (appended to `epics.md`) — approved

## Epic 17: Mod Data Correctness and Fixes

**Goal:** Admins can open, install and manage any mod without the manager failing on the mod database's data or acting on the wrong release, and settings and layouts behave as shown.

**Architecture:** `architecture/epic-17-mod-data-fixes.md` (ADR-1 to ADR-5). There is no preparation story; the two open questions are settled inside Stories 17.5 and 17.6, each with a recommended default.

**Order:** Story 17.1 first: it fixes a bug seen in production, and a release candidate follows it. Stories 17.2 and 17.3 change the same install code and run back to back, 17.2 first. The others are independent.

### Current State

- A mod with one release whose file ID is null in the mod database cannot be opened: the lookup returns 500 and the detail page shows "Failed to load mod details" with no way back to the browser
- Install takes the entry's newest release whatever its mod ID or version, so installing `instruments` installs `vsinstrumentsbase`, and installing `carryon` installs a release candidate; the UI labels that release "(Latest)"
- Only version changes are serialized per mod; install, enable, disable and remove can run while one is in progress
- An archive whose `modinfo.json` uses capitalized keys imports with the version "unknown"
- Browse cards show a mod as not installed when its installed mod ID is not the entry's first, and a newly installed mod shows "Unknown" in the Available column
- A Monitor key can read the game server password from the settings API and the config file viewer
- A changed refresh interval does not apply until the API restarts, and Entity Spawning shows "Disabled" when the server config has no value for it
- On a mod detail page the Installed tab does nothing, and a browse link with a page past the end shows an empty page
- The installed mods table scrolls sideways on tablets, the Settings tab list scrolls the page sideways on phones, and the Game Settings title row is wider than the settings panel on wide screens

### Target State

- Nulls in mod database data cannot fail a lookup, a browse page or an update check, and every error state on the detail page leads back to the browser
- Install picks the newest stable release of the mod that was asked for, and "(Latest)" names that release
- Operations on the same mod cannot run into each other; the second one is refused with 409
- Installed status is the same on browse cards, the detail page and the Installed list
- Monitor keys never receive the server password
- Settings take effect as saved and show what the game actually uses
- Mods navigation and layouts work at every width

---

### Story 17.1: Mod Detail Pages Cannot Fail on Bad Data

As an **administrator**,
I want **every mod in the browser to open, whatever the mod database returns for it**,
So that **one odd release does not hide a mod I want to install**.

**Acceptance Criteria:**

**Given** a mod whose releases include one with `"fileid": null` (for example `canjewelry`)
**When** I request `GET /api/v1alpha1/mods/lookup/{slug}`
**Then** the response is 200, every release is listed, and that release has `file_id: null`

*(Covers FR177)*

**Given** a mod database entry or listing item with `null` in any field the API reads, or a `null` element inside `tags`
**When** I look the mod up, browse with each sort, filter by tag, list tags, or run an update check
**Then** each request succeeds, the field has its default value, and null list elements are dropped

*(Covers FR177)*

**Given** the mod database data enters the API
**When** it is read by lookup, browse, search, sort, install and update checks
**Then** it has passed through one normalization step (Epic 17 ADR-1), and no caller relies on `.get(key, default)` to handle a null

*(Covers FR177)*

**Given** a mod detail page that fails to load (API error, unknown mod, or incomplete response)
**When** the error is shown
**Then** it has a Back to Browse link that returns to the browse state the page was opened from, as the loaded page does

*(Covers FR178)*

**Tasks:**

- [ ] Add the mod and release normalizers and apply them where `ModApiClient` receives mod database data (`VSS-a0r`, ADR-1)
- [ ] `ModRelease.file_id: int | None`; `fileId: number | null` in the web types
- [ ] Remove the per-field defaults the normalizers replace in `services/mods.py`, `routers/mods.py` and `services/mod_api.py`; use the release normalizer in `StoredRelease.from_api`
- [ ] Add Back to Browse to `ModDetailError`, reusing `browseTarget` and `MOD_DETAIL_RETURN_STATE` (`VSS-fv7`)
- [ ] Tests: a fixture with the `canjewelry` shape and one with a null in every field, against lookup, browse, each sort, tags and the update check; `ModDetailPage.test.tsx` for the three error states
- [ ] Browser verification: C&N Jewelry opens in the mod browser

---

### Story 17.2: Install Picks the Right Release

As an **administrator**,
I want **Install to give me the newest stable release of the mod I chose**,
So that **I do not end up with a different mod or a pre-release I did not ask for**.

**Acceptance Criteria:**

**Given** a mod database entry that ships several mod IDs (for example `instruments`, `vsinstruments`, `vsinstrumentsbase`)
**When** I install one of them, with or without a version
**Then** only releases with that mod ID are considered, and the installed mod has that mod ID

*(Covers FR179)*

**Given** a mod whose newest release is a pre-release (for example `carryon` with `2.0.0-rc.1`)
**When** I install it without naming a version
**Then** the newest stable release is installed

*(Covers FR180)*

**Given** the same mod
**When** I install it naming the pre-release version
**Then** that pre-release is installed

*(Covers FR180)*

**Given** a mod ID that has only pre-releases
**When** I install it without naming a version
**Then** its newest release is installed

*(Covers FR180)*

**Given** a version that no release of that mod ID has, including one that exists only under another mod ID of the entry
**When** I install naming it
**Then** the response is 404 `MOD_VERSION_NOT_FOUND` and nothing is installed

*(Covers FR179)*

**Given** a release with no file ID
**When** releases are chosen for install
**Then** it is never picked by default, and naming it fails with an error that says the release has no downloadable file, without a download request

*(Covers FR180)*

**Given** a mod's detail page or browse card
**When** I look at the install version list and the "(Latest)" label
**Then** the list holds only the releases of the mod ID that will be installed, "(Latest)" marks the release a plain install picks, and that release is preselected

*(Covers FR181)*

**Tasks:**

- [ ] One release selection function implementing Epic 17 ADR-2, used by `ModApiClient.download_mod` (`VSS-jhf`, `VSS-43b`)
- [ ] Lookup: `latest_version` from the same function, `install_mod_id` in the response, and `_compatibility_modid` defaulting to the install mod ID
- [ ] Web: install section and installed section list and label releases per ADR-2; an install with no chosen version sends no version (check what the API does today with `ModCard`'s `'latest'` string)
- [ ] Tests with `mod_instruments.json` and `mod_carryon.json`, a pre-release-only fixture, and a release without a file ID
- [ ] Browser verification: install `carryon` from a browse card and from its detail page

---

### Story 17.3: Mod Operations Are Safe Against Each Other

As an **administrator**,
I want **two operations on the same mod never to run at the same time**,
So that **a remove or toggle during an update cannot leave the mod half changed**.

**Acceptance Criteria:**

**Given** an install or version change is running for a mod
**When** I install, enable, disable, remove or change the version of the same mod
**Then** the request returns 409 `MOD_OPERATION_IN_PROGRESS`, and the mod's file and state are exactly what the running operation leaves

*(Covers FR182)*

**Given** two install requests for the same mod arrive together
**When** both are processed
**Then** one installs the mod and the other returns 409

*(Covers FR182)*

**Given** an operation is running for one mod
**When** I change a different mod
**Then** it proceeds without waiting

*(Covers FR182)*

**Given** Update All reaches a mod that is busy
**When** its version change is refused
**Then** that mod is reported as failed and the remaining mods are still processed, as today

*(Covers FR182)*

**Given** a mod archive whose `modinfo.json` uses `ModID`, `Version` or other capitalized top-level keys
**When** it is installed, or placed by a version change
**Then** it is imported with its real mod ID and version, and its `modinfo.json` is cached, the same as an archive with lowercase keys

*(Covers FR183)*

**Tasks:**

- [ ] Replace `_version_locks` with one per-mod operation lock used by install, enable, disable, remove and version change (`VSS-8wg`, Epic 17 ADR-3)
- [ ] `ModOperationInProgressError` and `MOD_OPERATION_IN_PROGRESS` (409) on all five routes; remove `MOD_VERSION_CHANGE_IN_PROGRESS`; update Update All's error handling and the API documentation
- [ ] Share the top-level key normalization between `read_modinfo` and `import_mod` (`VSS-0jl`)
- [ ] Tests: hold the lock with a blocked download and call each operation; concurrent installs; an archive with capitalized keys through install and version change

---

### Story 17.4: Installed Status Is Right Everywhere

As an **administrator**,
I want **a mod I have installed to show as installed, with its update status, wherever I see it**,
So that **I do not install a mod twice or wonder whether a new mod is up to date**.

**Acceptance Criteria:**

**Given** a mod database entry with several mod IDs, and I have installed one that is not its first
**When** I see the entry's card in the mod browser
**Then** the card shows Installed, as its detail page does

*(Covers FR184)*

**Given** the browse API
**When** it returns a mod
**Then** the item lists every mod ID of the entry (`mod_ids`), taken from the listing data without a request per mod

*(Covers FR184)*

**Given** I have just installed a mod
**When** I open the Installed list without running an update check
**Then** its Available column shows a real status ("Up to date" or an offered update), computed from the mod database data the install already fetched

*(Covers FR185)*

**Given** a mod with no stored update data (for example one found on disk at startup)
**When** I open the Installed list
**Then** its Available column shows "Not checked yet", not "Unknown"

*(Covers FR185)*

**Tasks:**

- [ ] Add `mod_ids` to `ModBrowseItem` from the listing's `modidstrs`; match installed mods against them on browse cards, reusing `web/src/lib/mod-ids.ts` (`VSS-49n`)
- [ ] After a successful install, store that mod's update record from the lookup the install made; a failure to store it must not fail the install (`VSS-br2`)
- [ ] Label the `not_checked` reason "Not checked yet" in `ModUpdateCell`
- [ ] Tests, including the `instruments` entry on a browse card

---

### Story 17.5: Monitor Keys Cannot Read the Server Password

As a **server owner**,
I want **a Monitor key never to receive the game server password**,
So that **I can hand out read-only access without handing out the password**.

*(Open question settled in this story: redact the password for Monitor, or make the endpoints Admin-only. Recommended default, used by the criteria below: redact (Epic 17 ADR-4), because the PRD gives Monitor read access to configuration (FR21, FR22) limited to non-sensitive data (FR32).)*

**Acceptance Criteria:**

**Given** a Monitor key and a server with a password set
**When** I request `GET /api/v1alpha1/config/game`
**Then** the Password setting has `value: null`, `secret: true` and `configured: true`, and the password appears nowhere in the response

*(Covers FR186)*

**Given** a Monitor key
**When** I request `serverconfig.json` through `GET /api/v1alpha1/config/files/...`, by any path that resolves to that file
**Then** the `Password` value is replaced by `"[redacted]"` when one is set and stays null when none is

*(Covers FR186)*

**Given** an Admin key
**When** I request either endpoint
**Then** the password is returned as today

*(Covers FR186)*

**Given** a Monitor key in the web UI
**When** I open Game Settings
**Then** Password shows "Set" or "Not set" and offers no reveal control

*(Covers FR186)*

**Tasks:**

- [ ] Record the redact-or-restrict choice in the story file before implementing
- [ ] `secret` flag on `ServerSetting`; role-dependent output in `GameConfigService.get_settings` and `ConfigFilesService.read_file`, redacted unless the caller is Admin (`VSS-qed`)
- [ ] Check a server-generated `serverconfig.json` for other secret fields and add any to the list
- [ ] Web: render a secret setting without a value as "Set" or "Not set"
- [ ] Tests for both endpoints and both roles, including alternate paths to `serverconfig.json`

---

### Story 17.6: Settings Behave as Saved

As an **administrator**,
I want **a setting to do what the screen says once I have saved it**,
So that **I do not have to restart the API or guess what the game is using**.

*(Open question settled in this story: VintageStory's default for `EntitySpawning` when `serverconfig.json` has no value. Recommended default, used by the criteria below: on, as `agentdocs/vs-serverconfig-commands.md` states; the story confirms it against a freshly generated server config before relying on it.)*

**Acceptance Criteria:**

**Given** a refresh interval setting with a job running on it
**When** I save a different interval
**Then** the job's next run is one new interval from the save, without restarting the API, and Scheduled Jobs shows the new interval

*(Covers FR187)*

**Given** a refresh interval above 0
**When** I save 0
**Then** its job is removed and no longer runs

*(Covers FR187)*

**Given** a refresh interval of 0
**When** I save a value above 0
**Then** its job is registered with that interval

*(Covers FR187)*

**Given** a boolean game setting that has no value in `serverconfig.json`
**When** I open Game Settings
**Then** the switch shows the game's default for that setting and is labeled as the default (for Entity Spawning: "Enabled (default)"), not "Disabled"

*(Covers FR188)*

**Given** a boolean setting whose game default is not known to the manager
**When** it has no value
**Then** it is shown as "Not set", with neither Enabled nor Disabled implied

*(Covers FR188)*

**Given** I switch such a setting
**When** it is saved
**Then** the explicit value is written and the "default" label goes away

*(Covers FR188)*

**Tasks:**

- [ ] One function that applies an interval setting to the scheduler, used at startup and passed as `scheduler_callback` (`VSS-8bl`, Epic 17 ADR-5); covers `mod_list_refresh_interval`, `server_versions_refresh_interval` and `metrics_collection_interval`
- [ ] Confirm the game's default for each boolean setting the manager shows; return it with the setting (`default`) and render null booleans from it (`VSS-2le`)
- [ ] Tests: each interval transition for each setting; null booleans with and without a known default
- [ ] Browser verification on a config without `EntitySpawning`, restoring every changed setting

---

### Story 17.7: Mods Navigation

As an **administrator**,
I want **the Mods tabs and shared browse links to take me where they say**,
So that **I am not stuck on a detail page or looking at an empty page**.

**Acceptance Criteria:**

**Given** I am on a mod detail page
**When** I look at the Mods tabs
**Then** Browse is the active tab

*(Covers FR189)*

**Given** I am on a mod detail page
**When** I click Installed
**Then** the Installed tab opens

*(Covers FR189)*

**Given** I am on a mod detail page
**When** I click Browse
**Then** the browser opens with the state Epic 16 ADR-1 defines: the state the page was opened from, otherwise the last browse state of the session, otherwise the default

*(Covers FR189)*

**Given** a browse URL whose `page` is beyond the last page of its results
**When** the first response arrives
**Then** the URL is replaced by the last page (page 1 when there are no results) without a new history entry, and that page's mods are shown

*(Covers FR190)*

**Given** a browse URL with a valid page
**When** it loads
**Then** it is requested directly, with no extra request

*(Covers FR190)*

**Tasks:**

- [ ] `getActiveTab`: treat `/game-server/mods/browse/...` as Browse; keep the Browse tab navigating from a detail page although it is the active value (`VSS-2oz`)
- [ ] Clamp the page after the first response, with `replace` (`VSS-nhb`)
- [ ] Tests in `ModsPage.test.tsx` for both tabs on a detail page and in `BrowseTab.test.tsx` for `?page=9999`; update the detour in `web/e2e/mod-browse-state.spec.ts` to use the Installed tab

---

### Story 17.8: Layout at Tablet and Phone Widths

As an **administrator**,
I want **pages to fit the screen I am using**,
So that **I do not scroll sideways to reach a control**.

**Acceptance Criteria:**

**Given** a viewport from 768px to 1023px wide
**When** I open Installed mods, including with an update offered
**Then** nothing scrolls sideways, and each mod's version, update status and Update action, enable toggle and remove action are reachable

*(Covers FR191)*

**Given** a viewport of 1024px or wider, or narrower than 768px
**When** I open Installed mods
**Then** the table and the phone cards are unchanged

*(Covers FR191)*

**Given** a 390px wide viewport
**When** I open Settings and each of its tabs
**Then** the page does not scroll sideways and every tab can be reached

*(Covers FR192)*

**Given** a viewport of 1560px or wider
**When** I open Game Settings
**Then** the title and the server status badge sit within the same centered 1280px width as the settings panel

*(Covers FR193)*

**Tasks:**

- [ ] Installed mods between `md` and `lg`: follow the UX spec's tablet rule (fewer columns, update shown inline), choosing between hiding columns and using the cards up to `lg` (`VSS-dp1`)
- [ ] Settings `TabsList`: wrap or scroll inside itself on small screens (`VSS-uni`)
- [ ] Constrain the Game Settings header to the panel's maximum width, in all three states of `SettingsPage` (`VSS-143`)
- [ ] Tests, and browser measurements at 390px, 768px, 900px, 1024px and 1920px

### 4.4 Architecture (`architecture/epic-17-mod-data-fixes.md`, new) — approved

| ADR | Decision | Story |
|---|---|---|
| ADR-1 | Mod database data is normalized once, in `ModApiClient`, where it enters; a null takes the field's default, except a release's file ID, which stays null | 17.1 |
| ADR-2 | Install considers only the requested mod ID's releases that have a file, and picks the first stable one in list order unless a version is named; lookup's `latest_version` and "(Latest)" use the same function | 17.2 |
| ADR-3 | One per-mod operation lock for install, enable, disable, remove and version change; a held lock means 409 `MOD_OPERATION_IN_PROGRESS`, with no waiting | 17.3 |
| ADR-4 | Secret settings are redacted for non-Admin roles in `GET /config/game` and in the config file viewer's `serverconfig.json`; the endpoints stay open to Monitor | 17.5 |
| ADR-5 | One function applies an interval setting to the scheduler (add, replace or remove its job), used at startup and on a settings change | 17.6 |

Stories 17.4, 17.7 and 17.8 need no architecture decision.

### 4.5 Other Artifacts — approved

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | Add `epic-17` (backlog), stories `17-1` to `17-8` (backlog) and `epic-17-retrospective` (optional), via `just sprint` | Now |
| Beads | Create epic `Epic 17: Mod Data Correctness and Fixes` (`VSS-4v5`); parent the 16 in-scope issues to it; close each with an AAR when its story is done | Now, and per story |
| `architecture/index.md` | Entry for the Epic 17 ADRs | Now |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 17.1 to 17.8 from `epics.md` and the Epic 17 ADRs; 17.1 first, then 17.2 and 17.3 in that order |
| Developer (`dev-story`) | Implement each story; record the redact-or-restrict choice (17.5) and the confirmed `EntitySpawning` default (17.6) in the story file before implementing them |
| Reviewer (`code-review`) | Delegated read-only review per story |
| Maintainer (Matt) | Approved this proposal; cuts `v0.1.0-rc.4` after Story 17.1; can overturn the recommended defaults in 17.5 and 17.6 at story creation |

**Success criteria:**

- C&N Jewelry opens in the mod browser, and a fixture with nulls in every mod database field passes lookup, browse and the update check
- Installing `instruments` installs `instruments`, and installing `carryon` without a version installs its newest stable release
- A Monitor key cannot obtain the server password from any config endpoint
- Each in-scope beads issue is closed with an AAR by its story
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: `VSS-a0r` on `v0.1.0-rc.3`, with 15 accumulated fixes. [x] 1.2 type: defects found in use and in code review. [x] 1.3 evidence: section 1 and the ADRs |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete. [x] 2.5 no resequencing; order inside Epic 17 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR177-FR193 added, MVP unaffected. [x] 3.2 architecture: new Epic 17 ADRs. [N/A] 3.3 UX spec: no change. [N/A] 3.4 deployment, CI and monitoring: no change |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1, 6.2 reviewed. [x] 6.3 approved by Matt, 2026-11-15 (scope approved before the workflow ran; no interactive review of the wording). [x] 6.4 handoff in section 5 |
