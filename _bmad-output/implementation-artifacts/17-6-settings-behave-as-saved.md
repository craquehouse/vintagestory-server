# Story 17.6: Settings Behave as Saved

Status: ready-for-dev

<!-- Implements FR187-FR188. Beads: VSS-8bl, VSS-2le. Implemented after Stories 17.5 (secret game settings), stacked on its branch; 17.7 and 17.8 follow. Line references were verified at 21457bf (story/17-4-installed-status-is-right-everywhere head) and MUST be re-checked: 17.5 changes `services/game_config.py`, `SettingField.tsx`, `GameConfigPanel.tsx`, `api/types.ts` and the game settings response. Epic 17 ADR-5 governs the scheduler half; no ADR governs the boolean half. No new dependencies. -->

## Story

As an **administrator**,
I want **a setting to do what the screen says once I have saved it**,
so that **I do not have to restart the API or guess what the game is using**.

## Acceptance Criteria

1. **Given** a refresh interval setting above 0 (`mod_list_refresh_interval`, `server_versions_refresh_interval` or `metrics_collection_interval`) and its job registered
   **When** I save a different value above 0 (`POST /api/v1alpha1/config/api/settings/{key}`)
   **Then** without an API restart its job (`mod_cache_refresh`, `server_versions_check`, `metrics_collection`) has the new interval, its next run is one new interval after the save, and the save does not run the job
   *(Covers FR187; `VSS-8bl`)*

2. **Given** a refresh interval above 0
   **When** I save 0
   **Then** its job is removed and does not run again; saving 0 when the job is not registered succeeds and changes nothing
   *(Covers FR187)*

3. **Given** a refresh interval of 0 (no job registered)
   **When** I save a value above 0
   **Then** its job is registered with that interval, first run one interval after the save (also for `server_versions_check`, which runs at once only at API startup)
   *(Covers FR187)*

4. **Given** a job that is running when its interval is changed or set to 0
   **When** the setting is saved
   **Then** the running execution is not cancelled and finishes; afterwards the job follows the new interval (or, for 0, does not run again)
   *(Covers FR187)*

5. **Given** I changed a refresh interval on the API Settings tab
   **When** I open the Scheduled Jobs tab
   **Then** it shows the new schedule and next run at once, not after the 30 s poll or the 30 s stale time
   *(Covers FR187)*

6. **Given** an interval value above 31,536,000 seconds (365 days)
   **When** I save it
   **Then** the request is refused with 400 `API_SETTING_INVALID`, nothing is saved and the job is unchanged
   *(Covers FR187: a value the scheduler cannot hold must not be saved)*

7. **Given** applying a saved interval to the scheduler fails
   **When** I save the setting
   **Then** the value stays saved (it applies at the next API start), the API answers 500 `API_SETTING_NOT_APPLIED` with a message that says so, and the API Settings tab shows a warning toast with that message, not a success toast
   *(Covers FR187; Epic 17 ADR-5 decision 5)*

8. **Given** the API starts
   **When** jobs are registered
   **Then** the same jobs are registered as today, through the same function a settings change uses, and `server_versions_check` still runs once at startup
   *(Covers FR187; Epic 17 ADR-5 decision 2)*

9. **Given** `GET /api/v1alpha1/config/game`
   **When** a setting has a game default known to the manager
   **Then** the setting carries `default` (`EntitySpawning`: `"default": true`); every other setting has no `default` key
   *(Covers FR188; `VSS-2le`)*

10. **Given** a boolean game setting with no value in `serverconfig.json` (`value: null`) and a known default
    **When** I open Game Settings
    **Then** the switch is in the default's position and reads "Enabled (default)" or "Disabled (default)" (Entity Spawning: "Enabled (default)"), never plain "Disabled"
    *(Covers FR188)*

11. **Given** a boolean game setting with `value: null` and no known default
    **When** I open Game Settings
    **Then** it reads "Not set", with neither "Enabled" nor "Disabled" in its label
    *(Covers FR188)*

12. **Given** a null boolean setting
    **When** I switch it and the save succeeds
    **Then** the explicit value is sent and the label reads plain "Enabled" or "Disabled", without "(default)"; a secret setting without a value (Story 17.5) still renders as Story 17.5 left it
    *(Covers FR188)*

13. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.6/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: One function applies an interval setting to the scheduler; startup uses it + tests (AC: 1, 2, 3, 4, 8, 13)
  - [x] 1.1: `api/src/vintagestory_api/jobs/__init__.py`: add `INTERVAL_JOBS` (setting key → job ID; the three pairs in AC 1) and `apply_interval_setting(scheduler: SchedulerService, key: str, seconds: int, *, startup: bool = False) -> None` (Dev Notes "The function"). Unknown key: `KeyError` from the table (a programming error, not caught)
  - [x] 1.2: `register_default_jobs` (`:35-109`) becomes: read settings as today (`ApiSettingsService().get_settings()`, `:52`; tests patch `vintagestory_api.jobs.ApiSettingsService`), then `apply_interval_setting(scheduler, key, getattr(settings, key), startup=True)` for each key. Keep the `job_registered` log event with its fields (`job_id`, `interval_seconds`, and `run_immediately=True` for `server_versions_check`) and the `default_jobs_registered` count: the three `*_logs_registration` tests assert them (the prototype that dropped them failed exactly those three). Module docstring: interval settings drive their jobs at startup and on change (Story 17.6, Epic 17 ADR-5)
  - [x] 1.3: Tests (Dev Notes "API tests", Task 1 rows). Real `SchedulerService`, inspected through `job_to_info` (typed; no suppression needed), not a mock
  - [x] Commit: `refactor(story-17.6/task-1): ...` (no visible change yet)

