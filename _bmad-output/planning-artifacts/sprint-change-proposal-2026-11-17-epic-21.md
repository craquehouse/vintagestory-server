# Sprint Change Proposal: Maintainer Decisions and Web Polish (Epic 21)

**Date:** 2026-11-17
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (batch, non-interactive; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Scope approved by Matt before planning (2026-11-17): five decisions of his own and fourteen beads. The five decisions are written in as decided. What the planner decided inside them and for the beads is in ten open questions (section 5), each with a default that the stories follow unless he answers otherwise. Eight stories, fourteen beads.

## 1. Issue Summary

**Trigger:** Epic 20 is done and on `main` (`05436da`, release `v0.1.0-rc.6`). Its review left five questions that the maintainer has now answered, each of which is work: restore Renovate's hold for uv, keep image rebuilds out of the release notes, make `VS_LOG_LEVEL` work, make the mod remove dialog wait for the removal, and adopt Prettier for the web. He also picked fourteen open beads, thirteen about the web UI (tables, dialogs, the mod detail page, tabs and layout) and one about the config file viewer. The backlog rule (2026-11-17) applies: the epic draws the backlog down, and what planning finds goes into a story, not into a new bead.

**Problem:** The web UI works but is rough at the edges that Epics 16 to 19 found and filed: a dialog that closes before its action is done, errors shown twice, versions sorted wrongly, a page too wide for a phone, descriptions without typography, touch targets under 44px, and two layout rules of the UX specification that were never built. The web code has no formatter. A documented setting does nothing. And two Renovate rules produce pull requests and release notes the maintainer does not want.

**Evidence** (code at commit `05436da`; details and line references in `architecture/epic-21-maintainer-decisions-and-web-polish.md`):

- The web has no Prettier or ESLint dependency; `just format-web` runs an unpinned `bunx prettier` with defaults over `src` only (`Justfile:231-232`). Measured with Prettier 3.10.1: defaults would change 318 of 332 files. The code's own style is single quotes (1,108 import lines to 131), semicolons (1,182 to 57), two spaces, and 0.4% of lines over 100 characters. With `singleQuote`, `printWidth: 100` and `trailingComma: es5`, and with the recorded fixtures, Markdown and HTML ignored, 231 of 319 files change (5,888 lines removed, 3,826 added). The recorded mod database fixtures alone would add 54,000 changed lines if they were not ignored.
- CI's `web` job does not run `just lint-web` (`.github/workflows/ci.yml:42-45`), and `just lint-web` is the same `tsc --noEmit` as part of `just typecheck-web`.
- `renovate.json:32` clears the preset's one-day hold for uv. The organisation preset (`craquehouse/renovate-config` at `021869b`) types every `digest` update `fix` and scopes Docker updates `container`, so a rebuild of a base image is `fix(container): ...` and becomes a release note (`cliff.toml:47-50`). Pull request #185 (uv 0.13.9) is open under the current rule with both halves.
- `Settings.log_level` (`api/src/vintagestory_api/config.py:40`) is used nowhere. The level is set in `initialize_debug_state` (`config.py:312-325`) from `VS_DEBUG`; `main.py:170` only writes a derived string into a log line. `project-context.md:400` describes `VS_LOG_LEVEL` as working.
- `ModTable`'s confirm button is a Radix `AlertDialogAction`, which closes the dialog on click (`web/src/components/ModTable.tsx:453-457`); one `useRemoveMod()` instance's `isPending` labels every mod's dialog (`:130`, `:458`).
- Five mutation hooks have no `onError` while their callers show a toast, so the client default adds a second one (`web/src/api/query-client.ts:34-39`): `useInstallMod` (`VSS-oc28`) and four more found in planning.
- TanStack Table's `alphanumeric` sort gives `1.0.0, 1.0.0-rc.2, 1.0.0-rc.12, ...` (run in planning): a release before its pre-releases, in the installed mods list (`VSS-qxxo`) and on the Version page (`VersionTable.tsx:161`). The Version page's private `compareVersions` puts `rc.12` before `rc.2` (`:100`).
- The dialog and sheet close buttons are a 16px icon with no box (`ui/dialog.tsx:72-78`, `ui/sheet.tsx:73-76`); tab triggers are about 30px (`ui/tabs.tsx:27`, `:43`).
- Five of the nine links that open a new tab do not say so; `@tailwindcss/typography` is not installed, so the description's `prose` classes do nothing (`ModDetailPage.tsx:784`); the mod detail header is one row that cannot wrap (`:612`).
- The sidebar preference is a boolean that every browser stores as `false` on first render (`PreferencesContext.tsx:49`, `:169-171`); no page but Game Settings has a maximum width (`layout/Layout.tsx:46-50`).
- `services/game_config.py:238` lists two Discord hosts where `services/mod_update_alerts.py:20-22` lists four; `services/config_files.py:230-231` and `:282-284` hold the other two edge cases of `VSS-wv0w`.

**Scope decisions (made by the maintainer, 2026-11-17):**

| Decision | Choice |
|---|---|
| Items in scope | Five maintainer decisions (no beads) and fourteen beads: `VSS-oc28`, `VSS-nuef`, `VSS-whnb`, `VSS-qxxo`, `VSS-759m`, `VSS-woae`, `VSS-pzj8`, `VSS-4vbj`, `VSS-3ry`, `VSS-vt4`, `VSS-wv0w`, `VSS-f9y`, `VSS-w85`, `VSS-alx` |
| Backlog rule | The epic draws the backlog down. Findings go into a story; related open beads are proposed as pull-ins, not added; the net bead change is reported |
| 1. Renovate hold for uv | Remove `minimumReleaseAge: null` from the uv rule. Document that a uv pull request opens with the Dockerfile half, stays red for about a day and must not be merged before the `.mise.toml` half arrives |
| 2. Base image release notes | Pure digest refreshes of Dockerfile images are `chore(container)`; version changes keep the preset's `fix` or `feat` |
| 3. `VS_LOG_LEVEL` | DEBUG, INFO, WARNING or ERROR, case-insensitive, overrides the level; unset keeps today's behaviour; an invalid value stops start-up naming the setting; documented in the README and `.env.example`; a `feat(api)` with a release note |
| 4. Mod remove dialog | Stays open with "Removing..." and a disabled confirm button until the DELETE finishes, then closes; an error is shown by a toast; the spinner tracks this mod's removal only; a `fix(web)` with a release note, unit tests and a stubbed E2E |
| 5. Prettier for the web | A pinned dev dependency (approved), a configuration matching the code's style, one dedicated reformat commit first among the web stories and listed in `.git-blame-ignore-revs`, a format check in `just lint-web` and CI, `just format` fixed |
| Typography | Prefer hand-written styles to `@tailwindcss/typography` unless a new dependency is justified |

**Grouping, and what changed from the suggested starting point:**

| Story | Decisions and beads | Why this grouping |
|---|---|---|
| 21.1 The Web Is Formatted Once and Stays Formatted | Decision 5 | As suggested: its own story and pull request, first among the web stories, reviewed by reproducing it |
| 21.2 Renovate: the uv Hold and Digest Refreshes | Decisions 1, 2 | As suggested: `renovate.json` and `RELEASING.md` |
| 21.3 A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases | Decision 3, `VSS-wv0w` | As suggested: the API's settings and one service, no web file |
| 21.4 The Mod Remove Dialog Waits, and One Toast per Failure | Decision 4, `VSS-oc28` | The suggested "mod table and dialogs" story is split in two. This half is behaviour of mutations: the dialog's pending and error states and the error toasts. Planning found the two-toast fault in four more hooks, which fills the story |
| 21.5 Version Sort, Sort State for Screen Readers and Close Buttons | `VSS-qxxo`, `VSS-whnb`, `VSS-759m`, `VSS-nuef` | The other half: sorting and accessibility of the two sortable tables (`ModTable`, `VersionTable`) and the shared close button. Six beads and a decision in one story would have passed six tasks |
| 21.6 Mod Detail Page Polish | `VSS-woae`, `VSS-pzj8`, `VSS-4vbj` | As suggested: one page, its sanitizer and its styles |
| 21.7 Tabs and Tables on Phones | `VSS-3ry`, `VSS-vt4`, `VSS-f9y` | The suggested "tabs and layout" story is split in two. This half is what is too small or too wide below 1024px, and includes the measurement of every page that the comment on `VSS-f9y` asks for |
| 21.8 Sidebar Default and Content Width | `VSS-w85`, `VSS-alx` | The other half: the two layout rules of the UX specification, both in `Layout` and the preferences. `VSS-alx` is size-m and changes the width of almost every page, so it is reviewed apart from the phone fixes |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 20 are done; none is invalidated. One new epic, Epic 21: Maintainer Decisions and Web Polish, with 8 stories. No resequencing.

**Story impact:** No existing story changes. Story 21.1 carries out what Epic 20 ADR-1 decision 7 left out of scope. Story 21.2 replaces one line that Story 20.7 added (Epic 20 ADR-10 decision 3 otherwise stands). Story 21.3 completes Epic 19 ADR-2 and ADR-3 for three edge cases. Story 21.8 completes Epic 16 ADR-3 decision 1 (the application-wide maximum width) and builds the tablet rule of the UX specification.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR260-FR285; frontmatter |
| Epics | Add Epic 21; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-21-maintainer-decisions-and-web-polish.md` (facts, ADR-1 to ADR-15); index entry |
| UX spec | No text change. Stories 21.7 and 21.8 build rules it already states (`:1209-1215`, `:1254-1258`, `:1289-1292`); the console exception to the maximum width is recorded in ADR-15 |
| CI | The `web` job gains a `just lint-web` step (21.1). No new job; the job-list guard in `scripts/tests/test-release.sh` is not affected |
| Project rules | `project-context.md`: the web format commands (21.1), the Logging section (21.3), the mutation error rule (21.4). `CLAUDE.md`: the command list (21.1) |
| Deployment and documentation | README and `.env.example` gain `VS_LOG_LEVEL` (21.3); `RELEASING.md` gains the uv pull request note and which image updates make a release note (21.2); no deployment has to change |
| Beads | Epic `Epic 21: Maintainer Decisions and Web Polish` (`VSS-syuj`) with the 14 in-scope issues as children |

**Technical impact:**

- Story 21.1 touches about 231 web files in one commit. Every open web branch would conflict with it; none is open.
- One new dev dependency: Prettier, pinned to an exact version (approved by the maintainer). No runtime dependency is added: the version comparison and the description styles are written by hand.
- The API changes in one story (21.3): a setting starts to work and three edge cases of the config file routes are corrected.
- The web stories change behaviour and layout only; no API request or response used by the web changes.
- The sidebar preference changes shape in the `vs_ui_prefs` cookie (a new key; the old one is read once and no longer written).
- Stories 21.4 to 21.8 touch shared components (`ui/dialog.tsx`, `ui/sheet.tsx`, `ui/tabs.tsx`, `Layout`), so each checks every user of the component it changes.

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 21.3 | `VS_LOG_LEVEL` (existing field, no effect until now) | Sets the log level at start-up: `DEBUG`, `INFO`, `WARNING` or `ERROR`, any letter case. Unset or blank: as before. Any other value stops start-up with an error naming the setting | Setting starts to work |
| 21.3 | `POST /api/v1alpha1/debug/enable` and `/disable` | Same responses. Disable returns to the configured level (`VS_LOG_LEVEL`, or INFO) where it always returned to INFO | Behaviour, only when `VS_LOG_LEVEL` is set |
| 21.3 | Start-up log line `api_starting` | `log_level` reports the level actually set | Changed value |
| 21.3 | `GET /api/v1alpha1/config/files/{path}` for roles other than Admin | Values that are Discord webhook URLs on `ptb.discord.com` or `canary.discord.com` are `[redacted]` | Fix |
| 21.3 | `GET /api/v1alpha1/config/directories` and `/config/files` | Entries that resolve outside the server data directory are no longer listed, for any role | Fix |
| 21.3 | The same two routes, for roles other than Admin, when the server data directory does not exist | A directory the role may not list answers 403 `FORBIDDEN` (was 200 with an empty list); a traversal answers 400 | Fix |
| 21.8 | Cookie `vs_ui_prefs` | New key `sidebar` (`auto`, `expanded`, `collapsed`); `sidebarCollapsed` is read once for migration and no longer written | Web-only |

No route is added or removed, no successful response gains or loses a field, and nothing is breaking. A deployment that sets `VS_LOG_LEVEL` to a value outside the four will not start after the update; no file in the repository sets it (open question 2).

**Draft release-note text** (commit subjects; the story scope is removed by git-cliff):

- Features: `feat(api): VS_LOG_LEVEL sets the log level`; `feat(web): collapse the sidebar by default on tablet-sized screens`; `feat(web): limit page width to 1280px on wide screens`
- Fixes: `fix(api): hide Discord webhook URLs on ptb and canary hosts from read-only keys`; `fix(api): leave links that point outside the data directory out of the config file listing`; `fix(web): the remove mod dialog stays open until the mod is removed`; `fix(web): a failed mod install shows one error message, not two`; `fix(web): a failed server install, removal or restart shows one error message, not two`; `fix(web): sort versions with pre-releases before their release`; `fix(web): announce the sort order of table columns to screen readers`; `fix(web): make dialog close buttons easier to tap`; `fix(web): say which links open in a new tab`; `fix(web): fit the mod detail page on phone screens`; `fix(web): show headings, lists and links in mod descriptions`; `fix(web): make tabs easier to tap on phones`; `fix(web): fit the scheduled jobs and version tables on phone screens`; and, only if the arrow key fault is fixed in code, `fix(web): settings tabs respond to arrow keys as soon as they appear`
- No note: Story 21.1 (`chore`, `ci`, `docs`), Story 21.2 (`chore`, `docs`), the cast removal (`refactor`), tests and documentation

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 21 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Eight stories, each tied to a maintainer decision or to existing beads. Effort medium, risk low; Stories 21.1 and 21.8 are medium (many files, every page) |
| 2. Rollback | Not viable. Nothing completed has to be undone; one line of Story 20.7 is replaced on the maintainer's decision |
| 3. MVP Review | Not needed |

**Effort:** Medium. Thirteen beads are size-s and one is size-m (`VSS-alx`); the five decisions are small except Prettier, which is mechanical. Stories 21.2 and 21.3 are the smallest; 21.7 and 21.8 the largest.

**Risks:**

- Story 21.1: the format commit conflicts with any web branch cut before it. It merges first among the web stories, with no other web branch open.
- Story 21.1: `.git-blame-ignore-revs` holds a hash, which a squash or a rebase would change. The project merges with merge commits; the story says so in the pull request.
- Story 21.1: an exact Prettier pin means a Renovate update can fail the check until someone runs `just format-web` in that pull request. This is the price of a check that gives everyone the same answer.
- Story 21.1: the shadcn files in `src/components/ui` are reformatted, so a later `shadcn add` writes a file in another style. `just format-web` fixes it, and the check says so.
- Story 21.2: after the change, every uv pull request is red for about a day. That is the maintainer's decision; the risk is that someone merges it early, which the script test and the documentation are there to prevent.
- Story 21.2: Renovate's behaviour for a group whose halves become ready at different times was reasoned in Story 20.7, not observed. The story records what the first update does.
- Story 21.3: a deployment with an invalid `VS_LOG_LEVEL` stops starting. The error names the setting, and the release note says it.
- Story 21.3: the debug switch and `VS_LOG_LEVEL` interact; the rule (ADR-4 decision 3) is the planner's and is open question 1.
- Story 21.4: silencing the default error handler for a hook leaves a failure unreported if a caller shows no toast. The story checks every caller and tests each hook for exactly one toast.
- Story 21.4: a dialog that cannot be dismissed while a request runs holds the user for as long as the request is unanswered. Any failure, a network failure included, returns the dialog to its error state, and the story tests that case.
- Story 21.5: a comparison function written by hand can be wrong at the edges. It is small, follows a published rule, and its tests list every case.
- Story 21.6: descriptions come from mod authors and vary; styles that suit most may break a few. Inline styles still win, and the rules are defaults with low specificity.
- Story 21.7: the arrow key fault may not be reproducible with a real keyboard. The story is written for both outcomes, with a time box.
- Story 21.7: measuring every page at five widths can find more than the story can fix. The rule is in ADR-13 decision 4: fix what is of the same kind, report the rest to the maintainer in the pull request.
- Story 21.8: existing users at tablet widths see the sidebar collapsed after the update (the specification's default); a user who had expanded it by choice cannot be told apart from one who never chose, and gets the default once.
- Story 21.8: a width cap in `Layout` changes every page above 1280px of content. Each page is checked at three wide widths in both sidebar states.
- Stories 21.4 and 21.5 both edit `ModTable.tsx`; 21.5 and 21.7 both edit `VersionTable.tsx`; 21.7 and 21.8 both edit `layout-widths.spec.ts`. They run one after another.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR260-FR285 for Epic 21 (Maintainer Decisions and Web Polish)".

**New section after FR259:**

### Epic 21: Maintainer Decisions and Web Polish

#### Web Formatting (Matt, 2026-11-17)

- FR260: Every TypeScript, CSS and JSON file of the web that Prettier covers is in Prettier's form under the committed configuration; the reformat is one commit that holds nothing else
- FR261: Prettier is a dev dependency of the web pinned to an exact version, with a committed configuration and ignore file; `just format-web` uses it, and recorded test fixtures, Markdown and HTML are not covered
- FR262: `just lint-web`, and through it CI's `web` job and `just check`, fails when a covered web file is not formatted
- FR263: The web reformat commit is listed in `.git-blame-ignore-revs`, so `git blame` skips it on GitHub and in a set-up worktree

#### Renovate (Matt, 2026-11-17)

- FR264: A uv update keeps the organisation preset's one-day hold on its `.mise.toml` half, and `RELEASING.md` says that its pull request opens with the Dockerfile half only, fails the uv version test for about a day, and must not be merged until it holds both halves
- FR265: A digest refresh of a Dockerfile image under an unchanged tag is committed as `chore(container)` and adds no release note; a version change of an image keeps the preset's `fix` or `feat` type

#### Log Level (Matt, 2026-11-17)

- FR266: `VS_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING` or `ERROR`, in any letter case) sets the API's log level at start-up; unset or blank, the level is DEBUG with `VS_DEBUG=true` and INFO otherwise, as before; it changes nothing else that `VS_DEBUG` controls
- FR267: Any other value of `VS_LOG_LEVEL` stops start-up with an error that names the setting; turning debug logging on at run time still sets DEBUG and turning it off returns to the configured level; the setting is documented in the README and `.env.example`

#### Config File Viewer

- FR268: Discord webhook URLs on `ptb.discord.com` and `canary.discord.com` are redacted for roles other than Admin like those on `discord.com` and `discordapp.com`, from one list of hosts
- FR269: A config directory listing never shows an entry that resolves outside the server data directory, for any role
- FR270: A role other than Admin asking for a directory it may not list gets 403 whether or not the server data directory exists

#### Mod Removal and Error Messages

- FR271: After the administrator confirms, the mod remove dialog stays open and shows that the removal is running, cannot be dismissed while it runs, and closes when the removal has succeeded (Matt, 2026-11-17)
- FR272: When a removal fails, one error message is shown and the dialog stays open so the administrator can try again or cancel
- FR273: The running state of the remove dialog belongs to the mod being removed; another mod's dialog never shows it (Matt, 2026-11-17)
- FR274: A failed action in the web UI shows exactly one error message: a mod install, a server install, uninstall or restart, and a change of the mod update webhook

#### Tables and Dialogs

- FR275: Versions are sorted by Semantic Versioning precedence (a pre-release before its release, numeric parts as numbers) in the installed mods list and on the Version page, by one comparison function and without a new dependency
- FR276: Sortable column headers expose their sort state to assistive technology (`aria-sort`: ascending, descending or none) in the installed mods table and the Version table
- FR277: The close button of every dialog and of the phone navigation sheet is at least 44 by 44px

#### Mod Detail Page

- FR278: Every link in the web UI that opens a new tab says so to assistive technology in the same words, including SVG links inside mod descriptions
- FR279: The mod detail page does not scroll sideways from 320px up: its header stacks below 768px and wide description content stays inside its card
- FR280: Mod descriptions are typeset (headings, paragraphs, lists, links, quotes, code and tables) with the theme's colours in both themes, without a new dependency

#### Tabs, Tables and Layout

- FR281: Tab buttons are at least 44px tall below 1024px in every tab list
- FR282: Arrow keys move focus and selection in the Settings tab list as soon as a tab can receive focus, or the cause of the reported delay is recorded with evidence when it cannot be reproduced with a real keyboard or lies outside the project's code
- FR283: The Scheduled Jobs and Version tables do not scroll inside themselves from 320 to 1023px in either sidebar state, and every page of the web UI has recorded measurements at those widths
- FR284: With no sidebar choice stored, the sidebar is collapsed from 768 to 1023px and expanded from 1024px; an explicit choice applies at every width and is kept; the choice can be set back to automatic
- FR285: Page content is at most 1280px wide and centered; the console pages use the full width

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** update entry "Added Epic 21 (8 stories) for Maintainer Decisions and Web Polish; FR260-FR285".

**FR Coverage Map:** rows FR260 to FR285 appended after FR259, each mapped to Epic 21.

**Story Summary:**

OLD:

```markdown
| **Total** | | **120** |
```

NEW:

```markdown
| Epic 21: Maintainer Decisions and Web Polish | 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8 | 8 |
| **Total** | | **128** |
```

### 4.3 Epic 21 Stories (appended to `epics.md`)

## Epic 21: Maintainer Decisions and Web Polish

**Goal:** Five decisions the maintainer made after Epic 20 are carried out: the web is formatted by Prettier and stays formatted, Renovate holds uv like every other tool and stops writing release notes for image rebuilds, `VS_LOG_LEVEL` works, and the mod remove dialog waits for the removal. Fourteen open beads about the web's tables, dialogs, mod detail page, tabs and layout, and about the config file viewer, are closed.

**Architecture:** `architecture/epic-21-maintainer-decisions-and-web-polish.md` (ADR-1 to ADR-15, with the facts checked at `05436da`). There is no preparation story. Story 21.7 starts its arrow key work with a time-boxed reproduction (ADR-12 decision 3).

**Decided by the maintainer (Matt, 2026-11-17):** the five decisions and the fourteen beads. For each decision: Prettier as a pinned dev dependency, one dedicated reformat commit that is first among the web stories and listed in `.git-blame-ignore-revs`, and a format check in `just lint-web` (ADR-1); the uv rule loses `minimumReleaseAge: null` and the red first day is documented (ADR-2); digest refreshes of Dockerfile images are `chore(container)` (ADR-3); `VS_LOG_LEVEL` with four values, case-insensitive, today's behaviour when unset and a start-up error when invalid (ADR-4); the remove dialog stays open with "Removing..." until the DELETE finishes and tracks its own mod (ADR-6). What the planner decided inside those and for the beads is listed as open questions in the change proposal (`sprint-change-proposal-2026-11-17-epic-21.md`, section 5), each with a default the stories follow.

**Order:** 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8.

**Dependencies:**

- Story 21.1 comes first among the web stories and merges before any other web branch of the epic is cut: it rewrites about 231 web files, and every later web change is made on formatted code.
- Stories 21.2 and 21.3 touch no file under `web/`. They need no other story's code and may be done before, after or beside 21.1; they are numbered here so the epic can start with them while 21.1 is in review. They share only the README and `RELEASING.md` with other stories.
- Story 21.4 comes before 21.5: both edit `ModTable.tsx` and its test.
- Story 21.5 comes before 21.7: both edit `VersionTable.tsx` (21.5 its sort, `aria-sort` and casts; 21.7 its columns on phones).
- Story 21.6 needs no other story's code after 21.1. It comes after 21.5 because 21.5 changes the shared dialog close button that the screenshot dialog on the mod detail page uses.
- Story 21.8 comes last and directly after 21.7: both extend `web/e2e/layout-widths.spec.ts`, 21.7 measures every page at phone and tablet widths before 21.8 changes the sidebar default there, and 21.8 changes the width of almost every page.
- Stories 21.4 to 21.8 are run one after another.

**Beads:** fourteen in scope, each closed with an AAR by its story: `VSS-wv0w` in 21.3; `VSS-oc28` in 21.4; `VSS-qxxo`, `VSS-whnb`, `VSS-759m` and `VSS-nuef` in 21.5; `VSS-woae`, `VSS-pzj8` and `VSS-4vbj` in 21.6; `VSS-3ry`, `VSS-vt4` and `VSS-f9y` in 21.7; `VSS-w85` and `VSS-alx` in 21.8. Stories 21.1 and 21.2 carry maintainer decisions and have no bead. What planning found is in the stories (the change proposal lists it), not in new beads.

**Product changes:** one new working setting, `VS_LOG_LEVEL` (21.3); three small corrections to the config file routes (21.3); the rest is behaviour and layout of the web UI. No route, response field or status code of an existing successful request changes. Nothing is breaking.

### Current State

- The web has no formatter: `just format-web` runs an unpinned Prettier with defaults that would rewrite almost every file, and nothing checks the format
- A uv update opens with both halves at once because the preset's one-day hold was cleared for it; a base image rebuild under the same tag is committed as `fix(container)` and becomes a release note
- `VS_LOG_LEVEL` is read into the settings and used nowhere; the log level follows `VS_DEBUG` only
- Discord webhook URLs on `ptb.` and `canary.` hosts are not redacted for read-only keys; an Admin directory listing shows links that leave the data directory; a read-only key gets an empty list instead of 403 when the data directory is missing
- The mod remove dialog closes at once and the removal runs behind it; its "Removing..." label is shared by every mod's dialog
- A failed mod install shows two error toasts, and so do a failed server install, uninstall and restart and a failed webhook setting
- Sorting by version puts a release before its pre-releases in the installed mods list and on the Version page; the installed mods headers have no `aria-sort`; dialog and sheet close buttons are 16px
- Five links open a new tab without saying so, and SVG links in descriptions cannot; the mod detail page is 674px wide on a 390px screen; mod descriptions show headings, lists and links as plain text
- Tab buttons are about 30px tall on phones; the Settings tabs can lose arrow key presses just after they render; the Scheduled Jobs and Version tables scroll inside themselves on phones
- The sidebar is expanded by default at tablet widths; apart from Game Settings no page has a maximum width

### Target State

- The web is formatted by a pinned Prettier with a committed configuration, the format commit is skipped by `git blame`, and `just lint-web` and CI fail on an unformatted file
- A uv update follows the preset's hold, and `RELEASING.md` says its pull request is red for a day and must wait; image rebuilds are `chore(container)` and stay out of the release notes
- `VS_LOG_LEVEL` sets the log level, an invalid value stops start-up, and the debug switch still gives DEBUG
- The config file viewer redacts all four Discord hosts, lists nothing that leaves the data directory, and answers 403 before it looks for the directory
- The remove dialog waits for its own mod's removal and stays open on an error; every failed action shows one toast
- Versions sort by Semantic Versioning precedence everywhere; sortable headers announce their state; close buttons are 44px
- Every new-tab link says so; the mod detail page fits a phone; descriptions are typeset in both themes
- Tabs are 44px tall below 1024px; the arrow key fault is fixed or explained; the two tables fit phones and every page has been measured there
- The sidebar follows the width until the user chooses; page content is at most 1280px wide, except the console

---

### Story 21.1: The Web Is Formatted Once and Stays Formatted

**Sprint key:** `21-1-web-formatted-once`
**Beads:** none (maintainer decision 5; Matt, 2026-11-17)
**FRs:** FR260, FR261, FR262, FR263

As a **developer**,
I want **the whole web in one formatter's form and a check that keeps it there**,
So that **formatting a file I work on never adds changes that are not mine**.

**Acceptance Criteria:**

**Given** `web/package.json` and `web/bun.lock`
**When** I read them
**Then** Prettier is a dev dependency at one exact version (no range), and `format` and `format:check` scripts run it over the web directory

*(Covers FR261; Matt, 2026-11-17)*

**Given** `web/.prettierrc.json`
**When** I read it
**Then** it sets `singleQuote: true`, `printWidth: 100` and `trailingComma: "es5"` and nothing else

*(Covers FR261; ADR-1 decision 2)*

**Given** `web/.prettierignore`
**When** Prettier runs over `web/`
**Then** it covers the tracked `.ts`, `.tsx`, `.css` and `.json` files in `src`, `e2e`, `tests` and at the top of `web/`, and leaves out `e2e/fixtures/`, Markdown and HTML files, `public/` and the build, coverage and Playwright output directories

*(Covers FR261; ADR-1 decisions 3 and 4)*

**Given** the web sources
**When** `prettier --check .` runs in `web/`
**Then** it reports no file that would be reformatted

*(Covers FR260)*

**Given** the format commit
**When** I read it
**Then** it holds only what `prettier --write .` wrote with the committed configuration: no hand edit, no configuration change, no `// prettier-ignore`, and its subject is `chore(story-21.1/task-2): format the web with prettier`

*(Covers FR260; Matt, 2026-11-17)*

**Given** the format commit's parent (which already holds the dependency, the configuration and the ignore file)
**When** a reviewer runs the same command on it
**Then** the resulting tree is identical to the format commit's tree

*(Covers FR260)*

**Given** `just typecheck-web`, `just test-web` and `just build-web`
**When** they run before and after the format commit
**Then** the results are the same: no new type error, the same tests pass, and the build succeeds

*(Covers FR260)*

**Given** the recorded mod database answers in `web/e2e/fixtures/moddb/`
**When** the format commit is made
**Then** no file under `web/e2e/fixtures/` has changed, and `just record-moddb` still writes files the check ignores

*(Covers FR260, FR261)*

**Given** `just lint-web`
**When** it runs
**Then** it runs the format check, fails when a covered file is not formatted, and no longer repeats the type check that `just typecheck-web` runs

*(Covers FR262)*

**Given** a pull request that contains an unformatted web file
**When** CI runs
**Then** the `web` job fails at a `just lint-web` step, and `scripts/tests/test-release.sh` still passes (the job list is unchanged)

*(Covers FR262)*

**Given** `just format-web` and `just format`
**When** they run on a formatted tree
**Then** they use the pinned Prettier and the committed configuration, and change no file

*(Covers FR261)*

**Given** the repository root
**When** I read `.git-blame-ignore-revs`
**Then** it names the web format commit's full hash under a comment line, below the API entry, and it was added in a separate commit of the same pull request

*(Covers FR263)*

**Given** the epic's branches
**When** Story 21.1's pull request merges
**Then** it is merged with a merge commit like every other, no other web branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main`

*(Covers FR263; Matt, 2026-11-17)*

**Tasks:**

- [ ] Add Prettier at an exact version, `web/.prettierrc.json`, `web/.prettierignore` and the `format` and `format:check` scripts; no source file changes in this commit (Epic 21 ADR-1 decisions 1 to 4)
- [ ] Run `prettier --write .` in `web/` and commit the result alone; record the file and line counts and that the type check, tests and build give the same results as before (ADR-1 decisions 5, 6 and 9)
- [ ] Add the commit's hash to `.git-blame-ignore-revs` (ADR-1 decision 7)
- [ ] `just lint-web` runs the format check and `just format-web` the pinned Prettier; add `just lint-web` to CI's `web` job; update the recipe comments and the command lists in `CLAUDE.md`, `project-context.md` and the README (ADR-1 decision 8)

---

### Story 21.2: Renovate: the uv Hold and Digest Refreshes

**Sprint key:** `21-2-renovate-uv-hold-and-digests`
**Beads:** none (maintainer decisions 1 and 2; Matt, 2026-11-17)
**FRs:** FR264, FR265

As the **maintainer**,
I want **uv held like every other tool and image rebuilds kept out of the release notes**,
So that **Renovate's pull requests follow the organisation's rules and the release notes list only what a user would notice**.

**Acceptance Criteria:**

**Given** `renovate.json`
**When** I read the uv rule
**Then** it has no `minimumReleaseAge`, it still groups `uv` and `ghcr.io/astral-sh/uv` as `chore(uv)`, and its description says the pull request opens with the Dockerfile half and must wait for the `.mise.toml` half

*(Covers FR264; Matt, 2026-11-17)*

**Given** `RELEASING.md`
**When** I read what it says about Renovate and uv
**Then** it says a uv pull request opens with only the Dockerfile change, that `scripts/tests/test-docker-context.sh` fails it for about a day until the `.mise.toml` change joins it, that this is expected, and that it must not be merged until it holds both files and CI is green

*(Covers FR264; Matt, 2026-11-17)*

**Given** `scripts/tests/test-docker-context.sh`
**When** the story is done
**Then** its uv version assertion is unchanged

*(Covers FR264; ADR-2 decision 4)*

**Given** `renovate.json`
**When** I read its rules
**Then** one rule matches the `dockerfile` manager with update types `digest` and `pinDigest` and sets the commit type `chore`, and no rule changes the type of a `patch`, `minor` or `major` update of a Dockerfile image

*(Covers FR265; Matt, 2026-11-17)*

**Given** a digest refresh of `node:26-slim` under the same tag
**When** Renovate commits it
**Then** the subject starts with `chore(container):`, and `just changelog` shows no note for it

*(Covers FR265; confirmed on the first such pull request after the merge, or by Renovate's dry run if one can be run; recorded in the story)*

**Given** a new version tag of a Dockerfile image
**When** Renovate commits it
**Then** the subject keeps the preset's `fix(container):` or `feat(container):`

*(Covers FR265)*

**Given** the changed `renovate.json`
**When** `renovate-config-validator --no-global` runs on it from a directory outside the repository
**Then** it reports the file as a valid repository configuration, and `web/package.json` and `web/bun.lock` are unchanged by the run

*(Covers FR264, FR265)*

**Tasks:**

- [ ] Remove `minimumReleaseAge: null` from the uv rule and rewrite its description; rewrite the uv paragraph of `RELEASING.md`; validate (Epic 21 ADR-2)
- [ ] Add the digest rule for the `dockerfile` manager; add a sentence to `RELEASING.md` on which image updates produce a release note; validate (ADR-3)
- [ ] Record the validator's output and, once Renovate has run with the new rules, what it did with the open uv pull request and the next digest refresh (ADR-2 consequences, ADR-3)

---

### Story 21.3: A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases

**Sprint key:** `21-3-log-level-and-config-viewer`
**Beads:** `VSS-wv0w` (API-096); maintainer decision 3 (Matt, 2026-11-17)
**FRs:** FR266, FR267, FR268, FR269, FR270

As an **operator**,
I want **to set the API's log level with `VS_LOG_LEVEL`, and the config file viewer to behave the same in its edge cases**,
So that **I can have quieter or more detailed logs without debug mode, and read-only keys see neither webhook secrets nor wrong answers**.

**Acceptance Criteria:**

**Given** `VS_LOG_LEVEL=warning` (any letter case) and `VS_DEBUG` unset
**When** the API starts
**Then** INFO and DEBUG lines are not written and WARNING and ERROR lines are, in JSON, and the `api_starting` line reports `WARNING` as the level

*(Covers FR266)*

**Given** `VS_LOG_LEVEL` unset or blank
**When** the API starts
**Then** the level is DEBUG with `VS_DEBUG=true` and INFO otherwise, as before

*(Covers FR266; Matt, 2026-11-17)*

**Given** `VS_DEBUG=true` and `VS_LOG_LEVEL=INFO`
**When** the API starts
**Then** the level is INFO, the console renderer is used, and the documentation pages and test routes are served as in any debug mode

*(Covers FR266; ADR-4 decision 2)*

**Given** `VS_LOG_LEVEL=DEBUG` and `VS_DEBUG` unset
**When** the API starts
**Then** DEBUG lines are written in JSON, and the documentation pages and test routes are not served

*(Covers FR266)*

**Given** `VS_LOG_LEVEL=verbose`
**When** the API starts
**Then** start-up stops with an error that names `VS_LOG_LEVEL` and the four allowed values and does not print the value

*(Covers FR267; Matt, 2026-11-17)*

**Given** `VS_LOG_LEVEL=WARNING` and a running API
**When** an Admin turns debug logging on and then off again
**Then** the level is DEBUG while it is on and WARNING after it is turned off, and the three `/debug` responses have the fields they have today

*(Covers FR267; ADR-4 decision 3)*

**Given** `VS_DEBUG=on`
**When** the API starts
**Then** logging is in debug mode, as the documentation pages already are

*(Covers FR267; ADR-4 decision 6)*

**Given** the README's configuration table, `.env.example`, the architecture's environment table and the Logging section of `project-context.md`
**When** I read them
**Then** each describes `VS_LOG_LEVEL`: the four values, that letter case does not matter, the default, what the debug switch does to it, and that any other value stops start-up

*(Covers FR267)*

**Given** a config file with the value `https://ptb.discord.com/api/webhooks/1/abc` or `https://canary.discord.com/api/webhooks/1/abc`
**When** a Monitor key reads the file
**Then** the value is `[redacted]`, as for `discord.com` and `discordapp.com`, and the API has one definition of the four hosts

*(Covers FR268; `VSS-wv0w`)*

**Given** a directory symlink, or a `.json` file symlink, inside the server data directory that points outside it
**When** an Admin key or a Monitor key lists the directory that holds it
**Then** the entry is not in the listing

*(Covers FR269; `VSS-wv0w`)*

**Given** the server data directory does not exist
**When** a Monitor key lists a directory it may not see (for example `Playerdata`)
**Then** the answer is 403 `FORBIDDEN`, as when the data directory exists; a path traversal is 400; and a request for the root or `ModConfig` still answers with an empty list

*(Covers FR270; `VSS-wv0w`)*

**Tasks:**

- [ ] Validate `log_level` in the settings (normalise, blank is unset, a bad value raises naming `VS_LOG_LEVEL`) with tests for every accepted and refused form (Epic 21 ADR-4 decisions 1 and 8)
- [ ] Apply the level at start-up and keep it through the debug switch: `initialize_debug_state` takes the configured level and the debug flag from the settings, `set_debug_enabled` returns to it, `api_starting` reports the level set; tests for each combination; its own `feat(api)` commit (ADR-4 decisions 2 to 6)
- [ ] Document `VS_LOG_LEVEL` in the README, `.env.example`, `architecture/project-structure-boundaries.md` and `project-context.md` (ADR-4 decision 7)
- [ ] One set of Discord hosts for redaction and for the webhook sender, with tests for the two added hosts; its own `fix(api)` commit (ADR-5 decision 1) (`VSS-wv0w`)
- [ ] Listings leave out entries that resolve outside the data directory for every role, and the path and role checks run before the missing-directory shortcut; tests for both roles; update the route documentation strings (ADR-5 decisions 2 to 4) (`VSS-wv0w`)

---

### Story 21.4: The Mod Remove Dialog Waits, and One Toast per Failure

**Sprint key:** `21-4-remove-dialog-and-single-toast`
**Beads:** `VSS-oc28` (UI-096); maintainer decision 4 (Matt, 2026-11-17)
**FRs:** FR271, FR272, FR273, FR274

As an **administrator**,
I want **the remove dialog to show me the removal until it is done, and one message when something fails**,
So that **I know whether the mod was removed and am not told the same error twice**.

**Acceptance Criteria:**

**Given** the remove dialog of an installed mod
**When** I confirm
**Then** the dialog stays open, the confirm button shows a spinner and "Removing...", and the confirm and Cancel buttons are disabled

*(Covers FR271; Matt, 2026-11-17)*

**Given** a removal that is running
**When** I press Escape
**Then** the dialog stays open

*(Covers FR271; ADR-6 decision 4)*

**Given** a removal that is running
**When** the DELETE succeeds
**Then** the dialog closes, the mod is no longer in the list, and the success message is shown once

*(Covers FR271)*

**Given** a removal that is running
**When** the DELETE fails
**Then** exactly one error toast is shown, the dialog stays open with the confirm button enabled and labelled "Remove" again, and the mod is back in the list behind it

*(Covers FR272; ADR-6 decision 3)*

**Given** the dialog after a failed removal
**When** I confirm again or cancel
**Then** confirming sends a new DELETE and cancelling closes the dialog with the mod still installed

*(Covers FR272)*

**Given** a removal of mod A that failed or finished
**When** I open the remove dialog of mod B
**Then** its confirm button reads "Remove" and is enabled; "Removing..." is shown only in the dialog of the mod whose DELETE is running

*(Covers FR273; Matt, 2026-11-17)*

**Given** the installed mods as cards (below 1024px)
**When** I remove a mod from its card
**Then** the dialog behaves the same as from the table

*(Covers FR271)*

**Given** the server uninstall dialog while its request runs
**When** I press Escape
**Then** the dialog stays open, as its disabled Cancel button already implies

*(Covers FR271; ADR-6 decision 7, found in planning)*

**Given** a mod install that the API refuses
**When** the install dialog shows the failure
**Then** exactly one error toast is shown, titled "Installation failed" with the API's message

*(Covers FR274; `VSS-oc28`)*

**Given** a failed server install, server uninstall, server restart or mod update webhook change
**When** the request fails
**Then** exactly one error toast is shown, with the caller's title and the API's message

*(Covers FR274; ADR-7 decision 2, found in planning)*

**Given** `project-context.md`
**When** I read its frontend rules
**Then** it says that a hook-level `onError` replaces the query client's default, that an `onError` passed to `mutate` runs in addition, and that a hook either reports its error or silences the default for its callers

*(Covers FR274; ADR-7 decision 5)*

**Given** the E2E suite
**When** CI runs it
**Then** an untagged spec covers the remove dialog with the DELETE stubbed (a delayed success and an error), sends no request that changes the stack, and passes on the throwaway container

*(Covers FR271, FR272)*

**Tasks:**

- [ ] The remove dialog: a plain destructive confirm button, open until the DELETE succeeds, Cancel and Escape blocked while it runs, open with "Remove" again after an error; unit tests for running, success and failure; a `fix(web)` commit with the release note (Epic 21 ADR-6 decisions 1 to 4, 6)
- [ ] The pending state compares the mutation's `variables` with the dialog's mod; unit test with a second mod's dialog (ADR-6 decision 5)
- [ ] The same Escape guard in `UninstallConfirmDialog`'s page, with a unit test (ADR-6 decision 7)
- [ ] `useInstallMod` silences the default `onError`; a test that a failed install shows one toast; a `fix(web)` commit with its release note (ADR-7 decisions 1 and 3) (`VSS-oc28`)
- [ ] The same for `useRestartServer`, `useInstallServer`, `useUninstallServer` and `useSetModUpdateWebhook`, after checking every caller reports the error; one test each; a `fix(web)` commit with its release note; the rule in `project-context.md` (ADR-7 decisions 2, 5 and 6)
- [ ] E2E spec for the remove dialog with the DELETE stubbed; update the counts in `web/e2e/README.md` (ADR-6 decision 8)

---

### Story 21.5: Version Sort, Sort State for Screen Readers and Close Buttons

**Sprint key:** `21-5-version-sort-aria-sort-close-buttons`
**Beads:** `VSS-qxxo` (UI-099), `VSS-whnb` (UI-100), `VSS-759m` (UI-101), `VSS-nuef` (UI-095)
**FRs:** FR275, FR276, FR277

As a **user of the tables and dialogs**,
I want **versions in their real order, the sort order announced, and close buttons I can hit**,
So that **a pre-release is not listed as newer than its release, a screen reader tells me how a table is sorted, and I can close a dialog on a phone**.

**Acceptance Criteria:**

**Given** installed mods with the versions `1.0.0`, `1.0.0-rc.2`, `1.0.0-rc.12`, `1.9.0` and `1.10.0`
**When** I sort by Version ascending
**Then** the order is `1.0.0-rc.2`, `1.0.0-rc.12`, `1.0.0`, `1.9.0`, `1.10.0`, and descending is the reverse, in the table and in the cards below 1024px

*(Covers FR275; `VSS-qxxo`)*

**Given** the Version page's table with `1.22.0` and `1.22.0-rc.1`
**When** I sort by Version ascending
**Then** `1.22.0-rc.1` comes before `1.22.0`

*(Covers FR275; found in planning)*

**Given** an installed game version `1.22.0-rc.2` and a listed version `1.22.0-rc.12`
**When** the Version page marks newer versions
**Then** `1.22.0-rc.12` is marked as newer

*(Covers FR275; found in planning)*

**Given** versions the comparison cannot read (for example `1.2`, `v1.0.0`, `beta`)
**When** a table sorts them with others
**Then** nothing throws, a leading `v` is ignored, a missing part counts as 0, unreadable strings come after readable ones, and the order is the same on every render

*(Covers FR275; ADR-8 decision 3)*

**Given** the web's dependencies
**When** the story is done
**Then** no package was added for the comparison, and the two tables and the "newer" mark use one function

*(Covers FR275)*

**Given** the installed mods table sorted by Name ascending
**When** a screen reader reads the header row
**Then** the Name header has `aria-sort="ascending"`, the Version and Status headers have `aria-sort="none"`, and the headers that cannot be sorted have no `aria-sort`

*(Covers FR276; `VSS-whnb`)*

**Given** either sortable table
**When** I change the sort column or its direction
**Then** `aria-sort` moves with it: `ascending` or `descending` on the sorted column and `none` on the other sortable columns

*(Covers FR276)*

**Given** `VersionTable.tsx`
**When** I read how it uses column meta
**Then** it reads `meta.className` with no type assertion, and the rendered classes are the same as before

*(`VSS-759m`; a refactor with no requirement of its own)*

**Given** any dialog with a close button, and the phone navigation sheet
**When** I measure the close button at 390px and at 1440px
**Then** it is at least 44 by 44px, its icon is where it was, and it does not cover the dialog's title text

*(Covers FR277; `VSS-nuef`)*

**Tasks:**

- [ ] `web/src/lib/version-compare.ts` with unit tests for every rule and for unreadable input (Epic 21 ADR-8 decisions 1 to 5) (`VSS-qxxo`)
- [ ] Use it in the installed mods Version column and in the Version table (the column's sort and the "newer" mark, replacing the private function); table tests for both directions and the cards; a `fix(web)` commit with the release note (ADR-8 decision 1) (`VSS-qxxo`)
- [ ] `aria-sort` on the sortable headers of both tables, chevrons hidden from screen readers; unit tests for each state; a `fix(web)` commit with the release note (ADR-9 decisions 1 and 2) (`VSS-whnb`)
- [ ] Remove the two casts in `VersionTable.tsx`; a `refactor` commit (ADR-9 decision 3) (`VSS-759m`)
- [ ] 44px close buttons in `ui/dialog.tsx` and `ui/sheet.tsx`; an E2E check of the size at 390px for one dialog and the sheet; a `fix(web)` commit with the release note (ADR-9 decisions 4 and 5) (`VSS-nuef`)

---

### Story 21.6: Mod Detail Page Polish

**Sprint key:** `21-6-mod-detail-polish`
**Beads:** `VSS-woae` (UI-094), `VSS-pzj8` (UI-092), `VSS-4vbj` (UI-093)
**FRs:** FR278, FR279, FR280

As a **user reading about a mod**,
I want **the page to fit my phone, the description to look like a document, and links to say where they open**,
So that **I can read and install from a phone, and a screen reader tells me before a link leaves the app**.

**Acceptance Criteria:**

**Given** the mod detail page of a mod with a homepage and a source URL
**When** a screen reader reads the ModDB Page, Homepage, Source and trailer links
**Then** each is announced with "(opens in a new tab)", and each shows a visible mark that it leaves the app

*(Covers FR278; `VSS-woae`)*

**Given** the other links in the web UI that open a new tab (the mod links in the installed list and on browse cards, the changelog links, the sidebar link)
**When** a screen reader reads them
**Then** each announces that it opens in a new tab, in the same words

*(Covers FR278; ADR-10 decisions 1 and 2, found in planning)*

**Given** a mod description that contains an SVG with a link
**When** the description is shown
**Then** the link opens in a new tab with `rel="noopener noreferrer"` and has an accessible note that says so; sanitizing the result again adds no second note; and a note the mod author wrote cannot stand in for it

*(Covers FR278; `VSS-woae`; ADR-10 decisions 4 and 5)*

**Given** the mod detail page at 320, 390 and 430px
**When** I open a mod with a long name, tags and an install card
**Then** the page does not scroll sideways, the header is stacked with the install card at full width, every control is inside the viewport, and the install and version controls are at least 44px tall

*(Covers FR279; `VSS-pzj8`)*

**Given** the mod detail page at 768px and wider
**When** I open it
**Then** the header is the one row it is today

*(Covers FR279)*

**Given** a description with headings, paragraphs, a bulleted and a numbered list, a link, a quote, inline code, a code block and a table
**When** it is shown in the light and in the dark theme
**Then** headings are larger and bolder than body text, lists show their markers and indentation, the link is in the link colour and underlined, the quote, code and table are set apart, and every colour comes from the theme

*(Covers FR280; `VSS-4vbj`)*

**Given** a description with a table, an image, a code block or a URL wider than the card
**When** it is shown at 320px
**Then** the wide element scrolls or shrinks inside the card and the page does not scroll sideways

*(Covers FR279, FR280)*

**Given** `web/package.json` and the description container
**When** the story is done
**Then** no dependency was added and the container has no `prose` class

*(Covers FR280; ADR-11 decisions 5 and 6)*

**Given** a description whose author set inline styles
**When** it is shown
**Then** the author's styles still apply over the defaults

*(Covers FR280; ADR-11 decision 7)*

**Tasks:**

- [ ] A new-tab link component with the hidden note; use it for the five unmarked links; the same wording in the three `aria-label` links; the visible mark on Homepage and Source; unit tests; a `fix(web)` commit with the release note (Epic 21 ADR-10 decisions 1 to 3) (`VSS-woae`)
- [ ] SVG links in descriptions get a `<title>` note in the sanitizer hook; unit tests including idempotence; confirm in a browser's accessibility snapshot and record the result (ADR-10 decisions 4 to 6) (`VSS-woae`)
- [ ] The header stacks below `md`, with the skeleton; unit tests; a `fix(web)` commit with the release note (ADR-11 decisions 1 and 2) (`VSS-pzj8`)
- [ ] Description styles under `.mod-description`, wide content contained, `prose` classes removed; a `fix(web)` commit with the release note (ADR-11 decisions 3 to 7) (`VSS-4vbj`)
- [ ] E2E on a stubbed mod detail answer: no sideways scroll and a stacked header at 320, 390 and 430px, the unchanged row at 768px, heading, list and link styles in both themes (ADR-11 decision 8)

---

### Story 21.7: Tabs and Tables on Phones

**Sprint key:** `21-7-tabs-and-tables-on-phones`
**Beads:** `VSS-3ry` (UI-089), `VSS-vt4` (UI-091, bug), `VSS-f9y` (UI-087)
**FRs:** FR281, FR282, FR283

As a **user on a phone or tablet**,
I want **tabs I can tap, tabs that answer the keyboard at once, and tables that fit the screen**,
So that **I do not miss a tab, lose a key press or scroll a table sideways inside the page**.

**Acceptance Criteria:**

**Given** the Settings, Mods and Version pages below 1024px
**When** I measure their tab buttons
**Then** each is at least 44px tall, and from 1024px up they are the height they are today

*(Covers FR281; `VSS-3ry`)*

**Given** the Settings tab list at 320 to 430px
**When** it wraps to two rows
**Then** both rows are inside the list's background, nothing overlaps the panel below, and the page does not scroll sideways

*(Covers FR281)*

**Given** the arrow key fault of `VSS-vt4`
**When** the story starts on it
**Then** it is first reproduced with a real keyboard in Chromium and Firefox and with the scripted steps, within the time box, and what was seen is recorded in the story

*(Covers FR282; ADR-12 decision 3)*

**Given** the fault is reproduced and its cause is in this project's code
**When** I focus a Settings tab as soon as the list is shown and press ArrowRight three times
**Then** focus and selection move one tab per press, in a unit test and in an E2E with no added wait

*(Covers FR282; ADR-12 decision 4)*

**Given** the fault cannot be reproduced with a real keyboard, or its cause is inside the tabs library
**When** the story ends
**Then** no workaround was added, and the bead is closed with the evidence: what was tried, on which browsers, and what was seen

*(Covers FR282; ADR-12 decision 5)*

**Given** the Scheduled Jobs tab from 320 to 1023px, with the sidebar expanded and collapsed
**When** I open it with an Admin key
**Then** each job is a card with its name, schedule, next run and status labelled, nothing scrolls sideways inside the panel, and from 1024px up the table is unchanged

*(Covers FR283; `VSS-f9y`)*

**Given** the Version page at 320 and 390px
**When** I open it
**Then** the version table fits its container without scrolling inside itself, each row still shows its channel, and its install action is at least 44px tall

*(Covers FR283; `VSS-f9y`)*

**Given** every page of the web UI (Dashboard, Version, Game Settings, Mods installed and browse, mod detail, both console pages, each Settings tab)
**When** it is measured at 320, 390, 430, 768 and 1023px in both sidebar states
**Then** the measurements are saved in the story's folder, and each page that scrolls sideways or has a table scrolling inside itself is either fixed in this story or reported to the maintainer in the pull request with its numbers

*(Covers FR283; the comment on `VSS-f9y`; ADR-13 decision 4)*

**Tasks:**

- [ ] 44px tab triggers below `lg` in `ui/tabs.tsx`; check the three tab lists at 320, 390, 430 and 768px; extend `layout-widths.spec.ts`; a `fix(web)` commit with the release note (Epic 21 ADR-12 decisions 1 and 2) (`VSS-3ry`)
- [ ] Reproduce the arrow key fault (real keyboard, then scripted) and record it; fix it with a unit test and an E2E, or close the bead with the evidence (ADR-12 decisions 3 to 5) (`VSS-vt4`)
- [ ] Scheduled Jobs as cards below `lg`, with unit tests for both layouts (ADR-13 decision 1) (`VSS-f9y`)
- [ ] The Version table without a Channel column below `sm`, channel shown under the version; unit tests (ADR-13 decision 2) (`VSS-f9y`)
- [ ] Measure every page at the five widths in both sidebar states, save the numbers, fix what is of the same kind; extend `layout-widths.spec.ts` for the two tables; a `fix(web)` commit with the release note (ADR-13 decisions 3 to 5) (`VSS-f9y`)

---

### Story 21.8: Sidebar Default and Content Width

**Sprint key:** `21-8-sidebar-default-and-content-width`
**Beads:** `VSS-w85` (UI-090), `VSS-alx` (UI-088)
**FRs:** FR284, FR285

As a **user on a tablet or a wide monitor**,
I want **the sidebar out of the way where space is short, and pages that do not stretch across a wide screen**,
So that **content has room at tablet widths and stays readable on large monitors**.

**Acceptance Criteria:**

**Given** a browser with no stored preferences
**When** I open the app at 900px
**Then** the sidebar is collapsed (64px), and at 1024px and wider it is expanded (160px)

*(Covers FR284; `VSS-w85`)*

**Given** no stored sidebar choice
**When** I resize the window across 1024px
**Then** the sidebar collapses and expands with the width

*(Covers FR284; ADR-14 decision 3)*

**Given** any width from 768px
**When** I use the sidebar's toggle
**Then** the sidebar changes, the choice is stored, and it is kept at every width and after a reload

*(Covers FR284; ADR-14 decision 4)*

**Given** a cookie written before this story with `sidebarCollapsed: true`
**When** I open the app
**Then** the sidebar is collapsed at every width from 768px, as before

*(Covers FR284; ADR-14 decision 2)*

**Given** a cookie written before this story with `sidebarCollapsed: false`
**When** I open the app
**Then** the sidebar follows the width: collapsed from 768 to 1023px and expanded from 1024px

*(Covers FR284; ADR-14 decision 2)*

**Given** UI Preferences
**When** I open the sidebar setting
**Then** I can choose Automatic, Expanded or Collapsed, the current value is shown, and Automatic returns the sidebar to following the width

*(Covers FR284; ADR-14 decision 5)*

**Given** a phone width and a stored choice of Collapsed
**When** I open the navigation menu
**Then** the sheet shows the full sidebar with labels and no collapse toggle

*(Covers FR284; ADR-14 decision 6, found in planning)*

**Given** the Dashboard, the Version page, Game Settings, the Mods page with both tabs and Settings at 1920px, in both sidebar states
**When** I measure the content
**Then** it is at most 1280px wide and centered in the area right of the sidebar, and nothing is clipped

*(Covers FR285; `VSS-alx`)*

**Given** the mod browser at 1920px
**When** I open it
**Then** the grid has four columns inside the 1280px content width

*(Covers FR285; ADR-15 decision 3)*

**Given** the Console page and the game server page with the console at 1920px
**When** I measure the console
**Then** it uses the full width of the content area and is wider than 1280px

*(Covers FR285; ADR-15 decision 4)*

**Given** the code
**When** I search for the 1280px width
**Then** it is written in one place, and Game Settings uses it

*(Covers FR285; ADR-15 decision 1)*

**Given** every page below 1280px of content width
**When** I compare it with before the story
**Then** its layout is unchanged

*(Covers FR285)*

**Tasks:**

- [ ] The sidebar preference becomes `auto`, `expanded` or `collapsed` with the migration of the old key; the effective state follows the width when `auto`; unit tests at 767, 768, 1023 and 1024px and for both old cookie values (Epic 21 ADR-14 decisions 1 to 4) (`VSS-w85`)
- [ ] The three-way control in UI Preferences and the always-full sidebar in the phone sheet; unit tests; a `feat(web)` commit with the release note (ADR-14 decisions 5 and 6) (`VSS-w85`)
- [ ] `layout-widths.spec.ts` writes the new key and checks a fresh browser at 900px and 1024px (ADR-14 decision 7) (`VSS-w85`)
- [ ] The 1280px cap in `Layout` with one constant, the console pages opted out, Game Settings on the shared constant; unit tests; a `feat(web)` commit with the release note (ADR-15 decisions 1 to 5) (`VSS-alx`)
- [ ] Check each capped page and the console at 1440, 1920 and 2560px in both sidebar states and extend `layout-widths.spec.ts`; update the UX notes in the story on what the spec asked and what was built (ADR-15 decision 6) (`VSS-alx`)

### 4.4 Architecture (`architecture/epic-21-maintainer-decisions-and-web-polish.md`, new)

| ADR | Decision | Story | Decided by |
|---|---|---|---|
| ADR-1 | Prettier at an exact version; `singleQuote`, `printWidth: 100`, `trailingComma: es5`; every tracked `.ts`, `.tsx`, `.css` and `.json` under `web/` except recorded fixtures (Markdown, HTML and output directories ignored); one reformat commit of about 231 files, its own story, first among the web stories, in `.git-blame-ignore-revs`; `just lint-web` becomes the format check and CI's `web` job runs it | 21.1 | Matt, 2026-11-17; options and covered files by the planner |
| ADR-2 | `minimumReleaseAge: null` is removed from the uv rule; the pull request opens with the Dockerfile half, fails the uv version test for about a day and must not be merged before the `.mise.toml` half joins; the rule's description and `RELEASING.md` say so; the script test is not relaxed | 21.2 | Matt, 2026-11-17 |
| ADR-3 | One rule: `dockerfile` manager, update types `digest` and `pinDigest`, type `chore`; the preset's `container` scope stays; version changes keep the preset's `fix` or `feat` | 21.2 | Matt, 2026-11-17; the rule's form by the planner |
| ADR-4 | `VS_LOG_LEVEL` is validated when the settings are read (four values, any case, blank is unset, anything else stops start-up naming the setting); it sets the level at start-up and nothing else `VS_DEBUG` controls; the run-time debug switch still sets DEBUG and returns to the configured level; the debug state comes from the settings | 21.3 | Matt, 2026-11-17; the switch rule by the planner |
| ADR-5 | One list of four Discord hosts for redaction and sending; listings leave out entries that resolve outside the data directory for every role; the path and role checks run before the missing-directory shortcut | 21.3 | Planner |
| ADR-6 | The remove dialog's confirm is a plain button: the dialog stays open and cannot be dismissed while the DELETE runs, closes on success, and stays open with "Remove" enabled again on an error (one toast); pending is the mutation's `variables` equal to the dialog's mod; the optimistic removal stays; the uninstall dialog gets the same Escape guard | 21.4 | Matt, 2026-11-17; error and dismissal behaviour by the planner |
| ADR-7 | A failed mutation shows one toast: where callers report the error, the hook silences the client default with its own `onError` (the existing form of two hooks); applied to `useInstallMod` and four more hooks with the same fault; the rule goes into `project-context.md`; no `MutationCache` redesign | 21.4 | Planner |
| ADR-8 | One `compareVersions` in `web/src/lib/version-compare.ts` following Semantic Versioning precedence, total and tolerant of loose strings, used by both tables and the "newer" mark; no package added | 21.5 | Planner |
| ADR-9 | `aria-sort` (`ascending`, `descending`, `none`) on every sortable header of both tables; the two casts in `VersionTable.tsx` are removed; the close button of dialogs and sheets is a 44px box at every width with the icon where it is | 21.5 | Planner |
| ADR-10 | One component for application links that open a new tab, with the hidden note; the same words in the three `aria-label` links; a visible mark on Homepage and Source; SVG links in descriptions get a `<title>` note from the sanitizer hook, confirmed in a browser | 21.6 | Planner |
| ADR-11 | The mod detail header stacks below `md`; descriptions are styled by rules under `.mod-description` with theme tokens, wide content contained, the dead `prose` classes removed; `@tailwindcss/typography` is not added | 21.6 | Planner |
| ADR-12 | Tab triggers are at least 44px tall below `lg`, changed once in `ui/tabs.tsx` and checked on all three tab lists; the arrow key fault gets a time-boxed reproduction with a real keyboard first, then a fix in the project's code or a closure with evidence, never a workaround | 21.7 | Planner |
| ADR-13 | Scheduled Jobs becomes cards below `lg`; the Version table hides Channel below `sm` and shows it under the version; every page is measured at five widths in both sidebar states, same-kind faults are fixed and the rest reported | 21.7 | Planner |
| ADR-14 | The sidebar preference becomes `auto`, `expanded` or `collapsed` (old `true` is `collapsed`, old `false` is `auto`); `auto` is collapsed from 768 to 1023px and expanded from 1024px, live; a choice wins at every width; UI Preferences offers the three values; the phone sheet always shows the full sidebar | 21.8 | Planner |
| ADR-15 | `Layout` caps content at 1280px, centered, from one constant; the mod browser grid is capped (it keeps its four columns); the two console pages are not capped | 21.8 | Planner |

The file also records the facts the decisions rest on, with file and line references.

### 4.5 Other Artifacts

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | `epic-21` (backlog), `epic-21-retrospective` (optional) and the eight story keys (backlog), via `scripts/sprint-status.sh` | Now |
| Beads | Epic `Epic 21: Maintainer Decisions and Web Polish` (`VSS-syuj`), labels UI, API and TOOLS; the 14 in-scope issues are its children. No child bead's content was changed | Now, and per story |
| `architecture/index.md` | Entry for the Epic 21 ADRs | Now |
| `project-context.md`, `CLAUDE.md`, README, `.env.example`, `RELEASING.md`, `web/e2e/README.md`, `architecture/project-structure-boundaries.md` | The rules, commands and settings the stories change | Stories 21.1 to 21.8 |
| `.github/workflows/ci.yml`, `Justfile`, `renovate.json`, `.git-blame-ignore-revs`, `web/package.json` | As the stories say | Stories 21.1 and 21.2 |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 21.1 to 21.8 from `epics.md` and the Epic 21 ADRs |
| Developer (`dev-story`) | Implement each story. In 21.1, the format commit holds nothing else and merges before any other web branch is cut. In 21.3, 21.4, 21.5, 21.6, 21.7 and 21.8, each change with a release note is its own commit with the subject written for users |
| Reviewer (`code-review`) | Delegated review per story. For 21.1, reproduce the format commit and compare trees |
| Maintainer (Matt) | Answers the open questions below, before the story each belongs to starts; watches the first uv pull request after 21.2 |

**Decided by the maintainer before planning (Matt, 2026-11-17), not open:** the five decisions as listed in section 1, and the fourteen beads.

**Open questions for the maintainer.** Each has a default; a story follows it unless he answers otherwise.

1. **`VS_LOG_LEVEL` against the run-time debug switch (ADR-4 decision 3; Story 21.3).** Default: `VS_LOG_LEVEL` sets the level at start-up and wins over `VS_DEBUG` there; turning debug logging on in the UI still sets DEBUG, and turning it off returns to `VS_LOG_LEVEL` (or INFO when unset). Alternative: `VS_LOG_LEVEL` always wins and the switch changes only the output format, which makes the switch do nothing visible when the variable is set.
2. **Is the start-up error for an invalid `VS_LOG_LEVEL` marked as breaking? (ADR-4 consequences; Story 21.3)** Default: no. The setting did nothing until now and no file in the repository sets it; the release note and README say that an invalid value stops start-up. Alternative: mark the commit breaking (`feat(api)!`), which puts it under Breaking Changes.
3. **The remove dialog on an error and while it waits (ADR-6 decisions 3 and 4; Story 21.4).** Default: on an error the dialog stays open with "Remove" enabled again (one toast), like the server uninstall dialog; while the request runs, Cancel is disabled and Escape is ignored. Alternative: close the dialog on an error, as today, and rely on the toast.
4. **The four other actions that show two toasts (ADR-7 decision 2; Story 21.4).** Default: fix all five in Story 21.4 (mod install from `VSS-oc28`, and server install, uninstall, restart and the webhook setting found in planning). Alternative: fix only the mod install and leave the others as they are.
5. **Description typography by hand, not by the plugin (ADR-11 decisions 3 and 6; Story 21.6).** Default: rules under `.mod-description` with theme tokens, no new dependency. Alternative: add `@tailwindcss/typography` (a new dev dependency; its `prose-invert` palette would still need overrides for the light theme).
6. **The sidebar preference (ADR-14; Story 21.8).** Default: three values (`auto`, `expanded`, `collapsed`); with `auto` the sidebar is collapsed from 768 to 1023px; an explicit choice wins at every width; an old stored `false` is read as `auto` (so a user who had expanded by choice gets the tablet default once), an old `true` as `collapsed`; UI Preferences offers the three values. Alternatives: keep the boolean and never collapse by width for a browser that has a cookie (the default would then reach only new browsers); or remember a choice per width range.
7. **Exceptions to the 1280px width (ADR-15 decisions 3 and 4; Story 21.8).** Default: the two console pages use the full width; the mod browser is capped and keeps its four columns (cards about 308px wide at 1920px where they are about 416px today). Alternative: leave the mod browser uncapped and give it more columns on wide screens, which is a larger change.
8. **Prettier's options and what it covers (ADR-1 decisions 2 to 4 and 8; Story 21.1).** Default: `singleQuote`, `printWidth: 100`, `trailingComma: es5`; the shadcn files in `src/components/ui` are formatted like the rest; Markdown and `index.html` are not covered; `just lint-web` becomes the format check (its `tsc` run duplicated `just typecheck-web`) and CI's `web` job gains the step. Alternatives: `trailingComma: all` (Prettier's default; 265 files instead of 242 before ignores), or leaving `src/components/ui` out (23 fewer files, two styles in the tree).
9. **The two tables on phones (ADR-13 decisions 1 and 2; Story 21.7).** Default: Scheduled Jobs as cards below 1024px; the Version table hides its Channel column below 640px and shows the channel under the version. Alternative: hide columns in both and accept that Scheduled Jobs still scrolls at 320px.
10. **Pull-ins (below).** Default: `VSS-q38r` into Story 21.4; `VSS-koo1` not now.

**Other open beads that share files with this epic (proposed, not added):**

| Bead | Shares | Recommendation |
|---|---|---|
| `VSS-q38r` (UI-097, size-s) Browse cards keep the old game version's badges after the installed version changes | `web/src/hooks/use-server-status.ts`: the fix invalidates the browse queries in `useInstallServer` and `useUninstallServer`, the hooks Story 21.4 edits for the toasts | Pull into Story 21.4. The story already has six tasks, so the uninstall dialog's Escape guard would be folded into the first task to keep the limit. One more bead closed |
| `VSS-koo1` (API-094, size-s) Content-Security-Policy follow-ups | Its second half (description media the policy blocks) is in `web/src/lib/mod-description.ts`, which Story 21.6 edits | Not now. Each item needs a policy decision (allow, strip or replace), which is security work for its own story, not polish |

Seen and not proposed, because they share no file with a story: `VSS-2bp` (favicon; web polish, but `index.html` and `public/` only), `VSS-7z3` (read-only game settings for a Monitor key), `VSS-o8s` (file browser paths with a slash), `VSS-9jv` (interval fields).

**Found during planning and handled inside the epic (no bead filed):**

1. CI's `web` job does not run `just lint-web`, so a format check there alone would not reach CI; Story 21.1 adds the step.
2. The recorded mod database fixtures would be 54,000 of the reformat's changed lines; Story 21.1 ignores `e2e/fixtures/`.
3. `main.py:170` does not set the log level, it logs a derived string; the level is set in `config.py:312-325`. ADR-4 names the right place, and the log line is corrected.
4. `VS_DEBUG` is parsed twice with different rules (`on` is true for the settings and false for logging); Story 21.3 uses one.
5. `project-context.md` describes `VS_LOG_LEVEL` as working, and does not contain the mutation `onError` rule that the code comments rely on; Stories 21.3 and 21.4 correct both.
6. Four more hooks show two toasts on failure (server install, uninstall, restart; the webhook setting); Story 21.4 fixes them with the bead's one (open question 4).
7. The server uninstall dialog, the model for the remove dialog, closes on Escape while its request runs; Story 21.4 guards it.
8. The Version page sorts versions with the same fault as `VSS-qxxo`, and its "newer" mark puts `rc.12` before `rc.2`; Story 21.5 uses the one comparison everywhere.
9. `VersionTable` sets no `aria-sort="none"` on unsorted sortable columns, and the phone navigation sheet's close button has the fault of `VSS-nuef`; Story 21.5 covers both.
10. Two more links open a new tab without saying so (`InstalledModParts.tsx:43`, `layout/Sidebar.tsx:210`), and the three that say it use different words; Story 21.6 covers them.
11. `prose-invert` would be wrong in the light theme even with the plugin; ADR-11 records it as a reason for hand-written styles.
12. Every browser already stores `sidebarCollapsed: false`, so "no stored preference" in `VSS-w85` cannot be detected as the bead assumes; ADR-14 changes the preference's shape.
13. A stored collapsed sidebar is shown icon-only inside the 256px phone sheet (by reading the code); Story 21.8 confirms and fixes it.
14. The mod browser grid never has more than four columns, so the cap does not reduce its columns as `VSS-alx` feared; it narrows the cards. ADR-15 records the numbers.
15. Admin listings may also show a `.json` file link that leaves the data directory (the same shortcut as for directories); Story 21.3 tests files and directories.

**Seen and left alone, with the reason (no bead filed):**

1. uvicorn's own log lines do not follow `VS_LOG_LEVEL`. The setting is about the API's structured log; the README says so.
2. The `/debug` responses do not report the level. Not asked for; an additive field can follow if the UI ever shows it.
3. The install dialogs (plain dialogs with a close button) can still be closed while their request runs; the request continues and its toast reports the result. Only the two destructive alert dialogs are guarded.
4. A redesign of mutation error handling around a `MutationCache` handler (ADR-7 decision 4).
5. More mod browser columns on very wide screens (ADR-15 decision 3).
6. The web still has no ESLint. Prettier is what the maintainer decided; a linter is a separate decision.
7. Pull request #185 (uv 0.13.9) is open under the current rule with both halves; it can be merged before or after Story 21.2.

**Planned net bead change:** closed 14 (the beads the maintainer picked). Opened 1 (the epic bead `VSS-syuj`, which closes with the epic). Filed from planning: none. Net: 14 fewer open beads, from 32 open before the epic to 18 after it (17 if `VSS-q38r` is pulled in).

**Success criteria:**

- `prettier --check` passes over the web, the format commit is alone and reproducible, and CI fails on an unformatted web file
- `renovate.json` validates; the uv rule has no hold override and `RELEASING.md` explains the red first day; a digest refresh of a Dockerfile image is committed as `chore(container)`
- `VS_LOG_LEVEL=warning` gives WARNING-level logs, an invalid value stops start-up naming the setting, and with it unset nothing changes
- The three config viewer cases of `VSS-wv0w` answer as ADR-5 says, for both roles
- The remove dialog stays open until its own mod's DELETE has succeeded and stays open on an error; each of the five failing actions shows one toast
- `1.0.0-rc.2 < 1.0.0-rc.12 < 1.0.0` in both tables; sortable headers carry `aria-sort`; close buttons measure 44px
- The mod detail page has no sideways scroll at 320px, descriptions show headings, lists and links in both themes, and every new-tab link says so
- Tab buttons measure 44px below 1024px; the arrow key bead is closed with a fix or with evidence; the two tables fit at 320px; every page has measurements
- A fresh browser at 900px has a collapsed sidebar, a stored choice wins, and content is at most 1280px wide except on the console pages
- Each of the 14 in-scope beads is closed with an AAR by its story
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: five maintainer decisions after Epic 20 and fourteen beads he chose. [x] 1.2 type: one bug (`VSS-vt4`), twelve web polish tasks, one API task, and five decisions on tooling, configuration and behaviour. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete except one line of Story 20.7's Renovate rule and Epic 20 ADR-1 decision 7. [x] 2.5 no resequencing; order inside Epic 21 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR260-FR285 added, MVP unaffected. [x] 3.2 architecture: new Epic 21 ADRs. [x] 3.3 UX spec: no text change; two of its rules are built and one exception is recorded in ADR-15. [!] 3.4 CI: one new step in the `web` job; one new dev dependency; one setting starts to work and can stop start-up when invalid |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1 scope approved before planning; the five decisions are Matt's (2026-11-17). [!] 6.2, 6.3 ten open questions with defaults are waiting for the maintainer; the planner's ADRs (ADR-5 and ADR-7 to ADR-15, and parts of ADR-1, ADR-3, ADR-4 and ADR-6) have not been reviewed yet. [x] 6.4 handoff in section 5 |
