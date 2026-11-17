# Story 21.7: Tabs and Tables on Phones

Status: ready-for-dev

<!-- Implements FR281-FR283, Epic 21 ADR-12 and ADR-13. Beads: VSS-3ry (UI-089), VSS-vt4 (UI-091, bug), VSS-f9y (UI-087). Stacked on Story 21.6 (stories run in order 21.1 to 21.8); Story 21.8 follows directly and extends the same E2E spec. Line references were verified at 966204f (epic-21-planning; web/ identical to 05436da, the commit the ADRs cite) and must be re-checked at implementation time: Story 21.1 reformats about 231 web files with Prettier (ui/tabs.tsx, JobsTable.tsx, VersionTable.tsx and layout-widths.spec.ts among them), and Story 21.5 edits VersionTable.tsx (sort function, aria-sort, the two meta casts). Web only. No API change, no new dependency. -->

## Story

As a **user on a phone or tablet**,
I want **tabs I can tap, tabs that answer the keyboard at once, and tables that fit the screen**,
so that **I do not miss a tab, lose a key press or scroll a table sideways inside the page**.

## Acceptance Criteria

1. **Given** the Settings, Mods and Version pages below 1024px
   **When** I measure their tab buttons
   **Then** each is at least 44px tall, and from 1024px up they are the height they are today (tab list 36px, triggers about 30px)
   *(Covers FR281; `VSS-3ry`)*

2. **Given** the Settings tab list at 320 to 430px
   **When** it wraps to two rows
   **Then** both rows are inside the list's background, nothing overlaps the panel below, and the page does not scroll sideways
   *(Covers FR281)*

3. **Given** the arrow key fault of `VSS-vt4`
   **When** the story starts on it
   **Then** it is first reproduced with a real keyboard in Chromium and Firefox and with the scripted steps, within the time box (half a day), and what was seen is recorded in the story
   *(Covers FR282; ADR-12 decision 3)*

4. **Given** the fault is reproduced and its cause is in this project's code
   **When** I focus a Settings tab as soon as the list is shown and press ArrowRight three times
   **Then** focus and selection move one tab per press, in a unit test and in an E2E with no added wait
   *(Covers FR282; ADR-12 decision 4)*

5. **Given** the fault cannot be reproduced with a real keyboard, or its cause is inside the tabs library
   **When** the story ends
   **Then** no workaround was added, and the bead is closed with the evidence: what was tried, on which browsers, and what was seen
   *(Covers FR282; ADR-12 decision 5)*

6. **Given** the Scheduled Jobs tab from 320 to 1023px, with the sidebar expanded and collapsed
   **When** I open it with an Admin key
   **Then** each job is a card with its name, schedule, next run and status labelled, nothing scrolls sideways inside the panel, and from 1024px up the table is unchanged
   *(Covers FR283; `VSS-f9y`)*

7. **Given** the Version page at 320 and 390px
   **When** I open it
   **Then** the version table fits its container without scrolling inside itself, each row still shows its channel, and its install action (the "Select" button) is at least 44px tall
   *(Covers FR283; `VSS-f9y`)*

8. **Given** every page of the web UI (Dashboard, Version, Game Settings, Mods installed and browse, mod detail, the console pages, each Settings tab)
   **When** it is measured at 320, 390, 430, 768 and 1023px in both sidebar states
   **Then** the measurements are saved in the story's folder (`_bmad-output/implementation-artifacts/21-7-browser/`), and each page that scrolls sideways or has a table scrolling inside itself is either fixed in this story or reported to the maintainer in the pull request with its numbers
   *(Covers FR283; the comment on `VSS-f9y`; ADR-13 decision 4)*

AC 4 and AC 5 are alternatives: exactly one of them applies, decided by Task 3 (Dev Notes "The arrow key fault").

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-21.7/task-N): ...; fix only for a change a user can see, subject written for users (it becomes the release note). Red first where a unit test can fail first. Run Prettier on the web files you change (Story 21.1). -->

- [ ] Task 1: Measure every page before any change (AC: 8)
  - [ ] 1.1: New `_bmad-output/implementation-artifacts/21-7-browser/page_widths.mjs` (Dev Notes "Measurement method"), modelled on `17-8-browser/layout_widths.mjs`. Reads only: every non-GET API request is refused, no screenshot, the output holds numbers, test IDs and `data-slot` names only. Do not edit `17-8-browser/` or `18-4-browser/`: they are those stories' records
  - [ ] 1.2: Rebuild the stack from this branch (`just docker restart`), then `cd web && bun ../_bmad-output/implementation-artifacts/21-7-browser/page_widths.mjs > ../_bmad-output/implementation-artifacts/21-7-browser/page_widths.before.json` with `VS_API_KEY_ADMIN` exported. Do not start or stop the game server. Check that the output holds no key, server name or password
  - [ ] 1.3: Record in the Dev Agent Record one table: per page, width and sidebar state, the document overflow and every scrolling element with `scrollWidth/clientWidth`. Classify each scrolling element with the rule in Dev Notes "What counts as a fault". Compare the Scheduled Jobs and Version rows with Dev Notes "Planning measurements"
  - [ ] 1.4: Commit the script and `page_widths.before.json`: `docs(story-21.7/task-1): measure every page at phone and tablet widths`

- [ ] Task 2: Tab triggers are 44px tall below `lg` (AC: 1, 2) (`VSS-3ry`)
  - [ ] 2.1: `web/src/components/ui/tabs.tsx`: `TabsList` (`:27`) keeps `h-9` and gains `max-lg:h-auto`; `TabsTrigger` (`:43`) gains `max-lg:min-h-11`. Nothing else in the file changes, and no tab list's caller changes (Dev Notes "Tabs")
  - [ ] 2.2: `web/e2e/layout-widths.spec.ts`: new block "Tab heights (Story 21.7, AC 1-2)" (Dev Notes "E2E"): the three tab lists at 320, 390, 430, 768 and 1023px have triggers at least 44px tall; at 1024px the list is 36px and its triggers are under 36px; at 320, 390 and 430px the Settings list's two rows are inside the list and the panel starts below it
  - [ ] 2.3: Rebuild the stack, run `cd web && bunx playwright test e2e/layout-widths.spec.ts`. The existing blocks "Settings tabs on phones" (`:508-547`) and "Other tab lists on phones" (`:549-567`) must pass unchanged
  - [ ] 2.4: Commit: `fix(story-21.7/task-2): make tabs easier to tap on phones`