- [x] Task 2: Saving an interval reschedules its job; bounds; failure reported + tests (AC: 1, 2, 3, 6, 7, 13)
  - [x] 2.1: `services/api_settings.py` `ApiSettings` (`:41-55`): `le=31_536_000` on the three interval fields; descriptions add "at most 365 days". Name the bound once (`MAX_INTERVAL_SECONDS = 31_536_000`, module level, docstring: longer intervals cannot be scheduled reliably and 0 disables a job)
  - [x] 2.2: `services/api_settings.py`: new `ApiSettingNotAppliedError(key, reason)` next to the other two errors (`:95-122`), message `"Saved '{key}', but its job could not be rescheduled: {reason}. The saved value applies when the API restarts."`. In `update_setting` (`:269-280`) wrap the callback call: `except Exception as e:` log `api_setting_not_applied` (error, key, value) and `raise ApiSettingNotAppliedError(key, str(e)) from e`. A broad catch is deliberate here: any scheduler failure after the save must be reported, and it is re-raised as a typed error, not swallowed. Replace the "stub for Epic 7" wording in the constructor docstring (`:142-144`)
  - [x] 2.3: `routers/config.py` `get_api_settings_service` (`:226-249`): add `scheduler: SchedulerService = Depends(get_scheduler)` (`routers/jobs.py:20-27`, deferred import of `main.get_scheduler_service`) and pass `scheduler_callback=partial(apply_interval_setting, scheduler)`. Delete the Epic 7 TODO (it names `scheduler.reschedule_job`, which does not exist). Update the `update_api_setting` docstring (`:299-321`): all three intervals, 0 removes the job, 500 `API_SETTING_NOT_APPLIED`. Add `except ApiSettingNotAppliedError` → 500, `{"code": ErrorCode.API_SETTING_NOT_APPLIED, "message": e.message}`. `models/errors.py`: `API_SETTING_NOT_APPLIED` after `API_SETTING_INVALID` (`:48-49`)
  - [x] 2.4: Tests (Dev Notes "API tests", Task 2 rows) and the changes in "Existing tests that change" for Task 2
  - [x] Commit: `fix(story-17.6/task-2): a changed refresh interval applies without restarting the API`

- [x] Task 3: Scheduled Jobs shows the change at once; a not-applied save warns + tests (AC: 5, 7)
  - [x] 3.1: `web/src/api/config.ts`: `INTERVAL_API_SETTINGS: ReadonlySet<string>` with the three keys, next to `SECRET_API_SETTINGS` (`:74`), doc comment "API settings whose change reschedules a job (Story 17.6)"
  - [x] 3.2: `web/src/hooks/use-api-settings.ts` `useUpdateApiSetting` `onSettled` (`:123-126`): receive `(_data, _error, { key })` and, when `INTERVAL_API_SETTINGS.has(key)`, also `invalidateQueries({ queryKey: queryKeys.jobs.all })`. On error too: a not-applied save (AC 7) has still changed the saved value and possibly the job
  - [x] 3.3: `web/src/features/settings/ApiSettingsPanel.tsx` `handleSave` (`:46-56`): when `err instanceof ApiError && err.code === 'API_SETTING_NOT_APPLIED'`, `toast.warning('Saved, not applied yet', { description: err.message })` instead of `toast.error('Update failed', ...)`; still rethrow. The hook has its own `onError` (`:117-122`), which replaces the query client's default handler (Story 17.3 learning), so this toast is the only one shown; verify no second toast appears
  - [x] 3.4: Tests (Dev Notes "Web tests", Task 3 rows)
  - [x] Commit: `fix(story-17.6/task-3): Scheduled Jobs shows a changed interval right away`

- [x] Task 4: Boolean game settings with no value show the game's default + tests (AC: 9, 10, 11, 12)
  - [x] 4.1: Before coding, record in the Dev Agent Record the default you rely on and its evidence (Dev Notes "Defaults: evidence"). If you find game-sourced evidence for another boolean's default (a config generated by the game without the manager's template, or the game's own code), add it to the table and record the source; otherwise do not add it
  - [x] 4.2: `services/game_config.py`: `ServerSetting.__init__` (`:49-81`) gains `default: bool | None = None` ("the value VintageStory uses when `serverconfig.json` has no value for the setting; None when the manager does not know it. Story 17.6"); set `default=True` on `EntitySpawning` (`:142-148`) with a one-line comment naming the evidence. `SettingInfo` (`:195-239`) gains `default: bool | None = None`; `to_dict` adds `"default"` only when not None, like `requires_restart` and `env_var` (`:235-238`). `get_settings` (`:462-475`) passes `setting_def.default`. This table is the one place defaults live
  - [x] 4.3: `web/src/api/types.ts` `GameSetting` (`:244-252`): `default?: boolean` with a doc comment ("the game's value when `value` is null; absent when unknown. Story 17.6")
  - [x] 4.4: `web/src/components/SettingField.tsx`: new prop `gameDefault?: boolean` (doc: used only for `type === 'bool'` with `value === null`). Initial value (`:115`) for bool: `value === null ? (gameDefault ?? false) : Boolean(value)`. State label (`:189-191`): see Dev Notes "Rendering a null boolean"; add `data-testid={`setting-state-${settingKey}`}` to that span. Header comment: Story 17.6. `GameConfigPanel.tsx` `renderSetting` (`:222-244`) passes `gameDefault={setting.default}`
  - [x] 4.5: Tests (Dev Notes "API tests" and "Web tests", Task 4 rows)
  - [x] Commit: `fix(story-17.6/task-4): a game setting with no value shows the game's default or "Not set"`

- [ ] Task 5: E2E against the Docker dev stack (AC: 1, 2, 3, 5, 10, 11, 12)
  - [ ] 5.1: New `web/e2e/settings-as-saved.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/settings-as-saved.spec.ts` and the admin key from `.env` (`just test-e2e-web` stops the stack afterwards). Also re-run `e2e/settings-empty-values.spec.ts` and `e2e/settings-desktop-layout.spec.ts`
  - [ ] 5.2: Record the before/after comparison of `GET /config/api`, `GET /jobs` job IDs and schedules, and `GET /config/game` in the Dev Agent Record. Do not start or stop the game server
  - [ ] Commit: `test(story-17.6/task-5): ...`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes with `.env` present (the lifespan tests need `VS_API_KEY_ADMIN`; see "Existing tests that change"); the diff adds no lint or type suppression and no `cast`; after `just test-api`, `git status --short` shows nothing under `dev/` (no `dev/vsmanager/state/api-settings.json`)
  - [ ] 6.2: Story status `review`, `just sprint set 17-6-settings-behave-as-saved review`, PR (base: the Story 17.5 branch while its PR is open, otherwise `main`), PR link on `VSS-8bl` and `VSS-2le`. The PR description names the API changes (`default` on game settings; interval bound; `API_SETTING_NOT_APPLIED`)

