# Story 19.7: E2E Runs in CI

Status: ready-for-dev

<!-- Implements FR228-FR230, Epic 19 ADR-14 (and ADR-5 decision 8). Bead: VSS-wenx (TOOLS-007, task, P4, size-m). Last story of Epic 19, stacked on Story 19.6 (stories run in order 19.1 to 19.7). Line references were verified at b6ae2f2 (epic-19-planning) and must be re-checked at implementation time: Story 19.2 adds the `/config.js` helper and its no-key spec, Story 19.3 adds the policy spec, and Stories 19.1 and 19.2 edit the compose files and the README. Tests, tooling and CI only: no API source change, no web source change, no API contract change, no new dependency, no release note. -->

## Story

As a **maintainer**,
I want **the browser tests to run against the built image on every pull request**,
so that **a change that breaks the page is caught before it is merged**.

## Acceptance Criteria

1. **Given** a pull request or a push to `main` **When** CI runs **Then** an `e2e` job builds the image, starts a container from it with a data directory that holds only the seeded `serverconfig.json` fixture and with placeholder keys, waits for `/healthz`, runs the E2E tests that carry no tag, and fails the run when one fails. *(FR228)*
2. **Given** the `e2e` job **When** it starts the container **Then** `VS_API_KEY` is set as Story 19.2 requires (to the placeholder Admin key), no game server is installed or started, and no real key or instance data is in the workflow or in the script it calls. *(FR228)*
3. **Given** a failed `e2e` job **When** I open the run **Then** the Playwright report is attached as an artifact. *(FR228)*
4. **Given** the E2E specs **When** I read them **Then** every test that needs the live mod database is tagged `@moddb`, every test that needs a game server that is installed or has run is tagged `@game-server`, every test that installs or removes a real mod is tagged `@install`, and each tag is explained in one place (`web/e2e/README.md`). *(FR229)*
5. **Given** the fixture `web/e2e/fixtures/serverconfig.json` **When** I read it **Then** it holds made-up values only, and the CI run copies it to `serverdata/serverconfig.json` in the container's data directory before the container starts. *(FR228)*
6. **Given** the settings specs (`settings-desktop-layout`, `settings-empty-values`, `settings-as-saved`, `monitor-password-redaction`) **When** they run against the seeded stack in CI **Then** each test that passes there carries no tag and runs in CI, and any test that still needs an installed or running game server keeps `@game-server` with a one-line reason. *(FR229)*
7. **Given** the CI invocation **When** it runs **Then** it leaves out the three tags, includes the no-key spec of Story 19.2 and the policy spec of Story 19.3, and the same `just` recipe (`just test-e2e-ci`) runs it on a developer's machine without touching the dev stack or `./data`. *(FR229)*
8. **Given** `just test-e2e-web` on a developer's machine with a game server installed **When** it runs **Then** it still runs every spec, tagged or not. *(FR229)*
9. **Given** the E2E specs **When** I search them for `localStorage.setItem('apiKey'` **Then** there is no match, and every spec that loads a page gets its key through the helper of Story 19.2. *(FR230)*
10. **Given** the workflow files **When** `just lint-workflows` runs **Then** it passes, and every action is pinned by commit like the existing jobs (`just test-scripts` asserts the pinning). *(FR228)*
11. **Given** a stack with no game server and the seeded configuration **When** an untagged test opens Game Settings, a Mods page or the Console **Then** the page renders its real content, because the shared helper answers `GET /api/v1alpha1/server/status` as installed when the stack says `not_installed`, and leaves the answer of a stack that has a game server unchanged. (Added by this story. See Dev Notes "ADR against the code".)
12. **Given** the container that `just test-e2e-ci` starts **When** the API inside it calls the mod database or the vendor's version API **Then** the call fails at once, so an untagged test that depends on either fails on every run and cannot pass by luck. (Added by this story. See Dev Notes "The stack the recipe starts".)
13. **Given** `web/e2e/terminal.spec.ts`, which opens `/terminal`, a route the web has not had since Epic 11 **When** this story is done **Then** the spec opens the Console page at `/game-server/console`, its tests pass on the seeded stack and carry no tag, and no test was skipped, tagged or deleted to get a green run without the maintainer's agreement. (Added by this story. See Dev Notes "terminal.spec.ts".)
14. **Given** this story's pull request **When** CI has run on it **Then** the `E2E tests` job passed, and the story records the run's URL and the number of tests it ran. *(FR228)*

## Tasks / Subtasks

<!-- Commit per task: type(story-19.7/task-N): ... with type test, ci, build, chore or docs. No feat, fix or perf: nothing here is visible to an admin, so nothing may reach the release notes. The order differs from the epic's task list in one place: the recipe (Task 3) comes before the tagging (Task 4), because the tagging is decided by running each spec against the stack the recipe starts. -->

- [ ] Task 1: Every spec gets its key through the Story 19.2 helper, and the dead `localStorage` scripts go + test (AC: 9) (`VSS-wenx`)
  - [ ] 1.1: New `scripts/tests/test-e2e-ci.sh` (style of `scripts/tests/test-docker-context.sh`, `lib.sh` helpers `pass`, `fail`, `assert_eq`, `finish`). First assertion, red first: `grep -rn "localStorage.setItem" web/e2e api/tests/e2e` finds nothing. `scripts/tests/run.sh` picks up `test-*.sh` by itself. Later tasks add assertions to this file
  - [ ] 1.2: Remove the 17 `page.addInitScript(... localStorage.setItem('apiKey', apiKey) ...)` blocks from the fifteen specs (Dev Notes "Inventory", column "Init scripts"), with the comments that describe them (for example `terminal.spec.ts:28-29`)
  - [ ] 1.3: Replace the six hand-written `/config.js` answers with the helper: `layout-widths.spec.ts:104-109`, `mod-detail-media.spec.ts:101-106`, `settings-desktop-layout.spec.ts:40-45`, `settings-empty-values.spec.ts:48-53`, `settings-as-saved.spec.ts:42-47`, `monitor-password-redaction.spec.ts:45-50` (`usePageKey`, which takes the key as an argument and is called with the Monitor key at `:108`). Keep what else those functions do (`readOnly` also refuses every write, `:110-117`)
  - [ ] 1.4: The twelve specs that relied on the stack's own `/config.js` call the helper with the Admin key before their first `page.goto`. Use the helper exactly as Story 19.2 shipped it (name, file, signature). Do not write a second helper and do not copy its body into a spec
  - [ ] 1.5: `api/tests/e2e/conftest.py`: delete the unused `authenticated_page` fixture (`:81-94`), which sets the same dead `localStorage` key, and fix the two docstrings that name a recipe that does not exist (`just docker-start` at `:56` and `:61` is `just docker start`)
  - [ ] 1.6: `cd web && bunx playwright test --list` still lists every test (127 at b6ae2f2 plus the tests of Stories 19.2 and 19.3) with no load error. Then `git restore web/playwright-report web/test-results` (Dev Notes "Tracked report files")

