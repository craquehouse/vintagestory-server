# Sprint Change Proposal: Config File Editing (Epic 23)

**Date:** 2026-11-19
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (scope named by the maintainer; product decisions asked in two rounds)
**Scope classification:** Minor
**Status:** Scope named by Matt (2026-11-19): `VSS-ato4` → `VSS-glz` → `VSS-hb4d`. On the planner's proposal he approved pulling in `VSS-o8s` and `VSS-7z3`. The same day he answered eight questions (section 5). Seven stories, five beads. Matt approved this proposal the same day; `sprint-status.yaml` has `epic-23` and its seven stories (backlog), and the epic bead `VSS-7f7s` has the five beads as children. Planner decisions not reviewed yet are listed in section 5.

## 1. Issue Summary

**Trigger:** Epic 22 is done and released (`v0.1.0-rc.8`, `main` at `fc525885`). The maintainer named the next epic from a chain of three beads: `VSS-ato4` (bug, P2) blocks `VSS-glz` (P2), which blocks `VSS-hb4d` (P3). The backlog rule (2026-11-17) applies: the epic draws the backlog down, related beads that share its files are proposed as pull-ins, and what planning finds goes into a story.

**Problem:** On the live server, `ModConfig/seasonalflowers.json` shows a parse error, because the viewer's strict JSON parser refuses the comments that the game's own reader accepts. Config files cannot be changed from the web UI at all, and a change made on the host keeps no record of the text it replaced. Along the way, the file browser keeps paths as slash-joined strings, and a Monitor key sees Game Settings fields that fail with 403 when saved.

**Evidence** (code at `fc525885`; details and line references in `architecture/epic-23-config-file-editing.md`, "Facts Checked in the Code"):

- `read_file` parses with strict `json.loads` (`services/config_files.py:429`). The web `FileViewer` pretty-prints the `_raw`/`_parse_error` fallback as an object (`FileViewer.tsx:121`). Monitor sees a commented file hidden entirely (`_raw: "[redacted]"`).
- The read returns no raw text and no version, so nothing could support an editor that keeps comments or a stale-write check.
- `GameConfigService`, Story 22.7's `reapply_edits` and config init all read `serverconfig.json` as strict JSON and write it back re-serialized.
- `ServerService` has `_lifecycle_lock`, `game_running` and `lifecycle_busy`. A save can hold the lock so that a start waits for it.
- `FileManagerPanel` and `PathBreadcrumb` split and join paths on `/`. `GameConfigPanel` does not read the role.
- The web has no editor or diff library. The CSP allows inline styles, 'self' scripts and no workers from elsewhere.