## Dev Notes

### The bugs (verified at 21457bf)

- **Intervals (`VSS-8bl`).** `ApiSettingsService.update_setting` saves (`services/api_settings.py:267`) and then calls `self._scheduler_callback(key, value)` for the three interval settings (`:273-280`), but `get_api_settings_service` builds the service without a callback (`routers/config.py:249`); its TODO (`:237-247`) names `scheduler.reschedule_job`, which `SchedulerService` does not have. Which job belongs to which setting, and "0 means not registered", live only inline in `register_default_jobs` (`jobs/__init__.py:55-107`). So a changed interval waits for a restart, 0 does not stop a job, and raising from 0 does not start one. The bead names two settings; `metrics_collection_interval` shares the callback and the defect.
- **Null booleans (`VSS-2le`).** `GET /config/game` returns `config.get(key)` (`services/game_config.py:463`), so a key missing from `serverconfig.json` is `null`. `SettingField` turns it into `Boolean(null)` = false (`components/SettingField.tsx:115`) and labels it "Disabled" (`:190`). Story 16.8 made null strings and numbers empty fields and left booleans as they were.

### The function (`jobs/__init__.py`, Epic 17 ADR-5)

```python
INTERVAL_JOBS: dict[str, str] = {
    "mod_list_refresh_interval": "mod_cache_refresh",
    "server_versions_refresh_interval": "server_versions_check",
    "metrics_collection_interval": "metrics_collection",
}
"""Interval setting -> the job it drives (Story 17.6). 0 means the job is not registered."""


def apply_interval_setting(
    scheduler: SchedulerService, key: str, seconds: int, *, startup: bool = False
) -> None:
    """Make the scheduler match one interval setting (Story 17.6, Epic 17 ADR-5).

    Above 0 adds the setting's job or replaces it; its next run is one interval from
    now. 0 removes the job when it is registered. `startup` only makes
    `server_versions_check` run once at once, as it always has at API start.
    """
```

- The job functions keep their lazy imports (as `register_default_jobs` does today, `:58`, `:76`, `:95`): a small `_job_function(key)` helper with one import per branch. The prototype of this function type-checked under pyright strict with 0 errors and 0 warnings and needed no suppression: it only calls `add_interval_job`, `get_job(...) is not None` and `remove_job`.
- **Replace, not reschedule.** `add_interval_job` passes `replace_existing=True` (`services/scheduler.py:136-140`) and builds a new `IntervalTrigger`, whose first run is now + interval (verified in the prototype: `next_run_time` between save + interval - 1 s and save + interval). That is ADR-5 decision 3 ("restarts the countdown"); do not use `run_immediately` outside startup.
- **0.** `remove_job` raises `JobLookupError` when the job is missing (`services/scheduler.py:193-202`); check `scheduler.get_job(job_id) is not None` first. 0 → 0 is a no-op (verified).
- **Same value again.** The callback runs on every save of an interval setting, also with an unchanged value (`update_setting` does not compare). Re-adding the job restarts its countdown, and re-registers a job deleted through `DELETE /jobs/{id}`. Keep that; it is the only way to restore such a job without a restart. The web never sends an unchanged value (`useSettingField` saves only when dirty, `hooks/use-setting-field.ts:245`, `:294`), so only a direct API call does this.
- **Running job (AC 4).** Replacing or removing a job in APScheduler 3.11 does not touch an execution in progress: it runs to the end. The scheduler allows one instance per job ID (`max_instances: 1`, `services/scheduler.py:63`), so if it is still running when the new interval first fires, that one run is skipped with APScheduler's "maximum number of running instances" warning. No lock or cancellation is added.
- **Scheduler not running.** `get_scheduler_service` raises `RuntimeError` before the lifespan has started it (`main.py:41-52`); the API serves requests only after the lifespan, so this happens only in tests that build an app without the lifespan and use the real dependency (none today: every API settings router test overrides `get_api_settings_service`, `tests/test_routers_config.py:598-603`).

### Bounds (AC 6, decision)

`ApiSettings` has only `ge=0` (`services/api_settings.py:41-55`). An interval so long that now + interval passes the year 9999 makes `add_interval_job` raise `OverflowError` (verified with 10^12 s). Today that would be saved and then crash `register_default_jobs` at the next start; after Task 2 it would also return `API_SETTING_NOT_APPLIED`. So the model gets `le=31_536_000` (365 days): anything longer is "never" in practice, and 0 already means off. The UI keeps its own narrower ranges (`ApiSettingsPanel.tsx:151-172`: 60 s to 1 day, 60 s to 7 days). Consequence: an `api-settings.json` that already holds a larger value fails validation and `get_settings` falls back to the defaults with the existing `api_settings_load_failed` warning (`:174-191`); that is the existing behavior for any invalid file and is accepted (such a value can only have been set through the API).

### Failure is reported, not silently saved (AC 7, decision)

ADR-5 decision 5: the setting is saved before the callback runs, and a failed callback is reported. The service raises `ApiSettingNotAppliedError` after the save; the router answers 500 `API_SETTING_NOT_APPLIED`. The message says the value is saved and applies at restart, so an admin does not save again expecting a different result. The web rolls back its optimistic value on error (`use-api-settings.ts:117-122`) and then refetches (`onSettled`), so the field shows the saved value; the toast is a warning, not "Update failed". With the bound in place, nothing known makes the callback fail; the path exists so a scheduler failure cannot leave the screen and the scheduler disagreeing silently.

### Rendering a null boolean (`SettingField`, decision)

```tsx
const isUnset = type === 'bool' && value === null && !field.isDirty;
const stateLabel = !isUnset
  ? (Boolean(field.value) ? 'Enabled' : 'Disabled')
  : gameDefault === undefined
    ? 'Not set'
    : `${gameDefault ? 'Enabled' : 'Disabled'} (default)`;
```