- [ ] Task 2: The `serverconfig.json` fixture and the server status stub + test (AC: 5, 11)
  - [ ] 2.1: `web/e2e/fixtures/serverconfig.json` (Dev Notes "The fixture"): a copy of `api/src/vintagestory_api/templates/serverconfig-template.json` with four values changed. Add to `scripts/tests/test-e2e-ci.sh`, red first: the file parses as JSON (`yq` is in `mise.toml`), `ServerName` is `E2E Fixture Server`, `ServerDescription` and `Ip` are `null`, `Password` is `e2e-fixture-password`
  - [ ] 2.2: In the module that holds Story 19.2's key helper, add a function that makes a stack without a game server look installed to the page (Dev Notes "The server status stub"). It rewrites the answer only when the real state is `not_installed`
  - [ ] 2.3: Call it in the set-up of every spec whose tests open a page behind the installed check: `/game-server/settings`, `/game-server/mods/**`, `/game-server/console`. That is every spec except `file-browser-navigation` (it opens `/config` only). Include the specs of Stories 19.2 and 19.3 where they open such a page
  - [ ] 2.4: Update the header comment of each spec that says it needs "a game server installed" only for the page to render (`settings-desktop-layout.spec.ts:16`, `settings-empty-values.spec.ts:14-15`, `monitor-password-redaction.spec.ts:19-20`, `layout-widths.spec.ts:30-31`): it now needs a `serverconfig.json`, which the seeded stack and a stack with a game server both have

- [ ] Task 3: `just test-e2e-ci`: one command that starts the seeded stack, runs the untagged tests and removes the stack + test (AC: 1, 2, 5, 7, 8, 12)
  - [ ] 3.1: New `scripts/e2e-ci.sh` (Dev Notes "The stack the recipe starts" has the steps and the reasons). Add it to the ShellCheck list in the `lint-scripts` recipe (`Justfile:143`)
  - [ ] 3.2: `Justfile`, in the TESTING section after `test-e2e-web` (`:59-91`): `test-e2e-ci *ARGS:` runs `mise exec -- ./scripts/e2e-ci.sh {{ARGS}}`, and `install-e2e-browsers:` runs `mise exec -C web -- bunx playwright install --with-deps chromium` and `mise exec -C api -- uv run playwright install chromium`. One comment line above each, as the other recipes have. `test-e2e-web` and `test-e2e-api` do not change (AC 8)
  - [ ] 3.3: `web/playwright.config.ts`: when `process.env.CI` is set the reporter is `[['list'], ['html']]`, otherwise `'html'` as today (`:23`), so the job log names each failing test. Correct the header comment (`:6-12`): the stack may have no game server. Nothing else in the config changes (`forbidOnly`, `retries`, `workers` at `:20-22` and `baseURL` at `:27` already suit CI)
  - [ ] 3.4: Add to `scripts/tests/test-e2e-ci.sh`: the script and `web/e2e/README.md` name the same three tags; the script defines both keys as constants and never expands a `VS_API_KEY*` variable it did not set itself
  - [ ] 3.5: Run `just install-e2e-browsers` once, then `just test-e2e-ci`. It will fail on the tests Task 4 tags or repairs. Confirm the container is gone afterwards (`docker ps -a --filter name=vintagestory-manager-e2e` is empty) and that the dev stack, if it was running, is untouched

- [ ] Task 4: Tag the specs after running each against the seeded stack, repair `terminal.spec.ts`, and record what runs in CI (AC: 4, 6, 7, 8, 13)
  - [ ] 4.1: Start from Dev Notes "Inventory". Tag with Playwright's `tag` option on a `test.describe` or on a single test, and add a one-line reason as a comment next to each tag
  - [ ] 4.2: `just test-e2e-ci` decides. An untagged test that fails there gets the tag for what it needs, or a `page.route` stub when it needs one answer and the test is about the page (Dev Notes "When an untagged test fails"). A test never gets a tag to hide a failure that is a bug. Stop and ask the maintainer if a test fails for a reason that is none of the three tags
  - [ ] 4.3: `terminal.spec.ts` (Dev Notes "terminal.spec.ts"): confirm that all 8 tests fail at the base commit on any stack, then move the spec to `/game-server/console`
  - [ ] 4.4: The four settings specs (AC 6): record per test whether it passed on the seeded stack. The inventory expects all 15 to pass and to carry no tag
  - [ ] 4.5: Run the full suite once against the dev stack with a game server installed, `just test-e2e-web` (AC 8), and record passed, failed and skipped. The real-install specs restore what they install (their snapshot guards are unchanged). Do not start or stop the game server. Compare `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/config/api` before and after and record that they are equal
  - [ ] 4.6: Record in the Dev Agent Record the output of `cd web && bunx playwright test --list --grep-invert "@moddb|@game-server|@install"` as a count per spec, and the same for each tag with `--grep`. The two totals add up to the whole suite

