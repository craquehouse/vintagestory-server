# Story 17.8: Layout at Tablet and Phone Widths

Status: ready-for-dev

<!-- Implements FR191-FR193. Beads: VSS-dp1, VSS-uni, VSS-143. Branch story/17-8-layout-at-tablet-and-phone-widths, stacked on story/17-7-mods-navigation (17.5, 17.6, 17.7 come first, each stacked on the previous). Line references were verified at 21457bf (story/17-4-installed-status-is-right-everywhere) and must be re-checked on the 17.7 head before editing. No Epic 17 ADR governs this story (the Epic 17 ADR file and the 2026-11-15 change proposal both say so); it follows Epic 16 ADR-3 (settings panel capped at 1280px and centered, two columns from `xl`) and the UX spec's "Responsive Design & Accessibility" section (`ux-design-specification.md:1194-1258`). Web only; no API change, no new dependency. -->

## Story

As an **administrator**,
I want **pages to fit the screen I am using**,
so that **I do not scroll sideways to reach a control**.

## Acceptance Criteria

1. **Given** a viewport from 768px to 1023px wide, with the sidebar expanded or collapsed
   **When** I open Installed mods (`/game-server/mods/installed`), including a mod with an offered update and a mod with a long name
   **Then** the page does not scroll sideways and no element in the page content scrolls sideways; each mod's version, update status and Update action, enable toggle and remove action are visible inside the viewport and work (they are the cards of Story 16.5, see Dev Notes "Decision: cards up to `lg`")
   *(Covers FR191; `VSS-dp1`)*

2. **Given** a viewport of 1024px or wider
   **When** I open Installed mods
   **Then** the table is shown with the same columns, cells and behavior as today. **Given** a viewport narrower than 768px, the phone cards are unchanged
   *(Covers FR191)*

3. **Given** a viewport from 320px to 430px wide
   **When** I open Settings (`/config`) as an Admin and select each of its four tabs (UI Preferences, API Settings, File Manager, Scheduled Jobs)
   **Then** the page does not scroll sideways; every tab is fully inside the viewport, can be selected by touch (click) and by keyboard (arrow keys from the focused tab list), and the selected tab is visible
   *(Covers FR192; `VSS-uni`)*

4. **Given** a viewport from 320px to 430px wide
   **When** I open the Mods page (Installed and Browse tabs) and the Game Server Version page (All / Stable / Unstable)
   **Then** their tab lists fit without making the page scroll sideways (true today, measured; this AC guards it)
   *(Covers FR192)*

5. **Given** any viewport of 1024px or wider, with the sidebar expanded or collapsed
   **When** I open Game Settings (`/game-server/settings`)
   **Then** the title starts at the settings panel's left edge and the server status badge ends at its right edge (each within 1px), inside the same centered 1280px maximum width; the loading and error states use the same width, so the title does not move when the status arrives
   *(Covers FR193; `VSS-143`)*

6. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.8/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: Measurement script and "before" numbers (AC: 1, 3, 4, 5)
  - [x] 1.1: New `_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs` (Dev Notes "Measurement method"), in the style of `_bmad-output/implementation-artifacts/16-6-browser/settings_layout.mjs`. It reads only; it stubs the installed mods and their update status with `page.route` and refuses every write
  - [x] 1.2: Run it against the Docker dev stack built from this branch before any source change (`just docker restart`, then `cd web && bun ../_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs > ../_bmad-output/implementation-artifacts/17-8-browser/layout_widths.before.json`). Compare with the numbers in Dev Notes "Measured on the dev stack"; a large difference means a story before this one changed the layout, so re-check before going on
  - [x] 1.3: Commit the script and `layout_widths.before.json` only (no screenshots): `docs(story-17.8/task-1): measure page layouts from phone to wide desktop widths`

