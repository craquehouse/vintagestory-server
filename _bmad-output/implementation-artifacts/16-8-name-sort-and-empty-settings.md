# Story 16.8: Name Sort and Empty Settings

Status: in-progress

<!-- Implements FR175-FR176. Beads: VSS-stm.1 (Name sort), VSS-7ed (empty settings, Password). Added to Epic 16 on 2026-11-13 after Stories 16.0-16.7 (sprint-change-proposal-2026-11-13.md, Addendum). Stacks on Story 16.7 (branch story/16-7-file-browser-breadcrumbs, PR #154), itself on #153, #152, #151, #150, #149, #148. No new dependencies. -->

## Story

As an **administrator**,
I want **the Name (A-Z) sort to list mods, and empty game settings to stay empty**,
so that **I can find mods alphabetically and edit settings without saving the word "null" or showing the server password**.

## Acceptance Criteria

1. **Given** the mod browser
   **When** I choose Name (A-Z)
   **Then** the API sorts all matching mods by name, ignoring leading and trailing spaces, letter case and accents (combining marks), with a stable order for equal names, and the browser shows one page of them with the same page controls and results count as the other sorts
   *(Covers FR175; `VSS-stm.1`)*

2. **Given** the Name (A-Z) sort with a `page`, search or filters in the URL (Story 16.1's browse state)
   **When** the browse page loads or the page changes
   **Then** the web UI requests `sort=name` with its normal page size (20; never more than the API's limit of 100), the results are that page of the alphabetical list of matching mods, and no client-side re-sorting is applied
   *(Covers FR175)*

3. **Given** a game setting whose value in `serverconfig.json` is null (Description, Password, IP Address on a fresh server)
   **When** I open Game Settings
   **Then** its field is empty, not the text "null", and focusing and leaving the field without typing saves nothing
   *(Covers FR176; `VSS-7ed`)*

4. **Given** Description (`ServerDescription`), Password or IP Address (`Ip`), the settings whose VintageStory default is null
   **When** I clear the field (empty or only spaces) and leave it, or a client sends `null`
   **Then** the API stores null, never the text "null", "None" or an empty string; with the game server running, a cleared Password is applied with `/serverconfig nopassword`, and a cleared Description, which has no console command to clear it, is written to the config file and marked as needing a restart
   *(Covers FR176)*

5. **Given** any other setting (for example Server Name, Welcome Message, Port, a toggle)
   **When** a client sends `null`
   **Then** the API rejects it with 400 `SETTING_VALUE_INVALID` instead of writing the text "None", and an empty Welcome Message is still saved as an empty string as today
   *(Covers FR176)*

6. **Given** the Password setting
   **When** I open Game Settings
   **Then** the password is masked (`type="password"`, `autocomplete="new-password"` so the browser does not fill in a saved login), and a button beside it shows and hides it ("Show password" / "Hide password", `aria-pressed`)
   *(Covers FR176)*

7. **Given** the changes
   **When** I use the other settings and sorts
   **Then** they behave as before: auto-save on blur and Enter, validation messages, env-managed badges and disabled inputs, toasts, Story 16.6 layout, and the Newest, Downloads and Trending sorts

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.8/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: API name sort ignores leading spaces, case and accents + tests (AC: 1)
  - [x] 1.1: `services/mod_api.py`: a `_name_sort_key(mod)` used by `sort_mods(..., "name")`: `str(mod.get("name") or "")`, stripped, NFKD-normalized with combining marks removed (`unicodedata`, standard library), `casefold()`; tie-break on the stripped name and then `assetid`, so equal names keep one order across cache refreshes. A null or missing name sorts as empty instead of raising
  - [x] 1.2: Tests in `tests/test_mod_api.py` (`TestSortMods` or next to `test_sort_by_name`): leading spaces (`" Auto Map"` between `"Apple"` and `"Butcher"`), case, accents (`"Étiquettes"` next to `"Etiquettes"`, before `"Farm"`), null and missing names, equal names ordered by `assetid`. A router test (`tests/test_mods_router.py`) that `sort=name&page=2&page_size=2` returns the second slice of the alphabetical order and correct pagination

- [x] Task 2: Web UI uses the server's Name sort with normal paging + tests (AC: 1, 2, 7)
  - [x] 2.1: `web/src/api/mods.ts` `fetchBrowseMods`: send `sort` for every option, including `name`
  - [x] 2.2: `web/src/hooks/use-browse-mods.ts`: pass `sort` through unchanged, use `params.pageSize ?? 20` for every sort (drop the `VSS-arp` 1000 page size), return the API's order (drop the client-side sort); remove the now-unused `sortModsByName` and its tests; update the doc comments
  - [x] 2.3: `web/src/features/mods/BrowseTab.tsx`: show `Pagination` for the Name sort like the other sorts and use the normal results count ("Showing N of T mods" / "Found N mods matching …") instead of "Showing all T mods sorted alphabetically"
  - [x] 2.4: Tests: `mods.test.ts` sends `sort=name`; `use-browse-mods.test.tsx` requests `sort=name&page_size=20` (and the given page), keeps the API order, never asks for more than 100; `BrowseTab.test.tsx` shows pagination and the normal count for Name sort with more than one page, and `?sort=name&page=3` requests page 3

- [ ] Task 3: API stores null for cleared Description, Password and IP Address + tests (AC: 4, 5)
  - [ ] 3.1: `services/game_config.py`: `ServerSetting` gains `nullable: bool = False` and `clear_command: str | None = None`; `ServerDescription`, `Password` and `Ip` are nullable; `Password` has `clear_command="/serverconfig nopassword"`
  - [ ] 3.2: `_validate_value`: `None` returns `None` for a nullable setting and raises `SettingValueInvalidError` ("… cannot be empty"/"null is not allowed") otherwise; for a nullable string setting a blank string (empty or only whitespace) becomes `None`. `update_setting` skips string sanitizing for `None`
  - [ ] 3.3: Applying `None`: with the server running and the setting live, use `clear_command` when there is one (no `{value}`); without one (Description) write the file and report `pending_restart=True` (and call `require_restart`); with the server stopped write the file as today. JSON stores `null`. Password stays redacted in logs (`***`), including the clear command path
  - [ ] 3.4: Tests in `tests/test_game_config.py` (service) and `tests/test_routers_config.py`: `None` and `""`/`"  "` for each nullable key write `null` to the file (server stopped); running server: Password `None`/`""` sends `/serverconfig nopassword`, Description `None` writes the file with `pending_restart=True` and no console command, Ip unchanged (file, restart); `None` for `ServerName`, `WelcomeMessage`, `Port`, `AllowPvP` → 400 `SETTING_VALUE_INVALID` and the file is unchanged; `""` for `WelcomeMessage` is still stored as `""`; the existing "None" string behavior is gone (red first: today `None` writes `"None"`)

- [ ] Task 4: Settings page shows empty settings as empty and masks Password + tests (AC: 3, 6, 7)
  - [ ] 4.1: `web/src/api/types.ts`: `GameSetting.value` and `GameSettingUpdateData.value` allow `null`
  - [ ] 4.2: `web/src/components/SettingField.tsx`: `value` prop allows `null`; non-boolean fields use `value ?? ''` as the initial value, so the input is empty and an untouched field is not dirty (no save on blur); booleans unchanged (`Boolean(value)`)
  - [ ] 4.3: `SettingField` gains an optional `masked` prop: the input is `type="password"` with `autoComplete="new-password"` and a ghost icon button inside its right edge (`Eye`/`EyeOff` from `lucide-react`, already a dependency; positioned like the search clear button in `BrowseTab`) that toggles `type` between `password` and `text`, with `aria-label` "Show password"/"Hide password" and `aria-pressed`; the input gets right padding so text does not run under the button. `GameConfigPanel` sets `masked` on the Password definition
  - [ ] 4.4: Tests: `SettingField.test.tsx`: a null string value renders an empty input (not "null"); focus and blur without typing does not call `onSave`; clearing a non-empty value and blurring calls `onSave` with `""`; a null number renders empty; `masked` renders `type="password"` with `autocomplete="new-password"`, the toggle shows and hides it and updates its label and `aria-pressed`, and editing and saving still work while masked. `GameConfigPanel.test.tsx`: with `ServerDescription`, `Password` and `Ip` null the inputs are empty and no "null" text is shown; Password is `type="password"`; Server Name is not masked; existing tests pass

- [ ] Task 5: Browser verification against the Docker dev stack (AC: all)
  - [ ] 5.1: Before any change to `./data`: copy `data/serverdata/serverconfig.json` to the session scratchpad and record its SHA-1 and the API values of `ServerDescription`, `Password` (null or not, never the value) and `Ip`; record the game server state
  - [ ] 5.2: `web/e2e/mod-browse-name-sort.spec.ts` (read-only): Name (A-Z) shows 20 cards, pagination and the normal count; pages 1, 2 and a later page (`?sort=name&page=N`) are each in alphabetical order (normalized like the API) and follow on from each other; every browse request has `page_size` ≤ 100 and no response is 422; a search with Name sort is alphabetical
  - [ ] 5.3: `web/e2e/settings-empty-values.spec.ts` (read-only): with the settings null, Description, Password and IP Address inputs are empty and the page has no "null" text; Password is masked and the toggle reveals and hides it. Uses `test.skip` only if the stack's settings are not null, with the reason printed (no silent skip)
  - [ ] 5.4: `just docker restart` (rebuild from this branch); run both specs. Then, with Playwright in a scratchpad script: type a value into Description and Password and leave each field, clear each and leave it, and after each step read the setting back through `GET /api/v1alpha1/config/game`: the cleared value is `null` (not `""`, `"null"` or `"None"`). Do not touch Server Name, IP Address or Port. Browser console clean
  - [ ] 5.5: Restore: copy the saved `serverconfig.json` back, confirm the SHA-1 matches the one from 5.1 and the API returns the recorded values. Screenshots stay in the scratchpad unless masked (`header span.font-semibold`, `#ServerName`, `#Password`)

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes
  - [ ] 6.2: Status review, `just sprint set 16-8-name-sort-and-empty-settings review`, PR to `story/16-7-file-browser-breadcrumbs` (stacks on #154, #153, #152, #151, #150, #149, #148), PR link on `VSS-stm.1` and `VSS-7ed`

## Dev Notes

### Today's behavior

**Name sort (`VSS-stm.1`).**

- `useBrowseMods` sends `page_size=1000` for `sort === 'name'` and strips `sort` from the query (`use-browse-mods.ts:81-86`; `fetchBrowseMods` skips `name`, `api/mods.ts:186-188`), then sorts the page with `localeCompare` (`sortModsByName`). The browse endpoint validates `page_size` with `le=100` (`routers/mods.py:235-237`), so the request fails with 422; React Query retries three times and the grid shows no cards until the error state appears (Story 16.0 probe: `16-0-spike/browse_probe.out.json`, three 422s, 0 cards, no error message within 3 s).
- `BrowseTab` hides `Pagination` for the Name sort and prints "Showing all N mods sorted alphabetically" (`BrowseTab.tsx:290-310`); Story 16.1 noted that `page` has no effect for it (ADR-1 implementation traps).
- **The API already sorts by name.** `SortOption` includes `"name"` (`services/mod_api.py:32`), `sort_mods` sorts by `name.lower()` ascending (`mod_api.py:780-781`), and the browse endpoint filters, sorts and slices the whole cached listing (`get_all_mods`, 9,564 mods) before paging (`routers/mods.py:320-376`), with tests (`test_mods_router.py:1599`, `test_mod_api.py:1037`). The polish note API-029 ("the API lacks a name sort") is stale. Checked on the running stack: `GET /mods/browse?sort=name&page=1&page_size=20` returns 200 and 479 pages.
- The API's key puts names with a leading space first (`" [Addon] Into The Fire…"`, `" Auto Map Markers…"` on page 1) and accented names after `z` (`"Étiquettes de caisses"` after `"zzz-bell-of-doom"`), and `m.get("name", "").lower()` would raise on a `null` name.

**Empty settings (`VSS-7ed`).**

- `GET /config/game` returns `value: null` for keys that are null or missing in `serverconfig.json` (`game_config.py:446-452`). On this stack `ServerDescription`, `Password` and `Ip` are null (VintageStory's defaults, `agentdocs/vs-serverconfig-commands.md` "Complete serverconfig.json Structure").
- `SettingField` renders `<Input value={String(field.value)}>` (`SettingField.tsx:166-168`), so null shows as "null". Its state starts at `null`, so focus and blur alone save nothing; but any edit that ends with the text "null" (type then delete a character), or typing after it ("nullsecret"), is saved as that string.
- **Risk confirmed in the API:** `_validate_value` turns any non-string into a string with `str(value)` (`game_config.py:499-501`), so a `null` sent by any client is stored as the text `"None"`, for every string setting, and `None` for int/bool fails with a confusing message. Today the web UI never sends `null`, so the UI risk is the "null" text above; the API risk is for other clients.
- Clearing a field sends `""`. With the server stopped, `""` is written to the file: VintageStory's default for these keys is null, and an empty `Ip` is not a valid bind address. With the server running, `""` goes through the console as `/serverconfig password ` (and `description `), whose effect is undocumented; `/serverconfig nopassword` is the documented way to remove the password.
- Password is `type="text"`, so the server password is shown in clear text, and a browser could autofill a saved login into it.

### Decisions

- **Name sort on the server (FR175).** The API already has `sort=name` over the whole cached listing, so `page`, `page_size`, search and filters work like the other sorts at no extra cost. Fetching every page client-side would mean 96 requests at the 100 limit and duplicate the sort. The web UI sends `sort=name`; the client-side sort, the 1000 page size and the hidden pagination are removed.
- **Sort key.** Strip, remove combining marks after NFKD, `casefold()`: close to the old client `localeCompare` for Latin names, standard library only. Punctuation keeps its code point order (`"(Abandoned)…"` before letters), as ICU's default collation does. Ties: stripped name, then `assetid`.
- **Which settings accept null: `ServerDescription`, `Password`, `Ip`** - exactly the managed settings whose VintageStory default is null. `ServerName` is required (the UI validates it), `WelcomeMessage` has a default text and an empty message is a valid choice (kept as `""`), and numbers and toggles have no empty state.
- **The API decides null.** A blank string for a nullable setting is stored as null in the API, so every client gets the same result and the web UI just sends what is in the field. `null` for a setting that cannot be null is rejected (400) instead of stored as `"None"`.
- **Running server.** Password clears with `/serverconfig nopassword`. No console command is documented to clear the description, so a cleared Description is written to the file and flagged for restart, the same path restart-required settings (Port, IP Address) use while the server runs. IP Address is restart-required already.
- **Masking.** `type="password"` with a show/hide toggle; no existing show/hide pattern in the app, so the toggle follows the search clear button's placement. `autocomplete="new-password"` stops browsers filling a saved login into the field (which would then be saved on blur).

### Out of scope (beads, not fixed here)

- `GET /config/game` is readable by the Monitor role, so Monitor users can read the server password (as they can through the config file viewer).
- `EntitySpawning` is missing from this stack's `serverconfig.json`, so the API returns null and the toggle shows "Disabled" although the game's default may be on.
- Whether VintageStory overwrites `serverconfig.json` from memory while running (which would undo file updates made while it runs) is not checked here; it affects Port and IP Address today.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API: `tests/test_game_config.py` has a `game_config_service` fixture with a temp `serverconfig.json` (`"Password": ""` in its fixture) and mocks the server service for running/stopped; reuse it. Router tests use `admin_headers`.
- Web: `use-browse-mods.test.tsx` and `mods.test.ts` mock `fetch`; `GameConfigPanel.test.tsx` has `mockGameConfig`; `SettingField.test.tsx` uses Testing Library with `userEvent`.
- jsdom does not apply Tailwind; assert attributes (`type`, `autocomplete`, `aria-*`), not layout.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7 in `./data`, game server installed but stopped). `./data` settings must end exactly as they started: back up `serverconfig.json`, restore it and compare its SHA-1. Never change Server Name. Committed screenshots must mask `header span.font-semibold`, `#ServerName` and `#Password`. E2E specs set `localStorage.apiKey` with an init script (`VS_API_KEY_ADMIN` from `.env`, default `changeme`); a first run seconds after `just docker restart` can fail while the server starts, rerun once healthy.

### Security Requirements

- Never log the password: the clear-command path logs `value="***"` like the others. Screenshots mask the password. No new endpoints.

### Development Commands

- `just test-api tests/test_mod_api.py tests/test_mods_router.py`, `just test-api tests/test_game_config.py tests/test_routers_config.py`, `just test-web src/hooks/use-browse-mods.test.tsx src/api/mods.test.ts src/features/mods/BrowseTab.test.tsx`, `just test-web src/components/SettingField.test.tsx src/features/game-server/GameConfigPanel.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/mod-browse-name-sort.spec.ts e2e/settings-empty-values.spec.ts`.

### Previous Story Intelligence

- **16.1:** browse state lives in the URL (`sort`, `page`, …) and `useBrowseMods` takes a controlled `page`; changing sort removes `page`. Nothing there needs to change for the Name sort beyond the hook.
- **16.6:** `SettingField` gives number inputs `max-w-xs`; `GameConfigPanel` lays out Server Info in two columns at `xl` (Password is the fourth field). Keep the `cn` class merge and DOM order.
- **16.5 / 16.6:** E2E specs read only; `just lint-web` is `tsc --noEmit`; commit types by user impact.

### Git Intelligence

- Branch `story/16-8-name-sort-and-empty-settings` from `origin/story/16-7-file-browser-breadcrumbs` (35ab6cc). Planned types: Task 1 `fix` (Name sort order), Task 2 `fix` (Name sort works), Task 3 `fix` (cleared settings saved as empty), Task 4 `fix` (empty settings and masked password), Task 5 `test`, Task 6 `chore`.

### Latest Technical Information

- No new libraries. `unicodedata.normalize("NFKD", s)` and `unicodedata.combining(ch)` (Python standard library); `Eye`/`EyeOff` icons from `lucide-react` (already used); `autocomplete="new-password"` is the WHATWG value that tells browsers not to autofill an existing password.

### Project Structure Notes

- New: `web/e2e/mod-browse-name-sort.spec.ts`, `web/e2e/settings-empty-values.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mod_api.py`, `api/src/vintagestory_api/services/game_config.py` (+ tests), `web/src/api/mods.ts`, `web/src/api/types.ts`, `web/src/hooks/use-browse-mods.ts`, `web/src/features/mods/BrowseTab.tsx`, `web/src/components/SettingField.tsx`, `web/src/features/game-server/GameConfigPanel.tsx` (+ tests).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.8: Name Sort and Empty Settings]
- [Source: _bmad-output/planning-artifacts/prd.md] FR175, FR176
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-1] (browse URL state, Name sort trap), #ADR-3 (out of scope note for `VSS-7ed`)
- [Source: _bmad-output/implementation-artifacts/16-0-spike/browse_probe.out.json] (422s)
- [Source: _bmad-output/implementation-artifacts/16-1-mod-browser-state-survives-mod-details.md], [16-6-settings-layout-on-desktop.md]
- [Source: agentdocs/vs-serverconfig-commands.md] (`/serverconfig nopassword`, null defaults)
- Beads: `VSS-stm.1`, `VSS-7ed`, parent `VSS-stm`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run, the 3 new `sort_mods` tests failed (leading space and accent order, `None` name raised `AttributeError`, ties in input order); the new router paging test passed already (the API pages name sort today). Then 206 passed in `test_mod_api.py` and `test_mods_router.py`; ruff clean, pyright 0 errors (3 pre-existing warnings).
- Task 2: red run, 6 new or rewritten tests failed (`mods.test.ts` 1, `use-browse-mods.test.tsx` 4, `BrowseTab.test.tsx` 1); then 182 passed, 2 skipped (pre-existing) in the three files; full web suite 3,121 passed, 4 skipped (pre-existing); `tsc` clean.

### Completion Notes List

- Story created 2026-11-13: context analysis of the browse hook and endpoint, the settings service and field, Stories 16.0, 16.1 and 16.6 and ADR-1/ADR-3.
- Task 1: `sort_mods(..., "name")` uses `_name_sort_key`: stripped, NFKD without combining marks, `casefold()`, then the stripped name and `assetid`; a null or missing name sorts as empty.
- Task 2: `fetchBrowseMods` sends `sort=name`; `useBrowseMods` passes every sort through with `pageSize ?? 20` and keeps the API's order (the 1000 page size and the client-side `sortModsByName` are removed, with its tests); `BrowseTab` shows page controls and the normal results count for the Name sort.

### File List

- `api/src/vintagestory_api/services/mod_api.py`
- `api/tests/test_mod_api.py`
- `api/tests/test_mods_router.py`
- `web/src/api/mods.ts`
- `web/src/api/mods.test.ts`
- `web/src/hooks/use-browse-mods.ts`
- `web/src/hooks/use-browse-mods.test.tsx`
- `web/src/features/mods/BrowseTab.tsx`
- `web/src/features/mods/BrowseTab.test.tsx`