- [ ] Task 3: The arrow key fault: reproduce first, then fix or close with evidence (AC: 3, 4, 5) (`VSS-vt4`)
  - [ ] 3.1: New `_bmad-output/implementation-artifacts/21-7-browser/arrow_keys.mjs` (Dev Notes "The arrow key fault", "Reproduction script"): a scripted matrix and a headed mode for a real keyboard, both with the same in-page event log
  - [ ] 3.2: Scripted runs against the Docker stack (production build), Chromium and Firefox: the matrix of Dev Notes (wait after the list is shown x gap between presses, 10 runs per cell). Save `arrow_keys.scripted.json`
  - [ ] 3.3: Real keyboard, Chromium and Firefox, each at a 1440px and a 390px wide window: the steps of Dev Notes "Real keyboard steps", 10 attempts per step. **This subtask needs a person at a keyboard.** The dev agent prepares the script and asks the maintainer to run it; it is not ticked on scripted evidence (`project-context.md:160-161`). Save the event logs as `arrow_keys.keyboard.<browser>.json`
  - [ ] 3.4: Write the result into the Dev Agent Record under "Arrow key reproduction": browsers and versions, what was tried, the two result tables, and which outcome applies by the rule in Dev Notes "Decision rule". **Stop condition:** the task ends when 3.2 and 3.3 are recorded and the rule gives an outcome, or when half a working day has been spent on 3.1 to 3.4 without a cause in this project's code. In the second case outcome B applies if 3.3 was done; if 3.3 could not be done, leave 3.3 unticked, do not close `VSS-vt4`, and say so in the pull request
  - [ ] 3.5 (outcome A only: reproduced with a real keyboard, or the lost presses depend on the time since render, and the cause is in this project's code): fix the cause where it is (Dev Notes "If outcome A applies"), with a unit test in `web/src/features/settings/SettingsPage.test.tsx` that presses ArrowRight three times straight after the tab list is rendered, and an E2E test in `layout-widths.spec.ts` that focuses `ui-preferences-tab` as soon as it is visible and presses ArrowRight three times with no wait and no assertion between presses. Commit: `fix(story-21.7/task-3): settings tabs respond to arrow keys as soon as they appear`
  - [ ] 3.6 (outcome B only: a real keyboard cannot reproduce it, or the cause is inside Radix): change no source file and no test for this bead. No retry, no delay, no key handler of our own, no replacement of Radix's roving focus. Commit the script and the JSON files: `docs(story-21.7/task-3): record the arrow key reproduction for the settings tabs`. The AAR text for `VSS-vt4` (Dev Notes "Beads") is written into the Dev Agent Record

- [ ] Task 4: The Scheduled Jobs and Version tables fit phones (AC: 6, 7) (`VSS-f9y`)
  - [ ] 4.1: `web/src/components/JobsTable.tsx`: below `lg` render a list of cards, one per job, chosen with `useMediaQuery(LG_UP_QUERY)` so that one layout is mounted (Dev Notes "Scheduled Jobs cards"). The table from 1024px is unchanged; the empty state is the same in both layouts
  - [ ] 4.2: `web/src/components/JobsTable.test.tsx`: tests for both layouts (Dev Notes "Web unit tests"), red first
  - [ ] 4.3: First re-measure the Version table on the Docker stack with only the Channel column hidden below `sm` (ADR-13 decision 2 as written), at 320px with the fixture of Dev Notes "E2E", and record `scrollWidth/clientWidth` in the Dev Agent Record. Planning measured 281/256, and 260/256 with ADR-13's icon button fallback added (Dev Notes "ADR against the code"). If your measurement also exceeds the container, continue with 4.4 as written. If it fits (for example because Story 21.5 changed the cells), stop at the Channel column and say so in the Completion Notes
  - [ ] 4.4: `web/src/components/VersionTable.tsx`: below `sm` the Channel and Status columns are hidden and their content is shown under the version number; the "Select" button is 44px tall below `lg`; the loading skeleton hides the same two columns (Dev Notes "Version table")
  - [ ] 4.5: `web/src/components/VersionTable.test.tsx`: tests for the inline channel and status and the classes (Dev Notes "Web unit tests"), red first
  - [ ] 4.6: `web/e2e/layout-widths.spec.ts`: new blocks "Scheduled Jobs below lg (Story 21.7, AC 6)" and "Version table on phones (Story 21.7, AC 7)" (Dev Notes "E2E"). Rebuild the stack and run the spec; also run `e2e/settings-as-saved.spec.ts` (it reads `job-schedule-*` and `job-next-run-*` on the Scheduled Jobs tab and changes a real setting which it restores itself; do not edit it)
  - [ ] 4.7: Commit: `fix(story-21.7/task-4): fit the scheduled jobs and version tables on phone screens`

- [ ] Task 5: Measure again, fix what is of the same kind, report the rest (AC: 8)
  - [ ] 5.1: Rebuild the stack and run `page_widths.mjs` into `21-7-browser/page_widths.after.json`. Record a before/after table in the Dev Agent Record. The Scheduled Jobs and Version rows must show no scrolling element from 320 to 1023px in both sidebar states (ADR-13 decision 3)
  - [ ] 5.2: For every other fault in the table (Dev Notes "What counts as a fault"): if the fix is of the same kind (a table, or a row of controls that does not wrap), fix it here with a unit test where a unit test can see it and one test in `layout-widths.spec.ts` at the width that failed; each such fix is its own commit `fix(story-21.7/task-5): fit <what> on phone screens`, written for users, and is listed in the pull request as a release note the proposal did not list. Anything larger (a page layout, a chart, a third-party widget, the mod browser's filters as a whole) is not fixed and not filed: it goes into the Completion Notes and the pull request with page, width, sidebar state and numbers
  - [ ] 5.3: `web/e2e/README.md` (`:10`, `:50`): update the test counts from `cd web && bunx playwright test --list --grep-invert "@moddb|@game-server|@install"` and `--list`; the numbers there (119 untagged, 146 of 150) are older than this epic, so count, do not add
  - [ ] 5.4: Commit `page_widths.after.json` and the README: `docs(story-21.7/task-5): record page widths after the phone layout changes`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes. `just lint-web` (the Prettier check since Story 21.1) passes. The diff adds no lint or type suppression, no `cast`/`as` on column meta, no skipped test, no `test.only`, no dependency. `git status --short` shows nothing under `dev/`, `data/`, `web/playwright-report/`, `web/test-results/`
  - [ ] 6.2: `just test-e2e-ci` is green (both passes, throwaway containers). All new tests are untagged, so the first pass runs them; record the counts
  - [ ] 6.3: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md:160-161`): Dev Notes "Manual check"
  - [ ] 6.4: Story status `review`, `just sprint set 21-7-tabs-and-tables-on-phones review`, pull request (base: Story 21.6's branch while its pull request is open, otherwise `main`; merge, do not squash). The description lists: "API contract changes: none"; the release notes (Dev Notes "Git Intelligence"); the arrow key outcome with its evidence; every measured fault that was not fixed, with its numbers (AC 8); the decision about the Status column (Dev Notes "ADR against the code")
  - [ ] 6.5: After merge the controller closes `VSS-3ry`, `VSS-f9y` and `VSS-vt4`, each with an AAR (abbreviated format, size-s) and `bd sync` (Dev Notes "Beads"). `VSS-vt4` is closed only if Task 3 reached an outcome

## Dev Notes

### The defects (verified at 966204f)

- **Tab buttons are about 30px tall (`VSS-3ry`).** `TabsList` is `inline-flex h-9 w-fit items-center justify-center rounded-lg p-[3px]` and `TabsTrigger` is `h-[calc(100%-1px)]` (`web/src/components/ui/tabs.tsx:27`, `:43`): 36px list, 29 to 30px trigger. Three tab lists use them and no other file imports `ui/tabs`: Settings (`features/settings/SettingsPage.tsx:44-65`; its list already has `h-auto max-w-full flex-wrap`, `:46`, from Story 17.8), Mods (`features/mods/ModsPage.tsx:100-121`, list at `:101`) and the Version page's channel filter (`components/ChannelFilter.tsx:42-58`, list at `:47`). The UX spec asks for 44 by 44px touch targets (`ux-design-specification.md:1289-1292`). The project's pattern is 44px below `lg`: `max-lg:h-11` (`features/mods/InstalledTab.tsx:98`, `:109`), `min-h-11` (`InstalledModCard.tsx:52`, `:78`).
- **Scheduled Jobs scrolls inside itself (`VSS-f9y`).** `JobsTable` has four text columns (`components/JobsTable.tsx:73-111`) and the shared `Table` wraps itself in `overflow-x-auto` (`components/ui/table.tsx:9`). It needs 523px and has 238, 308 and 348px at 320, 390 and 430px, and 510px at 768px with the sidebar expanded (`17-8-browser/layout_widths.after.json`). It sits inside a card (`features/settings/ScheduledJobsPanel.tsx:76-86`).
- **The Version table scrolls inside itself (`VSS-f9y`).** Five columns (`components/VersionTable.tsx:134-248`), Size already `hidden sm:table-cell` (`:191-193`). It needs 361px and has 256px at 320px and 326px at 390px: the page has its own `p-4` (`features/game-server/VersionPage.tsx:130`) inside the layout's `p-4`. The "Select" button is `size="sm"`, 32px tall (`:235-243`; `ui/button.tsx:25`).
- **Lost arrow key presses (`VSS-vt4`).** See "The arrow key fault". The Settings list gains its fourth trigger when `useAuthMe` resolves (`SettingsPage.tsx:35-36`, `:59-64`).
- **Pages never measured on phones.** Story 17.8 measured the Dashboard, the console and the mod browser only at 1920px (`17-8-browser/layout_widths.mjs`, header comment; the bead's comment).

### Planning measurements (a throwaway prototype, since discarded)

Measured on 2026-11-17 at 966204f with the changes of Tasks 2 and 4 applied, on the local Vite dev server (`bunx vite`), headless Chromium, every API answer stubbed (three jobs, four versions as in "E2E"). They are planning numbers: the Docker stack must confirm them (Tasks 1, 4.3 and 5.1).

| Width, sidebar | Tab trigger / list height | Settings list (rows) | Jobs | Version table (scroll/container) |
|---|---|---|---|---|
| 320, either | 44 / 50 | 94px (2 rows of 2) | cards 238px wide, no scroll | 256/256 |
| 390, either | 44 / 50 | 94px (2 rows of 2) | cards 308px, no scroll | 326/326 |
| 430, either | 44 / 50 | 94px (3 + 1) | cards 348px, no scroll | 366/366 |
| 768, expanded | 44 / 50 | 50px (1 row) | cards 510px, no scroll | 528/528, five columns from 640px |
| 1023, expanded | 44 / 50 | 50px | cards 765px, no scroll | 783/783 |
| 1024, expanded | 29 (Mods, Version), 30 (Settings) / 36 | 36px | table | 784/784, button 32px |

At 320 to 430px the panel started 24px below the two-row list (list 64 to 158px, panel at 182px) and no document scrolled sideways. The Version table variants at 320px (container 256px):

| Variant | scrollWidth / clientWidth | Columns (Version, Status, Actions) |
|---|---|---|
| Today (five columns, Size hidden) | 361/256 (Story 17.8) | |
| Channel hidden, badge under the version | 281/256 | 112, 88, 81 |
| The same, button as a 44px icon and the Actions header hidden from sight | 260/256 | 112, 88, 60 |
| Channel and Status hidden, both shown under the version | 256/256 (fits; the two columns need about 193px) | 164 to 175, 81 to 92 |

### Tabs (Task 2)

- The change is two class names in one file. Below `lg` the list's height is automatic and each trigger is at least 44px, so a one-row list is 50px (44 + 2 x 3px padding) and the wrapped Settings list is 94px. From `lg` the classes do not apply and everything is as today.
- `h-[calc(100%-1px)]` on the trigger stays: with an automatic list height the percentage has nothing to resolve against and the minimum decides.
- `SettingsPage.tsx:46` keeps its own `h-auto max-w-full flex-wrap`; do not remove `h-auto` there (it is what keeps the Settings list 36px with 30px triggers from `lg`, as today, and removing it would change the desktop height by a pixel).
- There is no unit test for the height: jsdom has no layout (the same reason as Epic 21 ADR-9 decision 5). The E2E block pins it. Do not add a test that only repeats the class string.
- Each of the three pages loses about 14px of height below 1024px (ADR-12 consequences). Check in the browser that nothing on the Mods and Version pages depended on the 36px (the Mods page content starts with `mt-4` under the list, `ModsPage.tsx:124`).

### The arrow key fault (Task 3)

**What the bead says:** in Chromium under Playwright, focus `ui-preferences-tab` as soon as `scheduled-jobs-tab` is visible and press ArrowRight three times at once: focus and selection stay on UI Preferences, or only one press moves. With 400ms before the first press, every press moves. It asks for a check with a real keyboard before any fix.

**What planning saw (not the reproduction AC 3 asks for; the local Vite dev server with stubbed API, headless Chromium, 2026-11-17):**

- The result depended on the gap between the three presses and not on the time since the list was shown. With 0ms and with 1500ms after `scheduled-jobs-tab` became visible: a 1ms gap ended on API Settings (one move), 10ms on File Manager (two moves), 30ms on Scheduled Jobs (three moves).
- An event log (a capturing `keydown` listener and a `focusin` listener on `window`) showed that every press reached the tab list and was handled (`defaultPrevented` true). The second and third `keydown` still had `ui-preferences-tab` as their target although focus moved to API Settings in between: they were dispatched before the first press's focus move ran.
- That matches the tabs library: `@radix-ui/react-roving-focus` 1.2.1 (`web/node_modules/@radix-ui/react-roving-focus/dist/index.mjs:189-202`) computes the next tab from `event.currentTarget` and moves focus in `setTimeout(() => focusFirst(candidateNodes))`. Presses that arrive before that timer runs are all computed from the same tab, so they all ask for the same neighbour.
- The tab list changing (`SettingsPage.tsx:59-64`) was not needed for the loss in these runs.

This points to outcome B, but it is one environment and a development build. The bead's 400ms observation is about the time since render, which these runs did not show. Task 3 decides on the Docker stack, with a real keyboard.

**Reproduction script (`21-7-browser/arrow_keys.mjs`).** Style of `17-8-browser/layout_widths.mjs`: Playwright imported from `web/node_modules`, `/config.js` answered with `VS_API_KEY_ADMIN`, every non-GET API request refused, no screenshot, output without instance values.

- Event log, installed with `addInitScript`: for each `keydown` of an arrow key record a timestamp (`performance.now()`), the target's test ID, the focused element's test ID at dispatch, `defaultPrevented` (read in a `setTimeout(0)`), and the number of `[role=tab]` elements; for each `focusin` on a tab record timestamp and test ID. Also record the time at which the fourth trigger appeared (a `MutationObserver` on the tab list).
- Scripted mode: for each browser (`chromium`, `firefox`; install Firefox with `bunx playwright install firefox` if it is missing, which changes no project file), each wait in 0, 100, 400 and 1500ms after the focus point, and each gap in 0, 10, 30 and 100ms between presses, 10 fresh contexts: focus `ui-preferences-tab`, press ArrowRight three times, read the focused tab and the selected tab 200ms later. Two focus points: as soon as `ui-preferences-tab` is visible (before the role is known) and as soon as `scheduled-jobs-tab` is visible (the bead's steps). Output: per cell, how many of 10 ended on the third tab to the right, and the log of one failing run.
- Headed mode (`--keyboard chromium|firefox`): open `/config` in a headed browser with the same event log, wait for the person to finish, and write the log on Enter in the terminal.

**Real keyboard steps (Task 3.3),** each 10 times per browser and window width, reloading the page each time:

1. Reload, click the UI Preferences tab the moment the tab list appears, press ArrowRight three times as fast as possible.
2. Reload, reach the tab list with the Tab key the moment it appears, press ArrowRight three times as fast as possible.
3. Reload, focus the list as in step 1 and hold ArrowRight for one second (key repeat), then press ArrowLeft once: note where focus ends and whether selection follows focus.
4. Steps 1 and 3 again in Chromium with the CPU slowed six times in the developer tools (the main thread is busy for longer after load).

For each attempt write down: the tab that has focus at the end, the tab that is selected, and whether any press visibly did nothing. A press "is lost" when the log has a `keydown` on a tab with no later `focusin` on its neighbour and focus did not move.

**Decision rule (Task 3.4).**

- **Outcome B (AC 5)** when a real keyboard loses no press in steps 1 and 2 in both browsers, or when every lost press (scripted or real) is one that was dispatched before the previous press's focus move had run (the log shows the stale target) and the loss does not depend on the wait since the list was shown. The cause is then the deferred focus move inside Radix.
- **Outcome A (AC 4)** when a real keyboard loses a press in step 1 or 2, or the scripted loss depends on the wait (it happens at 0 and 100ms and not at 1500ms with the same gap), and the log points at this project's code: the list of triggers changed, or the tab list or the page was remounted (a `focusin` followed by focus on `body`, a different `[role=tab]` count, a new element with the same test ID), in the window where presses were lost.
- If presses are lost with a real keyboard but the cause is inside Radix (for example only under key repeat in step 3), outcome B applies (ADR-12 decision 5 has two conditions joined by "or"); record it plainly in the AAR as a library limitation that a held key can show.

**If outcome A applies (Task 3.5).** Fix the cause that was found, not a symptom. The form ADR-12 decision 4 expects: the set of triggers does not change after the list can receive focus. In `SettingsPage.tsx` that means rendering the tab list once the role query has settled (success or error; on error the list has the three tabs every role sees, as today), with a placeholder of the same height while it is pending so the page does not jump. `useAuthMe` has `staleTime: Infinity`, so the placeholder shows once per session. Check the three panels still mount as today and `SettingsPage.test.tsx` passes. Not allowed as a fix: a delay, a retry, an own `onKeyDown` that moves focus, `key` tricks that remount the list, or a patch of Radix.

- Unit test (`SettingsPage.test.tsx`): render with the auth query pending, resolve it, then `await user.keyboard('{ArrowRight}{ArrowRight}{ArrowRight}')` straight after the list is in the document, and expect focus and `aria-selected` on the fourth tab. Radix moves focus in a `setTimeout`, so the test must use real timers or advance them; check the test fails before the fix and say in the Completion Notes if a unit test cannot show the fault (then the E2E carries AC 4, and the note says so).
- E2E (`layout-widths.spec.ts`): after `openPage(page, 1440, false, '/config')`, `await page.getByTestId('ui-preferences-tab').focus()` with no earlier wait than the locator's own, three `page.keyboard.press('ArrowRight')` with nothing between them, then expect focus and `aria-selected` on the tab three to the right of the start. Run it 30 times (`--repeat-each 30`) before and after the fix and record both counts.

**If outcome B applies (Task 3.6).** Nothing in `web/src` or `web/e2e` changes for this bead. The existing arrow key test (`layout-widths.spec.ts:531-546`) stays as it is: it waits for focus between presses, which is what a person's keystrokes do. No release note.

### Scheduled Jobs cards (Task 4.1)

- Pattern: `ModTable` (`components/ModTable.tsx:134`, `:401-423`) and `InstalledModCard` (`components/InstalledModCard.tsx:42-46`): `const isTableLayout = useMediaQuery(LG_UP_QUERY)` (`hooks/use-media-query.ts:17`, `:19`), one layout mounted, the cards in a `<ul className="space-y-3">` of `<li className="... rounded-lg border bg-card p-3 text-card-foreground">`. Call the hook before the early return for the empty state (`JobsTable.tsx:126-140`), which stays the same for both layouts.
- One source for both layouts: the four values (Job Name, Schedule, Next Run, Status) are rendered by the same code in the table cells and in the cards, with the same labels, so a label or a formatter cannot differ between layouts. Either build the cards from `table.getRowModel().rows` and each cell's renderer, or define the four fields once (label and render function) and build both the columns and the card rows from them. Do not read a column's `header` through a cast.
- Card markup: `<ul aria-label="Scheduled jobs" data-testid="job-cards">`; per job `<li data-testid="job-card-{id}">` holding a `<dl>` of four `dt`/`dd` pairs (each pair may sit in a `<div className="contents">`), a two-column grid such as `grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-2 text-sm`, the `dt` in `text-muted-foreground`, the `dd` with `min-w-0 break-words` so a long job ID or a cron expression wraps inside the card (measured at 238px: `server_versions_check` and `cron[hour='*/6', minute='0']` wrapped, nothing overflowed).
- Test IDs of the values stay as they are in both layouts (`job-name-{id}`, `job-schedule-{id}`, `job-next-run-{id}`, `job-status-{id}`): one layout is mounted, so they stay unique, and `e2e/settings-as-saved.spec.ts:184-199` keeps working at any width. `jobs-table` and `job-row-{id}` exist only in the table layout.
- The jobs list has no action (no button, no link), so there is no touch target to size. The same data is shown: nothing is added or left out.
- `ScheduledJobsPanel.tsx` does not change: the cards sit inside its card, as the table does.
- `formatSchedule` and `formatNextRunTime` (`:43-71`) do not change.

### Version table (Tasks 4.3 to 4.4)

- Channel column (`VersionTable.tsx:163-179`) and Status column (`:195-228`): add `meta: { className: 'hidden sm:table-cell' }`, as the Size column has (`:191-193`). The header and body cells already apply `meta.className` (`:352`, `:375`, `:407-409`; Story 21.5 removes the two casts there, do not bring them back).
- Version cell (`:138-160`): keep the existing `<span data-testid="version-table-version-{v}">` with the changelog link, and put it in a column (`flex flex-col items-start gap-1`) above a `sm:hidden` row (`flex flex-wrap items-center gap-1`) that shows the channel badge, the "Latest" badge when `isLatest`, and the "Installed" mark when `isInstalled`. Test IDs for the copies: `version-table-inline-channel-{v}`, `version-table-inline-latest-{v}`, `version-table-inline-installed-{v}`. The names must not start with `version-table-channel`: `VersionTable.test.tsx:214` finds the column's badge with the pattern `/version-table-channel/` inside a row. No "-" placeholder in the inline row.
- Render the badge and the status marks from one small component each (inside `VersionTable.tsx`), used by the column cell and by the inline row with a different test ID prefix, so the label and colours cannot differ.
- The copies are hidden with `display: none` from `sm`, and the columns below `sm`, so a screen reader meets each value once at any width.
- Actions (`:229-246`): the "Select" button gains `className="max-lg:h-11"` (44px below 1024px, the project's pattern; 32px from 1024px as today). The text stays "Select".
- Skeleton (`:253-278`): the Channel and Status head cells and body cells get `hidden sm:table-cell`, like Size (`:260`, `:270`), so the loading table does not scroll either.
- Below `sm` the table cannot be sorted by channel (its header is hidden); the channel filter tabs above the table cover that. Sorting by version stays.
- No `useMediaQuery` here: the table already hides Size with CSS, and both renderings are cheap.

### Web unit tests

Vitest runs in the `vmThreads` pool; follow `project-context.md:167-170` for globals. No skipped test. The width helper is `setViewportWidth` (`web/tests/viewport.ts:112`, imported as in `ModTable.test.tsx:57`; wrap it in `act` when components are mounted; `tests/setup.ts` resets to 1024px after each test).

`JobsTable.test.tsx` (new `describe` blocks; the existing tests run at 1024px and stay):

- At 390px: `job-cards` is in the document, `jobs-table` and `role="table"` are not; one `job-card-{id}` per job; each card contains the four labels "Job Name", "Schedule", "Next Run", "Status" as `dt` text and the four values by their test IDs, with the same text as the table shows for the same job (render once at 1024px and once at 390px and compare the four texts).
- At 1023px cards, at 1024px the table (the boundary).
- Changing the width with `act(() => setViewportWidth(...))` swaps the layout without remounting errors and never shows both.
- The empty state at 390px is `jobs-table-empty`, with no `job-cards`.
- `nextRunTime: null` shows "Never" in a card.

`VersionTable.test.tsx` (new block; existing tests stay):

- Each row has `version-table-inline-channel-{v}` with the same label and colour classes as `version-table-channel-{v}`; its container has `sm:hidden`.
- A latest row has `version-table-inline-latest-{v}`, an installed row `version-table-inline-installed-{v}`, a row that is neither has neither and no "-" in the inline row.
- The Channel and Status header cells and body cells have `hidden` and `sm:table-cell`; Version and Actions do not.
- The loading skeleton's Channel and Status cells have the same classes.
- The Select button has `max-lg:h-11` and still calls `onVersionSelect` with the version.

Class assertions are what jsdom can see; the E2E carries the real widths.

### Existing tests that change (deliberately)

Found by running the whole web unit suite against a throwaway prototype of Tasks 2 and 4 (since discarded): 132 files, 3307 passed, none failed; `tsc --noEmit` clean.

- **None fails.** `JobsTable.test.tsx`, `ScheduledJobsPanel.test.tsx` (`:124`, `:273`), `VersionTable.test.tsx`, `VersionPage.test.tsx`, `ChannelFilter.test.tsx`, `SettingsPage.test.tsx` and `ModsPage.test.tsx` run at jsdom's 1024px, so they see the table layouts and the desktop classes.
- **Would fail with other names:** `VersionTable.test.tsx:214` (`within(rows[0]).getByTestId(/version-table-channel/)`) finds two elements if the inline badge's test ID starts with `version-table-channel`. Use the names given above; do not loosen the test.
- **E2E, unchanged and must pass:** `layout-widths.spec.ts` "Settings tabs on phones" (`:508-547`) and "Other tab lists on phones" (`:549-567`); `settings-as-saved.spec.ts` (Scheduled Jobs values by test ID, default 1280px viewport).
- Stories 21.1 to 21.6 land first. Story 21.5 changes `VersionTable.test.tsx` (sort order, `aria-sort="none"`); re-run this list after rebasing. Anything else that fails is a regression: fix the code, not the test.

### E2E (`web/e2e/layout-widths.spec.ts`)

Extend the existing spec; do not create a new one (Story 21.8 extends the same file next). Untagged, so CI's first pass runs it. Reads only: `openPage` (`:263-281`) already installs `readOnly` (`:105-117`), which refuses every write; no screenshot; the game server is neither started nor stopped. Use the spec's helpers `horizontalOverflow` (`:227-241`), `documentOverflow` (`:243-245`), `boxOf` (`:247-251`), `expectInsideViewport` (`:254-260`), `SIDEBAR` (`:283-286`) and `CONFIG_TABS` (`:506`). Update the header comment (`:4-37`) with Story 21.7's lines.

Stubs (registered after `openPage`'s `readOnly`, or passed into `openPage` as a new option, so they run first):

- `fakeJobs(page)`: `GET /api/v1alpha1/jobs` fulfilled with `{"status":"ok","data":{"jobs":[...]}}`, three jobs with snake_case fields (`id`, `next_run_time`, `trigger_type`, `trigger_details`): `mod_cache_refresh` (interval, `every 3600 seconds`, a fixed ISO time), `server_versions_check` (cron, `cron[hour='*/6', minute='0']`, `next_run_time: null`), `mod_update_check` (interval, `every 21600 seconds`). Fulfilled, not passed on, so `fetchOnNewConnection` is not needed.
- `fakeVersions(page)`: `GET /api/v1alpha1/versions` with or without `?channel=` fulfilled with `{"status":"ok","data":{"versions":[...],"total":4,"cached":true,"cached_at":null}}`; four versions with `version`, `filename`, `filesize: "40.2 MB"`, `md5`, `cdn_url`, `local_url`, `is_latest`, `channel`: `1.22.7` (stable, latest), `1.22.7-rc.12` (unstable), `1.22.6` (stable), `1.21.6-pre.1` (unstable); filter by the `channel` query. The stub is required, not a convenience: in CI's first pass the vendor's version API resolves to loopback (`web/e2e/README.md:24`), so the real list is empty there.
- `installedVersion(page, '1.22.7')`: the page's `GET /api/v1alpha1/server/status` is fetched with `fetchOnNewConnection(route)` (`e2e/config-js.ts:32`) and answered with `state: 'installed'` and `version: '1.22.7'`, so the latest row is also the installed row (the widest status) on every stack. Register it after `pretendServerInstalled`; do not change `config-js.ts`.

New blocks:

- **Tab heights (AC 1-2).** For the Settings list (`/config`, wait for `scheduled-jobs-tab`), the Mods list (`INSTALLED` with `{ mods: true }`, triggers `installed-tab` and `browse-tab`) and the channel filter (`/game-server/version` with `fakeVersions`, triggers `channel-filter-all`, `-stable`, `-unstable`):
  - at 320, 390, 430, 768 and 1023px (sidebar expanded; at 768 and 1023px also collapsed): every trigger's box is at least 44px tall, inside the viewport, and `documentOverflow` is 0;
  - at 1024px: the list's box is 36px tall and every trigger is under 36px;
  - Settings at 320, 390 and 430px: every trigger's box lies inside the tab list's box (left, right, top and bottom), the list is taller than one row (more than 88px), the active panel's top is at or below the list's bottom, also after selecting the last tab.
- **Scheduled Jobs below lg (AC 6).** With `fakeJobs`, for each sidebar state and each of 320, 390, 430, 768 and 1023px: open `/config`, click `scheduled-jobs-tab`, expect `job-cards` visible and `jobs-table` to have count 0; three `job-card-*`; each card contains the texts "Job Name", "Schedule", "Next Run" and "Status"; each of the four value elements' boxes lies inside its card's box horizontally; `horizontalOverflow` equals `{ document: 0, scrolling: [] }`. At 1024px in both sidebar states: `jobs-table` visible with the four column headers, `job-cards` count 0.
- **Version table on phones (AC 7).** With `fakeVersions` and `installedVersion`, at 320, 390 and 430px: `version-table` visible; `horizontalOverflow` equals `{ document: 0, scrolling: [] }`; `version-table-header-channel` and `version-table-header-status` are hidden; for each of the four versions `version-table-inline-channel-{v}` is visible with "Stable" or "Unstable"; `version-table-inline-latest-1.22.7` and `version-table-inline-installed-1.22.7` are visible; each `version-table-select-{v}` is at least 44px tall and inside the viewport. At 768px in both sidebar states: the Channel header is visible, the inline channel hidden, no overflow, the button at least 44px. At 1024px: the button is 32px tall.

Box heights can be fractional; compare with `toBeGreaterThanOrEqual(44)` and, for "under 36", `toBeLessThan(36)`.

Story 21.8 changes how `openPage` writes the sidebar cookie (`:271-277`); leave that to 21.8.

### Measurement method (Tasks 1 and 5)

`21-7-browser/page_widths.mjs`, style of `17-8-browser/layout_widths.mjs` (copy its `readOnly`, `fakeInstalledMods`, `overflow` and `rect` helpers; do not import across story folders). Run from `web/` with `bun`, against `E2E_BASE_URL` (default `http://localhost:8080`), Admin key from `VS_API_KEY_ADMIN` answered on `/config.js`.

- Widths 320, 390, 430, 768 and 1023px, height 900; both sidebar states through the `vs_ui_prefs` cookie (`{ sidebarCollapsed }`), a fresh context per page and state. Below 768px the sidebar is a sheet and the two states should give the same numbers; measure both anyway and say so in the record if they do.
- Pages and what to wait for:

  | Page | URL | Data |
  |---|---|---|
  | Dashboard | `/` | live |
  | Version | `/game-server/version` | versions stubbed as in "E2E" |
  | Game Settings | `/game-server/settings` | live `serverconfig.json` (numbers only in the output) |
  | Mods, installed | `/game-server/mods/installed` | stubbed, the three mods of the 17.8 script |
  | Mods, browse | `/game-server/mods/browse` | live mod database |
  | Mod detail | `/game-server/mods/browse/carryon` | live mod database |
  | Console | `/game-server/console` | live; the server stays as it is |
  | Settings | `/config`, then each of the four tabs | jobs stubbed as in "E2E" |

  Make the pages render as installed the way `pretendServerInstalled` does (`e2e/config-js.ts:44`), in the script's own code.
- Per page: `documentOverflowX` (`scrollWidth - clientWidth` of the document), `scrolling` (every element under `main` with `overflow-x` `auto` or `scroll` and `scrollWidth > clientWidth`, as `testid-or-data-slot-or-tag:scrollWidth/clientWidth`), and the content area's `[left, right, width]`. For the three tab lists also each trigger's height; for the Scheduled Jobs tab and the Version page the layout (`table` or `cards`) and the table container's numbers.
- The output must hold no server name, key, password, mod description or log line: numbers, test IDs, `data-slot` names and tag names only.

### What counts as a fault (Tasks 1.3 and 5.2)

- A fault: the document scrolls sideways (`documentOverflowX > 0`), or a table's container (`data-slot="table-container"`) scrolls, or a row of controls is wider than its container.
- Not a fault: an element whose job is to scroll preformatted content, such as the console's terminal, a code or file viewer in the File Manager, a `pre` or a table inside a mod description. List them in the record with one line each saying why.
- Same kind (fix here): a table that needs fewer columns or cards; a row of buttons, badges or inputs that needs `flex-wrap` or `min-w-0`. Use the patterns of this story and Stories 16.5, 17.8 and 18.4.
- Larger (report, do not fix, do not file): a page whose layout must be redesigned, a chart, a third-party widget, the console terminal's own width. Story 21.6 has already fixed the mod detail header; if the mod detail page still scrolls, report it with numbers and name Story 21.6.

### Manual check (Task 6.3)

On the Docker stack built from this branch, in a browser's device toolbar at 320, 390 and 768px, and on a real phone if one is at hand: the three tab lists are easy to tap and look right in both themes (the active tab's background fills its 44px); the Settings list's two rows look like one control; Scheduled Jobs reads well as cards; the Version table shows channel, "Latest" and "Installed" under the version without crowding, and "Select" opens the install dialog (cancel it; do not install). At 1280px everything looks as before. Do not start or stop the game server. No screenshots; if one is needed for the pull request, it must not show the server name.

### Not changed (do not "fix" these here)

- The sidebar default at tablet widths and the 1280px content width: Story 21.8 (`VSS-w85`, `VSS-alx`). `openPage`'s cookie stays `{ sidebarCollapsed }` here.
- `ui/table.tsx`'s `overflow-x-auto` wrapper (`:9`): other tables rely on it.
- The installed mods table and cards (Stories 16.5, 17.8, 18.4), the dialog close buttons and `aria-sort` (Story 21.5), the mod detail header (Story 21.6).
- The Version table's sort functions and `compareVersions` (Story 21.5).
- `ScheduledJobsPanel.tsx`, `use-jobs.ts`, `ChannelFilter.tsx`, `ModsPage.tsx`: no edit is needed. `SettingsPage.tsx` changes only under outcome A.
- The tab lists' appearance from 1024px.
- Pre-existing and out of scope: `VSS-1ar` (3 Pyright warnings), `VSS-hnl` (skipped web tests), `VSS-6wj`.

### API contract changes

None. No route, field, status code or error code changes; the web calls the same routes.

### ADR against the code

- **ADR-13 decision 2 (Version table).** It hides the Channel column below `sm` and, "if that does not bring it under 256px", allows an icon button. Measured in planning with a 12-character pre-release version: Channel hidden gives 281/256, and the icon button with a visually hidden Actions header gives 260/256, so neither fits 320px. The story therefore also hides the Status column below `sm` and shows "Latest" and "Installed" under the version beside the channel badge (256/256, about 193px needed), and keeps the button's text. This goes one column further than the maintainer's answer 9 ("hides Channel below 640px"): Task 4.3 re-measures first, and the pull request states the decision so he can object. An icon-only install action was not chosen because it does not fit either and is harder to understand.
- **ADR-12 decision 3 (suspects).** Its three suspects are all in this project's code. Planning's probe points at a fourth: Radix's deferred focus move with presses that arrive faster than it runs ("The arrow key fault"). Task 3 tests all four.
- **ADR-13 decision 4 and the epic's AC 8 ("both console pages").** Only one console page has a route: `/game-server/console` (`web/src/App.tsx:139`). `GameServerPage.tsx` (the side-by-side layout ADR-15 names) is exported (`features/game-server/index.ts:10`) and rendered by no route, so it cannot be measured in a browser. The story measures the console page that exists and says so in the record. If an earlier Epic 21 story routes it, measure it too.
- **Epic task list.** The epic has five tasks with the tables' release note in the last one. Here the two table changes are one task (Task 4) with one `fix` commit, so there is one release note for both, as the proposal lists; the before measurement is its own first task, and the after measurement the fifth.
- Everything else in ADR-12 and ADR-13 matches the code at 966204f (line numbers re-read).

### Beads

Closed by the controller after merge, each with an abbreviated AAR (size-s) before `bd close`, then `bd sync`. Do not edit `.beads/` files.

- `VSS-3ry`: summary (44px triggers below 1024px in `ui/tabs.tsx`, three tab lists checked at 320 to 1023px), the E2E block, the commit link.
- `VSS-f9y`: summary (jobs cards below 1024px; Channel and Status under the version below 640px), unit and E2E tests, the measurement files, the list of anything reported and not fixed, commit links. The bead's comment (measure the other pages) is answered by `page_widths.*.json`.
- `VSS-vt4`: outcome A: the cause, the fix, the tests and the commit link. Outcome B: the evidence ADR-12 decision 5 asks for: browsers and versions, the real keyboard steps and their results, the scripted matrix, what the event log showed, the Radix file and line, and the sentence "no workaround was added". Close reason names the outcome.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first where a unit test can fail first. `just test-web <file>` after each change; `just check` before review.

- Unit tests: `vmThreads` pool; `setViewportWidth` for layouts; no skipped test; no test that writes outside its own temp data.
- E2E: stubbed with `page.route`; `fetchOnNewConnection(route)` for the one stub that passes a request on; untagged; type-checked by `web/e2e/tsconfig.json` (`just typecheck-web`); no screenshot; nothing written, so no snapshot guard is needed. If a fix in Task 5.2 needs real state, stop and ask: this story changes none.
- The measurement and reproduction scripts run against the Docker stack only and are not part of any test run.

### Security Requirements

- No new endpoint, no new data shown. Scheduled Jobs stays Admin-only (`SettingsPage.tsx:59-64`, `:79-83`; `ScheduledJobsPanel.tsx:30-32`).
- The committed JSON files hold numbers and test IDs only. Check each before committing: no API key, server name, password, log line or path under the data directory.

### Development Commands

- `just test-web src/components/JobsTable.test.tsx src/components/VersionTable.test.tsx`, `just test-web src/features/settings`, `just typecheck-web`, `just lint-web`, `just check`.
- `just docker restart`, then `cd web && bunx playwright test e2e/layout-widths.spec.ts` with `VS_API_KEY_ADMIN` exported; `just test-e2e-ci` for both CI passes on throwaway containers.
- Format only the files you change (`bunx prettier --write <files>` from `web/`, with the version Story 21.1 pinned); do not run `just format`.
- Use `just`, never raw `mise exec`.

### Previous Story Intelligence

- **17.8:** made the Settings list wrap (`h-auto max-w-full flex-wrap`), moved the installed mods cards to `lg`, and created the three beads of this story. Its review (L2) is the bead comment that asks for the other pages. Its measurement script is the model for Task 1.
- **18.4:** measured before choosing (`18-4-browser/column_widths.mjs`), and recorded where the epic's wording could not hold. Do the same in Task 4.3.
- **16.5:** one layout mounted with `useMediaQuery`; 44px controls; the jsdom viewport stand-in.
- **20.2:** the `vmThreads` pool and the stubbing rule; no skipped unit tests.
- **20.5 / 19.7:** `fetchOnNewConnection`, `pretendServerInstalled`, `serveConfigKey`; untagged specs run in CI; the counts in `web/e2e/README.md`.
- **Reviews of 17.x to 20.x:** a `fix` subject must describe something a user can see; a completion note must be true of the code; manual checks wait for the maintainer; tests must not write into `dev/`.

### Git Intelligence

- Base `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`) on `05436da` (`v0.1.0-rc.6`). Stories 21.1 to 21.6 land first.
- Planned commits: Task 1 `docs(story-21.7/task-1): measure every page at phone and tablet widths`. Task 2 `fix(story-21.7/task-2): make tabs easier to tap on phones` (release note). Task 3 outcome A `fix(story-21.7/task-3): settings tabs respond to arrow keys as soon as they appear` (release note, only then); outcome B `docs(story-21.7/task-3): record the arrow key reproduction for the settings tabs`. Task 4 `fix(story-21.7/task-4): fit the scheduled jobs and version tables on phone screens` (release note). Task 5 `docs(story-21.7/task-5): record page widths after the phone layout changes`, plus one `fix(story-21.7/task-5): ...` per same-kind fix, if any. Task 6 `chore(story-21.7/task-6): ...`.

