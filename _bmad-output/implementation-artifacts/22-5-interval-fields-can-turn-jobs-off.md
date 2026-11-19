# Story 22.5: Interval Fields Can Turn Jobs Off

Status: ready-for-dev

<!-- Implements FR300-FR303, Epic 22 ADR-11 and ADR-12 (ADR-14 decision 3 for the dev stack rule). Bead: VSS-9jv (UI-085), closes here; parent VSS-oole. Maintainer answer 10 (Matt, 2026-11-18): an On switch per interval, refresh fields 60 s to 365 days, Metrics Collection 1 s to 1 h with default 10 s. ADR-11 decisions 4 and 5 and all of ADR-12 are the planner's and not reviewed yet (ADR-12 was told to the maintainer with question 11 and not objected to). Order: 22.1, 22.2, 22.3, 22.4, 22.7, 22.8, 22.5, 22.6. This branch, story/22-5-interval-fields-can-turn-jobs-off, is stacked on story/22-8-container-stop-saves-the-world (22.8 in review) at 39068328; main is e16a7932 and none of Epic 22 is merged yet. The PR targets main and merges after 22.8's. Line references were verified at 39068328; the settings files cited (ApiSettingsPanel.tsx, SettingsPage.tsx, DurationSettingField.tsx, SettingField.tsx, SettingGroup.tsx, use-api-settings.ts, config.ts, and their tests) are unchanged since e16a7932, where ADR-11's facts were checked. Re-check every cited line before editing. Web, one API test and E2E: no API source change, no new route, no response change, no new dependency. Story 22.6 comes next and edits the same ApiSettingsPanel.tsx, its test and config.ts. -->

## Story

As an **administrator**,
I want **to turn each background job off and on, and set how often metrics are collected, from the API Settings tab**,
so that **I do not have to call the API by hand for what the API already allows**.

## Acceptance Criteria

1. **Given** the API Settings tab with Mod List Refresh at 4h
   **When** I turn its On switch off
   **Then** 0 is saved (`POST /api/v1alpha1/config/api/settings/mod_list_refresh_interval` with `{"value": 0}`), the duration input is replaced by "Off", one success toast is shown, and the job (`mod_cache_refresh`) is no longer listed in Scheduled Jobs
   *(FR300; ADR-11 decision 1)*

2. **Given** Mod List Refresh is off (saved 0)
   **When** I load the tab, and then turn the switch on
   **Then** it shows Off on load (switch unchecked, no duration input), and turning it on saves 14400 and shows the duration input with 4h
   *(FR300; ADR-11 decisions 1 and 4)*

3. **Given** the API Settings tab
   **When** I look at Refresh Intervals
   **Then** there is a Metrics Collection field with an On switch, accepting 1 second to 1 hour, defaulting to 10 seconds (turning it on saves 10), whose help text says that when it is off the dashboard's charts and its memory and players cards stop updating, and that `/metrics` is read live and keeps working
   *(FR301; ADR-11 decisions 2 and 3; refined, see "ADR against the code" 2)*

4. **Given** Mod List Refresh or Server Versions Refresh
   **When** I enter 30s, 2d or 400d
   **Then** 30s ("Must be at least 1m") and 400d ("Must be at most 365d") are refused with the field's bounds message and nothing is saved, and 2d is saved (the bounds are 60 seconds to 31,536,000 seconds, 365 days); typing 0 is refused too: only the switch turns a job off
   *(FR302; ADR-11 decision 2)*

5. **Given** the settings have not loaded a value for Server Versions Refresh, Enforce Env on Restart (or any other scalar setting the tab shows)
   **When** the fields render
   **Then** they show the API's defaults (Server Versions Refresh 1d, Enforce Env on Restart off, Mod List Refresh 4h, Metrics Collection 10s, Auto-Start off, Block Env-Managed on), all taken from one web constant, `API_SETTING_DEFAULTS` in `web/src/api/config.ts`, which an API test pins to `ApiSettings`' defaults
   *(FR302; ADR-11 decision 4; refined, see "ADR against the code" 5)*

6. **Given** a switch save that fails, or that answers 500 `API_SETTING_NOT_APPLIED`
   **When** I use a switch
   **Then** exactly one toast is shown, as for the duration input ("Update failed" with the message, or the warning "Saved, not applied yet"), the field shows the error message, and the switch shows the saved value: back where it was after a failure, and following the value the settings refetch returns after `API_SETTING_NOT_APPLIED` (which saved it)
   *(FR300; ADR-11 decision 6)*

7. **Given** a Monitor key
   **When** I open Settings (`/config`, also `/config?tab=api-settings`)
   **Then** the API Settings tab and its panel are not shown, UI Preferences is the selected tab, no request is made to `GET /api/v1alpha1/config/api` and "Failed to load settings" never appears; with an Admin key the tab is shown as before (once the role has loaded, like Scheduled Jobs)
   *(FR303; ADR-12; refined, see "ADR against the code" 1)*

8. **Given** a phone or tablet width (below 1024px)
   **When** I use an interval field's switch
   **Then** its tap target (the switch with its "On" text) is at least 44px tall, the switch's accessible name is "<field label> On" (for example "Mod List Refresh On"), it is described by the field's help text (`aria-describedby`, the error instead while one is shown), and nothing scrolls sideways at 390px
   *(Epic 21 ADR-12 decision 1 pattern; accessibility)*

9. **Given** fields without the switch (any `DurationSettingField` given no `offValue`/`onValue`)
   **When** they render and save
   **Then** they behave as before, except that a new `value` prop is now shown when the field is not being edited or saved (it was not, see "ADR against the code" 3)
   *(ADR-11 decision 5)*