- **Switch position.** Known default: the switch shows it. Unknown default: unchecked, labeled "Not set"; switching it on saves `true`. An unchecked track next to "Not set" is the closest a two-state switch gets; no third state is added.
- **Explicit value equal to the default.** With "Enabled (default)" the switch is on, so one click saves `false`; to store an explicit `true` the admin switches twice. Accepted: the game behaves the same either way.
- **After a save.** `useUpdateGameSetting` writes the new value into the cached config on mutate (`hooks/use-game-config.ts:92-110`), so `value` stops being null and the label loses "(default)" at once; the refetch confirms it. `field.isDirty` covers the moment between the switch and that cache write.
- **Told apart from a redacted secret (Story 17.5).** 17.5 marks a secret setting with `secret: true` and sends `value: null` (with `configured`) to Monitor keys; the only secret is `Password`, a string. A null boolean has `type: 'bool'` and no `secret`. Keep 17.5's secret branch first wherever it lives (re-read `SettingField.tsx` and `GameConfigPanel.tsx` after rebasing on 17.5) and make this story's branch depend on `type === 'bool'`, so neither can render the other. `default` is never set on a secret setting.
- **Env-managed booleans** get their value written at init (`services/config_init.py`), so they are not null in practice; if one is, it renders the same way, disabled.

### Defaults: evidence (decision)

- **`EntitySpawning`: default on.** Sources in the repo: `agentdocs/vs-serverconfig-commands.md:31` ("Creature spawning (default: on)", written in Epic 6 preparation; its own source is not recorded). A new VintageStory world spawns creatures, which is consistent with on. **How sure:** the "on" is credible but not confirmed from game code or a freshly generated config; the maintainer accepted it as the default for this story.
- **Finding that changes the picture (see "ADR against the code").** `EntitySpawning` is not a `serverconfig.json` setting in VintageStory 1.22.7. The game-written `serverconfig.json` on the dev stack (`ConfigVersion` 1.10, 77 keys) has no `EntitySpawning` key while it has every other managed key; the manager's template (`api/src/vintagestory_api/templates/serverconfig-template.json`, `ConfigVersion` 1.9) has none either; and the game libraries (`data/server/VintagestoryLib.dll`, `VintagestoryAPI.dll`) expose `EntitySpawning` as a property of `ISaveGame` (the world save), not of `IServerConfig` (whose documented properties include `AllowPvP`, `AllowFireSpread`, `AllowFallingBlocks`). So the API reads it from a file where the game never writes it: it is null on every server, and the effective value lives in the save, which the manager cannot read. "Enabled (default)" is right for a world whose spawning was never changed and wrong for one where `/serverconfig entityspawning false` was run.
- **The other six booleans** (`AllowPvP`, `AllowFireSpread`, `AllowFallingBlocks`, `PassTimeWhenEmpty`, `Upnp`, `AdvertiseServer`) are written by the game into every `serverconfig.json`, so they are null only in a hand-edited file. The only values in the repo are the manager's template ("sensible defaults based on VintageStory default config and DarkMatterProductions patterns", Story 6.0) and the dev stack's file, which is not independent of it; neither is the game's built-in default. They get no `default` and show "Not set" if ever null. Add one only with game-sourced evidence (Task 4.1).

### ADR against the code

- **ADR-5:** correct against the code; nothing changed. Two additions it does not state: the interval upper bound (the scheduler cannot hold every `int`) and that a same-value save restarts the countdown.
- **Epic 17 / sprint change proposal (FR188 for `EntitySpawning`):** both assume `EntitySpawning` is missing from `serverconfig.json` by accident and will be "confirmed against a freshly generated server config". It is missing by design (see "Defaults: evidence"), so no generated config can confirm it. This story still does what FR188 and the maintainer's decision ask (show "Enabled (default)"), because that is strictly better than "Disabled" for the common case. It does not fix the deeper problem: while the server is stopped, the toggle writes a key the game ignores (and probably drops when it rewrites the file); while it runs, the console command changes the save but not the file, so the label stays "(default)". That is a modeling defect from Story 6.2, outside `VSS-2le`'s scope, and is listed as a follow-up for the maintainer.

### API tests

Use the real `SchedulerService` (started in an async fixture, as `tests/test_jobs_registration.py:33-39`), and inspect jobs with `job_to_info(job)` (`models/jobs.py:35-77`; returns `trigger_details` "every N seconds" and a typed `next_run_time`). For the next-run check take `before`/`after` timestamps around the call and assert `before + N - 1 s <= next_run_time <= after + N`; no clock mocking is needed.

**No real job may run in these tests.** `startup=True` for `server_versions_check` sets the next run to now, and a started scheduler then runs `check_server_versions` (network; the lifespan tests already log "Job check_server_versions raised an exception" for this reason). The function imports the job functions lazily (`from module import name` at call time), so `monkeypatch.setattr` the three names in `vintagestory_api.jobs.mod_cache_refresh`, `.server_versions` and `.metrics_collection` to no-op async functions in a fixture used by every Task 1 and Task 2 test that drives a started scheduler.

