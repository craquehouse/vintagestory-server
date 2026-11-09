# Story 14.0: Epic 14 Technical Preparation

Status: done

<!-- API spike story (template-api-spike). Complete before Stories 14.1-14.6: their designs rest on the assumptions this story verifies. -->

## Story

As a **developer**,
I want **mod release behavior verified against the live mod database**,
so that **update logic rests on confirmed behavior**.

## Acceptance Criteria

1. **Given** the live mod API
   **When** releases are inspected for several mods
   **Then** findings document release ordering, whether old releases remain listed, and how filenames vary between versions
   **And** findings state whether a release's `modversion` and `modidstr` always match the `version` and `modid` in that release's `modinfo.json`

2. **Given** a mod file is replaced while the game server is running
   **When** the behavior is tested
   **Then** findings document whether replacement is safe before a restart
   **And** whether the server tolerates two versions of the same mod in the mods directory at once

3. **Given** common webhook receivers
   **When** payload requirements are researched
   **Then** a payload format is documented that works with Discord and generic receivers

4. **Given** real API responses were captured
   **When** fixtures are saved
   **Then** trimmed fixtures exist for Stories 14.1 and 14.2 to test against

5. **Given** the findings
   **When** they are compared with Epic 14 ADR-1 to ADR-6
   **Then** each ADR is marked confirmed or changed in `architecture/epic-14-mod-updates.md`
   **And** any assumption that failed has a recorded decision, with affected Epic 14 stories updated or backlog items created

## Tasks / Subtasks

<!-- Research story: no application code changes. Tasks produce documentation and fixtures. -->

- [x] Task 1: Verify mod release behavior against the live API (AC: 1)
  - [x] 1.1: Choose at least 5 mods, including one with many releases, one whose `urlalias` differs from `modidstrs[0]`, and one with pre-release game version tags
  - [x] 1.2: Compare release list order with each release's `created` timestamp; record any mismatch
  - [x] 1.3: Record whether old releases stay listed, and whether any `modversion` or `filename` repeats within one mod
  - [x] 1.4: Download 2 or 3 releases per mod and compare the archive's `modinfo.json` `modid` and `version` with the release's `modidstr` and `modversion`
  - [x] 1.5: Record releases with empty `tags`, and how `check_compatibility` classifies them

- [x] Task 2: Test replacing a mod while the server runs (AC: 2)
  - [x] 2.1: Run the image in a throwaway container with no host volume (never the repo's `./data`)
  - [x] 2.2: Install a 1.22 game server and an older release of a small mod, then start the server
  - [x] 2.3: Swap in a newer release (copy to a temporary name, rename over); record server log output before and after a restart
  - [x] 2.4: With the server stopped, place two versions of the same mod in the mods directory and record what the server does at startup

- [x] Task 3: Define the webhook payload (AC: 3)
  - [x] 3.1: Confirm against Discord's own documentation: 2000-character `content` limit, `allowed_mentions: {"parse": []}`, 429 handling with `retry_after`, and whether unknown top-level fields are accepted
  - [x] 3.2: Draft the payload: `content` summary plus a structured `updates` list; define truncation for long lists
  - [x] 3.3: Verify the payload against a local HTTP receiver; if the user provides a Discord test webhook, verify there too

- [x] Task 4: Create test fixtures (AC: 4)
  - [x] 4.1: Create `api/tests/fixtures/moddb/` and save 3 trimmed `/api/mod/{slug}` responses
  - [x] 4.2: Remove `text`, `screenshots` and long `changelog` HTML; keep release order, `modversion`, `filename`, `fileid`, `tags`, `modidstr`, `created`
  - [x] 4.3: Add a short README in that directory naming each fixture's source mod, capture date and the cases it covers

- [x] Task 5: Record findings and update plans (AC: 5)
  - [x] 5.1: Add a "Release behavior" section to `agentdocs/vintagestory-modapi.md`
  - [x] 5.2: Mark each ADR in `architecture/epic-14-mod-updates.md` as confirmed or changed, with evidence
  - [x] 5.3: If an assumption failed, record the decision; update the affected Epic 14 stories in `epics.md`, or create a bead for follow-up work
  - [x] 5.4: Run `just check` to confirm nothing broke

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] Story 14.2 omits ADR-1's warning for switching a stable install to a pre-release; a pre-release tagged for the current game version would switch without confirmation [epics.md Story 14.2; architecture/epic-14-mod-updates.md ADR-1]
- [x] [AI-Review][Medium] Story 14.2 and ADR-2 do not restrict the target release to the installed mod's modid; existing selection picks by version across all modids (instruments `1.0.1` exists under two modids) [epics.md Story 14.2; mod_api.py:352-358]
- [x] [AI-Review][Medium] "Older than the installed version" is undefined under the publish-order rule (CarryOn `2.0.0-pre.8` → `1.14.3`) [epics.md Story 14.2; prd.md FR141]
- [x] [AI-Review][Low] Webhook `updates` field `slug` does not name which identifier it carries [architecture/epic-14-mod-updates.md ADR-6]
- [x] [AI-Review][Low] PRD FR130 is not annotated with the pre-release narrowing [prd.md FR130]
- [x] [AI-Review][Low] Spike scripts and raw data are not committed; the story cites a scratchpad path [story Dev Agent Record, Task 2]
- [x] [AI-Review][Low] The `-` pre-release heuristic misclassifies a stable version such as `1.0.0-hotfix-2`; not acknowledged [architecture/epic-14-mod-updates.md ADR-1]
- [x] [AI-Review][Low] Discord delivery verified only against documentation and a local receiver; Story 14.6 has no live or replayed check [epics.md Story 14.6]
- [x] [AI-Review][Medium] ADR-1 lets a mod on a pre-release be offered a list-newer but version-older stable release (CarryOn `2.0.0-pre.8` would be offered `1.14.3`) [architecture/epic-14-mod-updates.md ADR-1; prd.md FR130; epics.md Story 14.1]
- [x] [AI-Review][Low] FR140 is not annotated with the installed-modid restriction [prd.md FR140]
- [x] [AI-Review][Low] Spike README says the probe downloads 12 releases (10 succeed) and does not mention the `findings.json` rename [14-0-spike/README.md]