- [ ] Task 5: The `e2e` job in `.github/workflows/ci.yml` + lint (AC: 1, 2, 3, 10)
  - [ ] 5.1: Add the job after `docker` (`ci.yml:54-66`). Dev Notes "The job" has the steps, the pins and the reasons
  - [ ] 5.2: Add to `scripts/tests/test-e2e-ci.sh`: `ci.yml` has an `e2e` job with `timeout-minutes`, and `ci.yml` contains no `secrets.` reference. The existing assertion in `test-docker-context.sh:19-22` already fails on an action that is not pinned by commit
  - [ ] 5.3: `just lint-workflows`, `just lint-scripts` and `just test-scripts` pass

- [ ] Task 6: Documentation (AC: 4, 7)
  - [ ] 6.1: New `web/e2e/README.md`, short: what each tag means with one example spec, the rule that a test with no tag needs only the stack `just test-e2e-ci` starts, how to add a tag, the two ways to run (`just test-e2e-ci` for the CI set on a throwaway container, `just test-e2e-web` for everything against the dev stack), the helper and the status stub in two sentences, the fixture and why its password is set
  - [ ] 6.2: `README.md` "End-to-end tests" (`:109-115`): replace the raw `mise exec` line (`:112`) with `just install-e2e-browsers`, add `just test-e2e-ci`, and link `web/e2e/README.md`
  - [ ] 6.3: `CLAUDE.md` command list (Testing block): one line for `just test-e2e-ci`

- [ ] Task 7: Quality gate and review hand-off (AC: all)
  - [ ] 7.1: `just check` passes. `just test-e2e-ci` passes twice in a row on a clean checkout of the branch. The diff adds no lint or type suppression, no `cast`, no `test.skip`, `test.fixme` or `test.only`, and no dependency. `git status --short` shows nothing under `dev/`, `data/`, `web/playwright-report/` or `web/test-results/`
  - [ ] 7.2: `git grep -n "localStorage.setItem" -- web/e2e api/tests/e2e` prints nothing (AC 9)
  - [ ] 7.3: Story status `review` and `just sprint set 19-7-e2e-runs-in-ci review`
  - [ ] 7.4: The controller pushes the branch and opens the pull request (the dev agent does not push or open it). CI runs only on pull requests that target `main` and on pushes to `main` (`ci.yml:3-8`), so while this branch is stacked on Story 19.6's branch a pull request against that branch runs nothing. The controller either opens the pull request against `main` once 19.6 is merged, or starts the run by hand with `gh workflow run ci.yml --ref <branch>` (`workflow_dispatch` is on, `ci.yml:8`). The story is not done until the `E2E tests` job has passed on this branch
  - [ ] 7.5: Record the run URL, the job's duration and the number of tests it ran in the Dev Agent Record (AC 14). If the job fails, fix the cause on the branch and wait for a green run. Do not raise the retries, widen a tag or lengthen the job's timeout to get one
  - [ ] 7.6: PR link on `VSS-wenx`. The PR description says: no API contract change, no release note, the count of tests that run in CI and the count per tag, and the decisions listed in Dev Notes "Decisions for the maintainer"

## Dev Notes

### What is there today (verified at b6ae2f2)