**Scope decisions (made by the maintainer, 2026-11-19):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-ato4`, `VSS-glz`, `VSS-hb4d`; `VSS-o8s` and `VSS-7z3` pulled in |
| Backlog rule | The epic draws the backlog down; findings go into stories; the net bead change is reported |
| Parser | JSON5 with `pyjson5` (answer 1) |
| `serverconfig.json` | Editable as strict JSON only; a save drops the pending edits it changes (answer 2) |
| Editor | CodeMirror 6 (answer 3) |
| Editable files | Every `.json` file Admin can read (answer 4) |
| Error check | An API check endpoint called while typing (answer 5) |
| History limits | Two API settings (answer 6) |
| Comparison | CodeMirror merge view (answer 7) |
| Monitor Game Settings | Disabled fields and a note (answer 8) |

**Grouping:**

| Story | Beads | Why this grouping |
|---|---|---|
| 23.1 Configs with Comments Can Be Viewed | `VSS-ato4` | The parser every later story uses, the read's new fields, and the viewer's error view |
| 23.2 File Browser Paths Are Lists of Names | `VSS-o8s` | A refactor of the panel the editor and history build on, done before them |
| 23.3 Game Settings Are Read-Only for Monitor Keys | `VSS-7z3` | The role hook the editor's button uses, with the bead's fix |
| 23.4 Config Files Can Be Saved Through the API | `VSS-glz` (first half) | The write path, the lock, the version check and the check endpoint: one API pull request to review the risky part |
| 23.5 Config Files Are Edited in the File Browser | `VSS-glz` (closes) | The editor, the new dependency, the guards and the E2E |
| 23.6 Config Edits Are Kept as History | `VSS-hb4d` (first half) | The store, its settings, its failure rule and the routes |
| 23.7 Config History in the File Browser | `VSS-hb4d` (closes) | The panel, the comparison, Restore, and the settings fields |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 22 are done; none is invalidated. One new epic, Epic 23: Config File Editing, with 7 stories. No resequencing.

**Story impact:** No existing story changes. Story 23.1 changes the reader Story 6.5 built and Story 19.1 hardened, keeping 19.1's rules. Story 23.4 extends Story 22.7's drop reasons. Story 23.3 moves Story 19.1's note and Epic 22 ADR-12's tab hiding onto one hook, with behaviour unchanged.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | FR309-FR326 added; frontmatter |
| Epics | Epic 23; FR coverage rows; Story Summary row (143 stories); frontmatter |
| Architecture | New `architecture/epic-23-config-file-editing.md` (facts, ADR-1 to ADR-9); index entry |
| UX spec | No text change. The editor and history follow the viewer's existing header and `AlertDialog` patterns, with 44px targets on phones |
| CI | No new job. Stories 23.5 and 23.7 add E2E checks to the CI set (throwaway container) |
| Project rules | None |
| Deployment and documentation | README file browser section (JSON5, editing, the stopped-server rule, history and its settings). No deployment change; the history directory is under the existing data volume |
| Beads | Epic `Epic 23: Config File Editing` with the five in-scope issues as children |

**Technical impact:**

- One new runtime API dependency, `pyjson5` (compiled; wheels for the image's platforms checked in planning).
- New web dependencies in the `@codemirror` scope, including `@codemirror/merge`, all in one chunk loaded on demand.
- The first API route that writes into `serverdata` on an admin's request. It holds the lifecycle lock while it writes.
- A new state directory, `vsmanager/state/config-history/`.
- No CSP change.

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 23.1 | `GET /config/files/{path}` | Parses JSON5; adds `parseError` for every role and `text` and `version` for Admin | Behaviour, additive fields |
| 23.4 | `PUT /config/files/{path}` | New, Admin only | New route |
| 23.4 | `POST /config/files/validate` | New, Admin only | New route |
| 23.4 | Story 22.7 pending edits | A `serverconfig.json` save drops the edits it changes (`file_edited`) | Behaviour |
| 23.6 | `GET /config/history/{path}`, `POST .../restore` | New, Admin only | New routes |
| 23.6 | `config_history_keep_count`, `config_history_max_age_days` | New API settings, default 20 and 0 | New settings |
| 23.6 | `vsmanager/state/config-history/` | New state directory | New files |
| 23.3 | Game Settings page | Disabled for keys that are not Admin | Web-only |

No route is removed, no existing field changes, and nothing is breaking.

**Draft release-note text** (commit subjects; git-cliff removes the story scope):

- Features: `feat(api): save config files through the API while the game server is stopped`; `feat(web): edit config files in the file browser while the game server is stopped`; `feat(api): keep earlier versions of config files saved through the API, and restore them`; `feat(web): see, compare and restore earlier versions of config files`
- Fixes: `fix(api): show mod configs that contain comments`; `fix(web): show a config file that cannot be parsed as text, with where the error is`; `fix(web): show game settings read-only to Monitor keys`
- No note: the dependencies (`build`), the path refactor (`refactor`), the role hook, tests and documentation

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 23 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Seven stories, each tied to an in-scope bead. Effort medium, risk medium (23.4 writes files on the data volume) |
| 2. Rollback | Not viable. Nothing completed has to be undone |
| 3. MVP Review | Not needed |

**Effort:** Medium. `VSS-glz` and `VSS-hb4d` are size-m each and split into an API story and a web story; `VSS-ato4` is size-m; `VSS-o8s` and `VSS-7z3` are small.

**Risks:**

- Story 23.4: writing into `serverdata`. The rules are the read's, plus an atomic replace, a version check and the lifecycle lock. Each refusal has a test, and tests never touch the dev stack (ADR-9).
- Story 23.4: a save during a start. The zero-wait lock refuses a save while anything holds the lock, and a start waits for a save in progress.
- Story 23.4: Story 22.7's write-back undoing an edit to `serverconfig.json`. ADR-4 decision 7 drops the edits the save changes, with a test per case.
- Story 23.1: `pyjson5`'s error position may be readable only from its message. ADR-1 decision 2 keeps that in one tested function and falls back to no position.
- Story 23.1: JSON5 is more lenient than the game in places, so the editor can accept a file the game refuses. The README says so (ADR-1 decision 6).
- Story 23.5: bundle size and CSP. CodeMirror is loaded on demand and checked under the enforced CSP.
- Story 23.6: the history directory grows. Per-file limits apply on save; a file never saved again keeps its revisions until the next save (documented).
- Stories 23.5 and 23.7: the E2E writes only files it created, only in the CI set's throwaway container.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR309-FR326 for Epic 23 (Config File Editing)".

**New section after FR308:** "Epic 23: Config File Editing", FR309 to FR326, in four groups: Viewing Configs with Comments (FR309-FR311), File Browser and Roles (FR312-FR313), Saving Config Files (FR314-FR320), Config History (FR321-FR326).

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** update entry "Added Epic 23 (7 stories) for Config File Editing; FR309-FR326".

**FR Coverage Map:** rows FR309 to FR326, each mapped to Epic 23.

**Story Summary:** `| Epic 23: Config File Editing | 23.1, ..., 23.7 | 7 |`, and the total from 136 to 143.

### 4.3 Epic 23 Stories (appended to `epics.md`)

The goal, order, dependencies, beads, product changes, current and target state, and Stories 23.1 to 23.7 with their acceptance criteria and tasks, are in `epics.md` under "Epic 23: Config File Editing".

### 4.4 Architecture (`architecture/epic-23-config-file-editing.md`, new)

Facts checked at `fc525885`, and:

- ADR-1 Config files are parsed as JSON5 with `pyjson5`
- ADR-2 The read returns the text for Admin, and the viewer shows unparseable files as text
- ADR-3 The file browser carries paths as lists of names
- ADR-4 Saving a config file through the API
- ADR-5 The editor is CodeMirror 6, in the file viewer
- ADR-6 Role-gated controls use one hook, and Game Settings are read-only for Monitor
- ADR-7 Saved config files keep their earlier versions
- ADR-8 History, comparison and restore in the file browser
- ADR-9 Tests never edit the dev stack's files

`architecture/index.md` gains the entry.

### 4.5 Other Artifacts

- `sprint-status.yaml` (through `just sprint`): `epic-23` and its retrospective entry, and the seven story keys, all `backlog`.
- Beads: the epic bead `VSS-7f7s` with `VSS-ato4`, `VSS-o8s`, `VSS-7z3`, `VSS-glz` and `VSS-hb4d` as children, each with a comment naming its story or stories.

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 23.1 to 23.7 from `epics.md` and the Epic 23 ADRs |
| Developer (`dev-story`) | Implement each story, one task per commit; each change with a release note is its own commit with the subject written for admins; never edit the dev stack's files in tests (ADR-9) |
| Reviewer (`code-review`) | Delegated, read-only review per story, given the commits and this contract |
| Maintainer (Matt) | Reviews the planner decisions below; confirms the manual check of Story 23.1 (`seasonalflowers.json` reads on the dev stack) |

**Questions for the maintainer, answered on 2026-11-19 in two rounds.** Each answer is recorded in the ADR status lines.

1. **Which relaxed syntax the parser accepts (ADR-1).** Default: comments and trailing commas through an in-house scanner. Alternatives: the JSON5 library; comments only. *Answered (Matt): JSON5 library.*
2. **Whether `serverconfig.json` can be edited (ADR-1 decision 5, ADR-4 decision 7).** Default: yes, strict JSON only, with pending 22.7 edits for changed keys dropped. Alternatives: exclude it; make every reader lenient. *Confirmed (Matt): yes, strict JSON only.*
3. **The editor (ADR-5).** Default: a textarea with line numbers. Alternatives: CodeMirror 6; Monaco. *Answered (Matt): CodeMirror 6.*
4. **Which files can be edited (ADR-4).** Default: every file Admin can read. Alternatives: root and ModConfig; ModConfig only. *Confirmed (Matt): every file Admin can read.*
5. **Where errors are checked (ADR-4 decision 10, ADR-5 decision 4).** Default: an API check endpoint while typing. Alternatives: `json5` in the browser; only on save. *Confirmed (Matt): API check endpoint.*
6. **History retention (ADR-7 decision 5).** Default: two API settings. Alternatives: a fixed constant; a count setting only. *Confirmed (Matt): API settings.*
7. **The comparison (ADR-8 decision 2).** Default: CodeMirror's merge view. Alternatives: a unified diff from the API; `jsdiff`. *Confirmed (Matt): CodeMirror merge view.*
8. **Game Settings for Monitor (ADR-6).** Default: disabled fields and a note. Alternative: plain values. *Confirmed (Matt): disabled fields and a note.*

**Planner decisions not reviewed yet:**

- The read's new fields: `parseError` for every role, `text` and `version` for Admin only; the version is the SHA-256 of the bytes (ADR-2 decision 1).
- Admin's view of a parsed file switches to its text with comments in Story 23.5; Monitor keeps the parsed view (ADR-5 decision 7).
- Infinity and NaN are parse errors in the viewer (ADR-1 decision 4).
- The save's rules (ADR-4):
  - The zero-wait lifecycle lock: a save is refused while anything holds it, not queued.
  - Running, starting and stopping all refuse a save; error and not installed allow it.
  - A BOM is kept if the file had one.
  - Owner and group are kept only when the API runs as root.
  - A save does not set "Restart required".
- Paths are lists of names, and a name that cannot be sent is refused in the web (ADR-3).
- `useIsAdmin`, with fields disabled while the role loads or fails (ADR-6 decisions 2 and 3).
- The editor (ADR-5):
  - Packages: only the `@codemirror` scope, no `basicSetup`, a lazy chunk.
  - Changes: no merge on a changed file, only Reload after confirmation.
  - Timing: the 500 ms check.
- The history store (ADR-7):
  - Location and layout: `vsmanager/state/config-history/<relative path>/`, keyed by the resolved path.
  - `savedBy` records the role, as there is no user identity until `VSS-2kdt`.
  - A save is refused if its revision cannot be stored.
  - The newest revision is never deleted by age.
  - Pruning happens on save only, with no job.
  - An unparseable revision can be read but not restored.
- The history UI: History is disabled while the editor has unsaved changes (ADR-8 decision 3).
- The E2E creates its own files with `docker exec` in the CI set only (ADR-9 decision 3).

**Other open beads that share files with this epic** (answered by Matt, 2026-11-19: `VSS-o8s` and `VSS-7z3` pulled in, the rest not):

| Bead | Shares | Recommendation |
|---|---|---|
| `VSS-o8s` (UI-081) File browser path breaks on directory names containing a slash | `FileManagerPanel.tsx`, `PathBreadcrumb.tsx` | Pulled in: Story 23.2 |
| `VSS-7z3` (UI-084) Monitor key sees editable game setting fields | The role gating the editor's button needs | Pulled in: Story 23.3 |
| `VSS-7ap` (API-012) Parse `serverconfig.json` into a typed object, validate paths | The idea of parsing `serverconfig.json`, not the code this epic changes | Not pulled in; its own epic. When built, it should parse through `parse_config_text(strict=True)` |
| `VSS-koo1` (API-094) CSP follow-ups | The CSP, which this epic does not change | Not pulled in. ADR-5 decision 2 checks the editor under the current CSP |
| `VSS-hv60` (UI-103) Leftover `.tmp` and `.bak` files in the mods directory | The idea of temporary files, not the mods directory | Not pulled in. ADR-4 decision 6 removes its own temporary file on failure |

Seen and not proposed, because they share no file with a story: `VSS-2n2` (whitelist), `VSS-jna` (connection loss), `VSS-egi` (EntitySpawning), `VSS-2kdt` (login), `VSS-v3be` (hand-added mods), `VSS-3tb1` (mod file follow-ups), `VSS-2bp` (favicon).

**Found during planning and handled inside the epic (no bead filed):**

1. The viewer's parse-error fallback is shown as an escaped object (part of `VSS-ato4`). Story 23.1 shows it as a warning and text (ADR-2 decision 3).
2. A commented file is hidden entirely from Monitor instead of being redacted key by key. Story 23.1 fixes this as a result of parsing it (ADR-2 decision 2).
3. JSON5's `Infinity` and `NaN` would make the read fail with a 500. Story 23.1 makes them a parse error (ADR-1 decision 4).
4. The read has no text and no version, which an editor and a stale-write check need. Story 23.1 adds them (ADR-2 decision 1).
5. `serverconfig.json` is read and rewritten as strict JSON by three services, so an editor save with comments would break them. Answer 2: strict JSON for that file (ADR-1 decision 5).
6. Story 22.7's write-back would undo an editor change to `Port` or `Ip` at the next start. Story 23.4 drops the edits a save changes (ADR-4 decision 7).
7. A save during a start could leave the game reading a half-written file. Story 23.4 holds the lifecycle lock (ADR-4 decision 4).
8. The role is checked in three places with copies of the same logic. Story 23.3 adds `useIsAdmin` (ADR-6 decision 3).
9. FastAPI does not limit the body size, so a save could post far more than 2 MiB. Story 23.4 checks the text's encoded size before parsing it (ADR-4 decision 2).

**Seen and left alone, with the reason (no bead filed):**

1. `GameConfigService._update_config_file` writes `serverconfig.json` through a fixed `.tmp` name without `fsync`, and `is_server_running` counts starting and stopping as stopped. Both are the Game Settings path, which this epic does not change. Epic 22's Story 22.7 accepted the starting and stopping window as a documented limitation.
2. Changes made through the Game Settings page, by the game, by mods or by hand are not recorded in the history (the bead's scope). The store could take them later.
3. Creating, renaming and deleting config files stay out of scope (the bead's scope).
4. The history keeps the role, not a person, until a login exists (`VSS-2kdt`).

**Planned net bead change:** closes 5 (`VSS-ato4`, `VSS-o8s`, `VSS-7z3`, `VSS-glz`, `VSS-hb4d`) and opens 1 (the epic bead, which closes with the epic). None filed from planning. Net: 5 fewer open beads, from 15 open before the epic to 10 after it.

**Success criteria:**

- `seasonalflowers.json` reads on the dev stack (manual, read-only); a commented file is redacted key by key for Monitor
- An unparseable file shows its error with line and column; Admin sees its text
- A save writes the exact text atomically while the game is stopped, and is refused while it runs, starts or stops, while a lifecycle operation runs, on a stale version, and on invalid text
- A start during a save waits for it; a `serverconfig.json` save is not undone by Story 22.7's write-back
- The editor checks as the admin types, guards unsaved changes, and works under the enforced CSP in its own chunk
- Each save keeps a revision. A revision can be compared and restored, and the limits apply on save
- Monitor sees Game Settings disabled with the note, and no Edit or History button
- Each in-scope bead is closed with an AAR by its story after merge
- `just check` and CI pass throughout, with 0 Pyright warnings and 0 skipped web tests

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: the maintainer named the epic and the bead chain after Epic 22's release. [x] 1.2 type: a bug and two new capabilities. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete. [x] 2.5 no resequencing; the order inside Epic 23 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR309-FR326 added, MVP unaffected. [x] 3.2 architecture: new Epic 23 ADRs. [x] 3.3 UX spec: no text change. [!] 3.4 one new compiled runtime dependency, new web dependencies, and the first API write into `serverdata` |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1 scope named by the maintainer (2026-11-19). [x] 6.2, 6.3 eight questions answered in two rounds and written in; the planner decisions in section 5 are not reviewed yet. [x] 6.4 approved by the maintainer (2026-11-19); sprint status and beads updated; handoff in section 5 |