- [x] Task 2: Installed mods use the cards up to `lg` + tests (AC: 1, 2, 6)
  - [x] 2.1: `web/src/hooks/use-media-query.ts:10-11`: add `LG_UP_QUERY = '(min-width: 64rem)'` with a doc comment (Tailwind v4's `lg`, 1024px at the default root font size) next to `MD_UP_QUERY`; update the module comment's example (`:3-5`, "table at md and up" becomes "table at lg and up")
  - [x] 2.2: `web/src/components/ModTable.tsx`: `isTableLayout = useMediaQuery(LG_UP_QUERY)` (`:129-130`, import `:57`); comment "Story 16.5, Story 17.8: the table at lg and up, cards below". Header comment (`:11-12`): "Below the `lg` breakpoint (Story 16.5 below `md`, Story 17.8 up to `lg`) ...". Nothing else in the file changes: columns (`:249-335`), table markup (`:368-399`) and the cards branch (`:400-418`) stay as they are
  - [x] 2.3: `web/src/components/InstalledModCard.tsx:1-9`: "for screens narrower than `lg`" (and Story 17.8 in the comment). No markup change
  - [x] 2.4: `web/src/features/mods/InstalledTab.tsx:97` and `:108`: `max-md:h-11` becomes `max-lg:h-11` on "Update all" and "Check for updates", so the toolbar has the same 44px touch targets as the cards in the whole card band. The comment at `:87` ("wraps on phones") stays; add one line that the 44px height applies up to `lg` (Story 17.8)
  - [x] 2.5: Tests (Dev Notes "Web tests", Task 2 rows) and the changes in "Existing tests that change" that belong to Task 2

- [x] Task 3: The Settings tab list wraps on narrow screens + tests (AC: 3, 4, 6)
  - [x] 3.1: `web/src/features/settings/SettingsPage.tsx:44`: `<TabsList className="h-auto max-w-full flex-wrap">` (Dev Notes "Decision: the Settings tabs wrap"). Do not change `web/src/components/ui/tabs.tsx`, `ModsPage.tsx` or `ChannelFilter.tsx`. Add "Story 17.8" to the header comment (`:1-14`)
  - [x] 3.2: Tests (Dev Notes "Web tests", Task 3 row)

- [ ] Task 4: The Game Settings title row shares the panel's width + tests (AC: 5, 6)
  - [ ] 4.1: `web/src/features/game-server/SettingsPage.tsx`: in each of the three returns (loading `:34-44`, error `:46-57`, main `:59-85`) wrap everything inside the outer `div` in `<div className="mx-auto max-w-[1280px]" data-testid="settings-page-content">`. The outer `div`s keep their classes and test IDs (`p-4 lg:p-6 h-full overflow-auto`). Give the header row (`:66`) `data-testid="settings-page-header"`. `GameConfigPanel` keeps its own `mx-auto max-w-[1280px]` (`GameConfigPanel.tsx:190`, `:203`, `:276`): inside a 1280px wrapper it is a no-op, and it keeps the panel capped where `GameConfigPanel` is used elsewhere. Header comment: Story 17.8, the title row and the panel share one centered 1280px width (Epic 16 ADR-3)
  - [ ] 4.2: Tests (Dev Notes "Web tests", Task 4 row)

- [ ] Task 5: E2E, "after" numbers and browser check (AC: 1-5)
  - [ ] 5.1: New `web/e2e/layout-widths.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/layout-widths.spec.ts` and the admin key from `.env`. Also re-run `e2e/installed-mods-phone.spec.ts`, `e2e/settings-desktop-layout.spec.ts`, `e2e/settings-empty-values.spec.ts` and `e2e/file-browser-navigation.spec.ts`
  - [ ] 5.2: `web/e2e/installed-mods-phone.spec.ts:1-18`: the header says the table is unchanged "at `md` and up"; change it to "at `lg` and up (Story 17.8: cards up to `lg`)". Its tests (390 and 1440 only) do not change
  - [ ] 5.3: Run the measurement script again into `layout_widths.after.json`; commit it with the E2E. Record in the Dev Agent Record a short before/after table (document overflow and the scrolling elements per page and width, and the Game Settings title/badge/panel edges at 1440, 1600 and 1920)
  - [ ] 5.4: Browser check on the stack (no screenshots kept): Installed mods at 900px with the sidebar expanded and collapsed, Settings at 390px through all four tabs by touch emulation and by keyboard, Game Settings at 1920px. This is a manual check: per `project-context.md` it is ticked only after the user confirms it. The game server is not started or stopped; no setting is changed

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast`/type assertion to silence an error
  - [ ] 6.2: Story status `review`, `just sprint set 17-8-layout-at-tablet-and-phone-widths review`, PR (base `story/17-7-mods-navigation` while its PR is open, otherwise `main`), PR link on `VSS-dp1`, `VSS-uni` and `VSS-143`. The PR description lists the follow-ups from Dev Notes "Follow-ups (not in this story)"

## Dev Notes

### The defects (measured, see "Measured on the dev stack")

- **Installed mods at tablet widths (`VSS-dp1`).** From `md` (768px) the Installed list is the TanStack table (`ModTable.tsx:129-130`, `useMediaQuery(MD_UP_QUERY)`, `use-media-query.ts:11`). Every `TableHead` and `TableCell` is `whitespace-nowrap` (`components/ui/table.tsx:71`, `:84`), so a row is as wide as its longest name, version, update cell (offered version, "pre-release", Update button), side badge, compatibility badge, switch and remove button together, and the table container scrolls sideways (`components/ui/table.tsx:5-18`, `overflow-x-auto`). The page itself does not scroll, but the enable toggle and the remove button sit off-screen to the right.
- **Settings tabs on phones (`VSS-uni`).** `TabsList` is `inline-flex h-9 w-fit` (`components/ui/tabs.tsx:27`) with `whitespace-nowrap` triggers (`:43`). The four Settings tabs (`features/settings/SettingsPage.tsx:44-63`) need 518px, so below about 550px the list sticks out of the content and the whole page scrolls sideways, on every tab.
- **Game Settings title row (`VSS-143`).** `GameConfigPanel` caps its content at 1280px and centers it (`GameConfigPanel.tsx:276`, Story 16.6), but the title row of `features/game-server/SettingsPage.tsx:66-71` is a full-width `flex justify-between`. As soon as the content area is wider than 1280px, the title starts left of the panel and the badge ends right of it.

### Measured on the dev stack

Read-only Playwright run on 2026-11-15 against the running Docker dev stack (Chromium, height 900; installed mods and update status stubbed with the three mods of `e2e/installed-mods-phone.spec.ts`: a 63-character name with an offered pre-release update, an incompatible mod, a disabled mod). "Expanded"/"collapsed" is the sidebar (`Layout.tsx:19`, 160px / 64px; `main` adds `p-4 md:p-6`, `:46-49`).

| Width | Sidebar | Installed mods (table width / container) | `/config` document overflow | Game Settings: title left, header right, panel left-right |
|---|---|---|---|---|
| 320 | either | cards, no overflow | 214px | |
| 390 | either | cards, no overflow | 144px | |
| 430 | either | cards, no overflow | 104px | |
| 768 | expanded / collapsed | 1163 / 560, 1163 / 656 | 0 | |
| 900 | expanded / collapsed | 1163 / 692, 1163 / 788 | 0 | |
| 1023 | expanded / collapsed | 1163 / 815, 1163 / 911 | 0 | |
| 1024 | expanded / collapsed | 1163 / 816, 1163 / 912 | 0 | 208, 976, 208-976 / 112, 976, 112-976 (aligned) |
| 1440 | expanded / collapsed | fits (1232, 1328) | 0 | aligned (panel 1184 / 1280 wide) |
| 1920 | expanded | fits (1712) | 0 | 208, 1872, 400-1680 |
| 1920 | collapsed | fits (1808) | 0 | 112, 1872, 352-1632 |

- The bead's 751px at 768px was measured with the five short-named mods of `./data` and no offered update; the stubbed set needs 1163px. Either way the table cannot fit 560-911px.
- Mods tabs: 185px; Version page channel tabs: 171px. Both fit at 320px (content 288px), so they are not changed (AC 4 guards them).
- At 320-430px the Scheduled Jobs table (530px) and at 320-390px the Version page table (361px) scroll inside their own containers; the page does not. Not part of FR192 (see "Follow-ups").
- Game Settings: the title is misaligned whenever the content area inside the page's own padding is wider than 1280px: above a 1536px viewport with the sidebar expanded, above 1440px collapsed. The epic AC's "1560px or wider" comes from the bead's estimate; AC 5 checks every width from 1024px instead.
- A throwaway prototype of Tasks 2.1-2.2, 3.1 and 4.1 (since discarded; served by Vite against the stack's API) measured: Installed mods at 768-1023px both sidebar states: cards, document overflow 0, no scrolling element; `/config` at 320/390/430: tab list 288/358/398px wide (two rows), document overflow 0 on every tab; Game Settings at 1920: title left = panel left (400 expanded, 352 collapsed), header right = panel right (1680 / 1632); at 1024 and 1440 unchanged.

### Decision: cards up to `lg` (`VSS-dp1`)

The UX spec's tablet rule is "Reduced column count in tables (hide Available column, show Update badge inline)" (`ux-design-specification.md:1209-1215`). The bead lists three options: hide Side below `lg`, fold Available into the Version cell below `lg`, or use the cards up to `lg`. Chosen: **the cards up to `lg`** (one constant, `LG_UP_QUERY`).

- **Folding columns does not fit.** The cells cannot wrap (`whitespace-nowrap`, above), so the Name column alone is as wide as the longest mod name. Dropping Side and Available and moving the update into the Version cell saves their widths but adds the offered version and the Update button to Version; with the measured 1163px the table would still need far more than the 560px available at 768px with the sidebar expanded. Making the name wrap would change the table at every width, which AC 2 rules out, and the result would still depend on the installed mods' names.
- **The cards already meet the spec's intent.** They show every column's information, the update status with the Update action inline (`InstalledModCard.tsx:70-82`), wrap long names (`:48`), give each control a 44px target (Story 16.5), and are rendered from the same sorted rows, handlers and dialogs as the table (`ModTable.tsx:400-418`). Tablets are touch devices, so the larger targets fit the band too, which is why Task 2.4 extends the toolbar's 44px buttons to `lg`.
- **Sorting.** The table's sortable headers are not on the cards; the cards follow the stored sort preference (Story 16.5). Between 768 and 1023px an admin can no longer click a header to sort. Accepted: the preference is kept and applies again at `lg`; the UX spec's tablet rule already drops table features.
- **`lg` boundary.** `(min-width: 64rem)` is 1024px; jsdom's default width in tests is 1024px (`web/tests/viewport.ts`), so every existing table test keeps rendering the table.
- **Not covered: the table at `lg` and wider with long names.** At 1024px the measured table (1163px) still scrolls inside its container (816px expanded, 912px collapsed); with short names it fits from about 1024px (bead). FR191 is limited to 768-1023px and AC 2 keeps the table unchanged, so this is a follow-up, not part of this story.

### Decision: the Settings tabs wrap (`VSS-uni`)

Wrap, not scroll inside the list. With `flex-wrap` and `max-w-full` the list is never wider than the content, so every tab is visible at once; a list that scrolls inside itself would hide "Scheduled Jobs" off-screen with no visible cue and would need extra code to scroll the selected tab into view. `h-auto` replaces `h-9` so a second row stays inside the muted background; the triggers' `h-[calc(100%-1px)]` (`tabs.tsx:43`) then resolves to their content height, and `flex-1` stretches the tabs of each row to the row's width. Keyboard behavior is Radix's roving focus (arrow keys move and, with the default automatic activation, select), which does not depend on layout.

The change is made at the call site, not in `components/ui/tabs.tsx`: the other two tab lists fit at 320px, and a change to the shared component would change every tab list's height. If a later tab list overflows, it gets the same three classes.

### Decision: align the title row only (`VSS-143`)

The bead offers an app-wide 1280px maximum content width (`ux-design-specification.md:1254-1258`, left out of Epic 16 by ADR-3 decision 1) or constraining the Game Settings header. Chosen: **the Game Settings page only**. At 1920px the dashboard, console, Version page, mod browser and `/config` all use the full content width today (measured: their content spans 184-1896px). Capping them in `Layout.tsx` would narrow the console and reduce the mod browser grid's columns on wide screens, changes that need their own UX decision and per-page checks, and would not align the Game Settings title by itself (that page adds its own `p-4 lg:p-6` inside `main`'s padding). Wrapping the page's content in the same `mx-auto max-w-[1280px]` as the panel is the smallest change that puts title, badge and panel on one edge in every state. The app-wide maximum stays a follow-up.

### Epic text against the code

- The epic AC for FR193 says "1560px or wider"; the misalignment starts above 1440px with the sidebar collapsed (see "Measured"). AC 5 checks every width from 1024px.
- Story 16.5 (FR172) said the table is unchanged "at `md` and up". FR191 replaces that for 768-1023px; FR172 itself (cards on narrow screens) still holds. The Story 16.5 E2E header is updated (Task 5.2).
- Epic 16 ADR-3 is consistent with the code and is not changed.

### Measurement method

`_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs`, run with `bun` from `web/` like `16-6-browser/settings_layout.mjs` (import Playwright from `../../../web/node_modules/@playwright/test/index.mjs`, `E2E_BASE_URL`, `VS_API_KEY_ADMIN`, API key through `localStorage.setItem('apiKey', ...)` in an init script).

- Widths 320, 390, 430, 768, 900, 1023, 1024, 1440, 1600, 1920 (1600 added for AC 5), height 900; each with the sidebar expanded and collapsed. The sidebar state is the `vs_ui_prefs` cookie: `context.addCookies([{ name: 'vs_ui_prefs', value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: true })), url: BASE }])` (`contexts/PreferencesContext.tsx:55`, merged with the defaults on load). A fresh browser context per page and state.
- Per page and width: `document.documentElement.scrollWidth - clientWidth` (must be 0), and every element under `main` whose computed `overflow-x` is `auto` or `scroll` and whose `scrollWidth > clientWidth`, reported as `testid-or-data-slot:scrollWidth/clientWidth` (the `horizontalOverflow` helper of `e2e/installed-mods-phone.spec.ts:176`).
- Pages and key rects (left, right, width, rounded): Installed mods with the stubbed mods (`mod-table`, `[data-slot="table-container"]`, `installed-mod-cards`, the Mods `[data-slot="tabs-list"]`); `/config` with the tab list rect, then each tab clicked and the overflow measured; the Version page channel tabs at 320-430; Game Settings at 1024 and wider: `settings-page-header` (after Task 4; before it, `[data-testid="settings-page"] > div:first-child`), its `h1`, the badge (header's last child), `game-config-layout`.
- No screenshots. If one is ever taken, mask `header span.font-semibold`, `#ServerName` and `#Password`; commit numbers, not images.

