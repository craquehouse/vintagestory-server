# Story 16.6: Settings Layout on Desktop

Status: in-progress

<!-- Implements FR173 per Epic 16 ADR-3. Bead: VSS-dfx. Stacks on Story 16.5 (branch story/16-5-installed-mods-on-phones, PR #152), itself on #151, #150, #149, #148. No new dependencies. VSS-7ed ('null' in empty settings, unmasked Password) is out of scope. -->

## Story

As an **administrator**,
I want **game server settings to use the width of a desktop screen**,
so that **I can see more settings without scrolling past half-empty cards**.

## Acceptance Criteria

1. **Given** a viewport at the Tailwind `xl` breakpoint (80rem, 1280px) or wider
   **When** I open Game Settings
   **Then** the settings panel is at most 1280px wide and centered (`max-w-[1280px] mx-auto`); Server Info spans the full panel width with its four text fields in two columns (Server Name | Description, Welcome Message | Password); below it are two independent column stacks, Player Settings then Network on the left and World Settings on the right, and no card stretches to match a neighbor's height
   *(Covers FR173; `VSS-dfx`; Epic 16 ADR-3)*

2. **Given** the two-column layout at `xl` or wider
   **When** I collapse or expand World Settings or Network
   **Then** only that card's own column changes: the cards in the other column keep their position and size

3. **Given** any viewport width
   **When** the number settings are shown (Max Players, Max Chunk Radius, Port)
   **Then** their inputs are at most 320px wide (`max-w-xs`), while text inputs fill the width of their card or column

4. **Given** a viewport narrower than `xl` (including 1024px and a 390px phone)
   **When** I open Game Settings
   **Then** the cards stack in one full-width column (Server Info, Player Settings, Network, World Settings), Server Info's fields are in one column, and the page does not scroll horizontally at 390px

5. **Given** the new layout
   **When** I use the settings
   **Then** editing behaves as before (auto-save on blur, validation messages, env-managed badges and disabled inputs, toasts), World Settings and Network are still collapsible by click and keyboard, the loading and error states are unchanged, and the other `SettingGroup` users (UI Preferences, API Settings) look and behave as before

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.6/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [x] Task 1: Number settings use a narrow input + tests (AC: 3, 5)
  - [x] 1.1: `SettingField`: the `Input` for `int` and `float` settings gets `max-w-xs` (merged with the existing error classes through `cn`); string inputs keep the `Input` default `w-full`; switches unchanged
  - [x] 1.2: Tests in `SettingField.test.tsx`: an `int` and a `float` input carry `max-w-xs`; a `string` input does not; the error classes still apply to a number input

- [ ] Task 2: `SettingGroup` accepts classes for its content + tests (AC: 1, 5)
  - [ ] 2.1: New optional `contentClassName` prop merged into `CardContent` (`cn('space-y-4', contentClassName)`); collapsible behavior, header and default markup unchanged
  - [ ] 2.2: Tests in `SettingGroup.test.tsx`: the class reaches the content element; without it the content keeps exactly `space-y-4`; the content is still hidden when collapsed

- [ ] Task 3: Two-column settings layout from `xl` + tests (AC: 1, 2, 4, 5)
  - [ ] 3.1: `GameConfigPanel`: inner wrapper `mx-auto max-w-[1280px] space-y-4` (`data-testid="game-config-layout"`); Server Info rendered with `contentClassName="xl:grid xl:grid-cols-2 xl:gap-4 xl:space-y-0"`; then `div.grid gap-4 xl:grid-cols-2 xl:items-start` (`game-config-columns`) holding `div.space-y-4` `game-config-column-left` (Player Settings, Network) and `game-config-column-right` (World Settings). The loading skeleton uses the same max width. `renderGroup` takes the optional content class; no other behavior changes. Update the doc comment
  - [ ] 3.2: Tests in `GameConfigPanel.test.tsx` ("Story 16.6: desktop layout" block): layout wrapper classes; Server Info outside the columns with the two-column content classes and its fields in DOM order Name, Description, Welcome, Password; left column contains Player Settings then Network, right column World Settings; columns container classes; collapsing World leaves Player and Network in the left column and their fields rendered, collapsing Network leaves World's fields rendered; Max Players and Port inputs carry `max-w-xs`, Server Name does not. Existing tests pass unchanged

- [ ] Task 4: Browser verification against the Docker dev stack + E2E spec (AC: 1-5)
  - [ ] 4.1: Before measurements: `16-6-browser/settings_layout.mjs` (adapted from `16-0-spike/settings_shots.mjs`; masks the server name and password) at 390, 1024, 1280, 1440 and 1920 on the pre-change build, output `settings_layout.before.json`
  - [ ] 4.2: `web/e2e/settings-desktop-layout.spec.ts`: at 1440x900 and 1920x1080 the panel is at most 1280px and centered in the content area; Server Info spans both columns and its fields sit in two columns; Player and Network share a left edge, World is to their right and starts at Player's top; collapsing World does not move or resize Player or Network, collapsing Network does not move or resize World; number inputs at most 320px wide, Server Name wider. At 1024x900 and 390x844 one column (all cards share a left edge and width) and no document overflow. Reads only; collapse is UI state
  - [ ] 4.3: `just docker restart` (rebuild from this branch); run the spec; rerun the measurement script for `settings_layout.after.json`; compare card boxes, input widths and page height before/after in the Dev Agent Record; browser console clean. Masked screenshots stay in the session scratchpad

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [ ] 5.1: `just check` passes
  - [ ] 5.2: Status review, `just sprint set 16-6-settings-layout-on-desktop review`, PR to `story/16-5-installed-mods-on-phones` (stacks on #152, #151, #150, #149, #148), PR link on `VSS-dfx`

## Dev Notes

### Today's behavior (measured on `story/16-5-installed-mods-on-phones` 014a3c8, Docker stack, Chromium; `16-6-browser/settings_layout.before.json`)

| Viewport | Panel | Card widths | Page height | Number/text input width |
|---|---|---|---|---|
| 390 | 326 | 326 | 1,952 | 276 |
| 1024 | 768 | 768 | 1,984 | 718 |
| 1280 | 1,024 | 1,024 | 1,984 | 974 |
| 1440 | 1,184 | 1,184 | 1,984 | 1,134 |
| 1920 | 1,664 | 1,664 | 1,984 | 1,614 |

- Card heights at every desktop width: Server Info 486, Player Settings 278, World Settings 518 (94 collapsed), Network 454 (94 collapsed). Today collapsing World moves Network up by 424px.
- Content area = viewport − 160px sidebar − 48px (`Layout` `md:p-6`) − 48px (`SettingsPage` `lg:p-6`): 1,024px at 1280 (ADR-3 estimated 1,072), so each `xl` column is 504px.
- `GameConfigPanel` renders four `SettingGroup`s in one `space-y-4` stack. `SettingField` renders `Input` (`w-full`) for strings and numbers and a `Switch` for booleans. Only `GameConfigPanel` passes `int`/`float` settings to `SettingField` (`ApiSettingsPanel` uses only `bool`), so the number width change is confined to game settings.

### Decisions

- **Tailwind responsive classes, no JS media query.** Every element is the same at every width; only classes change (`xl:grid-cols-2`, `xl:grid` on Server Info's content). Unlike Story 16.5 nothing is mounted twice, so CSS is enough and collapse state and unsaved input survive a resize. jsdom applies no Tailwind CSS: unit tests assert structure and class names, the E2E spec measures geometry.
- **Column stacks, as ADR-3 requires** ("two independent column stacks, not grid rows"): a two-column grid whose two items are stack wrappers. Collapsing a card only changes its own wrapper's height; `xl:items-start` keeps the shorter wrapper from stretching.
- **Order below `xl`: Server Info, Player Settings, Network, World Settings.** Stacks put Player and Network in one wrapper, so the DOM order is Player, Network, World. Keeping today's order (World before Network) in one column would need either CSS `order` with `display: contents` (visual order differs from focus and reading order, WCAG 2.4.3) or a JS media query that remounts the cards at 1280px (loses collapse state and unsaved typing). One DOM order at every width, matching the desktop reading order, is chosen; ADR-3 and the epic ask for a single column below `xl`, not a specific order. Recorded for review.
- **Server Info fields in two columns** through `SettingGroup`'s new `contentClassName` (grid at `xl`, `xl:space-y-0` to drop the stack margins), keeping row-wise DOM order Name, Description, Welcome, Password.
- **Narrow numbers in `SettingField`** (ADR-3 consequence: "SettingField sizing for numbers"), at every width.
- **Page header unchanged.** The 1280px limit is on the panel (ADR-3 decision 1); the title row and status badge keep the full width. The app-wide maximum is out of scope.

### Layout at `xl` (1280px viewport: 1,024px panel; 1920px: 1,280px panel, centered)

```text
┌──────────────────── Server Info (full width) ───────────────────────┐
│ Server Name              │ Description                              │
│ Welcome Message          │ Password                                 │
└─────────────────────────────────────────────────────────────────────┘
┌──────── Player Settings ────────┐ ┌──────── World Settings ▾ ────────┐
└─────────────────────────────────┘ │                                  │
┌──────── Network ▾ ──────────────┐ └──────────────────────────────────┘
└─────────────────────────────────┘
```

### Out of scope

- `VSS-7ed` (empty settings show `null`, Password unmasked), the app-wide maximum width, other settings pages, any other Epic 16 story.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-web <file>` after each task; `just check` before review.

- Vitest/jsdom applies no Tailwind CSS: assert class names and DOM containment. The `matchMedia` stand-in from Story 16.5 (`web/tests/viewport.ts`) is not needed (no media query in JS).
- `GameConfigPanel.test.tsx` mocks `fetch` and `sonner`; reuse its `mockGameConfig` and wrapper.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7). Never change setting values in `./data`; collapsing groups is UI-only. Committed screenshots (none planned) must mask `header span.font-semibold`, `#ServerName` and `#Password`. Check the browser console.

### Security Requirements

- UI-only; no API or data changes. The measurement script and screenshots mask the server name and password.

### Development Commands

- `just test-web src/components/SettingField.test.tsx`, `just test-web src/components/SettingGroup.test.tsx`, `just test-web src/features/game-server/GameConfigPanel.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/settings-desktop-layout.spec.ts`, `cd web && bun ../_bmad-output/implementation-artifacts/16-6-browser/settings_layout.mjs`.

### Previous Story Intelligence

- **16.5:** E2E specs set `localStorage.apiKey` with an init script (`VS_API_KEY_ADMIN`, default `changeme`); a first run seconds after `just docker restart` can fail while the server starts, rerun once healthy. `just lint-web` is `tsc --noEmit`. Commit types by user impact.
- **16.0:** `settings_shots.mjs` measures cards through `:scope > div > *`, which the new structure breaks; the 16.6 script selects `[data-slot="card"]`.
- **11.3 / 6.4:** `SettingsPage` wraps `GameConfigPanel` with the header and empty state; `SettingGroup`/`SettingField` are shared with the app Settings page.

### Git Intelligence

- Branch `story/16-6-settings-layout-on-desktop` from `origin/story/16-5-installed-mods-on-phones` (014a3c8). The three settings components have not changed since `b99e4cc` (semantic colors). Planned types: Task 1 `fix` (number boxes stretched across the screen), Task 2 `refactor`, Task 3 `feat`, Task 4 `test`, Task 5 `chore`.

### Latest Technical Information

- No new libraries. Tailwind v4: `xl` = `80rem`; `max-w-xs` = `20rem` (320px); `space-y-*` sets margins on children, so it is reset with `xl:space-y-0` where the content becomes a grid; `cn` (tailwind-merge) resolves conflicting classes.

### Project Structure Notes

- New: `web/e2e/settings-desktop-layout.spec.ts`, `_bmad-output/implementation-artifacts/16-6-browser/` (script, before/after JSON).
- Modified: `web/src/components/SettingField.tsx` (+ test), `web/src/components/SettingGroup.tsx` (+ test), `web/src/features/game-server/GameConfigPanel.tsx` (+ test).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.6: Settings Layout on Desktop]
- [Source: _bmad-output/planning-artifacts/prd.md] FR173
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-3: Game Server Settings Layout on Desktop]
- [Source: _bmad-output/implementation-artifacts/16-0-spike/settings_shots.out.json]
- [Source: _bmad-output/implementation-artifacts/16-5-installed-mods-on-phones.md]
- Beads: `VSS-dfx` (this story), parent `VSS-stm`; out of scope `VSS-7ed`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run, 3 of the 4 new width tests failed (the text-input test already passed); then 30 passed; `tsc` clean.

### Completion Notes List

- Task 1: `SettingField` gives `int`/`float` inputs `max-w-xs` (320px) at every width, merged with the error classes; text inputs keep `w-full`. Only game settings pass number types.

### File List

- `web/src/components/SettingField.tsx`
- `web/src/components/SettingField.test.tsx`
- `_bmad-output/implementation-artifacts/16-6-settings-layout-on-desktop.md`
- `_bmad-output/implementation-artifacts/16-6-browser/settings_layout.mjs` (new)
- `_bmad-output/implementation-artifacts/16-6-browser/settings_layout.before.json` (new)

## Change Log

- 2026-11-13: Story 16.6 created (ready-for-dev). Ultimate context engine analysis completed - comprehensive developer guide created.
