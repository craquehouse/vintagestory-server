# Story 21.8: Sidebar Default and Content Width

Status: ready-for-dev

<!-- Implements FR284-FR285. Beads: VSS-w85 (UI-090), VSS-alx (UI-088), parent VSS-syuj. Governed by Epic 21 ADR-14 (sidebar preference) and ADR-15 (1280px content width), both accepted by the maintainer (Matt, 2026-11-17, answers 6 and 7). Last story of Epic 21, stacked on Story 21.7 (which is stacked on 21.1 to 21.6). Line references are to 966204f (branch epic-21-planning, before any Epic 21 story): Story 21.1 reformats about 231 web files with Prettier (single quotes, width 100), 21.5 changes `ui/sheet.tsx`, 21.6 changes `layout/Sidebar.tsx:208-216`, 21.7 changes `ui/tabs.tsx`, `VersionTable.tsx`, `JobsTable.tsx` and `e2e/layout-widths.spec.ts`. Re-check every cited line before editing. Web only: no API change, no new dependency. -->

## Story

As a **user on a tablet or a wide monitor**,
I want **the sidebar out of the way where space is short, and pages that do not stretch across a wide screen**,
so that **content has room at tablet widths and stays readable on large monitors**.

## Acceptance Criteria

1. **Given** a browser with no `vs_ui_prefs` cookie
   **When** I open the app at 768px or 900px
   **Then** the sidebar is collapsed (64px) on the first paint, with no expanded sidebar shown first; at 1024px and wider it is expanded (160px); and the cookie the app writes holds `"sidebar":"auto"` and no `sidebarCollapsed` key
   *(Covers FR284; `VSS-w85`; ADR-14 decisions 1 and 3)*

2. **Given** the stored value `auto`
   **When** I resize the window across 1024px in either direction
   **Then** the sidebar collapses below 1024px and expands from 1024px without a reload, and the stored value stays `auto`
   *(Covers FR284; ADR-14 decision 3)*

3. **Given** any width from 768px
   **When** I use the sidebar's toggle
   **Then** the sidebar changes to the opposite of what is shown, the result is stored as `expanded` or `collapsed`, and it is kept at every width and after a reload. In particular: at 900px with `auto` (shown collapsed) one click stores `expanded`; a second click stores `collapsed`, and the sidebar then stays collapsed when the window is widened to 1440px. The toggle has an accessible name in both states ("Collapse sidebar", "Expand sidebar")
   *(Covers FR284; ADR-14 decision 4; the accessible name was found in planning, Dev Notes "Decision: what an explicit choice is")*

4. **Given** a cookie written before this story with `sidebarCollapsed: true`
   **When** I open the app
   **Then** the sidebar is collapsed at every width from 768px, as before, and the cookie the app writes back holds `"sidebar":"collapsed"` and no `sidebarCollapsed` key
   *(Covers FR284; ADR-14 decisions 1 and 2)*

5. **Given** a cookie written before this story with `sidebarCollapsed: false`
   **When** I open the app
   **Then** the sidebar follows the width (`auto`): collapsed from 768 to 1023px and expanded from 1024px
   *(Covers FR284; ADR-14 decision 2)*

6. **Given** a `vs_ui_prefs` cookie that is missing, is not JSON, is JSON but not an object (`null`, a number, a string, an array), or whose `sidebar` is not one of the three values
   **When** I open the app
   **Then** it renders without an error and the sidebar preference is `auto` (or `collapsed` when the same cookie also has `sidebarCollapsed: true`); a valid `sidebar` value always wins over `sidebarCollapsed`; the other preferences in the cookie are read as today
   *(Covers FR284; ADR-14 decision 2)*

7. **Given** UI Preferences (`/config`, first tab)
   **When** I look at the Layout group
   **Then** I can choose Automatic, Expanded or Collapsed, the stored value is shown as the selected one (also to assistive technology), choosing one applies at once and is stored, and Automatic returns the sidebar to following the width. The control fits at 320px without the page scrolling sideways
   *(Covers FR284; ADR-14 decision 5)*

8. **Given** a phone width (below 768px) and any stored value, `collapsed` and `auto` included
   **When** I open the navigation menu
   **Then** the sheet shows the full sidebar (logo, labels, sub-items, version) and no collapse toggle
   *(Covers FR284; ADR-14 decision 6)*

9. **Given** the Dashboard, the Version page, Game Settings, the Mods page with both tabs and Settings (`/config`) at 1440, 1920 and 2560px, in both sidebar states
   **When** I measure the page content
   **Then** it is `min(1280, viewport - sidebar - 48)` px wide, centered in the area right of the sidebar (equal space left and right, within 1px), nothing is clipped and the page does not scroll sideways. The padding (`p-4 md:p-6`) is outside the 1280px
   *(Covers FR285; `VSS-alx`; ADR-15 decisions 1, 2 and 6)*

10. **Given** the mod browser at 1920px with at least five mods listed
    **When** I open it
    **Then** the grid has four columns inside the 1280px content width (cards about 308px wide)
    *(Covers FR285; ADR-15 decision 3)*

11. **Given** the Console page (`/game-server/console`) at 1920px, in both sidebar states
    **When** I measure the console panel
    **Then** it is `viewport - sidebar - 48` px wide (1712px expanded, 1808px collapsed), wider than 1280px. `GameServerPage` (the side-by-side page the ADR names) has no route and is not changed (Dev Notes "ADR against the code")
    *(Covers FR285; ADR-15 decision 4)*

12. **Given** the web source
    **When** I search for `max-w-[1280px]` outside test files
    **Then** it is written once, in `web/src/components/layout/content-width.ts`, and `Layout`, the Game Settings page and `GameConfigPanel` all use that constant; `features/game-server/content-width.ts` is gone
    *(Covers FR285; ADR-15 decision 1)*

13. **Given** every page where the content area is 1280px wide or narrower (every viewport up to 1488px with the sidebar expanded, up to 1392px collapsed)
    **When** I compare it with before the cap
    **Then** its layout is unchanged; at every width the header bar and the sidebar are unchanged, and the mod detail page keeps its own narrower width (`max-w-4xl`, centered)
    *(Covers FR285; ADR-15 decisions 2 and 5)*

14. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; the diff adds no lint or type suppression and no type assertion to silence an error; no test run writes into `dev/`

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-21.8/task-N): ... ; feat/fix only for changes users would notice, subject written for users. Red first. Exactly two release notes: Task 2 and Task 4. -->

- [ ] Task 1: The sidebar preference rules in one module + tests (AC: 4, 5, 6)
  - [ ] 1.1: New `web/src/lib/sidebar-preference.ts` (Dev Notes "The preference module"): the type `SidebarPreference`, `SIDEBAR_PREFERENCES`, `isSidebarPreference`, `readSidebarPreference` (the migration) and `isSidebarCollapsed` (the width rule). Pure functions, no React, no cookie access. Nothing imports it yet
  - [ ] 1.2: New `web/src/lib/sidebar-preference.test.ts` (Dev Notes "Web tests", Task 1 rows), written first and seen failing
  - [ ] 1.3: Commit `refactor(story-21.8/task-1): add the sidebar preference rules`