### Project Structure Notes

- New: `_bmad-output/implementation-artifacts/21-7-browser/page_widths.mjs`, `page_widths.before.json`, `page_widths.after.json`, `arrow_keys.mjs`, `arrow_keys.scripted.json`, `arrow_keys.keyboard.<browser>.json`.
- Modified: `web/src/components/ui/tabs.tsx`, `web/src/components/JobsTable.tsx`, `web/src/components/JobsTable.test.tsx`, `web/src/components/VersionTable.tsx`, `web/src/components/VersionTable.test.tsx`, `web/e2e/layout-widths.spec.ts`, `web/e2e/README.md`. Under outcome A also `web/src/features/settings/SettingsPage.tsx` and `SettingsPage.test.tsx`.
- No API file, no fixture, no dependency.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.7: Tabs and Tables on Phones]
- [Source: _bmad-output/planning-artifacts/prd.md] FR281, FR282, FR283
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md#ADR-12, #ADR-13] (and "Tabs, tables and layout today")
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] (section 2 release-note subjects; section 5 answer 9)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] `:1209-1215`, `:1289-1292`
- [Source: _bmad-output/implementation-artifacts/17-8-layout-at-tablet-and-phone-widths.md], [18-4-installed-mods-list-at-every-width.md], [16-5-installed-mods-on-phones.md]
- `_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs`, `layout_widths.after.json`
- Beads: `VSS-3ry`, `VSS-vt4`, `VSS-f9y`, parent `VSS-syuj`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; the stubbing rule; commit format)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-11-17: Story 21.7 created and validated (ready-for-dev).