### Web tests

| Task | File | Test |
|---|---|---|
| 2 | `src/hooks/use-media-query.test.tsx` | `LG_UP_QUERY`: true at 1024 (default width) and 1440, false at 1023, 900, 768, 390 |
| 2 | `src/components/ModTable.test.tsx`, "Story 16.5: cards below md" (`:1662`; rename to "cards below lg (Stories 16.5, 17.8)") | at 768, 900 and 1023 (`it.each`, `setViewportWidth`): `installed-mod-cards` with one card per mod and no `mod-table`; at 1023 the card for `smithingplus` shows the Update button (`mod-update-button-smithingplus`, the block's `updatesResponse`) and clicking it starts the same confirmation flow as at 390 (reuse the existing card Update test's assertions); at 900 the card's toggle sends enable/disable and its remove button opens `remove-dialog` (one test each, same assertions as the existing 390 tests) |
| 2 | same block | the crossing test (`:1965`, see "Existing tests that change") checks 1023 → cards, 1024 → table, 767 → cards |
| 2 | `src/features/mods/InstalledTab.test.tsx` "toolbar on phones (Story 16.5)" (`:703`) | `:747-752` asserts `max-lg:h-11` (see "Existing tests that change"); rename the test "44px tall below lg" |
| 3 | `src/features/settings/SettingsPage.test.tsx`, `layout` block (`:321`) | the tab list (`getByRole('tablist')`) has `flex-wrap`, `max-w-full` and `h-auto`. jsdom does no layout, so the E2E is the real check |
| 4 | `src/features/game-server/SettingsPage.test.tsx` | in the loading, error, installed and not-installed states, `settings-page-content` exists inside `settings-page*`, has `mx-auto` and `max-w-[1280px]`, and contains the `Game Settings` heading; in the installed state it also contains `settings-page-header` (with the badge) and `game-config-panel`; in the not-installed state the empty state |