- [ ] Task 2: The sidebar follows the width until the user chooses + tests (AC: 1, 2, 3, 4, 5, 6, 7, 8, 14)
  - [ ] 2.1: `web/src/contexts/PreferencesContext.tsx`: `UserPreferences.sidebarCollapsed: boolean` (`:40`) becomes `sidebar: SidebarPreference`; the default (`:49`) becomes `'auto'`; `setSidebarCollapsed` (`:67`, `:187-189`, `:205`) becomes `setSidebarPreference(sidebar: SidebarPreference)`. `loadPreferences` (`:83-111`) reads the cookie as `unknown`, returns the defaults when it is not a plain object, and sets `sidebar: readSidebarPreference(parsed)` (Dev Notes "Reading the cookie"). The write effect (`:169-171`) is unchanged: it serializes `preferences`, which no longer has `sidebarCollapsed`, so the old key disappears on the first render
  - [ ] 2.2: `web/src/contexts/SidebarContext.tsx` (`:30-50`): `isCollapsed = isSidebarCollapsed(preferences.sidebar, useMediaQuery(LG_UP_QUERY))`; `toggleCollapse` calls `setSidebarPreference(isCollapsed ? 'expanded' : 'collapsed')`. The context's shape (`isCollapsed`, `isMobileOpen`, `toggleCollapse`, `setMobileOpen`) does not change, so `Layout`, `Header` and `Sidebar` keep their calls. Update the header comment (`:1-6`)
  - [ ] 2.3: `web/src/components/layout/Sidebar.tsx`: new optional prop `inSheet?: boolean` (default `false`) on `SidebarProps` (`:54-56`). Inside, `const isCollapsed = !inSheet && collapsed` (rename the value destructured at `:59`), so every existing use of `isCollapsed` (`:90-119`, `:137-154`, `:169`, `:184-198`, `:205`, `:217`) shows the full sidebar in the sheet; the collapse toggle (`:181-199`) is not rendered when `inSheet`. Give the toggle `aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}` and `data-testid="sidebar-toggle"`; its visible text "Collapse" stays
  - [ ] 2.4: `web/src/components/layout/Layout.tsx`: the sheet renders `<Sidebar inSheet />` (`:30`); the desktop sidebar container (`:35-38`) gets `data-testid="desktop-sidebar"` (for the E2E width checks). Nothing else here in this task
  - [ ] 2.5: `web/src/features/settings/UIPreferencesPanel.tsx` (`:124-150`): replace the "Start with Sidebar Collapsed" button with the three-way control (Dev Notes "The UI Preferences control"); update the header comment (`:4`). The test ID `sidebar-collapsed-toggle` is removed (no E2E uses it)
  - [ ] 2.6: Tests (Dev Notes "Web tests", Task 2 rows) and the Task 2 entries of "Existing tests that change", red first
  - [ ] 2.7: `just test-web`, `just typecheck-web`, `just lint-web`; format the changed web files with the Prettier that Story 21.1 pinned. Commit `feat(story-21.8/task-2): collapse the sidebar by default on tablet-sized screens`. The body says: with no choice made the sidebar is collapsed from 768 to 1023px; the sidebar's toggle or Settings > UI Preferences > Sidebar (Automatic, Expanded, Collapsed) sets a choice that applies at every width; a sidebar collapsed before the update stays collapsed; the phone menu always shows the full sidebar

- [ ] Task 3: Sidebar E2E and the "before" content widths + tests (AC: 1, 2, 3, 4, 5, 7, 8)
  - [ ] 3.1: `web/e2e/layout-widths.spec.ts` `openPage` (`:263-282`): write `{ sidebar: collapsed ? 'collapsed' : 'expanded' }` instead of `{ sidebarCollapsed: collapsed }`, and fix the comment at `:27-28`. Without this every "sidebar expanded" test from 768 to 1023px would run with a collapsed sidebar and still pass (Dev Notes "Existing tests that change"). Do the same in every helper Story 21.7 added that writes the cookie: after this task `grep -rn sidebarCollapsed web/e2e` finds the old key only in this story's migration test (S4)
  - [ ] 3.2: New describe "Sidebar default and choice (Story 21.8)" in the same spec (Dev Notes "E2E", tests S1 to S6). Untagged, read-only (`readOnly`), no cookie unless the test says so
  - [ ] 3.3: New `_bmad-output/implementation-artifacts/21-8-browser/content_widths.mjs` (Dev Notes "Measurement method") and its first run into `content_widths.before.json`, on the stack rebuilt from the branch at this point (sidebar done, cap not yet). Numbers only, no screenshot
  - [ ] 3.4: Rebuild the stack (`just docker restart`) and run `cd web && bunx playwright test e2e/layout-widths.spec.ts` with `VS_API_KEY_ADMIN` exported; then `just test-e2e-ci`. Commit the spec, the script and the "before" file: `test(story-21.8/task-3): check the sidebar default and choice at tablet and desktop widths`

- [ ] Task 4: Page content is at most 1280px wide and centered, except the console + tests (AC: 9, 10, 11, 12, 13, 14)
  - [ ] 4.1: New `web/src/components/layout/content-width.ts` (Dev Notes "The content width"): `PAGE_CONTENT_WIDTH = 'mx-auto max-w-[1280px]'` and `FULL_WIDTH_ROUTES = ['/game-server/console']`. Delete `web/src/features/game-server/content-width.ts` and move its test to `web/src/components/layout/content-width.test.ts`
  - [ ] 4.2: `web/src/components/layout/Layout.tsx` (`:46-50`): inside the padding `div` wrap `children` in `<div className={fullWidth ? undefined : PAGE_CONTENT_WIDTH} data-testid="page-content">`, where `fullWidth` is true when `useLocation().pathname` matches an entry of `FULL_WIDTH_ROUTES` (`matchPath` from `react-router`). The padding `div` keeps `p-4 md:p-6` and stays the first `div` in `main`
  - [ ] 4.3: Game Settings on the shared constant: `features/game-server/SettingsPage.tsx` (`:22`, `:46`, `:61`, `:75`) and `GameConfigPanel.tsx` (`:29`, `:196`, `:210`, `:298`) import `PAGE_CONTENT_WIDTH` from `@/components/layout/content-width`; their wrappers stay (Dev Notes "Decision: Game Settings keeps its wrappers"). Update the comments at `SettingsPage.tsx:11` and `GameConfigPanel.tsx:7`
  - [ ] 4.4: Tests (Dev Notes "Web tests", Task 4 rows) and the Task 4 entries of "Existing tests that change", red first
  - [ ] 4.5: `grep -rn "max-w-\[1280px\]" web/src | grep -v "\.test\."` shows one line. `just test-web`, `just typecheck-web`, `just lint-web`, Prettier on the changed files. Commit `feat(story-21.8/task-4): limit page width to 1280px on wide screens`. The body says: pages are centered with a maximum width of 1280px; the Console page keeps the full width; the mod browser keeps four columns