10. **Given** the story's commits
    **When** `just check` runs
    **Then** it passes with 0 skipped web tests, and the branch has exactly three release-note commits: `fix: allow refresh intervals up to 365 days, as the API does`, `feat: turn scheduled jobs off and on, and set metrics collection, in API Settings`, `fix: hide the API Settings tab from read-only keys` (the change proposal's draft, section 2)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first (Vitest + Testing Library). Commit per task: type(story-22.5/task-N): ... ; feat/fix only for what an admin notices, subject written for admins. Exactly three release notes: Tasks 2, 3 and 4. No .skip/.only in unit tests; a precondition skip inside an E2E test body is allowed. E2E runs only through `just test-e2e-ci` (throwaway container on 127.0.0.1:18080); never write to the dev stack at http://localhost:9080. -->

- [ ] Task 1: The optional On switch in `DurationSettingField` + tests (AC: 6, 8, 9)
  - [ ] 1.1: `web/src/components/DurationSettingField.tsx`: the `offValue`/`onValue` pair as Dev Notes "The switch in `DurationSettingField`" describes (props as a both-or-neither union; the switch in the label row inside a 44px-below-`lg` label with the text "On"; "Off" in place of the input; optimistic toggle, disabled while pending or env-managed, reverted on failure with the error shown; no range check for the two values). Header comment: add `Story 22.5: optional On switch (offValue/onValue)`
  - [ ] 1.2: Same file: the field follows a new `value` prop while it is neither being edited nor saving: `currentSeconds`, `initialRef` and `inputText` all take it (`:111-117` sets only `inputText`, which is not displayed outside editing, `:231`). This is what makes the switch show the saved value after a refetch (AC 6)
  - [ ] 1.3: Tests in `web/src/components/DurationSettingField.test.tsx` (Dev Notes "Web tests", Task 1 rows), written first and seen failing. The existing tests stay green unchanged (AC 9)
  - [ ] 1.4: `just test-web src/components/DurationSettingField.test.tsx`, `just typecheck`, `just format-web` then `just lint-web`. Commit `refactor(story-22.5/task-1): let a duration setting field turn its setting off and on` (no field uses the pair yet; the body names the value-follow change of 1.2 and that only the API Settings tab uses this component)

- [ ] Task 2: Refresh bounds and fallbacks from one constant of API defaults + tests (AC: 4, 5, 10)
  - [ ] 2.1: `web/src/api/config.ts`, next to `INTERVAL_API_SETTINGS` (`:76-86`): `MAX_INTERVAL_SECONDS = 31_536_000` and `API_SETTING_DEFAULTS` (Dev Notes "The defaults constant"), each with a doc comment naming its API source and the pinning test. In the same block fix the stale comment at `:79-80`: `INTERVAL_SETTINGS` is now `SCHEDULED_SETTINGS` (`api/src/vintagestory_api/services/api_settings.py:176-190`; renamed by Story 22.3, which left this comment as a drawdown)
  - [ ] 2.2: `web/src/features/settings/ApiSettingsPanel.tsx`: every `??` fallback reads `API_SETTING_DEFAULTS` (`:122`, `:137`, `:145` which becomes false, `:161`, `:172` which becomes 86400); both refresh fields get `max={MAX_INTERVAL_SECONDS}` (`:163` was 86400, `:174` was 604800); `min={60}` stays. Header comment: `Story 22.5: bounds and defaults match the API`
  - [ ] 2.3: New API test (Dev Notes "Pinning the defaults to the API"): `api/tests/test_api_settings.py`, class `TestWebDefaults`, reads `web/src/api/config.ts` and asserts `API_SETTING_DEFAULTS` and `MAX_INTERVAL_SECONDS` equal `ApiSettings()` and `api_settings.MAX_INTERVAL_SECONDS`. Seen failing first (for example with a wrong value), then green
  - [ ] 2.4: Web tests (Dev Notes "Web tests", Task 2 rows) and the Task 2 entries of "Existing tests that change", red first
  - [ ] 2.5: `just test-web src/features/settings/ApiSettingsPanel.test.tsx src/api/config.test.ts`, `just test-api tests/test_api_settings.py`, `just typecheck`, `just format-web`, `just lint`. Commit `fix(story-22.5/task-2): allow refresh intervals up to 365 days, as the API does` (body: Mod List Refresh was capped at 1 day and Server Versions Refresh at 7 days, the API allows 365 days; the tab's fallbacks now equal the API's defaults, so Enforce Env on Restart and Server Versions Refresh no longer show a value the API does not use when a setting is missing)

- [ ] Task 3: The switches on the three interval fields and the Metrics Collection field + tests (AC: 1, 2, 3, 6, 8, 10)
  - [ ] 3.1: `web/src/api/types.ts` `ApiSettingsData.settings` (`:304-314`): add `metricsCollectionInterval: number` (the API already returns it: `ApiSettings.redacted()`, `api_settings.py:166-170`). Do not add `scheduledRestartTimes` or `backupKeepCount`: Story 22.6 does (ADR-13 decision 4)
  - [ ] 3.2: `ApiSettingsPanel.tsx`: `offValue={0}` and `onValue={API_SETTING_DEFAULTS.<key>}` on Mod List Refresh and Server Versions Refresh; a third `DurationSettingField` after them, `settingKey="metrics_collection_interval"`, `label="Metrics Collection"`, `value={settings?.metricsCollectionInterval ?? API_SETTING_DEFAULTS.metrics_collection_interval}`, `min={1}`, `max={3600}`, the same `minMessage`/`maxMessage`, `offValue={0}`, `onValue={API_SETTING_DEFAULTS.metrics_collection_interval}`, `onSave={handleSave}` and the help text of Dev Notes "Metrics Collection's help text". The switches save through the same `handleSave` (`:48-63`), never a `mutate(..., { onError })` of their own (Dev Notes "One toast"). Header comment: `Story 22.5: interval jobs can be turned off; Metrics Collection field`
  - [ ] 3.3: Tests (Dev Notes "Web tests", Task 3 rows), red first; add `metricsCollectionInterval: 10` to the settings fixtures of `ApiSettingsPanel.test.tsx` (`:44-56`) and `SettingsPage.test.tsx` (`:51-62`)
  - [ ] 3.4: `just test-web`, `just typecheck`, `just format-web`, `just lint-web`. Commit `feat(story-22.5/task-3): turn scheduled jobs off and on, and set metrics collection, in API Settings` (body: each interval in Settings > API Settings > Refresh Intervals has an On switch; off saves 0 and stops the job, on saves the API's default; Metrics Collection is new, 1 second to 1 hour, default 10 seconds; with it off the dashboard's charts and memory and players cards stop updating, `/metrics` keeps working)

- [ ] Task 4: Hide the API Settings tab from a Monitor key + tests (AC: 7, 10)
  - [ ] 4.1: `web/src/features/settings/SettingsPage.tsx`: render the API Settings trigger (`:51-54`) and its `TabsContent` (`:71-73`) only when `isAdmin` (`:35-36`), exactly as Scheduled Jobs (`:59-64`, `:79-83`). Header and component comments (`:6`, `:30`): "API Settings: ... (Admin only)"; add `Story 22.5: API Settings is Admin only (Epic 22 ADR-12)`. No deep link, no stored tab, no controlled `Tabs` (Dev Notes "ADR against the code" 1)
  - [ ] 4.2: Tests (Dev Notes "Web tests", Task 4 rows) and the Task 4 entries of "Existing tests that change", red first
  - [ ] 4.3: `just test-web src/features/settings/SettingsPage.test.tsx`, `just typecheck`, `just format-web`, `just lint-web`. Commit `fix(story-22.5/task-4): hide the API Settings tab from read-only keys` (body: a Monitor key saw the tab and got "Failed to load settings", since only an Admin key can read the API settings; it now sees UI Preferences and File Manager)

- [ ] Task 5: E2E for the switch, the bounds, the Metrics Collection field and both roles + tests (AC: 1, 2, 3, 4, 7, 8)
  - [ ] 5.1: `web/e2e/settings-as-saved.spec.ts`: the tests of Dev Notes "E2E" (E1 inside the existing serial describe, whose snapshot and restore of `mod_list_refresh_interval` guard it; E2 to E4 as a new describe "API Settings tab (Story 22.5)"). Update the spec's header comment (`:4-22`) with this story's lines, the snapshot residue and the Monitor precondition. The base URL stays the config's default (`http://localhost:9080`, `web/playwright.config.ts:28`); `just test-e2e-ci` overrides it
  - [ ] 5.2: `web/e2e/README.md`: recount (`cd web && bunx playwright test --list | tail -1`, and with `--grep-invert "@moddb|@moddb-live|@install|@game-server"`) and update every count it states (`:10`, `:15`, `:50`; at 39068328: 250 tests, 246 in CI, 219 untagged, 27 `@moddb`)
  - [ ] 5.3: `just test-e2e-ci e2e/settings-as-saved.spec.ts` passes (throwaway container, Monitor key set, so no test is skipped there). Never against the dev stack
  - [ ] 5.4: Commit `test(story-22.5/task-5): check the interval switches, the bounds and the API Settings tab for each role`

- [ ] Task 6: Quality gate, review hand-off and the maintainer's check (AC: all)
  - [ ] 6.1: `just check` passes (lint, typecheck with the E2E project, all API and web tests) with 0 skipped web tests; `just test-e2e-ci` (both passes) passes. `git status --short` shows nothing under `dev/`. The diff has no `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `nosemgrep`, `.skip`/`.only` in unit tests, and no new `as` type assertion (`as const` is not one)
  - [ ] 6.2: `git log --oneline 39068328..HEAD` shows exactly three `feat`/`fix`/`perf` subjects, those of AC 10; `just changelog` shows the `feat` under Features and the two `fix` under Bug Fixes and nothing else from this story
  - [ ] 6.3: Complete the Dev Agent Record: every completion note checked against the code as committed, the File List, the test counts
  - [ ] 6.4: `just sprint set 22-5-interval-fields-can-turn-jobs-off review`; story Status `review`. Commit `chore(story-22.5/task-6): validate and move story 22.5 to review`. Do not push or open the PR unless the maintainer says so; report `git status` and the proposed commands
  - [ ] 6.5: Maintainer's manual check (maintainer only; leave unticked until he confirms; no agent writes to the dev stack): on the dev stack rebuilt from the branch (`just docker restart`, `http://localhost:9080`), first save a snapshot (`curl -s -H "X-API-Key: <admin key>" http://localhost:9080/api/v1alpha1/config/api > /tmp/api-settings-before.json`); in the browser turn Mod List Refresh off (Off shown, one toast, `mod_cache_refresh` gone from Scheduled Jobs), reload (still Off), turn it on (4h, the job back); look at Metrics Collection's help text and at a phone width; open Settings with the Monitor key (no API Settings tab). Then restore every setting exactly as before from the snapshot (turning a job on saves the API default, not the earlier value) and compare a fresh `GET` with the snapshot: identical. The game server is neither started nor stopped
  - [ ] 6.6: After the merge, as the maintainer directs: AAR comment on `VSS-9jv` (abbreviated format, small story), `bd close VSS-9jv`, `bd sync`

## Dev Notes

### The state today (verified at 39068328)

- `ApiSettingsPanel.tsx`: Mod List Refresh `value={settings?.modListRefreshInterval ?? 14400}`, `min={60}`, `max={86400}` (`:158-168`); Server Versions Refresh `?? 3600`, `max={604800}` (`:169-179`); Enforce Env on Restart `?? true` (`:142-149`); Auto-Start `?? false` (`:122`), Block Env-Managed `?? true` (`:137`). No Metrics Collection field. Saves go through `handleSave` (`:48-63`): `mutateAsync`, then `toast.success(`${key} updated`)`; on `API_SETTING_NOT_APPLIED` `toast.warning('Saved, not applied yet', { description })`; otherwise `toast.error('Update failed', { description })`; it rethrows in both error cases.
- API (`api/src/vintagestory_api/services/api_settings.py`): `MAX_INTERVAL_SECONDS = 31_536_000` (`:29`); defaults `auto_start_server` False (`:64-67`), `block_env_managed_settings` True (`:68-71`), `enforce_env_on_restart` False (`:72-75`), `mod_list_refresh_interval` 14400 (`:76-84`), `server_versions_refresh_interval` 86400 (`:85-92`), `metrics_collection_interval` 10 (`:93-98`), each interval `ge=0`, `le=MAX_INTERVAL_SECONDS`. `GET /config/api` returns `redacted()` (`:166-170`; `routers/config.py:280-306`), so `metrics_collection_interval` is already in the response; `GET` and `POST` are Admin only (`routers/config.py:282`, `:324`). Saving 0 removes the job at once (`jobs/__init__.py:99-103`, `apply_interval_setting`); a value above 0 adds it with its next run one interval later.
- `web/src/api/types.ts:304-314` `ApiSettingsData.settings` has no `metricsCollectionInterval`. The client turns keys to camelCase (`web/src/api/client.ts`), so it arrives as `metricsCollectionInterval`.
- `use-api-settings.ts`: `useUpdateApiSetting` (`:83-131`) is optimistic (`onMutate` writes the camelCase key into the cached settings, `:89-114`), rolls back in its own `onError` (`:115-120`) and invalidates `config.api` and, for `INTERVAL_API_SETTINGS`, `jobs.all` in `onSettled` (`:121-129`), so Scheduled Jobs shows a removed or added job at once (Story 17.6). Its only caller is `ApiSettingsPanel.tsx:43`.
- `DurationSettingField.tsx`: label row (`:236-250`), `Input` with `aria-describedby` error-or-description and `aria-invalid` (`:253-268`), description (`:271-275`), error with `role="alert"` (`:278-282`). Range check `validateRange` (`:133-146`) with `minMessage`/`maxMessage` placeholders. `save` (`:177-214`) does nothing when the value is unchanged (`:195-198`), sets the error from a thrown error (`:207-209`). The external-value effect (`:111-117`) updates `initialRef` and `inputText` only; outside editing the input shows `formatDurationSimple(currentSeconds)` (`:231`), so a new `value` prop is never displayed (no test covers that case; `DurationSettingField.test.tsx:537-556` covers only "while editing"). Only `ApiSettingsPanel` uses this component.
- `SettingField.tsx` boolean switches: optimistic `setValue` then `save`, `revertOnError: type === 'bool'` (`:126-136`, `:192-200`), state text with `aria-describedby="<key>-state <key>-desc"` (`:202-214`). It is the model for the new switch's optimistic behaviour and revert, not a component to reuse (it saves booleans).
- `ui/switch.tsx`: Radix `Switch`, `h-[1.15rem] w-8` (`:11`): 18px tall at every width. `SettingGroup.tsx`: `CardContent` is `space-y-4` (`:126`); the Refresh Intervals group is `collapsible` (`ApiSettingsPanel.tsx:156`).
- `SettingsPage.tsx`: `isAdmin = auth?.data?.role === 'admin'` from `useAuthMe()` (`:35-36`; `api/hooks/use-auth-me.ts`, `staleTime: Infinity`); uncontrolled `Tabs defaultValue="ui-preferences"` (`:44`); API Settings trigger and content for every role (`:51-54`, `:71-73`); Scheduled Jobs only for Admin (`:59-64`, `:79-83`). Route `/config` (`App.tsx:140`), no search parameter or stored tab anywhere (`grep -rn "useSearchParams" web/src` finds only the mod browser).
- Duration format: `formatDurationSimple` (`lib/duration-utils.ts:219-248`) gives `10s`, `1m`, `1h`, `4h`, `1d`, `365d`; `parseDuration` reads a plain number as seconds, so `0` parses to 0.

### ADR against the code

1. **There is no link to a tab and no stored tab (ADR-12 "a deep link or stored tab value of `api-settings` falls back"; epic AC "or a link to its API Settings tab").** `SettingsPage` is an uncontrolled `Tabs` with `defaultValue="ui-preferences"` (`SettingsPage.tsx:44`); `/config` reads no search parameter or hash, and no preference stores a tab. So for a Monitor key the fallback holds by construction: without the trigger and the content, UI Preferences is the only place to land. The story adds no deep link and no stored tab (that would be new scope). The unit tests pin that a Monitor never renders the trigger or the panel and never requests `/config/api`; the E2E also opens `/config?tab=api-settings` as a guard, so a tab parameter added later must keep the rule.
2. **Metrics Collection off freezes more than the charts (ADR-11 decision 3 names "the dashboard charts").** The Memory card and the Players card read `GET /metrics/current` (`MemoryCard.tsx:22`, `PlayersCard.tsx:36`, `useCurrentMetrics`), which returns the latest snapshot in the ring buffer (`routers/metrics.py:60-73`) that only the collection job fills. With collection off they keep showing the last collected values. The help text says so (AC 3). `/metrics` (Story 22.2) reads live (ADR-3 decision 4) and is unaffected.
3. **A new `value` is not displayed (needed by ADR-11 decision 1, "the saved value decides the switch").** See "The state today". After `API_SETTING_NOT_APPLIED` the value is saved but the save threw; only the refetch can show it. Task 1 makes the field follow the prop while it is neither editing nor saving. In the tab today this shows only when the 60-second poll or a save's refetch brings a different value (for example one saved with `curl`); it is part of Task 1's `refactor` commit, with no release note of its own (open question 1).
4. **The web type lacks `metricsCollectionInterval` (ADR-11 decision 2 needs it).** Added in Task 3; the API already sends it.
5. **One constant for all six scalar defaults, not only the two that differ (ADR-11 decision 4 names `serverVersionsRefreshInterval` and `enforceEnvOnRestart`).** Every fallback of the tab reads `API_SETTING_DEFAULTS`, so there is one source to pin. The pin is an API test that reads `config.ts`, not a web test that parses Python: the API's `ApiSettings()` is the source of truth and the test compares with its real defaults (Dev Notes "Pinning the defaults to the API").
6. **Task split (epic tasks 2 and 3).** The epic puts the switches, bounds and fallbacks in one `feat` commit and the Metrics Collection field in the next. The change proposal's draft release notes (section 2, `sprint-change-proposal-2026-11-18-epic-22.md:100-101`) list `fix(web): allow refresh intervals up to 365 days, as the API does` and `feat(web): turn scheduled jobs off and on, and set metrics collection, in API Settings`. The tasks follow the drafts: Task 2 is the bounds fix (with the fallbacks, which an admin cannot see when the API answers normally), Task 3 the switches with the new field. Six tasks, three release notes (AC 10). The scope `(web)` in the drafts is the release-note wording; the commits use the project's `(story-22.5/task-N)` scope, which git-cliff removes.
7. **`config.ts:79-80` names `INTERVAL_SETTINGS`,** which Story 22.3 renamed `SCHEDULED_SETTINGS` (`api_settings.py:176-190`) and left as a drawdown for Story 22.6 (`22-3-scheduled-restarts.md:100`, `:616`). Task 2 edits that block, so it fixes the comment.
8. **The switch's name is "<label> On", not "On" (ADR-11 decision 1 "a switch labelled 'On'").** Three switches named "On" could not be told apart by a screen reader or a test. The visible text stays "On" and is contained in the name (WCAG 2.5.3). `getByLabelText('Mod List Refresh')` and Playwright's `getByLabel('Mod List Refresh', { exact: true })` (`settings-as-saved.spec.ts:191`) still find only the input.
9. **The Admin tab appears once the role has loaded.** With `isAdmin` the API Settings trigger is absent while `/auth/me` loads or if it fails, as Scheduled Jobs already is. ADR-12 says "as it already does for Scheduled Jobs", so this is accepted; `layout-widths.spec.ts` waits for `scheduled-jobs-tab` before it uses the four tabs (`:627-629`, `:648-649`), so it is not affected.
10. **The epic's E2E task said "the Monitor check with a precondition skip".** In `just test-e2e-ci` a Monitor key is set (`scripts/e2e-ci.sh:26`, `:101`, `:139`), so the test runs there; the skip only applies to a stack without one.

### The switch in `DurationSettingField` (Task 1)

Props (keep the existing ones; the type becomes a both-or-neither union so a caller cannot pass one of the two):

```ts
interface DurationSettingFieldBaseProps { /* the existing props, unchanged */ }

/** Story 22.5: an On switch; both values or neither (Epic 22 ADR-11 decision 5) */
type OnOffProps =
  | {
      /** Saved when the switch is turned off (0: the job is not registered) */
      offValue: number;
      /** Saved when the switch is turned on (the API's default for the setting) */
      onValue: number;
    }
  | { offValue?: undefined; onValue?: undefined };

export type DurationSettingFieldProps = DurationSettingFieldBaseProps & OnOffProps;
```

Behaviour with the pair:

- **State:** one source, `currentSeconds`. `isOn = currentSeconds !== offValue`. Without the pair nothing below applies and the render is today's.
- **Label row** (`:236-250`): the field label, then the switch and its "On" text in one `<label>` that is the tap target: `className="inline-flex items-center gap-2 cursor-pointer max-lg:min-h-11"` (the project's 44px-below-`lg` pattern, Epic 21 ADR-12 decision 1; `ui/tabs.tsx:34` uses `max-lg:min-h-11`), then the env badge and the spinner as today. The field label's `htmlFor` points at the input only while the input is shown (no dangling `for` when off).
- **The switch:** `<Switch id={`${settingKey}-enabled`} checked={isOn} aria-label={`${label} On`} aria-describedby={error ? `${settingKey}-error` : description ? `${settingKey}-desc` : undefined} disabled={isDisabled} data-testid={`${settingKey}-switch`} onCheckedChange={handleToggle} />`. If clicking the switch inside the wrapping label toggles it twice in jsdom or a browser, use a sibling `<label htmlFor={`${settingKey}-enabled`}>On</label>` and put the min height on a wrapper of both; the unit test "one click, one save" decides.
- **Off:** in place of the `Input`, `<p data-testid={`${settingKey}-off`} className="text-sm text-muted-foreground">Off</p>`; description and error stay below as today.
- **Toggle:** `handleToggle(checked)`: return if `isDisabled`; `next = checked ? onValue : offValue`; remember `previous = currentSeconds`; `setError(null)`, `setIsEditing(false)`, `setCurrentSeconds(next)` (the switch moves at once, as `SettingField`'s switches do), `setIsPending(true)`; `await onSave({ key: settingKey, value: next })`; on success `initialRef.current = next` and `setInputText(formatDurationSimple(next))`; on failure `setCurrentSeconds(previous)` and `setError(message)` (the same message rule as `:207-209`); finally `setIsPending(false)`. `offValue` and `onValue` are not range-checked: `min` and `max` apply to typed input only, so typing `0` is refused with the min message (AC 4) and only the switch saves 0.
- **Following the prop (1.2, all fields):** the effect at `:111-117` becomes: when `value` changes and the field is neither editing nor pending, set `initialRef.current`, `currentSeconds` and `inputText` from it. While pending, the hook's optimistic write and its rollback change the prop; the field ignores both and settles from its own result; the `onSettled` refetch then brings the saved value, which the field shows. That is how the switch ends Off after `API_SETTING_NOT_APPLIED` on turning off (the hook rolls the cache back to 14400, the save threw so the field reverts to on, the refetch returns 0, the field shows Off).

### The defaults constant (Task 2, `web/src/api/config.ts`)

```ts
/**
 * The API's maximum for an interval setting: 365 days (`MAX_INTERVAL_SECONDS` in
 * `api/src/vintagestory_api/services/api_settings.py`; pinned by `TestWebDefaults` in
 * `api/tests/test_api_settings.py`).
 */
export const MAX_INTERVAL_SECONDS = 31_536_000;

/**
 * The API's default for each setting the API Settings tab shows (Story 22.5, Epic 22
 * ADR-11 decision 4): the tab's fallback when a value is missing, and the value an
 * interval's On switch saves. Keys are the API's setting keys. Keep each value a plain
 * literal on its own line: `TestWebDefaults` in `api/tests/test_api_settings.py` reads
 * this block and compares it with `ApiSettings()`.
 */
export const API_SETTING_DEFAULTS = {
  auto_start_server: false,
  block_env_managed_settings: true,
  enforce_env_on_restart: false,
  mod_list_refresh_interval: 14400,
  server_versions_refresh_interval: 86400,
  metrics_collection_interval: 10,
} as const;
```

Story 22.6 adds `backup_keep_count` to it when it adds that field (and the pinning test then covers it).

### Pinning the defaults to the API (Task 2, `api/tests/test_api_settings.py`)

A new class `TestWebDefaults` (pyright strict; no suppressions):

- `WEB_CONFIG = Path(__file__).resolve().parents[2] / "web" / "src" / "api" / "config.ts"` (tests -> api -> repository root).
- Extract the block between `export const API_SETTING_DEFAULTS = {` and the next `}`; every non-empty line in it must match `^\s*([a-z_]+): (true|false|\d[\d_]*),$` (fail with the line otherwise, so a computed value such as `4 * 3600` is refused rather than skipped). Convert `true`/`false` to bool and digits (underscores removed) to int.
- Assert the keys are exactly the six above, each is a field of `ApiSettings`, and each value equals `getattr(ApiSettings(), key)` with the same Python type (`bool` is not compared as `int`).
- Assert `export const MAX_INTERVAL_SECONDS = 31_536_000;` parses to `api_settings.MAX_INTERVAL_SECONDS`.
- A failure message names the web file and the key. If the block is not found the test fails (never skips).

The web side's own check of the constant (Task 2 rows) is that the panel's fallbacks use it; the values themselves are pinned only here.

### Metrics Collection's help text (Task 3)

`How often the dashboard's metrics are collected. When off, the dashboard's charts and its memory and players cards stop updating; /metrics is read live and keeps working.`

Tests match it by the two facts (`/charts and its memory and players cards stop updating/`, `/\/metrics is read live and keeps working/`), not the whole sentence.

### One toast (AC 6; project-context.md "Mutation errors")

`useUpdateApiSetting`'s own `onError` (`use-api-settings.ts:115-120`) replaces the query client's default toast (`api/query-client.ts:34-39`) and only rolls back; the panel's `handleSave` shows the one toast (success, warning or error) and rethrows, so the field can show the message. The switch must call the same `onSave` (`handleSave`) and nothing else; a `mutate(..., { onError })` or a second `toast` in the field would show two. The hook does not call `handleApiError` and is not silenced with `onError: () => {}`, which differs from the letter of the project rule but gives one toast with its single caller; it is not changed here.

### Web tests

Use each file's existing fetch pattern: `ApiSettingsPanel.test.tsx` and `SettingsPage.test.tsx` save and restore `globalThis.fetch`; new test files use `vi.stubGlobal('fetch', ...)` with `vi.unstubAllGlobals()` in `afterEach`. Do not mix both in one file (project-context.md, "Stubbing browser globals"). Toasts are the mocked `sonner` (`ApiSettingsPanel.test.tsx:13-20`); count calls with `toHaveBeenCalledTimes`.

| Task | File | Tests |
|---|---|---|
| 1 | `components/DurationSettingField.test.tsx` (new describe "On switch (Story 22.5)") | With `offValue={0} onValue={14400}` and `value={14400}`: a switch named "Test Setting On", checked, and the input showing 4h. With `value={0}`: switch unchecked, `test_setting-off` reads "Off", no textbox. Turning off calls `onSave` once with `{ key, value: 0 }`, then "Off" shows and no textbox; turning on from 0 calls `onSave` once with 14400 and the input shows 4h; a blur on it then saves nothing. A rejected save (Error "boom") puts the switch back, shows "boom" with `role="alert"`, and the switch's `aria-describedby` is `test_setting-error`; with a description and no error it is `test_setting-desc`. Disabled while the save is pending (a deferred promise) and when `envManaged`. One click on the "On" text and one click on the switch each call `onSave` exactly once. The tap target has `max-lg:min-h-11` (class check; the 44px is measured in E2E E3). Typing `0` with `min={60}` shows "Must be at least 1m" and does not call `onSave`. Without the pair: no switch is rendered (`queryByRole('switch')` null). **Following the prop:** `rerender` from 3600 to 7200 while not editing shows 2h (red today); with the pair, `rerender` to 0 shows Off and to 14400 shows 4h; a `rerender` while a save is pending is ignored and the field shows its own result |
| 2 | `features/settings/ApiSettingsPanel.test.tsx` | Mod List Refresh: `30s` -> "Must be at least 1m", no POST; `400d` -> "Must be at most 365d", no POST; `2d` -> one POST with 172800 and one success toast. The same three for Server Versions Refresh (with `serverVersionsRefreshInterval` 3600 as loaded, so `2d` is a change). Defaults with an empty `settings` object: Server Versions Refresh 1d, Enforce Env on Restart unchecked, Mod List Refresh 4h, Auto-Start unchecked, Block Env-Managed checked |
| 2 | `api/config.test.ts` | `API_SETTING_DEFAULTS` has exactly the six keys and every interval default is above 0 and at most `MAX_INTERVAL_SECONDS` |
| 3 | `features/settings/ApiSettingsPanel.test.tsx` (new describe "interval switches (Story 22.5)") | Three switches: "Mod List Refresh On", "Server Versions Refresh On", "Metrics Collection On", all checked with the fixture values. Metrics Collection shows 10s from the fixture and 10s with an empty `settings`; its description matches both facts of its help text; `0` -> "Must be at least 1s" and `2h` -> "Must be at most 1h", no POST; `30s` saves 30. Turning Mod List Refresh off: one POST to `/config/api/settings/mod_list_refresh_interval` with body `{"value":0}`, `toast.success` once with `mod_list_refresh_interval updated`, no error toast, `mod_list_refresh_interval-off` shown. Loaded with `modListRefreshInterval: 0`: Off on load, switch unchecked; turning on POSTs 14400 and the input shows 4h. The same on-value check for Server Versions Refresh (86400 -> 1d) and Metrics Collection (10 -> 10s). A failed POST (500 without a code) on a switch: `toast.error` once ("Update failed"), no success, switch back. `API_SETTING_NOT_APPLIED` on turning off, with the GET after the POST returning 0: `toast.warning` once, `toast.error` and `toast.success` not called, and the switch ends unchecked with Off shown (`waitFor`). Each switch's `aria-describedby` points at its description |
| 4 | `features/settings/SettingsPage.test.tsx` | The fetch mock answers `/auth/me` with `{ status: 'ok', data: { role } }` (role per test; Admin by default). **Monitor:** once the role has loaded (`waitFor` on the `/auth/me` call and its settled query), `queryByTestId('api-settings-tab')` and `queryByTestId('scheduled-jobs-tab')` are null, there are exactly two tabs (UI Preferences, File Manager), UI Preferences is active, `api-settings-panel` / `-loading` / `-error` are absent, and no fetch URL contains `/config/api`. **Admin:** `findByTestId('api-settings-tab')`, clicking it shows the panel (the existing tests, now explicit Admin). **Role loading** (`/auth/me` never resolves): no API Settings tab |

### Existing tests that change (deliberately)

- `ApiSettingsPanel.test.tsx:165-213` "uses default values when settings are undefined": Enforce Env on Restart becomes unchecked (was checked), Server Versions Refresh `1d` (was `1h`) (Task 2).
- `ApiSettingsPanel.test.tsx:674-697` "above maximum" (`2d` > 1d) becomes `400d` > 365d with "Must be at most 365d"; `:699-722` (`8d` > 7d) the same for Server Versions Refresh (Task 2).
- `SettingsPage.test.tsx:79-91`: the default fetch mock returns `mockApiSettings` for every URL, so today `/auth/me` gives no role and Scheduled Jobs is never shown in this file. It must answer `/auth/me` with a role; `:139-147`, `:169-183`, `:224-259` then wait for the Admin tab (`findByTestId`) before using it (Task 4).
- Fixtures gain `metricsCollectionInterval: 10` (Task 3).

Every other test stays as it is. Anything else that fails is a regression: fix the code, not the test.

### E2E (`web/e2e/settings-as-saved.spec.ts`, Task 5)

Why this file: Playwright runs files in parallel (`fullyParallel: true`, `workers` unset outside CI, `web/playwright.config.ts:19-22`), and the serial describe "A changed refresh interval applies at once" (`:137-224`) already snapshots and restores `mod_list_refresh_interval` (`:145-169`, the restore refuses to run without a snapshot). A second file writing the same setting could run at the same time and corrupt either snapshot. Story 22.5's write test goes inside that describe; its read-only tests next to it. No other spec writes API settings (`grep -rln "config/api" web/e2e`).

- **E1 (inside the serial describe, Admin):** "the On switch turns Mod List Refresh off and on again". Open `/config`, open Scheduled Jobs first (so its data is cached, as `:183-187`), then API Settings. If the snapshot is above 0: the switch "Mod List Refresh On" is checked; click it; exactly one `[data-sonner-toast]` with `mod_list_refresh_interval updated`; `mod_list_refresh_interval-off` reads Off and the textbox "Mod List Refresh" is gone; the API value is 0; Scheduled Jobs has no `job-schedule-mod_cache_refresh` within 5 s; reload the page, open API Settings: still Off, switch unchecked; click the switch: the API value is 14400, the input shows 4h, Scheduled Jobs shows `every 4h`. If the snapshot is 0: the same from Off (on, then off). The describe's `afterAll` restores the snapshot. Residue as for the existing test: the restored job's next run is one interval after the restore.
- **E2 (new describe, Admin, read-only):** every POST to `**/api/v1alpha1/config/api/settings/**` is routed to a failing stub that also fails the test if called. The Metrics Collection field is visible with its switch and help text (both facts); typing `400d` into Mod List Refresh and blurring shows "Must be at most 365d", `30s` shows "Must be at least 1m", and no POST was made.
- **E3 (new describe, Admin, read-only, 390px):** the "Mod List Refresh On" tap target (the switch's closest `label`) has a bounding box at least 44px tall, the switch is inside the viewport, and the document does not scroll sideways (`document.documentElement.scrollWidth <= innerWidth`).
- **E4 (new describe, roles, read-only):** Monitor: `test.skip(!MONITOR_KEY, 'VS_API_KEY_MONITOR is not set for this stack')` inside the body (as `file-browser-monitor-note.spec.ts:31-37`, `:138`); `serveConfigKey(page, MONITOR_KEY)`, `pretendServerInstalled(page)`; record every request whose URL ends with `/api/v1alpha1/config/api`; for `/config` and `/config?tab=api-settings`: `ui-preferences-tab` has `aria-selected="true"`, `file-manager-tab` is visible, `api-settings-tab` and `scheduled-jobs-tab` have count 0, "Failed to load settings" is not visible; after both, no request was recorded. Admin: `api-settings-tab` is visible and opens `api-settings-panel`.

The keys come from the environment as in the file today (`:25`) plus `const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';`. E2E are untagged (no live mod database, no game server). Run with `just test-e2e-ci e2e/settings-as-saved.spec.ts` (throwaway container on `127.0.0.1:18080`, removed after the run), and the whole suite with `just test-e2e-ci` in Task 6. Never against `http://localhost:9080`: writes to the dev stack are the maintainer's (6.5), and rebuilding it would stop its game server (ADR-14 decision 3).

### Not changed (do not "fix" these here)

- `ui/switch.tsx`, `ui/input.tsx` and `SettingField.tsx`: the 44px target is the new label around the switch; the duration input keeps its height (open question 2). `SettingGroup.tsx` is unchanged.
- `use-api-settings.ts` (one toast already; see "One toast").
- `scheduledRestartTimes`, `backupKeepCount`, the Scheduled Restarts and Disk Cleanup groups: Story 22.6.
- `GameConfigPanel.tsx` showing editable fields to a Monitor key: `VSS-7z3`, not pulled in (change proposal `:213`).
- The API: no source change; its bounds and defaults stay (the epic's "Product changes": "the existing settings' API bounds do not change").

### What admins see

- Each of Mod List Refresh, Server Versions Refresh and the new Metrics Collection has an On switch. Off saves 0 and the job disappears from Scheduled Jobs; On saves the API's default (4h, 1d, 10s), not the value before Off: to keep a custom interval, type it again after turning the job on.
- Refresh intervals up to 365 days are accepted. Metrics Collection accepts 1 second to 1 hour; a larger value set through the API is shown, but editing it in the tab is limited to 1 hour (ADR-11 decision 2).
- A Monitor key no longer sees API Settings (it saw only "Failed to load settings" there).

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-web <file>` after each change; `just check` before review.

- Web unit tests: Vitest + Testing Library (`userEvent` or `fireEvent`, as the file already does). No `.skip` or `.only`. The jsdom rules of `project-context.md` apply: `window.location` and `document` cannot be stubbed (use `setTestUrl` from `web/tests/location.ts` if a URL is needed; none is in this story), `matchMedia` and `ResizeObserver` are stubbed in `web/tests/setup.ts`. Layout heights are not measurable in jsdom: assert classes in unit tests, measure in E2E.
- The API pinning test runs with `just test-api tests/test_api_settings.py`.
- `git status --short` after the unit and E2E runs shows nothing under `dev/`.

### Security Requirements

- No new endpoint, request type or secret. Hiding the tab is a UI change: the API already refuses a Monitor key (`routers/config.py:282`, `:324`), and that stays the enforcement. The webhook URL stays write-only (`SECRET_API_SETTINGS`, unchanged).
- No instance-specific value (keys, server name, URLs other than `localhost` and the throwaway port) in the story, the PR, the tests or the AAR.

### Development Commands

- `just test-web src/components/DurationSettingField.test.tsx`
- `just test-web src/features/settings/ApiSettingsPanel.test.tsx src/features/settings/SettingsPage.test.tsx src/api/config.test.ts`
- `just test-api tests/test_api_settings.py`
- `just typecheck`, `just format-web`, `just lint`, `just check`
- `just test-e2e-ci e2e/settings-as-saved.spec.ts`, then `just test-e2e-ci`
- `just sprint set 22-5-interval-fields-can-turn-jobs-off review` (Task 6 only). Never edit `sprint-status.yaml` or `.beads/` by hand; never push without the maintainer's word.

### Previous Story Intelligence

- **22.8 / 22.7** (directly before; API only): no web change. Their branches stack this one; nothing they touch is touched here.
- **22.4:** `backup_keep_count` (0 to 1000, default 0) is in the API; the archive settings were dropped (ADR-9 amended 2026-11-19: saving `log_archive_retention_days` or `log_archive_keep_min` is 400 `API_SETTING_UNKNOWN`). Story 22.6 adds the field to the web; this story does not. `API_SETTING_DEFAULTS` is where 22.6 adds its default.
- **22.3:** `scheduled_restart_times` (list of `HH:MM`) is in the API response and arrives as `scheduledRestartTimes`; `INTERVAL_SETTINGS` became `SCHEDULED_SETTINGS` (the comment this story fixes). Web half: Story 22.6. Its restart jobs (`scheduled_restart_HHMM`) appear in Scheduled Jobs, unaffected by the interval switches.
- **22.1:** the Players card reads `/metrics/current` (why the help text names it); its tests used `vi.stubGlobal` in a new file and kept the save-and-restore pattern in existing files: the same rule here. It ran E2E only through `just test-e2e-ci <file>`.
- **17.6:** saving an interval reschedules its job and invalidates the jobs query; `API_SETTING_NOT_APPLIED` shows "Saved, not applied yet". Its E2E (`settings-as-saved.spec.ts`) is where this story's E2E goes.
- **21.7 / 21.8 (Epic 21):** 44px targets below `lg` with `max-lg:` classes; tab triggers already are. Review learnings: a `feat`/`fix` subject describes what an admin sees; completion notes must be true of the code as committed; manual checks are ticked only after the maintainer confirms; E2E specs are type-checked; the E2E README counts are kept right.

### Git Intelligence

- Base: `39068328` (`chore(story-22.8/task-6): validate and move story 22.8 to review`), on `story/22-8-container-stop-saves-the-world`; `main` is `e16a7932`. Recent work is API-only (22.7, 22.8), so the web settings code is as at Epic 21's end.
- Planned commits: Task 1 `refactor`, Task 2 `fix` (release note), Task 3 `feat` (release note), Task 4 `fix` (release note), Task 5 `test`, Task 6 `chore`. No other commit of this story may use `feat`, `fix` or `perf`.

### Latest Technical Information

- No new library. Radix Switch (`@radix-ui/react-switch`, via `ui/switch.tsx`) renders `<button role="switch" aria-checked>`; a `<label>` activates it (a button is a labelable element), and `aria-label` gives it its name over the label's text. TanStack Query v5: a hook-level `onError` replaces the client default and runs before `mutateAsync` rejects; `onSettled` runs after, so the refetch follows the field's catch. Prettier is pinned (`web/package.json`); format with `just format-web`.

### Project Structure Notes

- Modified: `web/src/components/DurationSettingField.tsx` and its test; `web/src/api/config.ts`, `web/src/api/config.test.ts`; `web/src/api/types.ts`; `web/src/features/settings/ApiSettingsPanel.tsx`, `SettingsPage.tsx` and their tests; `api/tests/test_api_settings.py`; `web/e2e/settings-as-saved.spec.ts`; `web/e2e/README.md`.
- New: none. Not touched: `api/src/`, `web/src/hooks/use-api-settings.ts`, `web/src/components/ui/`, `SettingField.tsx`, `SettingGroup.tsx`, `Justfile`, `scripts/`, `.github/`, `web/package.json`, `bun.lock`, compose files.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.5: Interval Fields Can Turn Jobs Off] (`:7604-7664`); Epic 22 header, order and dependencies (`:7233-7276`)
- [Source: _bmad-output/planning-artifacts/prd.md] FR300-FR303 (`:920-923`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] facts "The API Settings tab" (`:58-63`), ADR-11 (`:220-231`), ADR-12 (`:233-237`), ADR-14 (`:250-259`)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] findings (`:21`, `:220-223`), answers 10 and 11 (`:199-200`), draft release notes (`:100-101`), API Settings tab Admin only (`:92`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md] 44px pattern (`:114`), ADR-12 decision 1 (`:339`)
- [Source: _bmad-output/implementation-artifacts/22-3-scheduled-restarts.md] (`SCHEDULED_SETTINGS`, the comment drawdown `:100`, `:616`, the web contract `:401`); `22-4-log-archive-and-backup-cleanup.md` (ADR-9 amendment); `22-1-players-online-are-counted.md` (Players card, test-stub rule `:262`)
- Bead: `VSS-9jv` (UI-085), parent `VSS-oole`; discovered from `VSS-8bl`
- `project-context.md`: testing discipline, stubbing browser globals, no suppressions, mutation `onError` rule, commit message format, story sizing (6 tasks)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-11-19: Story created (create-story, non-interactive) from Epic 22 Story 22.5, ADR-11, ADR-12, ADR-14 and the code at 39068328. Status ready-for-dev.