## Dev Notes

### Why this story matters

Every Epic 14 design depends on these assumptions. If one is wrong, fix the plan here rather than mid-implementation.

| Assumption | Used by | If it fails |
|---|---|---|
| Releases are newest first, and old ones stay listed | ADR-1 detection, ADR-3 rollback | Sort by `created`; rollback needs file retention |
| Release `modversion` equals the installed `modinfo.json` version | ADR-1: the installed release is found by version | Every mod reports `unknown`; matching needs another key, such as filename |
| Release `modidstr` equals the archive's `modid` | ADR-2 validation | The validation rule changes |
| Each release has a distinct `filename` | ADR-2 swap, ADR-3 cache reuse | A cached file could be served for the wrong version; cache key must change |
| Replacing a file under a running server is safe | ADR-2 | Version change must require a stopped server |
| Discord accepts `content` plus extra fields | ADR-6 | Payload must be receiver-specific |

### Existing code to study (do not change it in this story)

- `api/src/vintagestory_api/services/mod_api.py`
  - `ModApiClient.get_mod()`: no response caching; every call hits ModDB.
  - `download_mod()`: streams to `{cache_dir}/mods/{filename}`, writes `.tmp`, then renames.
  - `check_compatibility()`: release-level status.
- `api/src/vintagestory_api/services/mod_state.py`
  - `import_mod()` and `_extract_modinfo_from_zip()`: where the installed `modid` and `version` come from.
  - `ModState` is keyed by filename.
- `api/src/vintagestory_api/services/mods.py`
  - `install_mod()`: the existing download, copy and atomic-rename sequence to reuse in Story 14.2.
  - `enable_mod()` and `disable_mod()`: the `.zip.disabled` convention.
- `api/src/vintagestory_api/jobs/mod_cache_refresh.py`: the job ADR-5 extends.
- Paths (`config.py`): cache is `/data/vsmanager/cache`, state is `/data/vsmanager/state`, mods are `/data/serverdata/Mods`.

### API facts already documented

From `agentdocs/vintagestory-modapi.md`:
- `statuscode` is a string (`"200"`).
- Releases are documented as newest first, but never verified for Epic 14.
- `/download?fileid=` redirects to the CDN, so use `follow_redirects=True`.
- CDN files are named `{modname}_{version}_{hash}.zip`, while the release `filename` drops the hash.
- No documented rate limits. Keep requests few and sequential: a few dozen in total is plenty.

### Webhook facts to confirm (Task 3)

From Discord's webhook documentation and client libraries:
- `content` is limited to 2000 characters.
- Set `allowed_mentions` to `{"parse": []}`. Mod names come from ModDB and could contain `@everyone`.
- A 429 response includes `retry_after` in seconds. Recommend at most one retry, or skipping until the next check; never block the job.
- Whether unknown top-level fields like `updates` are accepted is unconfirmed; test it.