### E2E (`web/e2e/layout-widths.spec.ts`)

Header comment as in `e2e/installed-mods-phone.spec.ts` (story, FRs, beads, what is stubbed, requirements). Reads only: the installed mods and update status are stubbed, every write is refused, no setting is changed, the game server is not started or stopped, no screenshot is taken.

1. **Installed mods (AC 1, 2).** Copy `MODS`, `COMPATIBILITY`, `updateStatus`, `fakeInstalledMods` and `horizontalOverflow` from `installed-mods-phone.spec.ts:28-191` (spec files share no helpers today). For each width in 320, 390, 430, 768, 900, 1023, 1024, 1440, 1920 and each sidebar state (cookie as in "Measurement method"): `document` overflow is 0. Below 1024: `installed-mod-cards` visible, no `mod-table`, `scrolling` is `[]`, and for the long-name mod the version text, `mod-update-button-longnamemod`, the enable toggle label of `installed-mod-card-offmod` and `mod-remove-longnamemod` each have a bounding box inside `[0, width]`. At 1024 and wider: `mod-table` visible with the six column headers, no cards; `scrolling` is `[]` at 1440 and 1920 only (at 1024 the long-name table still scrolls inside its container, see "Decision: cards up to `lg`"). At 900 with the sidebar expanded, clicking `mod-update-button-longnamemod` opens `version-change-dialog` (cancel it; the stub answers 409 confirmation-required, so nothing is installed).
2. **Settings tabs (AC 3).** At 320, 390 and 430: open `/config`; `document` overflow 0; each of the four triggers (`ui-preferences-tab`, `api-settings-tab`, `file-manager-tab`, `scheduled-jobs-tab`) has its box inside `[0, width]`; click each in turn: it gets `aria-selected="true"`, its box is still inside the viewport, and the document overflow is 0 with that tab's panel shown (wait for the panel's test ID: `ui-preferences-panel`, `api-settings-panel`, `file-manager-panel`, `scheduled-jobs-panel`). Keyboard: focus `ui-preferences-tab`, press ArrowRight three times; after each press the focused trigger is selected and inside the viewport. Both sidebar states are irrelevant below 768px (the sidebar is a sheet), so run each width once.
3. **Other tab lists (AC 4).** At 320 and 390: `/game-server/mods/installed` (stubbed) and `/game-server/version`: `document` overflow 0 and the tab list's box inside the viewport.
4. **Game Settings (AC 5).** At 1024, 1440, 1600 and 1920, sidebar expanded and collapsed: `settings-page-header` visible (requires an installed game server, as `settings-desktop-layout.spec.ts`); `h1` left equals `game-config-layout` left and the header's last child (the badge) right equals the layout's right, each within 1px; the layout is at most 1280px wide.