| Task | File | Tests |
|---|---|---|
| 1 | `tests/test_jobs_registration.py`, new `TestApplyIntervalSetting` | parametrized over the three keys: changed (3600 → 600: one job, "every 600 seconds", next run as above); to 0 (job gone); from 0 (job added, next run one interval away, also `server_versions_check`); 0 → 0 (no job, no error); `startup=True` for `server_versions_refresh_interval` gives `next_run_time` ≈ now and for the other two one interval away. Running job (AC 4): register a job under `mod_cache_refresh` whose coroutine waits on an `asyncio.Event` and records that it finished, with `run_immediately=True`; once it has started, `apply_interval_setting(..., 600)` then `..., 0)`; set the event; the coroutine finishes normally (not cancelled) |
| 1 | `tests/test_jobs_registration.py` existing classes | unchanged: `register_default_jobs` still registers the same jobs, logs `job_registered`, and registers none when all are 0 |
| 2 | `tests/test_api_settings.py` | `ApiSettings(mod_list_refresh_interval=31_536_001)` raises; `update_setting(key, 31_536_001)` raises `ApiSettingInvalidError` for each key and leaves the file unchanged; a callback that raises → `ApiSettingNotAppliedError` with the key in the message, the new value saved (`get_settings()`), `api_setting_not_applied` logged; `TestSchedulerCallback` (`:290-347`) keeps its mock-callback tests (they test the service contract) |
| 2 | `tests/test_routers_config.py`, new class | app with `get_server_service` overridden to the existing `mock_server_service`/`temp_settings` (so writes go to the temp dir), `get_scheduler` (`routers/jobs.py`) overridden to a real started `SchedulerService`, and `get_api_settings_service` **not** overridden. `POST .../mod_list_refresh_interval {"value": 600}` → 200, then `GET /api/v1alpha1/jobs` lists `mod_cache_refresh` with `trigger_details` "every 600 seconds"; `{"value": 0}` → 200 and the job is gone; `{"value": 3600}` → back. Same three steps for the other two keys (parametrize). `31_536_001` → 400 `API_SETTING_INVALID`, job unchanged. Make the scheduler's `add_interval_job` raise (monkeypatch on the instance) → 500 `API_SETTING_NOT_APPLIED`, and `GET /config/api` returns the saved value. If `TestClient` (it runs the app on its own thread) cannot drive the scheduler started on the test's loop, use `httpx.AsyncClient(transport=ASGITransport(app=app))` instead |
| 4 | `tests/test_game_config.py` | `get_settings().to_dict()`: `EntitySpawning` has `"default": True` with and without a value in the file; no other setting has a `default` key; `SettingInfo(...).to_dict()` omits `default` when None. A config without `EntitySpawning` returns `value: None` and `default: True` |
| 4 | `tests/test_routers_config.py` | `GET /config/game` on a config without `EntitySpawning`: that setting is `{"value": null, "default": true, ...}` |

### Web tests

| Task | File | Test |
|---|---|---|
| 3 | `src/hooks/use-api-settings.test.tsx` (`useUpdateApiSetting`, `:143`) | after saving `mod_list_refresh_interval`, `queryKeys.jobs.all` is invalidated (spy on `invalidateQueries`), also when the request fails; after saving `auto_start_server` it is not |
| 3 | `src/features/settings/ApiSettingsPanel.test.tsx` | a 500 `API_SETTING_NOT_APPLIED` answer shows a warning toast with the API message and no "Update failed" toast. The file's `sonner` mock (`:13-19`) has `success`, `error` and `info` only: add `warning: vi.fn()`, or the component throws on the new call |
| 3 | `src/features/settings/ScheduledJobsPanel.test.tsx` or `SettingsPage.test.tsx` | optional if the hook test covers it; do not add a timing-based test |
| 4 | `src/components/SettingField.test.tsx` (new describe "Story 17.6: booleans with no value") | `value={null}`, `type="bool"`, `gameDefault={true}`: switch checked, `setting-state-<key>` reads "Enabled (default)"; `gameDefault={false}`: unchecked, "Disabled (default)"; no `gameDefault`: unchecked, "Not set" and the label contains neither "Enabled" nor "Disabled"; switching from "Enabled (default)" calls `onSave` with `false` and the label reads "Disabled"; switching from "Not set" calls `onSave` with `true`; `value={true}` with `gameDefault={false}` reads plain "Enabled" (default ignored when a value exists). Existing "boolean input" tests (`:184-300`) stay as they are |
| 4 | `src/features/game-server/GameConfigPanel.test.tsx` | a config whose `EntitySpawning` is `{ value: null, default: true }` and `AllowPvP` is `{ value: null }` (no default): "Enabled (default)" and "Not set"; with 17.5 in place, a Monitor-style Password `{ value: null, secret: true, configured: true }` still renders 17.5's "Set" (the two branches do not interfere) |

### E2E (`web/e2e/settings-as-saved.spec.ts`)

Style of `e2e/settings-empty-values.spec.ts` (header comment with requirements; API key from `VS_API_KEY_ADMIN`; viewport 1440x900). No screenshots. Game settings page: `/game-server/settings`; API Settings and Scheduled Jobs: `/config` (tabs `api-settings-tab`, `scheduled-jobs-tab`).

1. **Null booleans, stubbed.** `page.route('**/api/v1alpha1/config/game', ...)`: fetch the real response with `route.fetch()`, then set `EntitySpawning` to `value: null, default: true` and `AllowFireSpread` to `value: null` without `default`, and fulfill. Assert `setting-state-EntitySpawning` reads "Enabled (default)" and `setting-state-AllowFireSpread` reads "Not set". Then stub `POST **/config/game/settings/EntitySpawning` to fulfill `{status:"ok", data:{key:"EntitySpawning", value:false, method:"file_update", pending_restart:false}}` and make the GET stub return `value: false` from then on; switch Entity Spawning; the label reads "Disabled". Every other `POST`/`DELETE` under `/config/game` is fulfilled with 500 so nothing real is written; the server name and password are never read into an assertion or screenshot.
2. **Interval through the real API (serial describe, snapshot guard).** `beforeAll`: snapshot `GET /config/api` (`mod_list_refresh_interval`) and `GET /jobs` with `hasSnapshot = true`. Test: on `/config` API Settings, set Mod List Refresh to `2h` (or `3h` if the snapshot is 7200), blur, wait for the success toast; open Scheduled Jobs: `job-schedule-mod_cache_refresh` reads "every 2h" (or "every 3h") and `job-next-run-mod_cache_refresh` changed from the snapshot, without reload. Through the API: `POST .../mod_list_refresh_interval {"value": 0}` → `GET /jobs` has no `mod_cache_refresh`; `POST` the snapshot value back → the job is listed with the snapshot schedule. `afterAll` (refuses without the snapshot): if `GET /config/api` differs from the snapshot, `POST` the snapshot value. Expected residue: the restored job's next run is one interval after the restore, not the old time (a restart would do the same); record it. If the snapshot value is 0, assert the transitions from 0 instead and restore 0. Do not touch the other two intervals on the stack (unit and router tests cover them).

### Existing tests that change (deliberately)

Found by running the affected API files against a throwaway prototype of Task 1 and the Task 2 wiring (since discarded); the web side was not prototyped.