- [ ] Task 5: Wide-screen checks, E2E for the cap and the UX notes + tests (AC: 9, 10, 11, 13)
  - [ ] 5.1: Rebuild the stack and run `content_widths.mjs` into `content_widths.after.json`. Compare with Dev Notes "Expected numbers"; a difference of more than 1px is a finding to explain before going on
  - [ ] 5.2: `web/e2e/layout-widths.spec.ts`: new describe "Content width on wide screens (Story 21.8)" (Dev Notes "E2E", tests W1 to W4), and the three long-name tests at `:414-427` rewritten (Dev Notes "Existing tests that change", the Story 18.4 entry). Update the spec's header comment (`:4-37`) with this story's lines
  - [ ] 5.3: `web/e2e/README.md`: recount the tests (`cd web && bunx playwright test --list | tail -1`, and with `--grep-invert "@moddb|@moddb-live|@install|@game-server"`) and update every count the README states (at 966204f: 150 tests, 146 in CI, 119 untagged; Story 21.7 will have changed them)
  - [ ] 5.4: Run the whole changed spec and `e2e/settings-desktop-layout.spec.ts`, `e2e/installed-mods-phone.spec.ts`, `e2e/terminal.spec.ts`, `e2e/content-security-policy.spec.ts` on the rebuilt stack, then `just test-e2e-ci`
  - [ ] 5.5: Browser check on the stack (manual, ticked only after the user confirms it; no screenshot kept): at 1920px and 2560px in both sidebar states look at the Dashboard (the chart fills its card), the Version page, both Mods tabs, a mod detail page, Game Settings and each Settings tab for clipped or lopsided content; the Console at 1920px; at 900px a fresh profile shows the collapsed sidebar. Do not start or stop the game server and change no setting other than the sidebar preference
  - [ ] 5.6: Fill "UX notes: what the spec asked and what was built" in the Dev Agent Record from the template in Dev Notes, with the measured numbers. Commit the spec, the README, the "after" file and the story notes: `test(story-21.8/task-5): check page widths at 1440, 1920 and 2560px`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes (lint with the Prettier check of Story 21.1, typecheck with the E2E project, all tests; 0 skipped web tests added). `git status --short` shows nothing under `dev/`. The diff has no `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, no new `as` assertion and no `nosemgrep`
  - [ ] 6.2: `git log --oneline <base>..HEAD` shows exactly two `feat`/`fix`/`perf` subjects, the two the change proposal lists (section 2): `collapse the sidebar by default on tablet-sized screens` and `limit page width to 1280px on wide screens`. `just changelog` shows both under Features and nothing else from this story
  - [ ] 6.3: Complete the Dev Agent Record: every completion note checked against the code as committed, the File List, the before/after table
  - [ ] 6.4: Story status `review`, `just sprint set 21-8-sidebar-default-and-content-width review`, PR against Story 21.7's branch while its PR is open, otherwise `main`. The PR description says: no API contract change; the `vs_ui_prefs` cookie's new `sidebar` key and the migration of `sidebarCollapsed`; what existing users see (Dev Notes "What existing users see"); the Story 18.4 AC 6 change (a 63-character mod name now wraps at every width); the `GameServerPage` finding; the Follow-ups
  - [ ] 6.5: Close `VSS-w85` and `VSS-alx`, each with an AAR first (`bd comments add`, then `bd close`, then `bd sync`; abbreviated AAR for the size-s `VSS-w85`, full AAR for the size-m `VSS-alx`), once the PR is merged or as the maintainer directs

## Dev Notes

### The state today (verified at 966204f)

- **Where the sidebar state lives.** One boolean, `preferences.sidebarCollapsed` (`web/src/contexts/PreferencesContext.tsx:40`, default `false` at `:49`), in the JSON cookie `vs_ui_prefs` (`:55`; `web/src/lib/cookies.ts:14-43`, one year, `SameSite=Lax`). `loadPreferences` (`:83-111`) reads it on the first render, field by field, with the default for anything missing or of the wrong type, and the defaults when `JSON.parse` throws. The provider writes the whole object back whenever it changes, **the first render included** (`:169-171`). So every browser that has opened the app already stores `sidebarCollapsed: false`; a stored `true` can only come from a choice. That is why "no stored preference" cannot be detected from the boolean, and why ADR-14 changes its shape.
- **Who reads it.** `SidebarProvider` (`contexts/SidebarContext.tsx:30-50`) exposes `isCollapsed: preferences.sidebarCollapsed` and `toggleCollapse`, which writes the negation. This is the project's own context, not shadcn's sidebar component; there is no other state, no `localStorage` and no keyboard shortcut (`grep -rn "keydown\|metaKey\|ctrlKey" web/src/components/layout web/src/contexts` finds nothing). The only two ways to change it are the toggle at the foot of the sidebar (`layout/Sidebar.tsx:181-199`) and the button in UI Preferences (`features/settings/UIPreferencesPanel.tsx:129-149`, test ID `sidebar-collapsed-toggle`).
- **Who uses `isCollapsed`.** `Layout` sets `--sidebar-width` to 64px or 160px (`layout/Layout.tsx:19`); the header (`Header.tsx:23`) and `main` (`Layout.tsx:47`) follow that variable from `md` up. `Sidebar` (`:59`) draws icons only when collapsed and passes the value to `ExpandableNavItem` (`:169`).
- **The phone sheet.** Below `md` the fixed sidebar is hidden (`Layout.tsx:36`, `hidden md:block`) and the same `<Sidebar />` is rendered in a 256px sheet (`:24-32`). It reads the same `isCollapsed`, so a stored `true` draws the icon-only sidebar, with its toggle, inside the sheet (read from the code; Task 2's test confirms it first, red). **With `auto` this would hit every phone**, because below 1024px `auto` means collapsed. The sheet fix is therefore in the same commit as the width rule (Task 2), not a later one.
- **The toggle has no name when collapsed.** Expanded it reads "Collapse"; collapsed it is an icon with no text and no `aria-label` (`Sidebar.tsx:191-192`). The existing unit tests find it by the icon's class name (`Sidebar.test.tsx:213-215`).
- **Media queries.** `useMediaQuery(LG_UP_QUERY)` (`web/src/hooks/use-media-query.ts:17-31`, `(min-width: 64rem)`) is a `useSyncExternalStore` hook: it is right on the first render and follows resizes. Unit tests get `matchMedia` from `web/tests/viewport.ts` (installed by `tests/setup.ts:52`, reset to 1024px after each test, `:73`); `setViewportWidth(width)` changes it and must be wrapped in `act` when components are mounted.
- **Content width.** `Layout` renders `<div className="p-4 md:p-6">{children}</div>` (`Layout.tsx:49`) with no maximum. Only Game Settings is capped, by `SETTINGS_CONTENT_WIDTH = 'mx-auto max-w-[1280px]'` (`features/game-server/content-width.ts:7`), used at `features/game-server/SettingsPage.tsx:46`, `:61`, `:75` and `GameConfigPanel.tsx:196`, `:210`, `:298`. The mod detail page caps itself (`features/mods/ModDetailPage.tsx:524-577`, `container mx-auto max-w-4xl`, 896px, centered).
- **Routing.** `App.tsx:120-147`: `BrowserRouter` > `Layout` > `PageErrorBoundary` > `Suspense` > `Routes`. `Layout` is inside the router and outside `Routes`, so it can call `useLocation` but there are no route handles (`useMatches` needs a data router, which the app does not use).
- **Fixed and full-bleed elements.** In `web/src` outside `components/ui`, only two elements are `fixed`: the header (`Header.tsx:23`) and the desktop sidebar (`Layout.tsx:36`). Nothing uses `sticky`, a negative horizontal margin, `w-screen` or `100vw` (grep at 966204f). Page title rows and toolbars (the Mods tab list, the Installed toolbar, the browse search row, the Game Settings title row) are ordinary children of the page, so they are capped with it and keep sharing its edges. Dialogs, sheets and toasts are portals outside `main`.

### Decision: what an explicit choice is (ADR-14 decision 4)

- A choice is made by the sidebar's toggle or by the UI Preferences control. Nothing else writes `expanded` or `collapsed`: not a resize, not opening the phone sheet, not the first render.
- The toggle stores **the opposite of what is shown**, never `auto`. One choice for all widths.
- Toggling at tablet width and then widening the window:

  | Start (stored, width) | Action | Stored | At 900px | At 1440px |
  |---|---|---|---|---|
  | `auto`, 900px (shown collapsed) | toggle | `expanded` | expanded | expanded |
  | `expanded`, 900px | toggle | `collapsed` | collapsed | **collapsed** |
  | `auto`, 1440px (shown expanded) | toggle | `collapsed` | collapsed | collapsed |
  | `collapsed`, 1440px | toggle | `expanded` | **expanded** | expanded |
  | any | UI Preferences > Automatic | `auto` | collapsed | expanded |

  The second row is the one that may surprise: a user who opened and closed the sidebar on a tablet has, by the ADR, chosen "collapsed" and keeps it on a desktop width until they toggle again or pick Automatic. Not built: returning to `auto` when a toggle lands on what `auto` would show (it would make the toggle's result depend on the width, and the ADR says a choice wins everywhere), and a memory per width range (rejected in ADR-14 decision 4).
- Below 768px the toggle is not shown (AC 8). The UI Preferences control works at every width; on a phone its effect is seen only after the window is 768px or wider.
- No keyboard shortcut exists and none is added.
- The toggle gets an accessible name because it is now the way to make the choice and the E2E must find it in both states. This is the one item found in planning and added under the backlog rule; it adds no release note of its own.

### The preference module (`web/src/lib/sidebar-preference.ts`, Task 1)

```ts
export type SidebarPreference = 'auto' | 'expanded' | 'collapsed';

/** In the order UI Preferences shows them. */
export const SIDEBAR_PREFERENCES: readonly SidebarPreference[] = ['auto', 'expanded', 'collapsed'];

export function isSidebarPreference(value: unknown): value is SidebarPreference;