Run the new spec together with every existing spec once (`bunx playwright test`); all specs read only or restore what they change, and this one changes nothing.

### Existing tests that change (deliberately)

Found by running the whole web suite against a throwaway prototype of Tasks 2-4 (since discarded): 3182 passed, 4 skipped, 1 failed.

- `web/src/components/ModTable.test.tsx:1965` "switches between table and cards when the viewport crosses md": at 768 it now gets cards. Rewrite as crossing `lg` (1023 cards, 1024 table) and keep the `md` side (767 cards). (Task 2)
- **Not run in the prototype (Task 2.4 was not prototyped), but will fail:** `web/src/features/mods/InstalledTab.test.tsx:747-752` asserts `max-md:h-11` on both toolbar buttons; it becomes `max-lg:h-11`. (Task 2)
- `tsc -b` (the web typecheck) passed on the prototype. Anything else that fails is a regression (AC 6): fix the code, not the test.
- Known load flakes from Story 17.4 (`InstallConfirmDialog`, `QuickInstallButton`, `SettingField`, `GameConfigPanel`, one test each, pass alone): re-run before suspecting this story.

### Overlap with Stories 17.5-17.7 (re-check before editing)

This story is implemented after 17.5, 17.6 and 17.7, each stacked on the previous. None of their epic tasks names a file this story edits, but re-read these before changing them, and re-run the measurement script (Task 1.2) on the 17.7 head:

- 17.5 (Password "Set" / "Not set" for Monitor keys) and 17.6 (null booleans shown as the game's default) change `web/src/components/SettingField.tsx` and the content of the settings panels, possibly `GameConfigPanel.tsx`. This story does not edit either; check that `GameConfigPanel` still has `data-testid="game-config-layout"` with `mx-auto max-w-[1280px]` (`:276`) and that a new label ("Set", "Enabled (default)") does not widen a field at 390px (the E2E measures `/game-server/settings` only from 1024; add 390 to the measurement script's Game Settings run if 17.5/17.6 added inline content).
- 17.7 changes `web/src/features/mods/ModsPage.tsx` (`getActiveTab`, the Browse tab handler) and its tests, and `web/e2e/mod-browse-state.spec.ts`. This story does not edit `ModsPage.tsx`; AC 4 measures its tab list, so re-check its markup (`:82-92`) if 17.7 added a tab or changed the labels.

### Not changed (do not "fix" these here)

- `components/ui/tabs.tsx`, `components/ui/table.tsx`, `ModsPage.tsx`, `ChannelFilter.tsx`, `Layout.tsx`, `GameConfigPanel.tsx`, `InstalledModCard.tsx` markup, the table's columns.
- No app-wide maximum content width; no change to the double padding of the Game Settings page (`p-4 lg:p-6` inside `main`'s `p-4 md:p-6`).
- Tab trigger heights (about 29px) stay below the 44px touch target; only the Installed mods controls follow the 44px rule (Story 16.5).
- The sidebar is not collapsed by default at tablet widths (UX spec `:1211`); its state stays the user's preference.

### Follow-ups (not in this story; for the maintainer to file)

1. The Installed mods table at `lg` and wider scrolls inside its container when a mod name is long (1163px needed with a 63-character name and an offered pre-release update; 816px available at 1024px with the sidebar expanded), because table cells do not wrap.
2. The Scheduled Jobs table (530px) scrolls inside its container at 320-430px, and at 768px with the sidebar expanded (510px); the Version page table (361px) at 320-390px.
3. App-wide 1280px maximum content width (UX spec `:1254-1258`), with a decision for the console and the mod browser grid.
4. Tab triggers are about 29px tall on phones, below the UX spec's 44px touch target.
5. The UX spec's tablet sidebar default (collapsed to icons) is not implemented.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- Layout in jsdom is only the media query stand-in (`web/tests/viewport.ts`, `setViewportWidth`, reset to 1024 after each test). Class assertions pin the CSS; the E2E and the measurement script verify the layout.
- E2E: stub with `page.route`, refuse writes, no screenshots, do not start or stop the game server, change no setting.

### Security Requirements

- No new endpoint, no data change. The measurement script and the E2E read the admin key from the environment and never print it; no instance-specific value (server name, password) is written to a committed file.

### Development Commands

- `just test-web src/hooks/use-media-query.test.tsx src/components/ModTable.test.tsx src/features/mods/InstalledTab.test.tsx src/features/settings/SettingsPage.test.tsx src/features/game-server/SettingsPage.test.tsx`, `just typecheck-web`, `just lint-web`, `just check`.
- E2E: `just docker restart`, then `cd web && bunx playwright test e2e/layout-widths.spec.ts e2e/installed-mods-phone.spec.ts e2e/settings-desktop-layout.spec.ts` (`just test-e2e-web` stops the stack afterwards).
- Do not run `just format-api` or a whole-repo formatter.

### Previous Story Intelligence

- **16.5:** introduced the cards, `useMediaQuery`, the jsdom media query stand-in and the `horizontalOverflow` E2E check; its review added a test that an open dialog survives a layout switch (`ModTable.test.tsx`, "keeps an open remove dialog when the layout switches"), which stays valid at the new boundary.
- **16.6 / Epic 16 ADR-3:** the 1280px cap lives in `GameConfigPanel`; `settings-desktop-layout.spec.ts` checks the panel's layout and must still pass.
- **17.4:** E2E specs run in parallel (`fullyParallel: true`, `playwright.config.ts:19`); this spec changes nothing, so it cannot disturb the others. A `feat`/`fix` subject must describe what an admin sees.
- **17.3:** a hook's own `onError` replaces the query client's default; not relevant here (no new mutation).
- **17.2:** E2E cleanup must be guarded by a snapshot; not needed here because nothing is written.

### Git Intelligence

- Base for line numbers: 21457bf (Story 17.4 done). Release notes come from commit subjects (`cliff.toml`). Planned: Task 1 `docs` (measurements), Task 2 `fix` (installed mods show as cards on tablets, so no control is off-screen), Task 3 `fix` (the Settings tabs wrap on phones instead of widening the page), Task 4 `fix` (the Game Settings title and status line up with the settings on wide screens), Task 5 `test` (plus `docs` for the after numbers), Task 6 `docs`.

### Latest Technical Information

- No new libraries. Tailwind v4 breakpoints: `md` 48rem, `lg` 64rem; `max-lg:` applies below 64rem. Radix Tabs: `activationMode` defaults to `automatic`, so arrow-key focus selects the tab.

### Project Structure Notes

- New: `web/e2e/layout-widths.spec.ts`, `_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs`, `layout_widths.before.json`, `layout_widths.after.json`.
- Modified: `web/src/hooks/use-media-query.ts`, `web/src/components/ModTable.tsx`, `web/src/components/InstalledModCard.tsx` (comment), `web/src/features/mods/InstalledTab.tsx`, `web/src/features/settings/SettingsPage.tsx`, `web/src/features/game-server/SettingsPage.tsx`, `web/e2e/installed-mods-phone.spec.ts` (comment), and the tests listed above.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.8: Layout at Tablet and Phone Widths]
- [Source: _bmad-output/planning-artifacts/prd.md] FR191-FR193 (`:693-695`), FR172 (`:660`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-3: Game Server Settings Layout on Desktop]
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (17.8 needs no decision)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md] (17.8 follows ADR-3 and the UX spec's tablet rules)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Responsive Design & Accessibility] (`:1194-1258`, touch targets `:1289-1292`)
- [Source: _bmad-output/implementation-artifacts/16-5-installed-mods-on-phones.md], [16-6-settings-layout-on-desktop.md], `16-6-browser/settings_layout.mjs`, `16-0-spike/settings_shots.mjs`
- Beads: `VSS-dp1`, `VSS-uni`, `VSS-143`, parent `VSS-4v5`
- `project-context.md` - critical implementation rules (no suppressions; manual test tasks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Started from `story/17-6-settings-behave-as-saved` at 684c83d (Stories 17.7, 17.5 and 17.6 done, each stacked on the previous); the story file was cherry-picked from `draft/17-8-layout-at-tablet-and-phone-widths` (1f216da). Every line reference written at 21457bf was re-read before use. Unchanged: `use-media-query.ts`, `ModTable.tsx` (`:11-12`, `:57`, `:129-130`), `InstalledModCard.tsx:1-9`, `InstalledTab.tsx` (`:87`, `:97`, `:108`), `features/settings/SettingsPage.tsx`, `features/game-server/SettingsPage.tsx`, `e2e/installed-mods-phone.spec.ts`. Moved by Story 17.6: `GameConfigPanel.tsx`'s 1280px caps are now `:195`, `:208` and `:295` (`data-testid="game-config-layout"`, still `mx-auto max-w-[1280px]`). Story 17.7 left the Mods tab list's labels and triggers as they were (two tabs, Installed and Browse).
- The web takes its API key from `/config.js` since Story 17.5, not from `localStorage`; the measurement script answers `/config.js` with `VS_API_KEY_ADMIN`, as the 17.5/17.6 E2E specs do.

### Completion Notes List

- Story created 2026-11-15: context analysis of `ModTable`/`InstalledModCard`/`InstalledTab`/`useMediaQuery` and the jsdom viewport stand-in, the shadcn `Table`/`Tabs` components, the three tab lists, both `SettingsPage`s, `GameConfigPanel`'s 1280px cap and `Layout`; read-only measurements on the running dev stack at 320-1920px with the sidebar expanded and collapsed; a throwaway prototype of Tasks 2-4 measured in the browser and run against the whole web suite to find the tests that change.

- Task 1: `17-8-browser/layout_widths.mjs` measures every width (320, 390, 430, 768, 900, 1023, 1024, 1440, 1600, 1920; height 900) with the sidebar expanded and collapsed (the `vs_ui_prefs` cookie), a fresh browser context per page and state: Installed mods (stubbed with the three mods of `installed-mods-phone.spec.ts`), `/config` and each of its four tabs, the Version page (320-430), Game Settings at every width (not only from 1024, because Stories 17.5/17.6 added inline labels to the settings fields), and at 1920 expanded the content span of five other pages. Every non-GET API request is refused. Run on the stack rebuilt from this branch before any source change (`layout_widths.before.json`); checked that the output holds no key, server name, description, welcome message or password. Against the story's numbers: the same picture, with the long-name table now 1183px wide (story: 1163; 20px more from the update cell since 21457bf) and the Scheduled Jobs table 523px (story: 530). `/config` overflows the document by 214/144/104px at 320/390/430 on every tab; Installed mods at 768-1024 scrolls inside `table-container` (1183/560 ... 1183/912); Game Settings is misaligned at 1600 expanded (title 208, header right 1552, panel 240-1520) and at 1600/1920 collapsed and 1920 expanded (panel 400-1680, title 208, badge right 1872), aligned at 1024 and 1440. Game Settings at 320-430: no overflow (the 17.5/17.6 labels do not widen a field).
- Task 2: `LG_UP_QUERY = '(min-width: 64rem)'` next to `MD_UP_QUERY` (module comment example now "table at lg and up"); `ModTable` uses it (`:130-131`, comment "Story 16.5, Story 17.8"), header comment updated; `InstalledModCard` comment says narrower than `lg`; `InstalledTab`'s two toolbar buttons are `max-lg:h-11`, with a one-line Story 17.8 comment under the 16.5 one. Tests (red first: 15 failed before the change): `use-media-query.test.tsx` `LG_UP_QUERY` at 1024/1440 true, 1023/900/768/390 false, and at the default width; `ModTable.test.tsx` block renamed "cards below lg (Stories 16.5, 17.8)", a nested "at tablet widths (Story 17.8)" block: one card per mod and no table at 768/900/1023 (`it.each`), the 1023px card's Update button sends the same `PUT .../version` `{version: '1.6.0', confirm: false}` as at 390, the 900px card's toggle sends `disable`, the 900px card's remove button opens `remove-dialog` and confirming sends `DELETE`; the crossing test now goes 1024 table → 1023 cards → 1024 table → 767 cards; `InstalledTab.test.tsx` "44px tall below lg" asserts `max-lg:h-11`. Whole web suite: 129 files, 3254 passed, 4 skipped.
- Task 3: `features/settings/SettingsPage.tsx` `<TabsList className="h-auto max-w-full flex-wrap">` with a one-line comment, and "Story 17.8" in the header comment; `tabs.tsx`, `ModsPage.tsx` and `ChannelFilter.tsx` unchanged. Test (red first): the `layout` block checks that the tab list has `flex-wrap`, `max-w-full` and `h-auto`. `src/features/settings/`: 6 files, 135 passed.

### File List

- `_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs` (new)
- `_bmad-output/implementation-artifacts/17-8-browser/layout_widths.before.json` (new)
- `web/src/hooks/use-media-query.ts`
- `web/src/hooks/use-media-query.test.tsx`
- `web/src/components/ModTable.tsx`
- `web/src/components/ModTable.test.tsx`
- `web/src/components/InstalledModCard.tsx`
- `web/src/features/mods/InstalledTab.tsx`
- `web/src/features/mods/InstalledTab.test.tsx`
- `web/src/features/settings/SettingsPage.tsx`
- `web/src/features/settings/SettingsPage.test.tsx`

## Change Log

- 2026-11-15: Story 17.8 created (ready-for-dev).