- `api/tests/test_api_settings.py:724-730` `test_accepts_very_large_integer_string` ("999999999"): now above the bound; change to accept `"31536000"` and add the rejection of `"31536001"`. (Task 2)
- `api/tests/test_routers_config.py:1416-1430` `test_get_api_settings_service_factory`: calls `get_api_settings_service(server_service=...)`; pass `scheduler=SchedulerService()` too and assert the service was built (it passes without, because the default is the `Depends` marker, but that is accidental). (Task 2)
- `api/tests/test_jobs_registration.py` `test_mod_cache_refresh_logs_registration`, `test_server_versions_check_logs_registration`, `test_metrics_collection_logs_registration`: fail if the `job_registered` log is dropped; keep the log (Task 1.2), do not change the tests.
- **Environment, not regressions:** `tests/test_jobs_registration.py` `TestJobRegistrationLifespan` (2), `tests/test_scheduler.py` `TestSchedulerLifespanIntegration` (4) and all of `tests/test_jobs_router.py` (12, errors) fail in a checkout without `.env` (`ValueError: VS_API_KEY_ADMIN must be set`, `config.py:178`); they failed identically on the unmodified base in the story-creation worktree. Run `just check` where `.env` exists.
- Router tests that use the real `get_api_settings_service` must override `get_server_service` with temp settings; otherwise `Settings()` resolves `VS_DATA_DIR=../dev` (`Justfile:35`) and writes `dev/vsmanager/state/api-settings.json`.
- Anything else that fails is a regression (AC 13): fix the code, not the test.

### Not changed (do not "fix" these here)

- How `EntitySpawning` is stored and applied (savegame vs. `serverconfig.json`; see "ADR against the code").
- The UI ranges of the interval fields, and `metrics_collection_interval` having no UI field (`ApiSettingsPanel.tsx:145-173`); 0 is reachable through the API only, as today.
- `DELETE /jobs/{id}`, `GET /jobs` response shape, `JobsTable` formatting.
- The game settings update path (`update_setting`, console vs. file), Story 17.5's secret handling.

### API contract (`v1alpha1`)

- `GET /config/game` settings gain an optional `default` (boolean; only `EntitySpawning` today). Additive.
- `POST /config/api/settings/{key}`: interval values above 31,536,000 → 400 `API_SETTING_INVALID`; new 500 `API_SETTING_NOT_APPLIED` (value saved, job not rescheduled). Success bodies unchanged.
- `GET /jobs` reflects a changed interval immediately.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review. Every commit is green; after Task 1 nothing visible changes, after Task 2 the API reschedules and the web is unaware until Task 3.

### Security Requirements

- `POST /config/api/settings/{key}` stays Admin-only (`RequireAdmin`); `GET /jobs` stays Admin-only. `GET /config/game` keeps `RequireAuth`; `default` is public game knowledge. The not-applied message carries the key and the scheduler's error text only; interval settings are never secrets (`SECRET_SETTINGS` is the webhook URL only, `services/api_settings.py:83`).

### Development Commands

- `just test-api tests/test_jobs_registration.py tests/test_api_settings.py tests/test_routers_config.py tests/test_scheduler.py tests/test_jobs_router.py tests/test_game_config.py`, `just test-web src/components/SettingField.test.tsx src/features/game-server/GameConfigPanel.test.tsx src/hooks/use-api-settings.test.tsx src/features/settings/ApiSettingsPanel.test.tsx`, `just typecheck-api`, `just typecheck-web`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **17.4:** router tests must not reach real singletons that write into `dev/` (it found `mod-updates.json` written); here the risk is `api-settings.json`. E2E that changes real state needs a snapshot guard and must restore the stack exactly, and must stay safe when spec files run in parallel (its M1): this spec is the only one that changes API settings.
- **17.3:** a hook's own `onError` replaces the query client's default handler (`api/query-client.ts:34-39`), so `ApiSettingsPanel`'s toast is the only one; tests must not read private members (`reportPrivateUsage`).
- **17.2:** a `feat`/`fix` subject must describe what an admin sees; do not use `just format-api`.
- **17.1:** pyright strict baseline 0 errors, 3 pre-existing warnings in tests; keep each commit green.
- **16.8:** introduced null strings/numbers as empty fields and the masked password; its E2E (`settings-empty-values.spec.ts`) reads only and must still pass.
- **8.3 / 7.2:** `useJobs` polls every 30 s (`hooks/use-jobs.ts:43`) and the global `staleTime` is 30 s (`api/query-client.ts:19`), which is why the Scheduled Jobs tab can show the old schedule after a save (AC 5).

### Git Intelligence