/**
 * The preference stored in a parsed vs_ui_prefs cookie. A valid `sidebar` wins. Otherwise the
 * key written before Story 21.8 is read once: `sidebarCollapsed: true` can only come from a
 * choice, so it is `collapsed`; `false` was written on every first render, so it is `auto`.
 */
export function readSidebarPreference(stored: Record<string, unknown>): SidebarPreference;

/** `auto` is collapsed below `lg` (1024px) and expanded from it; a choice applies at every width. */
export function isSidebarCollapsed(preference: SidebarPreference, isLgUp: boolean): boolean;
```

- `isSidebarPreference` compares with `SIDEBAR_PREFERENCES` by `some((item) => item === value)` (an `includes` on a typed array would need an assertion for an `unknown` argument).
- `readSidebarPreference`: `isSidebarPreference(stored.sidebar) ? stored.sidebar : stored.sidebarCollapsed === true ? 'collapsed' : 'auto'`. Only the boolean `true` counts; the string `"true"`, `1` and anything else are `auto`.
- `isSidebarCollapsed` returns `true` for `auto` below `lg`, phones included. The phone sheet ignores it (`inSheet`), and the fixed sidebar is hidden there, so the value is not seen below 768px.
- The string `sidebarCollapsed` appears in this module and in tests only.

### Reading the cookie (`PreferencesContext.tsx:83-111`, Task 2.1)

- Today `JSON.parse(cookieValue) as Partial<UserPreferences>` works for `null` only because reading a property of `null` throws inside the `try`. Make it explicit and remove the assertion: `const parsed: unknown = JSON.parse(cookieValue)`; when it is not a non-null, non-array object, return the defaults; otherwise narrow it to `Record<string, unknown>` with a type guard (a local `isRecord(value: unknown): value is Record<string, unknown>`; `grep -rn "function isRecord" web/src` finds none at 966204f, re-check and reuse one if an earlier Epic 21 story added it). The four existing validators (`isValidTheme`, `isValidFontSize`, `isValidInstalledModsSort`, and the `typeof ... === 'boolean'` check for `gameServerNavExpanded`) already take `unknown` or narrow by `typeof`, so they need no change. Do not add an `as`.
- The old key is not written: the returned object has exactly the five keys of `UserPreferences`, and the effect at `:169-171` serializes that object.
- Downgrade: an older web build reads `sidebarCollapsed`, finds none and shows the sidebar expanded; a `collapsed` choice made after this story is lost on a downgrade. Accepted (the cookie is a convenience, and the app has no downgrade path for preferences).
- Two tabs: each tab writes its whole in-memory object, so the last change wins, as today. Not changed.

### The UI Preferences control (Task 2.5)

- Follow the theme selector directly above it in the same file (`UIPreferencesPanel.tsx:54-75`): a label, a row of three `Button`s (`size="sm"`, `variant` `'default'` for the stored value and `'outline'` for the others) and one line of help text. No new component and no new dependency (`ui/` has no radio or toggle group; do not add one).
- Label "Sidebar". Buttons in the order of `SIDEBAR_PREFERENCES` with the labels Automatic, Expanded, Collapsed and the test IDs `sidebar-auto`, `sidebar-expanded`, `sidebar-collapsed`. The row is `role="group"` with `aria-labelledby` pointing at the label's `id`, and each button has `aria-pressed` (true for the stored value), so the current value is announced. Help text: "Automatic collapses the sidebar on screens narrower than 1024px. Expanded and Collapsed apply at every width."
- The row must fit a 320px screen: use `flex flex-wrap gap-2` for the row, so a button drops to a second line when the three do not fit (their labels are longer than the theme buttons'; not measured in planning). `layout-widths.spec.ts:511-529` already checks the UI Preferences tab for sideways scrolling at 320, 390 and 430px and will catch a row that does not wrap.
- It shows the **stored** value, not what is drawn: with `auto` at 900px the selected button is Automatic while the sidebar is collapsed.

### The content width (Task 4)

`web/src/components/layout/content-width.ts`:

```ts
/** At most 1280px, centered (UX spec "Content Width Constraints", Epic 21 ADR-15). Written once. */
export const PAGE_CONTENT_WIDTH = 'mx-auto max-w-[1280px]';