- `.github/workflows/ci.yml` has four jobs: `api` (`:18-30`), `web` (`:32-40`), `scripts` (`:42-52`, runs `just lint-workflows`) and `docker` (`:54-66`, builds `linux/amd64` with `cache-from: type=gha` and `cache-to: type=gha,mode=max`, pushes nothing, loads nothing). Triggers are pull requests to `main`, pushes to `main` and `workflow_dispatch` (`:3-8`). `permissions: contents: read` is set for the whole workflow (`:10-11`), and `concurrency` cancels a superseded run (`:13-15`).
- Actions are pinned by full commit SHA with the version in a comment. The pins to reuse: `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `jdx/mise-action@d5574b52816a478f9d4e6529a3f6ff17a8a36785 # v5.2.8`, `docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1`, `docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0` (all in `ci.yml`), and `actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2` (`release.yml:53`). The job needs no action the repository does not already pin.
- `just test-e2e-web` (`Justfile:59-91`) starts the dev Compose stack with `just docker start`, waits up to 30 s for `/healthz`, runs `bun run test:e2e {{ARGS}}` and stops the stack. The dev stack mounts `./data` (`docker-compose.dev.yaml:14-15`), the developer's own data, usually with a game server installed.
- `web/playwright.config.ts`: `testDir: './e2e'`, `fullyParallel`, `forbidOnly`, 2 retries and 1 worker when `CI` is set, `reporter: 'html'`, `baseURL` from `E2E_BASE_URL` (`:17-28`). `@playwright/test` is 1.65.1 in `web/bun.lock`. The `tag` option and `--grep-invert` work on it: a prototype tagged one `describe` and one test and `--list --grep-invert "@moddb|@game-server|@install"` left them out.
- `web/e2e/` has 18 specs and 127 tests. Fifteen specs carry the dead init script, 17 occurrences. Six answer `/config.js` themselves. The specs are not type-checked: `web/tsconfig.json:33` includes `src` and `tests` only, and Vitest excludes `e2e` (`web/vitest.config.ts:22`). So `just check` does not see a broken spec. `bunx playwright test --list` loads every spec and is the cheap check after an edit.
- `api/tests/e2e/test_e2e_health.py` has three tests (`/healthz`, `/readyz`, the page title). They use pytest-playwright's `page`, so they need the Python Playwright's own Chromium (`playwright` 1.65.2 in `api/uv.lock`, a separate download from the web's). The base URL is `PLAYWRIGHT_BASE_URL`, default `http://localhost:8080` (`conftest.py:65-73`). The session fixture skips every test when the address does not answer (`:49-63`), so a wrong address looks like a pass. The script waits for `/healthz` before it runs them.
- The image runs as the user `vsmanager` (`Dockerfile:68`, `:78`) and creates `/data/server`, `/data/serverdata` and `/data/vsmanager` owned by that user (`:74-75`). It declares no `VOLUME`. Its base is an `amd64` image (`:36`).
- The API creates its data directories at start (`main.py:101-102`), starts no game server unless `auto_start_server` is on and a server is installed (`:117-141`; the default is off, `services/api_settings.py:37-40`), and registers its periodic jobs (`:144-151`). One job runs once at start: `server_versions_check` (`jobs/__init__.py:44`), which calls the vendor's API.
- `main` has no branch protection and the repository has no rulesets (checked with `gh api`, 2026-11-16). See "ADR against the code".

### ADR against the code

- **ADR-14 decision 10 says the seeded file is enough for the settings specs. It is not.** The API reads the game settings from `serverconfig.json` alone (`services/game_config.py:469-472`, `:499-512`), which is what the ADR checked. The web does not ask the API for them until the server status says a game server is installed: `SettingsPage` renders `EmptyServerState` instead of `GameConfigPanel` (`web/src/features/game-server/SettingsPage.tsx:33-36`, `:85-94`), and "installed" means the server's own files exist under `/data/server` (`services/server.py:502-509`, `:897-905`). The same check hides every Mods page (`web/src/App.tsx:72-100`, `GameServerModsPage`) and the Console (`features/game-server/ConsolePage.tsx:28-31`, `:80-89`). On a stack with no game server, 80 of the 91 tests the inventory expects in CI would see "Install a VintageStory server" and fail, including 46 of the 54 in `layout-widths` and every test that stubs its mod data. Without a fix CI would run 11 tests.
  The story keeps the maintainer's decision (the settings specs run in CI, no game server in CI) with a stub at the page: the shared helper answers `GET /api/v1alpha1/server/status` as installed when the stack says `not_installed` (AC 11). The settings themselves still come from the real API and the seeded file. Rejected: placing fake server files in `/data/server` so the API reports installed. The API would then report a version it cannot read and offer to start a server that is not there.
- **ADR-14 decision 1 puts the placeholder keys in the job's `env`.** The story puts them in `scripts/e2e-ci.sh` as constants. The recipe has to behave the same on a developer's machine, where `mise` loads `.env` (`mise.toml` `[settings] env_file`) and with it the developer's real `VS_API_KEY_ADMIN`. A script that read the keys from the environment would start the throwaway container with a real key. With constants the workflow holds no key at all.
- **ADR-14 decision 1 says "an empty data directory".** The container has no mounted data directory: the fixture is copied into the container's own `/data` (see "The stack the recipe starts"). The result is what the ADR asks for, a data directory that holds only the seeded file, without a host directory the container's user cannot write to.
- **ADR-14 decision 7 says "the job is required like the others".** No job is required today: `main` is not protected. The job fails the run like the others, which is all the workflow can do. Making checks required is a repository setting and the maintainer's to change.
- **ADR-14 decision 10 gives "an empty password" as an example of a fixture value.** The fixture sets a made-up password. Reason in "The fixture".
- **ADR-14 sorts the specs by what they need and does not mention `terminal.spec.ts`.** That spec needs nothing outside the stack and should fail everywhere, because its route is gone. See "terminal.spec.ts".
- Everything else in ADR-14 and in ADR-5 decision 8 matches the code at b6ae2f2.

### The server status stub (Task 2.2)

In the helper module of Story 19.2, next to the key helper. Suggested name `pretendServerInstalled(page)`; follow the naming Story 19.2 used.

```ts
await page.route('**/api/v1alpha1/server/status', async (route) => {
  if (route.request().method() !== 'GET') return route.fallback();
  const response = await route.fetch();
  const body = await response.json();
  if (response.ok() && body.data?.state === 'not_installed') {
    body.data = { ...body.data, state: 'installed', version: FIXTURE_GAME_VERSION };
  }
  await route.fulfill({ response, json: body });
});
```

- The body is the API's own snake_case envelope (`{"status": "ok", "data": {"state": ..., "version": ...}}`, `routers/server.py:166`, `services/server.py:899-905`). `state: 'installed'` is the stopped state (`web/src/api/types.ts:40`). `FIXTURE_GAME_VERSION` is a constant in the module, `'1.22.7'`, the version the specs' fake compatibility data already names (`layout-widths.spec.ts:76-85`).
- On a stack with a game server the state is not `not_installed` and the answer passes through unchanged, so `just test-e2e-web` behaves as before (AC 8).
- `route.fetch()` and `route.fulfill({ response, json })` are the pattern the specs already use (`monitor-password-redaction.spec.ts:140-150`, `settings-as-saved.spec.ts:109-126`). Give `body` a declared type, not `any`.
- Order with the other routes: Playwright runs the route registered last first. `readOnly` in `layout-widths` and `mod-detail-media` registers `**/api/**` and falls back for every `GET` (`layout-widths.spec.ts:110-117`), so the stub works whether it is registered before or after.
- The stub covers the page only. A test's direct API calls (`request.get(...)`) see the real state. No untagged test asks the API for the server state.
- With the stub in the shared set-up, "the page needs an installed server to render" is never a reason for `@game-server`. That tag is for a test that needs something a real game server left behind or does: files it wrote, a running process, a console that answers.

### The fixture (Task 2.1)

`web/e2e/fixtures/serverconfig.json` is a copy of `api/src/vintagestory_api/templates/serverconfig-template.json` (199 lines, the file the manager itself writes on a first start, already public, no data from any server) with these values:

| Key | Template | Fixture | Why |
|---|---|---|---|
| `FileEditWarning` | the manager's sentence | `E2E fixture with made-up values. Not a real server configuration.` | says what the file is |
| `ServerName` | `Vintage Story Server` | `E2E Fixture Server` | recognisable in a failure |
| `Password` | `null` | `e2e-fixture-password` | see below |
| `ServerDescription`, `Ip` | `null` | `null` (unchanged) | `settings-empty-values` needs a setting with no value (`:24-28`, `:59-60`) |

Everything else stays as in the template. `EntitySpawning` is not in the template, so the API reports it with no value and its default (`services/game_config.py:163-171`), which is a state a real file can have.

What each settings spec needs from it:

- `settings-desktop-layout` (5 tests): the panel and the inputs `#ServerName`, `#ServerDescription`, `#WelcomeMessage`, `#Password`, `#MaxClients`, `#MaxChunkRadius`, `#Port`, `#Ip` (`:119-133`). All fifteen managed settings render whatever their value, so any valid file serves. `#Password` exists only for an Admin key, which the helper gives the page.
- `settings-empty-values` (2 tests): test 1 checks every one of Description, Password and IP Address that is `null` and skips itself only when none is (`:59-60`). With the fixture it checks Description and IP Address. Test 2 checks the password field's masking and needs no particular value.
- `settings-as-saved` (3 tests): test 1 reads the real settings and overrides two of them in the answer (`:109-126`); every write to the game settings is stubbed (`:91-108`). Tests 2 and 3 change `mod_list_refresh_interval` through the real API and restore it (`:144-176`). They need the job `mod_cache_refresh` to exist, which it does on a fresh stack (default 14400 s, `services/api_settings.py:49-56`). Rescheduling the job fetches nothing: its next run is one interval later (`jobs/__init__.py:66-68`).
- `monitor-password-redaction` (5 tests): tests 1 and 2 need a Monitor key on the stack and in the test process (`:29`, `:82`, `:106`), which the script sets. With a password of 8 or more characters they also assert that the Monitor answers do not contain it and that the file viewer shows `"[redacted]"` (`:93-99`, `:125-132`). With no password those assertions never run. That is why the fixture sets one: the check that a Monitor key cannot read the password then runs on every pull request. Test 2 opens `/config`, the File Manager and `serverconfig.json` in the root listing (`:118-123`), which the seeded file provides.

The password is in a public repository on purpose. It is a made-up value in a test file, the README says so, and `scripts/tests/test-e2e-ci.sh` pins it so nobody replaces it with a real one unnoticed.

`COPY web/ ./` (`Dockerfile:27`) puts the fixture into the web build stage and not into the final image.

### The stack the recipe starts (Task 3.1)

`scripts/e2e-ci.sh`, `set -euo pipefail`, run from the repository root. A prototype of this script and of the job passed ShellCheck and actionlint. It was not run: story creation does not start containers.

1. **Constants.** `ADMIN_KEY="e2e-admin-placeholder-key"`, `MONITOR_KEY="e2e-monitor-placeholder-key"`, container name `vintagestory-manager-e2e`, the fixture path, and the tag expression `@moddb|@game-server|@install`. The keys are never read from the environment (see "ADR against the code").
2. **Image.** `E2E_IMAGE` names an image that is already built (the job sets it). When it is unset the script runs `docker build --platform linux/amd64 -t vintagestory-server:e2e .`, which shares its layer cache with the dev stack's builds.
3. **Port.** `E2E_PORT`, default `18080`, published on `127.0.0.1` only. Not 8080: the dev stack may be running, and worktrees take ports from 8080 to 8179 (`scripts/worktree-setup.sh:35`).
4. **Create, seed, start.** `docker rm -f` a leftover container of the same name, then `docker create` with the port, the environment (`VS_API_KEY_ADMIN`, `VS_API_KEY_MONITOR`, `VS_API_KEY` set to the Admin key, `VS_DATA_DIR=/data`) and three `--add-host <host>:127.0.0.1` entries for `mods.vintagestory.at`, `api.vintagestory.at` and `cdn.vintagestory.at`. Then `docker cp` the fixture to `<container>:/data/serverdata/serverconfig.json`, then `docker start`, then `docker exec --user root <container> chown vsmanager:vsmanager /data/serverdata/serverconfig.json`.
   - No `VS_DEBUG`: the stack runs as a production deployment does. The dev stack sets `VS_DEBUG=true` (`docker-compose.dev.yaml:22`), so this is the first place the specs meet production mode. After Story 19.3 that means no `/docs` and the policy as an operator gets it.
   - No bind mount. A host directory on a CI runner belongs to the runner's user and the container's `vsmanager` could not create its directories in it. Copying into the created container needs no permissions on the host and leaves nothing behind when the container is removed. `docker cp` creates the file as root, hence the `chown`. A game setting saved for real is written to a temporary file and renamed (`services/game_config.py:838-841`), which works in a directory `vsmanager` owns.
   - The three hosts are every external host the API calls (`grep -rn "vintagestory.at" api/src`). Pointed at loopback, a call to one is refused at once and the API answers 502. That is AC 12: a test that passes only because the mod database answered cannot be left untagged, and a pull request cannot fail because the mod database is slow (ADR-14 decision 4). The start-up version check fails and logs an error. That is expected in this stack.
5. **Wait** up to 60 s for `GET /healthz` on the chosen port (the first start under emulation on an Apple silicon machine is slow). On a timeout print the container's log and fail.
6. **Run.** Export `VS_API_KEY_ADMIN`, `VS_API_KEY_MONITOR`, `E2E_BASE_URL`, `PLAYWRIGHT_BASE_URL` and `PLAYWRIGHT_HTML_OPEN=never` (without it a failed local run serves the HTML report and never returns). Then `(cd web && bun run test:e2e --grep-invert "<tags>" "$@")` and `(cd api && uv run pytest tests/e2e)`. Run both even when the first fails, and exit non-zero when either failed. The script runs under `mise exec` from the recipe, so `bun` and `uv` are the pinned ones.
7. **Clean up** in an `EXIT` trap: on a failure print the last 200 lines of the container's log (the keys are placeholders and the API never logs a key), then `docker rm -f` the container. Keep the exit status.

`just test-e2e-ci e2e/settings-as-saved.spec.ts` runs one spec the same way, through `"$@"`.

The recipe never touches `./data`, `dev/` or the dev stack's container, so it needs no snapshot guard: everything it changes is inside a container it removes.

### Inventory (Task 4, expected result, to be confirmed by `just test-e2e-ci`)

Counts are from `bunx playwright test --list` at b6ae2f2. "Stub" means the server status stub of Task 2.

| Spec | Tests | Init scripts | Own `/config.js` | Needs | Expected |
|---|---|---|---|---|---|
| `browse-game-version` | 5 | 1 (`:101-103`) | no | 4 stub `GET /mods/browse` (`:86-88`); `live:` (`:167`) reads the mod database | 4 untagged with stub; `live:` `@moddb` |
| `file-browser-navigation` | 5 | 1 (`:76-78`) | no | a directory inside another under `serverdata` (`:54-71`), which only a game server that has run creates | all `@game-server` |
| `install-file-conflict` | 2 | 1 (`:80-82`) | no | live lookup and live browse (`:90`, `:104`) | all `@moddb` |
| `installed-mod-any-modid` | 3 | 1 (`:89-91`) | no | live lookup (`:98`, `:64-66`) | all `@moddb` |
| `installed-mods-phone` | 4 | 1 (`:202-204`) | no | everything under `/mods` stubbed (`:64-173`) | untagged with stub |
| `installed-status` | 4 | 2 (`:145-147`, `:219-221`) | no | test 1 live browse (`:150`); 2 "Not checked yet" tests stubbed (`:86`, `:178`); the serial block installs `playercorpse` (`:198-272`) | 2 untagged with stub; test 1 `@moddb`; the serial block `@moddb` and `@install` |
| `layout-widths` | 54 | 0 | yes | installed mods stubbed, every write refused (`:103-226`); Game Settings rows need the settings (`:570-594`); Version page tabs render without a version list | untagged with stub |
| `mod-browse-name-sort` | 3 | 1 (`:105-107`) | no | live browse | all `@moddb` |
| `mod-browse-state` | 7 | 1 (`:128-130`) | no | live browse, live game version list | all `@moddb` |
| `mod-detail-bad-data` | 2 | 1 (`:50-52`) | no | live lookup and browse | all `@moddb` |
| `mod-detail-media` | 5 | 0 | yes | 4 stub the lookup and the image CDN (`:126-148`); the `betterruins` test is live (`:382`) | 4 untagged with stub; the live test `@moddb` |
| `mod-install-release` | 6 | 1 (`:127-129`) | no | 4 UI tests use the live lookup (`:125-213`); the serial block installs and removes real mods (`:215-308`) | 4 `@moddb`; the serial block `@moddb` and `@install` |
| `mods-navigation` | 4 | 1 (`:55-57`) | no | live browse | all `@moddb` |
| `monitor-password-redaction` | 5 | 0 | yes | `serverconfig.json`, a Monitor key | untagged with stub |
| `settings-as-saved` | 3 | 1 (`:37-39`) | yes | `serverconfig.json`; changes and restores one API setting | untagged with stub |
| `settings-desktop-layout` | 5 | 1 (`:35-37`) | yes | `serverconfig.json` | untagged with stub |
| `settings-empty-values` | 2 | 1 (`:43-45`) | yes | `serverconfig.json` with a `null` setting | untagged with stub |
| `terminal` | 8 | 2 (`:30-32`, `:107-109`) | no | a route that does not exist | repaired, untagged with stub |

Expected totals: 91 untagged, 36 tagged (`@moddb` 31 of which 3 are also `@install`, `@game-server` 5), plus the specs of Stories 19.2 and 19.3, which their stories write to run in CI. The numbers are a prediction from reading the specs. Task 4.6 records the real ones.

Tagging syntax (Playwright 1.65):

```ts
// Reads the live mod database through the stack
test.describe('Mod browser Name (A-Z) sort', { tag: '@moddb' }, () => { ... });

test('live: the cards agree with the browse response', { tag: '@moddb' }, async ({ page }) => { ... });

test.describe('...real API (Story 17.4)', { tag: ['@moddb', '@install'] }, () => { ... });
```

Do not put the tag in the test title, and do not use `test.skip` on an environment variable in its place. A tag is visible in `--list` and in the report, and the three names are fixed by ADR-14 decision 2.

### When an untagged test fails on the seeded stack (Task 4.2)

In this order:

1. It shows "Install a VintageStory server". The status stub is missing from that spec's set-up, or registered after `page.goto`.
2. A request the test does not care about got a 502 because the mod database is blocked (for example the Browse page also asks for `/mods/gameversions` and `/mods/tags`, `web/src/api/mods.ts:143`, `:159`). If the test's assertions still hold, nothing to do. If the page shows an error the test trips over, stub that one answer with `page.route` in the test and say why in a comment. This applies to the policy spec of Story 19.3 if it collects console errors: a 502 is logged by the browser as a failed resource.
3. It needs the mod database's real content to mean anything. Tag it `@moddb`.
4. It needs a file or a process only a real game server has. Tag it `@game-server` with the reason.
5. Anything else is a bug in the test or in the product. Do not tag it. Fix the test when the test is wrong. When the product is wrong, stop and tell the maintainer: this story changes no product code.

A test that is flaky on the seeded stack is case 5. `retries: 2` in CI is not a reason to accept it.

### terminal.spec.ts (Task 4.3)

The spec opens `/terminal` in every test (`:36`, `:46`, `:55`, `:68`, `:88`, `:120`, `:130`) and clicks a sidebar link named "terminal" (`:80`). The router has no such route (`web/src/App.tsx:113-133`): the console moved to `/game-server/console` in Epic 11, and the sidebar link is "Console" (`web/src/components/layout/Sidebar.tsx:81`). The component the spec was written for, `web/src/features/terminal/Terminal.tsx` with its `aria-label="Terminal page"`, is imported by nothing but its own unit test. So all 8 tests should fail on any stack today. Confirm that first by running the spec at the base commit, and record the result.

The spec says of itself that it needs no running game server (`:12-13`), so it belongs in CI. Move it to the page that exists:

- Open `/game-server/console` with the key helper and the status stub (the page is behind the installed check, `ConsolePage.tsx:80-89`).
- Keep the checks that still describe the product: the page (`data-testid="console-page"`, `ConsolePage.tsx:65`) and its `h1` "Server Console" (`:70`; use `getByRole('heading', { level: 1, name: 'Server Console' })`, because the panel has a title with the same text), the terminal (`role="application"`, name "Server console terminal", `web/src/components/terminal/TerminalView.tsx:152`) with its `.xterm` element, a WebSocket opened to a URL containing `/console/ws`, and the sidebar link "Console" leading to `/game-server/console`.
- Drop the two checks of the old wrapper (`getByLabel('Terminal page')` and its `flex` and `h-full` classes, `:42`, `:70-72`). Say so in the completion notes.
- The connection status checks (`getByRole('status')`, `:58`, `:134`) may match more than one element on the Console page. Scope them to the console panel.
- Replace `page.waitForTimeout(1000)` (`:123`) with `page.waitForEvent('websocket', ...)`.
- Keep the file name. Update its header comment.

Do not start or stop the game server, and do not send a console command. If a kept check cannot pass on a stack with no game server, tag that one test `@game-server` with the reason. If the spec cannot be repaired at all, stop and ask the maintainer. Deleting it or tagging it out is his decision (`project-context.md:162-165`).

### The job (Task 5.1)

```yaml
  e2e:
    name: E2E tests
    runs-on: ubuntu-latest
    timeout-minutes: 30
    env:
      # The image the recipe starts; built below and never pushed
      E2E_IMAGE: vintagestory-server:e2e
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: jdx/mise-action@d5574b52816a478f9d4e6529a3f6ff17a8a36785 # v5.2.8
      - uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1
      - uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: .
          platforms: linux/amd64
          push: false
          load: true
          tags: ${{ env.E2E_IMAGE }}
          cache-from: type=gha
      - run: just install-web --frozen-lockfile
      - run: just build-api
      - run: just install-e2e-browsers
      - run: just test-e2e-ci
      - if: ${{ failure() }}
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: playwright-report
          path: |
            web/playwright-report/
            web/test-results/
          if-no-files-found: ignore
          retention-days: 7
```

This text passed `just lint-workflows` in a prototype appended to `ci.yml` at b6ae2f2.

- **Same triggers** as the other jobs: it is one more job in the same workflow, and the workflow's `permissions: contents: read` covers it. It reads no secret, so it also runs on a pull request from a fork.
- **Cache.** `cache-from: type=gha` reads what the `docker` job writes. No `cache-to`: two jobs writing the same cache scope in one run would race. No `needs: docker` either: the jobs run side by side, and on a pull request that changes `web/` or `api/` both rebuild the changed layers from the same cached base. If the measured time says otherwise, `needs: docker` is the alternative, and the reason goes in the completion notes.
- **`load: true`** puts the image into the runner's Docker so `docker create` finds it. The `docker` job does not load, which is why the build is repeated here.
- **Timeout.** 30 minutes. Expect about 10: the build, two browser downloads, and about 100 tests on one worker (`playwright.config.ts:22`). Record the real duration (Task 7.5).
- **The artifact** holds the HTML report and `test-results/`, where Playwright keeps the trace of a first retry (`playwright.config.ts:28`). `if-no-files-found: ignore` covers a failure before Playwright ran. A trace records the page, which shows only the fixture's made-up values and the placeholder keys.
- **No browser cache.** It would need a cache action the repository does not pin yet. Follow-up if the download proves slow.
- `CI=true` is set by the runner, so `forbidOnly`, the retries, the single worker and the `list` reporter apply.

### Tracked report files

`web/playwright-report/index.html` and `web/test-results/.last-run.json` are tracked in git (since Story 4.4), and every Playwright command rewrites them, `--list` included. After each run: `git restore web/playwright-report web/test-results`. Never commit them: a report holds whatever the page showed. Untracking and ignoring them is a follow-up (see the report), not this story.

### Existing tests that change (deliberately)

- All 18 specs in `web/e2e/` are edited: the key helper in each, the init script out of fifteen, the status stub in seventeen, tags in eleven, and `terminal.spec.ts` rewritten against the Console page. No assertion of a passing test changes except in `terminal.spec.ts`.
- The specs Stories 19.2 and 19.3 added get the status stub where they open a page behind the installed check, and a `page.route` stub where they tripped over a blocked external call. Their assertions do not change.
- `api/tests/e2e/conftest.py` loses an unused fixture. Its three tests do not change.
- No Vitest test and no pytest test outside `tests/e2e` changes. `just test-scripts` gains `test-e2e-ci.sh`.

### Not changed (do not "fix" these here)

- No file under `api/src/` or `web/src/`. The installed check in the web stays as it is, and so does the unused `features/terminal/Terminal.tsx`.
- `just test-e2e-web`, `just test-e2e-api`, `just docker ...`, both compose files, the `Dockerfile`.
- The `api`, `web`, `scripts` and `docker` jobs, and `release.yml`.
- The `@moddb` tests stay live. Recording mod database answers for them is a follow-up (ADR-14 decision 9).
- `file-browser-navigation` stays `@game-server`. Seeding a directory tree for it is not in ADR-14.
- The snapshot guards of `installed-status`, `mod-install-release` and `settings-as-saved`.
- Type-checking the specs, and untracking the report files.
- Branch protection.

### API contract changes

None. No endpoint, field, status or error code changes. The story touches tests, the Justfile, one script, one workflow and documentation.

### Decisions for the maintainer

Each is written into the story and can be reversed in review:

1. The page-level server status stub, so that pages behind the installed check render in CI (AC 11).
2. The CI container cannot reach the mod database or the vendor's API (AC 12).
3. The fixture has a made-up password, so the Monitor redaction is asserted in CI. ADR-14 suggested an empty one.
4. `terminal.spec.ts` is repaired against the Console page (AC 13).
5. The placeholder keys live in the script, and the container has no mounted data directory.
6. The unused `authenticated_page` fixture in `api/tests/e2e/conftest.py` goes with the other dead `localStorage` scripts.

### Testing Requirements

- This story's tests are the E2E run itself, `scripts/tests/test-e2e-ci.sh` (red first, extended task by task) and the linters. Each task ends with `just test-scripts`, and from Task 3 on with `just test-e2e-ci`.
- `just check` does not load the specs. After every spec edit run `cd web && bunx playwright test --list` and restore the report files.
- A manual browser check is not needed: nothing an admin sees changes. The proof is the green `E2E tests` job (Task 7.4).
- E2E runs must not start or stop the game server, must not send console commands, and take no screenshots. `just test-e2e-ci` cannot reach a game server at all. For the one full run against the dev stack (Task 4.5) the before and after comparison is recorded.
- Do not print a key or a password in a test failure message. The existing specs compare with `includes` for that reason (`monitor-password-redaction.spec.ts:92-99`). Keep it that way.

### Security Requirements

- No secret in the workflow, the script, the fixture or the specs. The two keys and the password are made-up constants, pinned by `test-e2e-ci.sh`, and named as placeholders where they are defined.
- The container's port is published on `127.0.0.1` only.
- The job has `contents: read` and nothing else, uses no `pull_request_target`, and interpolates no pull request text into a `run:` step.
- The artifact is public on a public repository. It holds fixture values only. Never run the recipe against a real data directory to "see more": the script has no option for one, and it must not get one.

### Development Commands

- `just install-e2e-browsers` (once), `just test-e2e-ci`, `just test-e2e-ci e2e/<spec>`, `just test-e2e-web` (full suite, dev stack).
- `cd web && bunx playwright test --list --grep-invert "@moddb|@game-server|@install"`.
- `just test-scripts test-e2e-ci.sh`, `just lint-scripts`, `just lint-workflows`, `just check`.
- Do not run `just format-web` or `just format-api` (they reformat unrelated files; `format-web` does not cover `e2e/` anyway).

### Previous Story Intelligence

- **19.2:** the helper that answers `/config.js` with a chosen key and the no-key spec. Read its Completion Notes for the helper's file and signature before Task 1. The dev compose file then sets `VS_API_KEY` to the Admin key by default, so `just test-e2e-web` keeps a working page even where a spec forgot the helper. The seeded container sets it explicitly.
- **19.3:** the policy spec opens the dashboard, the console, the mod browser, a mod detail page, the installed list, the settings and the version page and expects no violation and no console error. Three of those pages are behind the installed check, and a blocked external call logs a console error. Expect to add the status stub and one or two `page.route` stubs to it (Task 2.3, "When an untagged test fails"). Its policy is the production one in this stack (no `VS_DEBUG`).
- **19.1:** roles other than Admin see the root config files and `ModConfig` only. `monitor-password-redaction` test 2 reads `serverconfig.json` in the root listing with a Monitor key, which stays allowed. Re-check after 19.1 that the redacted text is still `"[redacted]"`.
- **17.2, 17.4, 17.6:** a spec that changes real state restores it behind a snapshot guard. Those guards are untouched. Spec files run in parallel locally (`fullyParallel`), so two specs must not install the same mod (`installed-status.spec.ts` header).
- **17.5:** the web stopped reading `localStorage` for the key, which is what made the init scripts dead.
- **17.x and 18.x reviews:** a completion note must be true of the code. Record counts and run results as they were, including a failing first run.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`). Stories 19.1 to 19.6 land first.
- Planned commits: Task 1 `test(story-19.7/task-1): e2e specs take their key from the config.js helper`. Task 2 `test(story-19.7/task-2): serverconfig fixture and server status stub for e2e`. Task 3 `build(story-19.7/task-3): just test-e2e-ci runs the untagged e2e tests on a seeded container`. Task 4 `test(story-19.7/task-4): tag e2e tests that need the mod database, a game server or a real install`. Task 5 `ci(story-19.7/task-5): run the e2e tests on every pull request`. Task 6 `docs(story-19.7/task-6): how to run the e2e tests and what the tags mean`. Task 7 `chore(story-19.7/task-7): move story 19.7 to review`.

### Project Structure Notes

- New: `web/e2e/fixtures/serverconfig.json`, `web/e2e/README.md`, `scripts/e2e-ci.sh`, `scripts/tests/test-e2e-ci.sh`.
- Modified: all 18 `web/e2e/*.spec.ts`, the specs and the helper module added by Stories 19.2 and 19.3, `web/playwright.config.ts`, `api/tests/e2e/conftest.py`, `Justfile`, `.github/workflows/ci.yml`, `README.md`, `CLAUDE.md`.
- `web/e2e/fixtures/` is new. Playwright collects only `*.spec.ts` and `*.test.ts` under `testDir`, so a JSON file there is not picked up as a test.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.7: E2E Runs in CI]
- [Source: _bmad-output/planning-artifacts/prd.md] FR228, FR229, FR230
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-14, #ADR-5 (decisions 7 and 8), #ADR-6 (decision 13)]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (sections 2 and 5; the developer hand-off line for 19.7)
- [Source: _bmad-output/implementation-artifacts/18-2-install-and-version-change-keep-records-right.md], [17-4-installed-status-is-right-everywhere.md]
- Bead: `VSS-wenx`, parent `VSS-fl9b`
- `project-context.md` (commit format `:615-640`; failing tests are never excluded without the maintainer `:162-165`), `CLAUDE.md` (always `just`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-16 (create-story, non-interactive) and validated against the create-story checklist. Prototypes, discarded: the `tag` option with `--grep-invert` on two specs (`playwright test --list`), the `e2e` job appended to `ci.yml` (`just lint-workflows` passed), and `scripts/e2e-ci.sh` (ShellCheck passed). No container was started and no E2E test was run, so the inventory's "Expected" column is a prediction from reading the specs and the web source.

### File List

## Change Log

- 2026-11-16: Story 19.7 created and validated (ready-for-dev).