- Base 21457bf (Story 17.4 done). Planned subjects: Task 1 `refactor` (no visible change), Task 2 `fix` (a changed refresh interval applies without restarting the API), Task 3 `fix` (Scheduled Jobs shows a changed interval right away), Task 4 `fix` (a game setting with no value shows the game's default or "Not set"), Task 5 `test`, Task 6 `docs`. Release notes come from commit subjects (`cliff.toml`).

### Latest Technical Information

- APScheduler 3.11.3 (`api/uv.lock`); the project pins `<4.0` (`services/scheduler.py:9`). `add_job(..., replace_existing=True)` on a running scheduler replaces the stored job; an `IntervalTrigger` without `start_date` starts at now + interval. The package ships no `py.typed`; reach jobs through `SchedulerService` and `job_to_info` so no new suppression is needed.
- TanStack Query v5: `onSettled(data, error, variables, context)`; `invalidateQueries({ queryKey: ['jobs'] })` refetches the mounted Scheduled Jobs query, or marks it stale for its next mount.

### Project Structure Notes

- New: `web/e2e/settings-as-saved.spec.ts`.
- Modified: `api/src/vintagestory_api/jobs/__init__.py`, `services/api_settings.py`, `routers/config.py`, `models/errors.py`, `services/game_config.py`; `api/tests/test_jobs_registration.py`, `test_api_settings.py`, `test_routers_config.py`, `test_game_config.py`; `web/src/api/config.ts`, `web/src/api/types.ts`, `web/src/hooks/use-api-settings.ts`, `web/src/features/settings/ApiSettingsPanel.tsx`, `web/src/components/SettingField.tsx`, `web/src/features/game-server/GameConfigPanel.tsx`, and the web tests above.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.6: Settings Behave as Saved]
- [Source: _bmad-output/planning-artifacts/prd.md] FR187, FR188
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-5: Interval Settings Drive Their Jobs] (ADR-4 for 17.5's `secret`/`configured`)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md] (open question for 17.6; API contract changes)
- [Source: _bmad-output/implementation-artifacts/16-8-name-sort-and-empty-settings.md] (null strings/numbers; bead `VSS-2le` found there)
- [Source: _bmad-output/implementation-artifacts/17-4-installed-status-is-right-everywhere.md] (structure, review learnings)
- `agentdocs/vs-serverconfig-commands.md` (`EntitySpawning` row, `:31`)
- Beads: `VSS-8bl`, `VSS-2le`, parent `VSS-4v5`
- `project-context.md` (no suppressions; manual test tasks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Started from `story/17-5-monitor-keys-cannot-read-the-server-password` at 252498e (Story 17.5 done, stacked on 17.7 and 17.4); the story file was cherry-picked from `draft/17-6-settings-behave-as-saved` (5d70c5e). Every line reference written at 21457bf was re-read before use. Unchanged since 21457bf: `jobs/__init__.py`, `services/api_settings.py`, `services/scheduler.py`, `routers/jobs.py`, `models/jobs.py`, `models/errors.py`. Moved by Story 17.5: in `routers/config.py` `get_api_settings_service` is now `:242-265` (was `:226-249`) and `update_api_setting` `:297-358`.

### Completion Notes List

- Story created 2026-11-15: context from the interval wiring (`ApiSettingsService`, `get_api_settings_service`, `register_default_jobs`, `SchedulerService`, `main.py` lifespan, `routers/jobs.py`, `job_to_info`), the web API Settings and Scheduled Jobs tabs and their hooks, the game settings service and `SettingField`/`GameConfigPanel`, Story 16.8, the Epic 17 ADRs and the 17.1-17.4 reviews. The scheduler half was prototyped (apply function, router wiring, a real-scheduler test) and the affected API test files run against it; the prototype was discarded.

- Task 1: `jobs/__init__.py` gained `INTERVAL_JOBS`, a lazy-import `_job_function(key)` and `apply_interval_setting(scheduler, key, seconds, *, startup=False)`: above 0 it calls `add_interval_job` (which replaces with a new `IntervalTrigger`, so the next run is one interval from now), with `run_immediately` only for `server_versions_check` at startup; 0 removes the job only when `get_job` finds it; an unknown key raises `KeyError`. It logs `job_registered` (`job_id`, `interval_seconds`, and `run_immediately=True` for the startup run of `server_versions_check`). `register_default_jobs` reads the settings as before and calls it for each key with `startup=True`, then logs `default_jobs_registered` with the count. No suppression: the function only uses `add_interval_job`, `get_job(...) is not None` and `remove_job`. Tests (`TestApplyIntervalSetting`, 17): the table; changed, to 0, from 0 and 0 to 0 for each key (real started scheduler, read through `job_to_info`, next run between `before + N - 1 s` and `after + N`); startup leaves the other two jobs one interval away, and on a scheduler not yet started `server_versions_check` has `next_run_time` between before and after (on a started scheduler the immediate run would fire at once, so the "now" is checked before start); unknown key; a running execution under `mod_cache_refresh` survives a change to 600 and then 0 and finishes (not cancelled). A `no_real_jobs` fixture replaces the three job functions with a no-op so no test reaches the network. The existing classes are unchanged and pass, including the three `*_logs_registration` tests. Red first: the module did not import (`INTERVAL_JOBS`, `apply_interval_setting` missing). The file: 49 passed; ruff clean; pyright 0 errors, the 3 pre-existing warnings.

- Task 2: `MAX_INTERVAL_SECONDS = 31_536_000` (module level, docstring as in 2.1) and `le=MAX_INTERVAL_SECONDS` on the three interval fields, descriptions saying "at most 365 days". `ApiSettingNotAppliedError(key, reason)` after `ApiSettingInvalidError`, with the story's message. `update_setting` calls the callback inside `try`/`except Exception`, logs `api_setting_not_applied` (error; `key`, `value`, `error`) and re-raises the typed error `from e`; the constructor docstring no longer says "stub for Epic 7". `get_api_settings_service` takes `scheduler: SchedulerService = Depends(get_scheduler)` (imported from `routers/jobs.py`) and passes `scheduler_callback=partial(apply_interval_setting, scheduler)`; the Epic 7 TODO is gone; `update_api_setting` documents all three intervals, 0, the bound and the 500, and maps `ApiSettingNotAppliedError` to 500 `API_SETTING_NOT_APPLIED` (new `ErrorCode` after `API_SETTING_INVALID`). The interval key tuple in `update_setting` stays: importing `INTERVAL_JOBS` there would make `services` import `jobs`, which imports `services.api_settings` (a cycle). Tests: `test_api_settings.py` `TestIntervalBound` (the constant; the model accepts 31,536,000 and refuses 31,536,001 for each key; `update_setting` above the bound raises `ApiSettingInvalidError`, leaves the file byte-identical and does not call the callback) and `TestSchedulerCallbackFailure` (the message; a raising callback gives `ApiSettingNotAppliedError` with the key and reason, `__cause__` kept, the value saved, `api_setting_not_applied` logged), for every key; `TestSchedulerCallback` unchanged. `test_routers_config.py` `TestIntervalSettingsReschedule`: `httpx.AsyncClient` over `ASGITransport` (so the app runs on the loop the real started scheduler runs on), `get_settings`/`get_server_service` overridden to the temp settings, `get_scheduler` to the real scheduler, `get_api_settings_service` not overridden; for each key 600 → `GET /jobs` "every 600 seconds", 0 → job gone, 3600 → back, and the file written in the temp state dir; a non-interval setting leaves `GET /jobs` unchanged; 31,536,001 → 400 `API_SETTING_INVALID`, jobs and saved value unchanged; `add_interval_job` raising on the instance → 500 `API_SETTING_NOT_APPLIED` whose message names the key, the reason and the restart, and `GET /config/api` returns the saved value. The job functions are no-ops in these tests. Existing tests changed as the story lists: `test_accepts_very_large_integer_string` now uses "31536000", with a new rejection of "31536001"; `test_get_api_settings_service_factory` passes `scheduler=SchedulerService()`. Red first: the service test module did not import, and 6 router tests failed (5 new, the factory test). After: the API files of the story 284 passed; full `just test-api` 2668 passed; nothing written under `dev/`; ruff clean; pyright 0 errors, 3 warnings.

- Task 3: `INTERVAL_API_SETTINGS` in `api/config.ts` after `SECRET_API_SETTINGS`. `useUpdateApiSetting` `onSettled(_data, _error, { key })` also invalidates `queryKeys.jobs.all` for an interval key, on success and on error. `ApiSettingsPanel.handleSave` shows `toast.warning('Saved, not applied yet', { description: err.message })` for an `ApiError` with code `API_SETTING_NOT_APPLIED` and still rethrows; anything else keeps "Update failed". The hook's own `onError` replaces the query client's default handler (`api/query-client.ts`), so the warning is the only toast. Tests: `use-api-settings.test.tsx` "useUpdateApiSetting and Scheduled Jobs (Story 17.6)" (the jobs query is invalidated after saving each of the three intervals and after a 500 `API_SETTING_NOT_APPLIED`; not after `auto_start_server`); `ApiSettingsPanel.test.tsx` (the `sonner` mock gains `warning`; a 500 `API_SETTING_NOT_APPLIED` on Mod List Refresh shows one warning toast with the API message, and neither an error nor a success toast). No timing-based Scheduled Jobs test (optional per the story; the hook test covers the invalidation). Red first: 5 failed. The two files: 58 passed; `just typecheck-web` and `just lint-web` clean.

- Task 4.1 (evidence, recorded before coding): the only default relied on is `EntitySpawning` = on, from `agentdocs/vs-serverconfig-commands.md:31` ("Creature spawning (default: on)"; its own source is not recorded), credible but not confirmed from game code. Re-checked on this branch: the dev stack's game-written `data/serverdata/serverconfig.json` (`ConfigVersion` 1.10, 77 keys) has no `EntitySpawning` key and has all six other managed booleans; no decompiler is installed here, so the game libraries were not read further. No game-sourced evidence was found for any other boolean, so none was added.
- Task 4: `ServerSetting.default: bool | None = None` (docstring as in 4.2; "this table is the one place defaults live"), `default=True` on `EntitySpawning` with a one-line comment naming the evidence; `SettingInfo.default`, added to `to_dict` only when not None; `get_settings` passes `setting_def.default` for every role (the default is public game knowledge; Password has none). Web: `GameSetting.default?: boolean`; `SettingField` prop `gameDefault?: boolean`; the bool initial value is `value === null ? (gameDefault ?? false) : Boolean(value)`; the state span has `data-testid="setting-state-<key>"` and reads "Enabled (default)"/"Disabled (default)" with a known default, "Not set" without one, and the plain state otherwise; `GameConfigPanel.renderSetting` passes `gameDefault={setting.default}` after 17.5's `configured` branch, which stays first. Tests: `test_game_config.py` `TestGameDefaults` (no default by default; `EntitySpawning` is the only setting with one; no secret has one; `SettingInfo.to_dict` omits/includes it; `get_settings` for Admin and Monitor with and without `EntitySpawning` in the file: `value` true/None, `default: true`, no other setting has the key); `test_routers_config.py` `TestGameSettingsDefault` (`GET /config/game` on a config without `EntitySpawning`, both keys: `{"value": null, "default": true}`, `AllowPvP` without `default`); `SettingField.test.tsx` "Story 17.6: booleans with no value" (the six cases of the story); `GameConfigPanel.test.tsx` "Story 17.6: booleans with no value" (`EntitySpawning` `{value: null, default: true}` reads "Enabled (default)" and is checked, `AllowPvP` `{value: null}` reads "Not set" and is unchecked; with a Monitor-style Password `{value: null, secret: true, configured: true}` 17.5's "Set" status is still shown, with no `#Password` and no `setting-state-Password`). Existing "boolean input" tests unchanged and passing. Red first: 11 API tests and 8 web tests failed. API files 248 passed, web files 77 passed; typecheck and lint clean for both.
- Deviation (Task 4.4, the label condition): the story's `isUnset = type === 'bool' && value === null && !field.isDirty` reads "(default)" again once a save resolves while the `value` prop is still null, because `useSettingField.save` sets its initial ref to the saved value on success, so `isDirty` turns false while the switch shows the new position (e.g. unchecked next to "Enabled (default)"). In the app the optimistic cache write gives the setting its value first, but the story's own unit test (a static `value={null}`) would fail and the label would depend on that ordering. Used instead `isUnset = type === 'bool' && value === null && field.value === initialValue`: the "(default)"/"Not set" label shows only while the switch is where it started; once moved it is the plain state; after a failed save the cache rolls back to null, the field resets to the default and the label returns to "(default)". Same results for every case the story lists.

### File List

- `api/src/vintagestory_api/jobs/__init__.py`
- `api/tests/test_jobs_registration.py`
- `api/src/vintagestory_api/services/api_settings.py`
- `api/src/vintagestory_api/routers/config.py`
- `api/src/vintagestory_api/models/errors.py`
- `api/tests/test_api_settings.py`
- `api/tests/test_routers_config.py`
- `web/src/api/config.ts`
- `web/src/hooks/use-api-settings.ts`
- `web/src/hooks/use-api-settings.test.tsx`
- `web/src/features/settings/ApiSettingsPanel.tsx`
- `web/src/features/settings/ApiSettingsPanel.test.tsx`
- `api/src/vintagestory_api/services/game_config.py`
- `api/tests/test_game_config.py`
- `web/src/api/types.ts`
- `web/src/components/SettingField.tsx`
- `web/src/components/SettingField.test.tsx`
- `web/src/features/game-server/GameConfigPanel.tsx`
- `web/src/features/game-server/GameConfigPanel.test.tsx`

## Change Log

- 2026-11-15: Story 17.6 created (ready-for-dev).
- 2026-11-15: Validated against the create-story checklist (see the story-creation report): interval upper bound added after the prototype showed an unbounded value overflows the scheduler after it is saved; `job_registered` log kept after the prototype broke three log tests; lifespan test failures traced to the missing `.env`, not the change; `EntitySpawning` found to be a savegame property, not a `serverconfig.json` key, so only it gets a known default and the finding is recorded under "ADR against the code"; router tests told to keep writes out of `dev/`.
