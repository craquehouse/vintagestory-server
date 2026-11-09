# Story 14.0: Epic 14 Technical Preparation

Status: ready-for-dev

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

- [ ] Task 2: Test replacing a mod while the server runs (AC: 2)
  - [ ] 2.1: Run the image in a throwaway container with no host volume (never the repo's `./data`)
  - [ ] 2.2: Install a 1.22 game server and an older release of a small mod, then start the server
  - [ ] 2.3: Swap in a newer release (copy to a temporary name, rename over); record server log output before and after a restart
  - [ ] 2.4: With the server stopped, place two versions of the same mod in the mods directory and record what the server does at startup

- [ ] Task 3: Define the webhook payload (AC: 3)
  - [ ] 3.1: Confirm against Discord's own documentation: 2000-character `content` limit, `allowed_mentions: {"parse": []}`, 429 handling with `retry_after`, and whether unknown top-level fields are accepted
  - [ ] 3.2: Draft the payload: `content` summary plus a structured `updates` list; define truncation for long lists
  - [ ] 3.3: Verify the payload against a local HTTP receiver; if the user provides a Discord test webhook, verify there too

- [ ] Task 4: Create test fixtures (AC: 4)
  - [ ] 4.1: Create `api/tests/fixtures/moddb/` and save 3 trimmed `/api/mod/{slug}` responses
  - [ ] 4.2: Remove `text`, `screenshots` and long `changelog` HTML; keep release order, `modversion`, `filename`, `fileid`, `tags`, `modidstr`, `created`
  - [ ] 4.3: Add a short README in that directory naming each fixture's source mod, capture date and the cases it covers

- [ ] Task 5: Record findings and update plans (AC: 5)
  - [ ] 5.1: Add a "Release behavior" section to `agentdocs/vintagestory-modapi.md`
  - [ ] 5.2: Mark each ADR in `architecture/epic-14-mod-updates.md` as confirmed or changed, with evidence
  - [ ] 5.3: If an assumption failed, record the decision; update the affected Epic 14 stories in `epics.md`, or create a bead for follow-up work
  - [ ] 5.4: Run `just check` to confirm nothing broke

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

### API Quirks Discovered

### Architecture Decisions Made

### Backlog Items Created

### Completion Notes List

### File List