### Security

- Never commit a real webhook URL or log it. If testing against Discord, get the URL through a private prompt, not chat, and delete the webhook afterwards.
- Fixtures must contain only public ModDB data.

### Testing Requirements

- This is a research story with no application code, so no new tests are required.
- `just check` must still pass, since fixtures sit under `api/tests/`.
- Fixtures must be valid JSON and small, under 20 KB each.

### Development Commands

- `just check`: full validation
- Throwaway container (Task 2), port 18080 bound to localhost only and no host volume:
  `docker run -d --rm --name vss-spike --platform linux/amd64 -p 127.0.0.1:18080:8080 -e VS_API_KEY_ADMIN=<throwaway> <image>`
- The image comes from `docker build --platform linux/amd64 -t vss-spike .`

### Project Structure Notes

- **New directory:** `api/tests/fixtures/moddb/`. No fixtures directory exists yet; existing tests build data inline, as `SMITHINGPLUS_MOD` in `tests/test_mod_api.py` does.
- **Documentation changes:** `agentdocs/vintagestory-modapi.md`, `_bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md`, and `epics.md` only if a story needs changing.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.0]
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-1 to ADR-6
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-09.md] scope decisions
- [Source: agentdocs/vintagestory-modapi.md] current API documentation
- [Source: _bmad-output/implementation-artifacts/13-0-epic-13-technical-preparation.md] previous preparation story
- [Source: project-context.md] Security Patterns §3 "Never Log Sensitive Data"; Critical Rules §6 "Atomic File Writes"
- [Discord: Webhook resource](https://docs.discord.com/developers/resources/webhook)

## Senior Developer Review (AI)

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review
**Outcome:** Changes Requested

**Summary:** The spike work is well evidenced. Fixtures match their README and the live API (8 spot-checks), Discord documentation claims were confirmed, and `just check` passed (1833 API, 2911 web). The plans it produced leave Story 14.2 open to guesswork in three places.

### Action Items

- [x] [Medium] Story 14.2 omits ADR-1's warning for switching a stable install to a pre-release; a pre-release tagged for the current game version would switch without confirmation [epics.md Story 14.2; architecture/epic-14-mod-updates.md ADR-1]
- [x] [Medium] Story 14.2 and ADR-2 do not restrict the target release to the installed mod's modid; existing selection picks by version across all modids (instruments `1.0.1` exists under two modids) [epics.md Story 14.2; mod_api.py:352-358]
- [x] [Medium] "Older than the installed version" is undefined under the publish-order rule (CarryOn `2.0.0-pre.8` → `1.14.3`) [epics.md Story 14.2; prd.md FR141]
- [x] [Low] Webhook `updates` field `slug` does not name which identifier it carries [architecture/epic-14-mod-updates.md ADR-6]
- [x] [Low] PRD FR130 is not annotated with the pre-release narrowing [prd.md FR130]
- [x] [Low] Spike scripts and raw data are not committed; the story cites a scratchpad path [story Dev Agent Record, Task 2]
- [x] [Low] The `-` pre-release heuristic misclassifies a stable version such as `1.0.0-hotfix-2`; not acknowledged [architecture/epic-14-mod-updates.md ADR-1]
- [x] [Low] Discord delivery verified only against documentation and a local receiver; Story 14.6 has no live or replayed check [epics.md Story 14.6]

### Verified Correct

- Fixtures: valid JSON, 26 B to 10,408 B, trimmed as documented, order preserved; every claimed case present
- Live API: CarryOn order, `urlalias` not a lookup key, repeated filenames, removed-mod 404 shape, instruments modid span
- Code claims: unsanitized `filename` paths (VSS-432), `check_compatibility` empty-tag behavior, ADR-5 interval and gating
- Discord documentation claims; story File List matches the git diff

### Not Checked by the Reviewer

- Task 2 container experiment (Docker not permitted in the review)
- Task 1 aggregate statistics and the spike scripts (not committed)

## Senior Developer Review (AI): Follow-up

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of commits `c8a076f`..`0b1cf30`
**Outcome:** Changes Requested

**Summary:** All eight earlier findings verified resolved, with consistent wording across ADRs, stories and PRD; BMAD bookkeeping correct; `stats.py` reproduces every quoted figure; no secrets in `14-0-spike/`; `just check` passed (1833 API, 2911 web). One new Medium design gap and two Low documentation issues.

### Action Items

- [x] [Medium] ADR-1 lets a mod on a pre-release be offered a list-newer but version-older stable release (CarryOn `2.0.0-pre.8` would be offered `1.14.3`) [architecture/epic-14-mod-updates.md ADR-1; prd.md FR130; epics.md Story 14.1]
- [x] [Low] FR140 is not annotated with the installed-modid restriction [prd.md FR140]
- [x] [Low] Spike README says the probe downloads 12 releases (10 succeed) and does not mention the `findings.json` rename [14-0-spike/README.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Findings Summary

**Task 1: ModDB release behavior (live API, 2026-11-09).** 10 mods sampled (464 releases); 10 releases downloaded and parsed with `ModStateManager._extract_modinfo_from_zip`.

| Question | Finding |
|---|---|
| Release order | Newest first in all 10 mods, by both `created` and `releaseid` |
| Old releases stay listed | Yes; up to 89 releases per mod, back to 1.15-era versions |
| `modversion` equals archive `modinfo.json` version | Yes, 10 of 10 |
| `modidstr` equals archive `modid` | Yes, 10 of 10 |
| One modid per ModDB entry | **No.** 225 of 4,852 entries list several modids. `instruments` spans `instruments`, `vsinstruments`, `vsinstrumentsbase`; `hudclock` includes `hudclockserver` releases |
| `modversion` unique within an entry | **No.** `instruments` repeats `1.0.1` under different modids |
| `filename` unique within an entry | **No.** `egocaribautomapmarkers` reuses `Auto Map Markers.zip` and `Auto Map Markers (1.19).zip` |
| Lookup keys | `/api/mod/{key}` resolves any release `modidstr` or the numeric ModDB `modid`; **not** `urlalias` |
| Removed mods | `maltiezfirearms` (in the January export) now returns `"404"` under every key |
| Empty `tags` | None seen. Pre-release tags (for example `1.22.0-rc.1`) are common; against 1.22.7 they classify as `not_verified` |
| Compatibility against 1.22.7 | Most popular mods have only 2-8 `compatible` releases, often only `not_verified` ones |
| Filenames | 70 of 464 contain spaces; none contain path separators. CDN URLs add a hash, the `filename` does not |

**Pre-existing risk found:** `mod_api.py:366-367` and `mods.py:712` build file paths directly from the ModDB-supplied `filename` without sanitizing it.

**Release order is not version order.** CarryOn lists `2.0.0-rc.1`, then `1.14.3`, then `2.0.0-pre.8`: a 1.x maintenance release was published after a 2.0 pre-release. Under ADR-1 as written, a user on stable `1.14.3` would be offered `2.0.0-rc.1`. Pre-release mod versions (`-rc`, `-pre`, `-dev`) are common among compatible releases.

**Task 2: Replacing a mod under a running server (2026-11-09).** Throwaway container from this branch's image, VintageStory 1.22.7, code mod Auto Map Markers (`egocaribautomapmarkers`). Script and full log: `14-0-spike/swap_test.py` and `14-0-spike/swap_test.log`.

| Step | Result |
|---|---|
| Boot with 5.0.2 | Loaded: "Mods, sorted by dependency: game, egocaribautomapmarkers, creative, survival" |
| Swap to 5.0.3 while running (temp file, rename into place, delete old) | Server kept running; no errors or reload in the 30 seconds after; only an emulation "tick took 582ms" warning |
| Restart | Loaded `Auto Map Markers 5.0.3 - Vintage Story 1.22.zip` with no errors |
| Both versions present at startup | Warning: "Multiple mods share the mod ID 'egocaribautomapmarkers' (…5.0.2…, …5.0.3…)". Only 5.0.3 loaded. The log line was truncated by the capture filter, so whether the game picks by version or by filename order is unconfirmed |
| API view with both files present | `GET /mods` listed only 5.0.2: the API and the game disagreed about the installed version |

**Task 3: Webhook payload (2026-11-09).** Discord facts from its own documentation:

| Fact | Source |
|---|---|
| `content` "up to 2000 characters"; at least one of `content`, `embeds`, `components`, `file`, `poll` required | [Webhook resource](https://docs.discord.com/developers/resources/webhook) |
| Guidance: use `allowed_mentions` "to prevent unexpected mentions" | Same page |
| Success: `204 No Content` unless `wait=true` | Same page |
| Unknown top-level fields: **not specified** | Same page |
| 429 body: `message`, `retry_after` (float seconds), `global`, optional `code`; `Retry-After` and `X-RateLimit-*` headers | [Rate limits](https://docs.discord.com/developers/topics/rate-limits) |
| Separate Slack-compatible (`/slack`) and GitHub-compatible (`/github`) execute endpoints exist | Webhook resource |

Because Discord does not document how it treats extra fields, a single combined payload relies on unspecified behavior. Prototype (`14-0-spike/webhook_probe.py`) sends a receiver-specific payload instead:

- **Discord URL** (host `discord.com`, `discordapp.com`, `ptb.discord.com` or `canary.discord.com`, path starting `/api/webhooks/`): `{"content": <summary>, "allowed_mentions": {"parse": []}}`
- **Any other URL:** `{"event": "mod_updates_available", "content": <summary>, "updates": [{"slug", "name", "installed", "offered", "compatibility"}]}`
- **Summary:** one line per mod, `- {name}: {installed} → {offered} ({compatibility})`, truncated with "…and N more" to stay under 2000 characters

Verified against a local receiver with httpx (`follow_redirects=False`): generic delivery returned 204 with all three fields; a 302 response was not followed; a 429 body's `retry_after` was read; 80 updates produced 1,950 characters ending "…and 49 more"; mod names containing `@everyone` stay as text with mentions suppressed; look-alike hosts (`discord.com.evil.example`, a `/discord.com/` path) were not treated as Discord. **Not verified against a live Discord webhook**: none was provided.

### API Quirks Discovered

- A not-found response is `{"statuscode": "404"}` with no `mod` key (the API doc showed `"mod": null`; corrected)
- `urlalias` is not a lookup key; any release `modidstr` and the numeric ModDB `modid` are
- Publish order is not version order; maintenance releases can follow a pre-release
- One ModDB entry can hold several modids; `modversion` and `filename` repeat within an entry
- Release `filename` is author-chosen text, often with spaces

### Architecture Decisions Made

Recorded in `architecture/epic-14-mod-updates.md`, each ADR now marked with its status:

| ADR | Status | Change |
|---|---|---|
| ADR-1 Detection | Changed | Filter releases to the installed modid; identify the installed release by modid and version; stable installs are offered only stable releases (user decision 2026-11-09); mods on a pre-release can be offered a newer release only if its base version is not lower (follow-up review) |
| ADR-2 Version change | Changed | Validate archive modid **and** version; use only the final path component of `filename`; failing to delete the old file rolls the change back |
| ADR-3 Rollback source | Changed | Reuse a cached file only after it validates as the target release |
| ADR-4 Status store | Confirmed | Store `modidstr` with each release |
| ADR-5 Scheduled checks | Confirmed | No change |
| ADR-6 Webhook | Changed | Receiver-specific payload; mentions suppressed; mark alerts sent only after a 2xx response |

Epic 14 stories updated in `epics.md`: 14.1 (modid filtering, pre-release rule), 14.2 (archive version check, filename rule, failed delete), 14.6 (payload, retry on next check). PRD FR130 still reads "newest newer release compatible…"; the pre-release rule narrows it and lives in ADR-1 and Story 14.1.

### Backlog Items Created

- `VSS-432` [API-061] (P1, bug): sanitize ModDB-supplied release filenames in the existing install path
- `VSS-jhf` [API-062] (P2, bug): mod install can pick a release from a different modid in the same ModDB entry (found in code review)

### Completion Notes List

- Task 1: Sampled 10 mods (464 releases) from the live API and parsed 10 archives with the project's own extractor. Release order and `modversion`/`modidstr` agreement held; several modids per entry, repeated filenames and versions, and publish-order versus version-order did not.
- Task 2: In a throwaway container with no host volume, replaced Auto Map Markers 5.0.2 with 5.0.3 under a running 1.22.7 server without errors; 5.0.3 loaded on restart. Two copies of one modid produce a warning and only one loads, while the API reports the other.
- Task 3: Confirmed Discord's limits from its own documentation; prototyped a receiver-specific payload and verified it against a local receiver (204, redirect not followed, 429 `retry_after` read, truncation to 1,950 characters, mention suppression, look-alike hosts rejected). Not tested against a live Discord webhook; none was provided.
- Task 4: Added four fixtures (largest 10.4 KB) and a README covering each case.
- Task 5: Documented release behavior, marked all six ADRs, updated three stories, filed `VSS-432`. `just check` passes: 1833 API tests, 2911 web tests.
- Spike scripts, trimmed sampled data and logs are in `_bmad-output/implementation-artifacts/14-0-spike/`; `stats.py` reproduces the aggregate figures.
- ✅ Resolved review finding [Medium]: Story 14.2 and FR141 require confirmation for a pre-release when the installed version is stable; Story 14.3 lists the warning; ADR-2 and `MOD_CONFIRMATION_REQUIRED` state the same conditions.
- ✅ Resolved review finding [Medium]: ADR-2 step 1 and Story 14.2 resolve the target only among releases with the installed modid and reject other modids; Story 14.2 requires tests with the instruments and CarryOn fixtures. The same flaw in today's install path is filed as `VSS-jhf` [API-062].
- ✅ Resolved review finding [Medium]: ADR-1 defines newer and older as position in the release list for the installed modid; Story 14.2 and FR141 use that definition.
- ✅ Resolved review finding [Low]: ADR-6 states that `slug` is the installed mod's modid, the identifier used in `/mods/{slug}`.
- ✅ Resolved review finding [Low]: FR130 now states the pre-release rule and points to Epic 14 ADR-1.
- ✅ Resolved review finding [Low]: ADR-1 records the `1.0.0-hotfix-2` limitation and that no such version was sampled.
- ✅ Resolved review finding [Low]: Story 14.6 tasks add tests replaying Discord `204` and `429` responses and a manual check against a test Discord webhook.
- ✅ Resolved review finding [Low]: Committed the scripts, trimmed sampled data, logs and a README in `_bmad-output/implementation-artifacts/14-0-spike/`; `stats.py` reproduces every aggregate figure from committed data.
- ✅ Resolved review finding [Medium]: ADR-1, FR129, FR130 and Story 14.1 add a base-version check for mods on a pre-release (numeric part before `-`, compared component by component; no offer if unparsable). Story 14.1 requires CarryOn fixture tests proving `2.0.0-pre.8` is offered `2.0.0-rc.1` but never `1.14.3`.
- ✅ Resolved review finding [Low]: FR140 now limits switching to releases for the installed mod's modid.
- ✅ Resolved review finding [Low]: README states 10 downloads, two from each of five mods (the sixth mod's lookup returns 404), and documents the `findings.json` rename.

### File List

- Created: `api/tests/fixtures/moddb/README.md`
- Created: `api/tests/fixtures/moddb/mod_carryon.json`
- Created: `api/tests/fixtures/moddb/mod_instruments.json`
- Created: `api/tests/fixtures/moddb/mod_egocaribautomapmarkers.json`
- Created: `api/tests/fixtures/moddb/mod_not_found.json`
- Modified: `agentdocs/vintagestory-modapi.md`
- Modified: `_bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md`
- Modified: `_bmad-output/planning-artifacts/epics.md`
- Modified: `_bmad-output/implementation-artifacts/14-0-epic-14-technical-preparation.md`
- Modified: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Modified: `_bmad-output/planning-artifacts/prd.md` (FR130, FR141; review follow-ups)
- Created: `_bmad-output/implementation-artifacts/14-0-spike/` (`README.md`, `moddb_probe.py`, `probe-findings.json`, `sampled-releases.json`, `stats.py`, `stats.txt`, `swap_test.py`, `swap_test.log`, `webhook_probe.py`)

## Change Log

- 2026-11-09: Completed the Epic 14 API spike. Verified ModDB release behavior and live mod replacement, defined the webhook payload, added fixtures, and updated ADR-1 to ADR-6 and Stories 14.1, 14.2 and 14.6 with the findings.
- 2026-11-09: Addressed code review findings - 8 items resolved (3 Medium, 5 Low). Story 14.2 and ADR-2 now restrict version changes to the installed modid and require confirmation for pre-releases and older releases; ADR-1 defines older by release order; ADR-6 names the `slug` field; FR130 and FR141 updated; Story 14.6 adds Discord checks; spike evidence committed. Filed `VSS-jhf` for the same modid flaw in the existing install path.
- 2026-11-09: Addressed follow-up review findings - 3 items resolved (1 Medium, 2 Low). Mods on a pre-release are only offered releases whose base version is not lower (ADR-1, FR129, FR130, Story 14.1); FR140 limited to the installed modid; spike README corrected.
- 2026-11-09: Second follow-up review approved. Clarified per-release versus installed parse failure in ADR-1 and Story 14.1, recorded the stable-install base-version limitation in ADR-1, and corrected the story's own summary row and README note. Story marked done.