/** Routes whose page uses the full width of the content area: the console (ADR-15 decision 4). */
export const FULL_WIDTH_ROUTES: readonly string[] = ['/game-server/console'];
```

- **Which wrapper.** A new `div` inside `Layout`'s padding `div`, so the padding is outside the 1280px (ADR-15 decision 1): `<div className="p-4 md:p-6"><div className={fullWidth ? undefined : PAGE_CONTENT_WIDTH} data-testid="page-content">{children}</div></div>`. The wrapper is always rendered, so the console page's DOM differs from the other pages only by the class. `max-w` on the padding `div` itself would put the padding inside the 1280px (content 1232px).
- **How the console opts out.** `Layout` computes `fullWidth = FULL_WIDTH_ROUTES.some((path) => matchPath(path, pathname) !== null)` from `useLocation()`. `matchPath` with a string pattern matches the whole path and accepts a trailing slash (checked, see "Latest Technical Information"). The ADR offers "a route handle or a wrapper": handles need a data router (see "Routing"), and a wrapper route in `App.tsx` would leave the `Suspense` fallback and the error boundary outside the cap, so a lazy page would jump sideways when it loads. A list next to the constant keeps the rule in the layout, as the ADR asks, with no negative margin. `Layout` is always rendered inside a router (`App.tsx:120-121`; `Layout.test.tsx:50` uses `MemoryRouter`).
- **Why the constant is in `components/layout`.** `Layout` must not import from a feature folder; the two Game Settings files import from the layout folder instead.
- **Tailwind** scans `.ts` files under `src`, so the class in a constant is generated, as it is today for `SETTINGS_CONTENT_WIDTH`.
- **Not capped:** the header bar (it stays fixed from the sidebar's edge to the right edge of the window; the server name stays at its left), the sidebar, and `/game-server/console` in all its states (loading, error, not installed, installed).
- **Capped by the layout with no change of their own:** Dashboard (`/`), Version (`/game-server/version`), Mods installed and browse, mod detail (896px, centered inside the centered 1280px, so its position on screen does not change), Settings (`/config`), the redirects and the `PageLoading` fallback.

### Decision: Game Settings keeps its wrappers

`features/game-server/SettingsPage.tsx` and `GameConfigPanel.tsx` keep their own `div`s with the width class and only change the import. Inside a parent that is already at most 1280px wide the same class does nothing, so the page does not move; the wrappers keep Story 17.8's title-row alignment and its tests (`settings-page-content`, `game-config-layout`) untouched, and `GameConfigPanel` stays capped wherever it is rendered. ADR-15 decision 1 allows either ("becomes that constant or is removed"). Removing the wrappers would be a second change with no visible effect.

### Expected numbers (computed from the classes; Task 5.1 measures them)

Content area = viewport - sidebar (160 or 64). Uncapped content = area - 48 (`md:p-6`). Capped content = `min(1280, area - 48)`, left edge = sidebar + (area - content) / 2.

| Viewport | Sidebar | Content before (left to right, width) | Content after (left to right, width) |
|---|---|---|---|
| 1280 | expanded | 184 to 1256, 1072 | unchanged |
| 1440 | expanded | 184 to 1416, 1232 | unchanged |
| 1440 | collapsed | 88 to 1416, 1328 | 112 to 1392, 1280 |
| 1920 | expanded | 184 to 1896, 1712 | 400 to 1680, 1280 |
| 1920 | collapsed | 88 to 1896, 1808 | 352 to 1632, 1280 |
| 2560 | expanded | 184 to 2536, 2352 | 720 to 2000, 1280 |
| 2560 | collapsed | 88 to 2536, 2448 | 672 to 1952, 1280 |

- The cap takes effect above a viewport of 1488px (sidebar expanded) or 1392px (collapsed); at exactly those widths the content is 1280px with or without it.
- Console panel at 1920px: 1712px expanded, 1808px collapsed, before and after.
- Mod browser at 1920px: four columns (`ModBrowseGrid.tsx:41`, `xl:grid-cols-4`, chosen by viewport width) of (1280 - 3 x 16) / 4 = 308px; today about 416px expanded. `VersionGrid.tsx:35` has the same classes and behaves the same.
- The Dashboard's stat grid is two columns from `sm` (`Dashboard.tsx:120`); its cards become 632px wide. The chart is in a `ResponsiveContainer` and follows its card.
- Installed mods table: its container is at most 1280px. See the Story 18.4 entry below.
- The bead's "184-1896px (1712px)" for 1920px expanded matches the first "before" row for that width.

### ADR against the code

1. **`GameServerPage` has no route (ADR-15 decision 4, epic AC "the game server page with the console").** `features/game-server/GameServerPage.tsx` is exported from `features/game-server/index.ts:10` and rendered by nothing but its own test; `App.tsx:127-140` routes `/game-server` to Version, Settings, Mods and Console only. There is one reachable console page, and it is exempt. The story does not route, change or delete `GameServerPage`. If it is ever given a route, that path must be added to `FULL_WIDTH_ROUTES`; the doc comment on the constant says so. AC 11 is written for the Console page only. (Follow-up 1.)
2. **A route handle is not available (ADR-15 decision 4, "a route handle or a wrapper").** See "The content width": the opt-out is a path list read by `Layout`.
3. **Capping the Mods page ends Story 18.4's "long name on one line" at wide widths (ADR-15 decision 2 against Story 18.4 AC 6).** Story 18.4 measured that the installed mods table with its 63-character test name needs about 1327px to keep that name on one line; it fits at 1440px collapsed (1328px container) and at 1920px, and wraps at 1440px expanded (1232px). With the cap the table's container is never wider than 1280px, so that name wraps to two lines at **every** width. Short names and the Available cell stay on one line from 1280px, as before. The maintainer confirmed that the Mods page is capped (answer 7), so the story follows the ADR: the three E2E tests that assert one line for the long name are rewritten (below), and the PR description names the change. Exempting the Installed tab is the alternative; it is not taken here because it would make the two Mods tabs different widths.
4. **Task order (epic tasks 1 and 2).** The epic puts the width rule in its first task and the phone sheet in its second. With `auto`, the width rule alone would show the icon-only sidebar in every phone's sheet, and changing the preference's type breaks `UIPreferencesPanel`'s compile, so the rule, the sheet and the control are one commit (Task 2), preceded by the pure module (Task 1). The epic's five tasks map to Tasks 1 to 5 here; Task 6 is the quality gate.

### What existing users see

- At 1024px and wider, nothing changes for the sidebar.
- From 768 to 1023px the sidebar is collapsed after the update unless the user toggles it. A user who had collapsed it before keeps it collapsed at every width. A user who had collapsed and expanded it again is treated as never having chosen (ADR-14 decision 2).
- On phones, the menu always shows the full sidebar.
- On screens wider than about 1500px, pages are centered with empty space left and right; the Console page is as before.

### Web tests

Vitest runs in the `vmThreads` pool: follow the stubbing rule in `project-context.md` ("Stubbing browser globals in web unit tests"). Use `setViewportWidth` from `web/tests/viewport.ts` for widths (wrapped in `act` after mount), never a redefined `window.matchMedia`. No skipped test.

| Task | File | Cases |
|---|---|---|
| 1 | `src/lib/sidebar-preference.test.ts` (new) | `readSidebarPreference`: `{}` is `auto`; `{ sidebarCollapsed: true }` is `collapsed`; `{ sidebarCollapsed: false }` is `auto`; `{ sidebar: 'expanded', sidebarCollapsed: true }` is `expanded` (the new key wins); each of the three valid values is returned; `{ sidebar: 'bogus' }`, `{ sidebar: null }`, `{ sidebar: 1 }` are `auto`; `{ sidebar: 'bogus', sidebarCollapsed: true }` is `collapsed`; `{ sidebarCollapsed: 'true' }` and `{ sidebarCollapsed: 1 }` are `auto`. `isSidebarCollapsed`: the six combinations of three values and `isLgUp`. `isSidebarPreference`: the three values, and `''`, `'Auto'`, `undefined`, `true` |
| 2 | `src/contexts/PreferencesContext.test.tsx` | no cookie: `sidebar` is `auto` and the first `setCookie` call's JSON has `"sidebar":"auto"` and no `sidebarCollapsed`; old `true`: `collapsed`, and the JSON written back has `"sidebar":"collapsed"` and no `sidebarCollapsed`; old `false`: `auto`; a cookie that is `not valid json {{{`, `null`, `5`, `"x"` and `[]`: the defaults, no throw (one `it.each`); `sidebar: 'bogus'` with a valid `theme: 'dark'`: `auto` and the theme kept; `setSidebarPreference` for each value updates the state and the cookie |
| 2 | `src/contexts/SidebarContext.test.tsx` | `it.each` over 767, 768, 1023, 1024 and 1440px for each stored value (set the width before rendering): `auto` is collapsed below 1024 and expanded from it, `expanded` is never collapsed, `collapsed` always; `auto` follows a resize from 1440 to 900 and back while mounted and writes no new cookie value; the five rows of the table in "Decision: what an explicit choice is", each asserting the stored value and `isCollapsed` at 900 and at 1440; old `{ sidebarCollapsed: true }` at 1440: collapsed; old `{ sidebarCollapsed: false }` at 900: collapsed, at 1440: expanded |
| 2 | `src/components/layout/Sidebar.test.tsx` | `inSheet` with stored `collapsed`: "Dashboard", "Game Server" and "VSManager" labels, the full logo (`/vintagestory-logo.webp`), the version, and no `sidebar-toggle`; `inSheet` with `auto` at 390px: the same; without `inSheet` and stored `collapsed`: icons only, as today; the toggle's accessible name is "Collapse sidebar" expanded and "Expand sidebar" collapsed (`getByRole('button', { name: ... })`) |
| 2 | `src/components/layout/Layout.test.tsx` | stored `collapsed`, sheet opened by the menu button: the text "Dashboard" is in the document (the fixed sidebar is collapsed and shows no labels, so the label can only come from the sheet) and exactly one `sidebar-toggle` exists (the fixed sidebar's); written first, it fails on today's code, which confirms the planning finding; `--sidebar-width` is 64px at 900px with no cookie and 160px at 1024px |
| 2 | `src/features/settings/UIPreferencesPanel.test.tsx` | the three buttons render in the group named "Sidebar"; Automatic is pressed by default; old `{ sidebarCollapsed: true }`: Collapsed is pressed; `{ sidebar: 'expanded' }`: Expanded is pressed; clicking each writes its value to the cookie; Automatic after Collapsed writes `"sidebar":"auto"`; at 900px with `auto` the pressed button is Automatic |
| 4 | `src/components/layout/content-width.test.ts` (moved) | `PAGE_CONTENT_WIDTH` is `'mx-auto max-w-[1280px]'`; `FULL_WIDTH_ROUTES` is `['/game-server/console']` |
| 4 | `src/components/layout/Layout.test.tsx` | `renderLayout` gains an optional route (`MemoryRouter initialEntries`). At `/`, `/game-server/version`, `/game-server/settings`, `/game-server/mods/installed`, `/game-server/mods/browse`, `/game-server/mods/browse/some-mod` and `/config`: `page-content` has both classes of `PAGE_CONTENT_WIDTH`, contains the child, and its parent has `p-4` and `md:p-6`. At `/game-server/console` and `/game-server/console/`: `page-content` has neither class and still contains the child. At `/game-server/consolex`: capped |
| 4 | `src/features/game-server/SettingsPage.test.tsx`, `GameConfigPanel.test.tsx` | the existing class assertions, with the new import |

jsdom applies no layout, so widths in pixels are checked only in the E2E.

### E2E (`web/e2e/layout-widths.spec.ts`)

Extends the existing spec; stubbed, read-only and **untagged**, so CI runs it (`web/e2e/README.md` "Tags"). Use the spec's own helpers: `readOnly` (`:106-117`, which calls `serveConfigKey` and `pretendServerInstalled` from `e2e/config-js.ts` and refuses every write), `fakeInstalledMods` (`:120-225`), `boxOf`, `documentOverflow`. Any new stub that passes a request on to the API uses `fetchOnNewConnection(route)`. E2E specs are type-checked (`web/e2e/tsconfig.json`, `just typecheck-web`). No screenshot. The game server is neither started nor stopped. Nothing real changes: the only state is the `vs_ui_prefs` cookie of the test's own browser context, so no snapshot guard is needed.

The fixed sidebar and `main` animate their width for 300ms (`Layout.tsx:36`, `:47`). After a toggle, a resize or a preference change, wait with `await expect.poll(async () => (await boxOf(page.getByTestId('desktop-sidebar'), 'sidebar')).width).toBe(64)`; never with a fixed pause. On the first load there is no animation, so S1 reads the width as soon as the sidebar is visible.

A helper `prefsCookie(page)` reads the context's `vs_ui_prefs` cookie and returns the parsed JSON (`decodeURIComponent` first; `cookies.ts:41` encodes it).

**Sidebar (Task 3):**

- **S1, fresh browser (AC 1).** No cookie added. At 768 and 900px: the sidebar is 64px wide; at 1024 and 1440px: 160px. `prefsCookie` has `sidebar: 'auto'` and no `sidebarCollapsed` key. This test must not use `openPage` (it adds a cookie); give it its own small opener that only sets the viewport, calls `readOnly` and navigates.
- **S2, follows the width (AC 2).** Fresh at 900px (64px); `setViewportSize` to 1100: 160px; back to 900: 64px; the cookie still says `auto`.
- **S3, a choice wins (AC 3).** Fresh at 900px; click `sidebar-toggle` (name "Expand sidebar"): 160px, cookie `expanded`; reload: 160px; click again (name "Collapse sidebar"): 64px, cookie `collapsed`; widen to 1440px: still 64px; reload at 1440px: 64px.
- **S4, old cookies (AC 4, 5).** Cookie `{ sidebarCollapsed: true }` at 1440px: 64px, and the cookie afterwards has `sidebar: 'collapsed'` and no `sidebarCollapsed`. Cookie `{ sidebarCollapsed: false }`: 64px at 900px and 160px at 1440px, cookie `auto`.
- **S5, UI Preferences (AC 7).** Cookie `{ sidebar: 'collapsed' }`, `/config` at 1440px: `sidebar-collapsed` has `aria-pressed="true"` and the sidebar is 64px; click `sidebar-auto`: 160px, cookie `auto`; resize to 900px: 64px; click `sidebar-expanded`: 160px at 900px.
- **S6, phone sheet (AC 8).** Cookie `{ sidebar: 'collapsed' }` at 390px: click the "Open menu" button; inside the dialog named "Navigation menu" the links "Dashboard" and "VSManager" are visible with their text, the `aside` is 256px wide and there is no `sidebar-toggle` in the dialog. Repeat with no cookie.

**Content width (Task 5):**

- **W1, capped pages (AC 9, 13).** For each of 1280, 1440, 1920 and 2560px and each sidebar state (eight tests; each visits the pages below in `test.step`s): `page-content`'s box is `min(1280, width - sidebar - 48)` wide within 1px; the space between the sidebar's right edge and the box equals the space between the box and the viewport's right edge within 1px; `documentOverflow` is 0. Pages and the element to wait for: `/` (`dashboard-stats-grid`, or the heading "Dashboard" if the stack's state shows another branch of the page), `/game-server/version` (`version-page`), `/game-server/settings` (`game-config-layout`), `/game-server/mods/installed` with `fakeInstalledMods` (`mod-table`), `/game-server/mods/browse` with the browse stub of W2 (`mod-browse-grid`), `/config` (`ui-preferences-panel`). The header's box still spans from the sidebar's right edge to the viewport's right edge.
- **W2, mod browser columns (AC 10).** Stub `GET /api/v1alpha1/mods/browse` with eight made-up items (the item shape of `BROWSE_BODY` in `e2e/content-security-policy.spec.ts:195-217`, with `logo_url: null` so no image is requested), `/mods/gameversions` with one version and `/mods/tags` with none (the same spec, `:299-304`); add the three paths to `fakeInstalledMods` or a small route of its own registered after `readOnly`. At 1920px, both states: the first four cards share one `y`, the fifth is lower, the grid is 1280px wide within 1px and each card is 308px wide within 1px. Check the browse response's pagination fields against `web/src/api/types.ts` when building the body.
- **W3, console (AC 11).** `/game-server/console` at 1920px, both states: `console-panel`'s width is `1920 - sidebar - 48` within 1px (1712 and 1808) and `page-content` is as wide; `documentOverflow` is 0. `e2e/terminal.spec.ts` shows how the page is opened on a stack with no game server.
- **W4, mod detail (AC 13).** One state at 1920px: the mod detail page (`mod-detail-page`, lookup stubbed as in `content-security-policy.spec.ts:305-307` or with the spec's own lookup stub at `:165-206`) is 896px wide and centered in `page-content`.

The Game Settings tests at `:569-593` (title and badge against the panel at 1024 to 1920px) must pass unchanged; they are the check that the nested width class moved nothing.

### Measurement method (`_bmad-output/implementation-artifacts/21-8-browser/content_widths.mjs`)

Copy the frame of Story 21.7's measurement script if it has one in its folder, otherwise of `18-4-browser/column_widths.mjs` (Playwright from `../../../web/node_modules/@playwright/test/index.mjs`, `E2E_BASE_URL`, `/config.js` answered with `VS_API_KEY_ADMIN`, the read-only route, the installed mods stub). Run with `bun` from `web/` against the dev stack on port 8080.

- Widths 1024, 1280, 1440, 1920 and 2560, height 900, each with the sidebar expanded and collapsed through the cookie (`{ sidebar: 'expanded' }` or `{ sidebar: 'collapsed' }`), a fresh context per state.
- Pages: Dashboard, Version, Game Settings, Mods installed (stubbed), Mods browse (stubbed as in W2), a mod detail page (stubbed), `/config` with each of its tabs, Console.
- Per page: the rect (left, right, width, rounded) of `main > div > div` (after Task 4 this is `page-content`; before it, record `main > div`'s content box as left + 24 to right - 24), the document's sideways overflow, every element under `main` that scrolls sideways; plus per page one key element: the Dashboard's `dashboard-stats-grid` and `metrics-chart-card`, the first and fifth browse card, `mod-table` and the height of the long-named mod's row, `console-panel`, `mod-detail-page`, `game-config-layout`.
- Output is JSON to stdout, redirected to `content_widths.before.json` (Task 3.3) and `content_widths.after.json` (Task 5.1). No screenshot. If one is ever taken for the review, mask `header span.font-semibold`, `#ServerName` and `#Password`, and do not commit it.
- The script writes only into the story's folder; nothing is written under `dev/`.

### Existing tests that change (deliberately)

Found by prototyping Tasks 1, 2 and 4 on 966204f and running the whole web suite (prototype discarded): `tsc --noEmit` reported 3 errors and `vitest run` 14 failed of 3307, in three files. Everything in `Sidebar.test.tsx`, `Layout.test.tsx`, `Header.test.tsx`, `ExpandableNavItem.test.tsx`, `ModTable.test.tsx`, `SettingsPage.test.tsx` and `GameConfigPanel.test.tsx` passed (the last two with the import changed). Line numbers will have moved after Story 21.1's reformat; find the tests by name.

- `web/src/contexts/PreferencesContext.test.tsx` (6 fail, and the 3 type errors at `:218`, `:221`, `:228`): "loads default preferences when no cookie exists" (`:45`), "loads preferences from cookie when present" (`:59`), "uses defaults for missing or invalid cookie values" (`:81`), "handles corrupted cookie JSON gracefully" (`:100`): the expected objects have `sidebar` instead of `sidebarCollapsed` (`'auto'`, and `'collapsed'` for the cookie with the old `true`, which stays in that test as a migration case). The describe "setSidebarCollapsed" (`:213-236`, 2 tests) becomes "setSidebarPreference". (Task 2)
- `web/src/contexts/SidebarContext.test.tsx` (3 fail): "persists isCollapsed to cookie when changed to true" (`:81`), "... to false" (`:95`), "persists isCollapsed on every state change" (`:194`): they expect `"sidebarCollapsed":true/false` in the cookie; now `"sidebar":"collapsed"` / `"sidebar":"expanded"`. **Pass but must be rewritten, because their names would no longer be true:** "initializes isCollapsed to false when no preferences exist" (`:57`) and "... when sidebarCollapsed is false in preferences" (`:65`) hold only because jsdom's default width is 1024px; replace them with the width table of "Web tests". "initializes isCollapsed from preferences when sidebarCollapsed is true" (`:47`) and "toggleCollapse flips state from true to false" (`:125`) keep the old cookie on purpose (migration). (Task 2)
- `web/src/features/settings/UIPreferencesPanel.test.tsx` (5 fail): "renders sidebar toggle" (`:68`), the describe "sidebar toggle" (`:159-183`, 3 tests) and "loads saved preferences from cookie" (`:186`): the test ID `sidebar-collapsed-toggle` is gone; rewrite for the three buttons. (Task 2)
- `web/src/components/layout/Sidebar.test.tsx:209-332` (pass): the tests in "Sidebar Collapse Behavior", "renders icon when collapsed" and "shows tooltips when sidebar is collapsed" find the toggle by `innerHTML.includes('panel-left-close')`; change them to the accessible name while there, since the name is now part of AC 3. (Task 2)
- `web/src/components/layout/Layout.test.tsx` (pass): "sets --sidebar-width to 64px when collapsed" (`:96`) finds the toggle by `/collapse/i`, which still matches "Collapse sidebar". "shows desktop sidebar on tablet and larger" (`:182`) sets `innerWidth` to 768 by `Object.defineProperty`: at that width the sidebar is now collapsed, and the test still passes because it only counts `aside` elements; change it to `setViewportWidth(768)`, as the stubbing rule asks. "applies main content padding correctly" (`:149`) reads `main.querySelector('div')`, which stays the padding `div`. (Tasks 2 and 4)
- `web/src/components/ModTable.test.tsx:1415`, `:1443`, `:1923`, `:2157` (pass): four cookie fixtures carry `sidebarCollapsed: false`; change them to `sidebar: 'auto'`, so the old key is left only in tests about the migration. (Task 2)
- `web/src/features/game-server/content-width.test.ts`: moved to `components/layout/content-width.test.ts` and extended. `SettingsPage.test.tsx:13`, `:337` and `GameConfigPanel.test.tsx:6`, `:781`, `:855`, `:863`: the import and the constant's name. (Task 4)
- `web/e2e/layout-widths.spec.ts` `openPage` (`:263-282`): the cookie. Not a failure but a silent change: with `{ sidebarCollapsed: false }` the "sidebar expanded" tests at 768, 900 and 1023px (`:290-307`), the Update test at 900px (`:327`) and the sort test at 900px (`:456`) would run with a collapsed sidebar. Every test Story 21.7 added through `openPage` is corrected by the same edit. (Task 3)
- `web/e2e/layout-widths.spec.ts:414-427`, **the Story 18.4 entry** ("the long name and the Available cell on one line" at 1440px collapsed and 1920px in both states): these three will fail after Task 4 (the table's container is 1280px; the long name needs about 1327px). Replace them with three tests at the same widths and states that assert what the 1024px test asserts (`:375-384`): nothing scrolls sideways, the long-named mod's toggle and remove button are inside the viewport, and its name is taller than Off Mod's (it wraps); keep the Available cell's one-line check from `expectOneLine` for that row. Update the comment at `:414-415` and the spec header's Story 18.4 lines (`:11-15`). The short-name tests at 1280, 1440 and 1920px (`:404-411`) must pass unchanged; if one fails, stop and report it. (Task 5)
- E2E outside this spec: at 966204f no other spec opens a page between 768 and 1023px or wider than 1440px (`settings-desktop-layout.spec.ts` uses 1024, 1440 and 1920 and asserts `<= 1280`, `:80-87`; the rest use 390, 1280 or 1440 with the default sidebar, where the content is 1232px at most). Re-check after Story 21.7: `grep -rn "setViewportSize\|viewport:" web/e2e`.
- Anything else that fails is a regression (AC 14): fix the code, not the test.

### Not changed (do not "fix" these here)

- The sidebar's widths (160px and 64px; the UX spec's 240px was never built), its breakpoints (`md` for the sheet, `lg` for `auto`), its contents and the 300ms animation.
- The header bar: full width, server name at its left edge, not aligned with the centered content (ADR-15 decision 5).
- `GameServerPage.tsx` and its test; `GameServerLayout` in `App.tsx`; the routes.
- The mod browser's number of columns, `VersionGrid`, the mod detail page's `max-w-4xl`, the Dashboard's grid.
- The Console page's height rule (`ConsolePage.tsx:60-64`).
- The other preferences, the cookie's name, lifetime and attributes, `lib/cookies.ts`.
- `use-media-query.ts` and `tests/viewport.ts` (used as they are).
- No keyboard shortcut for the sidebar, no per-width memory, no "reset preferences" button.
- 44px touch targets for the UI Preferences buttons (the theme buttons beside them are `size="sm"` too; a change would cover the whole panel).

### API contract changes

None. No route, request, response field, status code or error code changes; the API is not touched. The one stored-data change is in the browser: the `vs_ui_prefs` cookie gains the key `sidebar` (`"auto"`, `"expanded"` or `"collapsed"`), and `sidebarCollapsed` is read once for migration and no longer written. The PR and the release notes cite this.

### Follow-ups (not in this story; for the maintainer)

1. `GameServerPage` (`features/game-server/GameServerPage.tsx`, its test and its export) is unreachable code since the Game Server section got its own pages. Removing it, or giving it a route, is a product decision outside the two beads.
2. The header's server name is not aligned with the centered content on wide screens. ADR-15 decision 5 leaves the header alone; whether it should follow the content is a design question.
3. A very long mod name (the 63-character name of the E2E fixture) wraps in the installed mods table at every width once the page is capped (see "ADR against the code" 3). If one-line names matter more than a common width, the Installed tab could be exempted later.

### UX notes: what the spec asked and what was built (template for Task 5.6)

| UX spec (`ux-design-specification.md`) | Built |
|---|---|
| Desktop, 1024px+: "Full sidebar navigation (240px)" (`:1203`) | Expanded by default from 1024px; 160px wide (unchanged, set before this story) |
| Tablet, 768-1023px: "Collapsible sidebar (default collapsed to icons)" (`:1211`) | Collapsed (64px) with no choice stored; a choice wins at every width (ADR-14) |
| Tablet: "Full-width console" (`:1214`) | The Console page uses the full content width at every width (ADR-15 decision 4) |
| Mobile: "Hamburger menu replacing sidebar" (`:1218`) | Unchanged; the sheet now always shows the full sidebar |
| "Max content width: 1280px", "Centered with auto margins on ultra-wide" (`:1256-1258`) | Every page but the console; padding outside the 1280px; measured numbers from `content_widths.after.json` |

The dev adds the measured rows (1440, 1920, 2560px, both states) under the table.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-web <file>` after each change; `just check` before review.

- Unit tests set widths with `setViewportWidth` and cookies through the mocked `@/lib/cookies` (`getCookie` return value, `setCookie` calls), as the three existing test files do. Assert on the last `setCookie` call's JSON by parsing it, not only by substring, where a test must show a key is absent.
- E2E needs the stack rebuilt from the branch (`just docker restart`) and `VS_API_KEY_ADMIN` exported; `just test-e2e-ci` runs both CI passes on throwaway containers.
- `git status --short` after the unit and E2E runs shows nothing under `dev/`.
- After Task 2 and before Task 3 the E2E "sidebar expanded" labels below 1024px are wrong (see above); do not run or judge the E2E suite between those two commits.

### Security Requirements

- No new endpoint, no new request, no secret. The cookie holds UI preferences only and is parsed defensively (AC 6): a hand-edited cookie cannot throw past `loadPreferences` or put an unknown string into a class name, because the value is checked against the three literals before use.
- The measurement script and the E2E read only and refuse every write to the API. No instance-specific value (server name, password, key) in the story, the PR, the JSON files or the AARs.

### Development Commands

- `just test-web src/lib/sidebar-preference.test.ts src/contexts/PreferencesContext.test.tsx src/contexts/SidebarContext.test.tsx src/components/layout/Sidebar.test.tsx src/components/layout/Layout.test.tsx src/features/settings/UIPreferencesPanel.test.tsx`
- `just test-web src/components/layout/content-width.test.ts src/components/layout/Layout.test.tsx src/features/game-server/SettingsPage.test.tsx src/features/game-server/GameConfigPanel.test.tsx`
- `just typecheck-web`, `just lint-web`, `just check`
- `just docker restart`, then `cd web && bunx playwright test e2e/layout-widths.spec.ts`; `just test-e2e-ci`
- `cd web && bun ../_bmad-output/implementation-artifacts/21-8-browser/content_widths.mjs > ../_bmad-output/implementation-artifacts/21-8-browser/content_widths.before.json`
- Never `just sprint` before Task 6.4; never edit `sprint-status.yaml` or `.beads/` by hand.

### Previous Story Intelligence

- **21.7** (directly before): it measures every page at 320 to 1023px in both sidebar states and extends `layout-widths.spec.ts`. Its "sidebar expanded" measurements at 768 to 1023px describe a state that, after this story, a user reaches only by choosing Expanded; they stay valid for that state. Read its Completion Notes for pages it reported as still scrolling at tablet widths with the sidebar expanded.
- **21.1:** the web is formatted by a pinned Prettier and `just lint-web` checks it. The files this story edits in `contexts/` and `components/layout/` used double quotes at 966204f and will have been rewritten; the code samples here use the configured single quotes.
- **21.5 / 21.6:** `ui/sheet.tsx`'s close button is 44px (it sits at the top right of the phone sheet; AC 8's sheet test must not count it as a toggle), and `Sidebar.tsx`'s GitHub link says it opens a new tab. Keep both.
- **17.8:** introduced `LG_UP_QUERY`, `layout-widths.spec.ts`, the cookie-per-context way of setting the sidebar state, and `SETTINGS_CONTENT_WIDTH`; found both beads of this story. Its measurement script is the model for this one.
- **18.4:** measured the installed mods table's column needs; its AC 6 is narrowed by this story (see "ADR against the code" 3).
- **16.5:** `useMediaQuery` and `tests/viewport.ts`; one layout is mounted and chosen by the hook, which is the pattern `SidebarProvider` follows.
- **Review learnings from Epics 19 and 20 that apply:** a `feat` or `fix` subject must describe something an admin can see (both of this story's do); a completion note must be true of the code as committed (re-read each before review); tests must not write into `dev/`; manual checks are ticked only after the user confirms; E2E specs are type-checked; new E2E tests that need no live mod database or game server stay untagged; the README's test counts are kept right. The TanStack Query `onError` learning does not apply (no query or mutation is added).

### Git Intelligence

- Base for the line references: `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`). The implementation branch is cut from Story 21.7's branch.
- Planned commits: Task 1 `refactor`, Task 2 `feat` (release note), Task 3 `test`, Task 4 `feat` (release note), Task 5 `test`, Task 6 `docs` (story record and status). Release notes come from `feat`/`fix`/`perf` subjects (`cliff.toml`, `RELEASING.md`), so no other commit of this story may use those types.

### Latest Technical Information

- No new library. React Router 8 (`react-router` `^8.0.0` in `web/package.json`; 8.5.1 installed at 966204f): `useLocation` and `matchPath` work under `BrowserRouter` and `MemoryRouter`. Checked against the installed version: `matchPath('/game-server/console', p)` matches `/game-server/console` and `/game-server/console/`, in any letter case (as `Routes` does), and not `/game-server/consolex` or `/game-server/console/x`.
- Tailwind v4: `lg` is `(width >= 64rem)`; `LG_UP_QUERY` is the same boundary in `min-width` form, so the sidebar's `auto` rule, the installed mods cards and the `lg:` classes switch at the same pixel. Both are in `rem`: browser zoom moves the boundary in device pixels, as for every other breakpoint.
- `useSyncExternalStore` gives the right value on the first client render, so a fresh browser at 900px never paints the expanded sidebar first.

### Project Structure Notes

- New: `web/src/lib/sidebar-preference.ts`, `web/src/lib/sidebar-preference.test.ts`, `web/src/components/layout/content-width.ts`, `web/src/components/layout/content-width.test.ts`, `_bmad-output/implementation-artifacts/21-8-browser/content_widths.mjs`, `content_widths.before.json`, `content_widths.after.json`.
- Deleted: `web/src/features/game-server/content-width.ts`, `web/src/features/game-server/content-width.test.ts`.
- Modified: `web/src/contexts/PreferencesContext.tsx`, `SidebarContext.tsx`, `web/src/components/layout/Layout.tsx`, `Sidebar.tsx`, `web/src/features/settings/UIPreferencesPanel.tsx`, `web/src/features/game-server/SettingsPage.tsx`, `GameConfigPanel.tsx`, their tests, `web/src/components/ModTable.test.tsx` (fixtures), `web/e2e/layout-widths.spec.ts`, `web/e2e/README.md`.
- Not touched: `api/`, `Justfile`, `scripts/`, `.github/`, `web/package.json`, `bun.lock`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.8: Sidebar Default and Content Width] (`:7112-7202`)
- [Source: _bmad-output/planning-artifacts/prd.md] FR284, FR285 (`:880-881`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md] facts (`:117-120`), ADR-14 (`:366-385`), ADR-15 (`:387-403`); ADR-13 decision 4 for Story 21.7's measurements
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] section 2 (cookie change `:94`, release-note subjects `:100`), risks (`:134-136`), answers 6 and 7 (`:1014-1015`), planning findings 12 to 14 (`:1042-1044`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-3] decision 1 (the application-wide maximum this story completes)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] responsive rules (`:1201-1218`), content width (`:1254-1258`)
- [Source: _bmad-output/implementation-artifacts/17-8-layout-at-tablet-and-phone-widths.md] (measurement method, E2E, follow-ups that became these beads)
- [Source: _bmad-output/implementation-artifacts/18-4-installed-mods-list-at-every-width.md] (column measurements `:105-113`, AC 6 `:40-42`, "Epic text against the code" `:237`)
- Beads: `VSS-w85`, `VSS-alx`, parent `VSS-syuj`; discovered from `VSS-dp1` and `VSS-143`
- `project-context.md`: commit message format, the stubbing rule for web unit tests, no suppressions, manual test tasks need the user's confirmation

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### UX notes: what the spec asked and what was built

### File List

## Change Log

- 2026-11-17: Story 21.8 created and validated (ready-for-dev). Validation against the create-story checklist, every cited path and line read at 966204f. Tasks 1, 2 and 4 were prototyped and the whole web suite run (14 failures in three files and 3 type errors, all listed; prototype discarded). Findings fixed in the story: with `auto`, the width rule alone would show the icon-only sidebar in every phone's sheet, so the rule, the sheet and the preferences control are one commit; `GameServerPage` has no route, so one console page is exempt, by a path list in the layout (route handles need a data router); the cap makes Story 18.4's 63-character name wrap at every width, so three E2E tests are rewritten and the PR says so; `openPage` must write the new key or the tablet "sidebar expanded" tests run collapsed and still pass; the collapsed toggle had no accessible name; the cookie is read as `unknown` with a guard instead of an assertion; expected widths computed for 1280 to 2560px in both sidebar states.
