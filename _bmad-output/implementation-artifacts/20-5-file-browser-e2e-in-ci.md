# Story 20.5: The File Browser E2E Tests Run in CI

Status: ready-for-dev

<!-- Implements FR248-FR251, Epic 20 ADR-8. Beads: VSS-3mr (UI-030, task, P2, size-m), closed after merge; VSS-571h (TEST-006, task, P4, size-m), parts 2, 3 and 4 here, part 1 in Story 20.6, which closes it. Closing VSS-3mr (with VSS-37a, closed in Story 20.2) lets the old epic VSS-029 "Web UI Test Coverage" close here. Fifth story of Epic 20, stacked on Story 20.4 (stories run in order 20.1 to 20.7). Line references were verified at 7f04ea2 (epic-20-planning; its code is 3f1c6ea, the commit the ADRs cite) and must be re-checked at implementation time: Story 20.3 gives every recipe `positional-arguments`, turns `lint-scripts` into globs, adds `web/e2e/tsconfig.json` and untracks the Playwright report files; Story 20.4 adds a `semgrep` job to `ci.yml`. Tests, one script, one recipe, CI and documentation only: no file under api/src or web/src changes, no API contract change, no new dependency, no release note. -->

## Story

As a **maintainer**,
I want **the file browser's browser tests to run on every pull request, including a directory that appears while I watch**,
so that **the file browser is covered in CI and the old test-coverage epic can close**.

## Acceptance Criteria

1. **Given** `just test-e2e-ci` **When** it starts the throwaway container **Then** the container's `serverdata` holds a directory inside another directory with made-up names (`Logs/Archive`), owned by the manager's user (`vsmanager`), beside the seeded `serverconfig.json`, and the job log shows the owner. *(FR248)*
2. **Given** `web/e2e/file-browser-navigation.spec.ts` **When** CI runs **Then** its five tests run and pass, the spec carries no `@game-server` tag, and it still creates, changes and deletes nothing. *(FR248)*
3. **Given** the same spec on the dev stack with a game server's data **When** it runs there (Dev Notes "The dev-stack check") **Then** it passes as before, the new-directory test of AC 4 skips with its message, and the stack's directory tree is the same before and after. *(FR248)*
4. **Given** the file manager open on a directory (`Logs`) in the throwaway stack **When** a new, uniquely named directory is created in that directory from outside the page (`docker exec`) and the page is loaded again **Then** the new directory is in the list and can be opened (the breadcrumb shows its name and the list is empty). *(FR249)*
5. **Given** that test on a stack that is not the throwaway container (`E2E_CONTAINER` unset, or not `vintagestory-manager-e2e`) **When** it runs **Then** it skips with a message that says why and changes nothing in that stack's data; `scripts/tests/test-e2e-ci.sh` checks that the CI script exports the container's name and that the spec and the script name the same container, so CI cannot skip it. *(FR249; Matt, 2026-11-17)*
6. **Given** `VSS-3mr` and `VSS-37a` closed **When** the story is merged **Then** the controller closes the old epic `VSS-029` "Web UI Test Coverage" with an AAR that names Stories 16.7, 20.2 and 20.5; it then has no open child. *(FR249)*
7. **Given** the `e2e` job **When** it runs a second time with the same Playwright versions **Then** it restores the browsers from a cache and does not download them, the cache action is pinned by commit, and the key changes only when a Playwright version (web or API) or the runner's system (`ImageOS`, architecture) changes. *(FR250)*
8. **Given** the cache **When** the story measures the job **Then** it records the job time (3 min 16 s) and the browser step's time (43 s) before, and the cold (cache miss) and warm (cache hit) times after, and the cache is removed again if the warm run does not save at least 15 s (Dev Notes "Keep or remove the cache"). *(FR250)*
9. **Given** the connection reset in the server-status stub **When** the time-boxed investigation is done **Then** the comment in `web/e2e/config-js.ts` states the cause if it was reproduced, or what was tried if it was not, and the single retry either stays with that reason or is removed because the cause is gone; no new bead is opened for it. *(FR251)*
10. **Given** `web/e2e/README.md` **When** I read it **Then** it lists the seeded directories, says what the new-directory test needs and why it skips elsewhere, and says that no test carries `@game-server` now and when the tag is still the right one. *(FR248, FR249)*
11. **Given** this story's pull request **When** CI has run on it **Then** the `E2E tests` job passed with 119 Playwright tests (113 before, plus the five navigation tests and the new one; re-count at implementation), and the story records the run's URL. *(FR248-FR250)*

## Tasks / Subtasks

<!-- Six tasks, the project's limit (project-context.md:259). Commit per task: type(story-20.5/task-N): ... with type test, ci, build, docs or chore. No feat, fix or perf: nothing here is visible to an admin, so nothing may reach the release notes. The epic's first two tasks (seed, then untag) are one task here: the untagging is decided by running the spec on the seeded stack, and the two land in one commit. -->

- [ ] Task 1: Seed `Logs/Archive` in the throwaway container and run the navigation spec in CI + test (AC: 1, 2, 3) (`VSS-571h` part 2)
  - [ ] 1.1: Red first, in `scripts/tests/test-e2e-ci.sh` (before the `# The e2e job exists` block, `:53`): the script defines `SEEDED_DIR="Logs/Archive"` (exact line, `assert_eq` as for the keys at `:33-36`). Run `just test-scripts test-e2e-ci.sh` and see it fail
  - [ ] 1.2: `scripts/e2e-ci.sh`: the constant after `FIXTURE` (`:21`), with a one-line reason; after the `chown` (`:66`), `docker exec "$CONTAINER" mkdir -p "/data/serverdata/$SEEDED_DIR"` (no `--user`: the image's user is `vsmanager`, `Dockerfile:78`) and `docker exec "$CONTAINER" ls -ld "/data/serverdata/$SEEDED_DIR"` so the log shows the owner (AC 1). Update the header comment (`:4-7`): the data directory holds the fixture and one seeded empty directory tree. Dev Notes "The seeded tree"
  - [ ] 1.3: `web/e2e/file-browser-navigation.spec.ts`: remove `{ tag: '@game-server' }` from the `test.describe` (`:108`) and the reason comment above it (`:106-107`). Rewrite the "Requirements" header (`:15-19`): `just test-e2e-ci` seeds the nested directory; on another stack it needs a game server that has run. Nothing else changes: the spec stays read-only and keeps discovering its path through the API (`findNestedPath`, `:56-73`)
  - [ ] 1.4: `just test-e2e-ci e2e/file-browser-navigation.spec.ts`: 5 passed. Then the full `just test-e2e-ci` (expect 118: 113 plus 5, until Task 2). If a navigation test fails on the seeded stack, it is a bug in the test or the seeding: fix that, never re-tag. Stop and ask if it needs what only a game server has
  - [ ] 1.5: The dev-stack check (AC 3; Dev Notes "The dev-stack check"): the navigation spec against the dev stack with a game server's data, the directory tree compared before and after. Record the result
  - [ ] 1.6: `just lint-scripts` and `just test-scripts` pass

- [ ] Task 2: The "new directory appears after a reload" test and what the script exports for it + test (AC: 4, 5) (`VSS-3mr`)
  - [ ] 2.1: Red first, in `scripts/tests/test-e2e-ci.sh`: the script has `export E2E_CONTAINER="$CONTAINER"` (write the expected value in double quotes with `\$`, not single quotes: ShellCheck SC2016 flags a single-quoted `$`, and no directive may silence it); the export comes before the `test:e2e` line; the `THROWAWAY_CONTAINER = '...'` constant in the new spec equals the script's `CONTAINER` (`:20`); the script still passes `VS_DATA_DIR=/data` (`:61`), which the spec's `/data/serverdata` depends on
  - [ ] 2.2: `scripts/e2e-ci.sh`: `export E2E_CONTAINER="$CONTAINER"` next to the other exports (`:81-87`), with a comment naming the spec that uses it
  - [ ] 2.3: New `web/e2e/file-browser-new-directory.spec.ts`, untagged (Dev Notes "The new-directory test" has the steps, the guard and the reasons). It skips with a message when `process.env.E2E_CONTAINER` is not exactly `vintagestory-manager-e2e`, the way `file-browser-monitor-note.spec.ts:140` skips without a Monitor key
  - [ ] 2.4: `just test-e2e-ci e2e/file-browser-new-directory.spec.ts`: 1 passed. `cd web && bunx playwright test e2e/file-browser-new-directory.spec.ts --list` and a run against any other stack: skipped with the message (part of 1.5's dev-stack run). `just typecheck-web` passes (Story 20.3 type-checks `web/e2e/`; the spec imports `node:child_process` and `node:crypto`, which its `types: ["node"]` covers)
  - [ ] 2.5: Full `just test-e2e-ci` twice in a row, both green (expect 119). Record the counts. `docker ps -a --filter name=vintagestory-manager-e2e` is empty afterwards

- [ ] Task 3: Cache the Playwright browsers in the `e2e` job; times before and after + test (AC: 7, 8) (`VSS-571h` part 3)
  - [ ] 3.1: Red first, in `scripts/tests/test-e2e-ci.sh`: the `e2e` job has an `actions/cache` step whose `path` is `~/.cache/ms-playwright` and whose `key` is `${{ steps.playwright.outputs.key }}`, and that step comes before the `just install-e2e-browsers` step (`yq` on step indexes). `test-docker-context.sh:19-22` already fails on an unpinned action; `test-release.sh:321-325` does not change (no new job)
  - [ ] 3.2: `Justfile`, after `install-e2e-browsers` (`:98-101`): a recipe `playwright-versions` that prints `web-<version>-api-<version>` from the two installed Playwright CLIs (Dev Notes "The cache"). `just playwright-versions` at 7f04ea2 prints `web-1.65.1-api-1.65.2`
  - [ ] 3.3: `.github/workflows/ci.yml`, `e2e` job, between `just build-api` (`:98`) and `just install-e2e-browsers` (`:99`): a step `id: playwright` that writes the key to `$GITHUB_OUTPUT`, and an `actions/cache` step pinned by commit SHA with the version comment (Dev Notes "The cache" has the text and the SHA to re-check). `just install-e2e-browsers` stays as it is: it downloads only what the cache did not restore, and `--with-deps` still installs the system packages
  - [ ] 3.4: `just lint-workflows`, `just lint-scripts`, `just test-scripts` pass
  - [ ] 3.5: Measure on the pull request (with the controller, who pushes): the first run is a cache miss, a re-run of the `e2e` job (`gh run rerun <run-id> --job <job-id>`) is a hit. Record for each: the job time, the cache step's time, the `install-e2e-browsers` step's time, and whether its log shows a download. Before: job 3 min 16 s, browser step 43 s (`main`, 2026-11-17). Apply Dev Notes "Keep or remove the cache"

- [ ] Task 4: The time-boxed investigation of the connection reset; the comment and the retry + test (AC: 9) (`VSS-571h` part 4)
  - [ ] 4.1: Run the probe of Dev Notes "The connection reset" against the throwaway container. **Time box: 60 minutes of wall-clock work, including any fix attempt. Stop condition: a reset reproduced (record the attempt count, the delay, the error text), or the box spent, whichever comes first.** The probe spec is a scratch file that is never committed
  - [ ] 4.2: Reproduced: if time is left in the box, try the one client-side fix in Dev Notes and re-run the probe. The retry goes only if the probe then shows no reset in as many attempts as it took to reproduce, three times over; otherwise the retry stays
  - [ ] 4.3: Rewrite the comment above `fetchWithOneRetry` (`web/e2e/config-js.ts:21-26`) to the outcome: the cause and why one retry is the right answer for a `GET`; or "the cause is gone because ..." with the retry removed; or, not reproduced, what was tried (probe, attempts, delays, stack) and that the cause is still unknown, with the retry kept. Keep the sentences about an abort at the end of a test and a second failure (19.7 review L-2) if the retry stays
  - [ ] 4.4: Record the outcome in the Completion Notes. No product change (uvicorn flags, the `Dockerfile` `CMD`) in this story: a server-side change goes under Follow-ups. Delete the probe file; `git status --short` shows no scratch file. Full `just test-e2e-ci` green

- [ ] Task 5: `web/e2e/README.md` + test (AC: 10)
  - [ ] 5.1: "Two ways to run them" (`:7-12`): the throwaway container is seeded with `fixtures/serverconfig.json` and the empty directory `Logs/Archive`, and the script exports `E2E_CONTAINER` for the one spec that creates a directory in it
  - [ ] 5.2: Tag table (`:23-27`): `@game-server` stays, with the example column "no test today", and a sentence after the table: since Story 20.5 no test carries it; it is the right tag for a test that needs a running game server process or files only a game server writes that the CI script cannot seed (for example a world save or a server log with content), and a test that only needs a directory or a small file should get it seeded in `scripts/e2e-ci.sh` instead
  - [ ] 5.3: A short section "Tests that change the throwaway stack": `file-browser-new-directory.spec.ts` creates a uniquely named empty directory under `Logs` with `docker exec`; it runs only when `E2E_CONTAINER` is `vintagestory-manager-e2e` and skips with a message on any other stack, so it never changes a developer's data; `scripts/tests/test-e2e-ci.sh` keeps CI from skipping it
  - [ ] 5.4: `just test-scripts test-e2e-ci.sh` passes (it greps the README for the three backticked tags, `test-e2e-ci.sh:27-29`)

- [ ] Task 6: Quality gate, CI and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes. `just test-e2e-ci` green twice in a row on a clean checkout of the branch. The diff adds no lint or type suppression, no `cast`, no `test.only`, `test.fixme`, and no `test.skip` other than the guard of Task 2.3, and no dependency. `git status --short` shows nothing under `dev/`, `data/`, `web/playwright-report/`, `web/test-results/` and no probe file
  - [ ] 6.2: `cd web && bunx playwright test --list --grep-invert "@moddb|@game-server|@install"` and `--grep @game-server`: record the counts (expect 119 in 17 files, and 0). The two sets plus `@moddb` (31) add up to the whole suite (150: 149 at 7f04ea2 plus the new test)
  - [ ] 6.3: Story status `review` and `just sprint set 20-5-file-browser-e2e-in-ci review`
  - [ ] 6.4: The controller pushes the branch and opens the pull request against `main` (the dev agent does not push or open it). The story is not done until the `E2E tests` job is green on this pull request. If it fails, fix the cause on the branch; do not raise retries, add a tag, or lengthen the timeout. Record the run URL, the job time, and the counts (AC 11), and the cache measurement of Task 3.5
  - [ ] 6.5: After merge, the controller closes the beads (Dev Notes "Beads"): `VSS-3mr` with an AAR, then `VSS-029` with an AAR that names Stories 16.7, 20.2 and 20.5, and adds a progress comment to `VSS-571h` (parts 2-4 done, part 1 in Story 20.6). The PR description says: no API contract change, no release note, the CI test count before and after, and the cache numbers

## Dev Notes

### What is there today (verified at 7f04ea2)

- `scripts/e2e-ci.sh` (Story 19.7) starts `vintagestory-manager-e2e` (`:20`) on `127.0.0.1:18080` with `VS_DATA_DIR=/data` (`:61`), copies the fixture into `/data/serverdata/serverconfig.json` before start (`:64`), chowns it as root (`:66`), waits for `/healthz` (`:68-79`), exports the keys and the base URL (`:81-87`), runs Playwright with `--grep-invert "$TAGS"` (`:90`, `TAGS` at `:23`), re-checks `/healthz` and runs the API E2E tests (`:91-100`). The trap removes the container (`:31-41`). Nothing under `serverdata` but the fixture: the API creates `server/`, `serverdata/` and `vsmanager/...` at start-up (`api/src/vintagestory_api/config.py:213-224`), no subdirectory of `serverdata`.
- `file-browser-navigation.spec.ts` is the only `@game-server` test (`:108`, 5 tests). `findNestedPath` (`:56-73`) does a breadth-first search over `GET /api/v1alpha1/config/directories` for the deepest path up to 3 levels and fails when there is none of depth 2. It is read-only.
- `FileManagerPanel.tsx` keeps the current directory in component state (`:54`), not the URL, and the Settings page opens on the UI Preferences tab (`SettingsPage.tsx:44`). After a reload the test must click `file-manager-tab` and open the directory again. Hidden (dot) directories are filtered (`FileManagerPanel.tsx:87-89`). An empty directory renders `file-list-empty` (`web/src/components/FileList.tsx:111`); a directory item is `file-item-<name>` (`FileList.tsx:151`).
- The directory listing reads the disk on every request, sorted by name (`api/src/vintagestory_api/services/config_files.py:292-296`), so a directory created by `docker exec` is listed on the next request.
- `web/e2e/config-js.ts:21-33`: `fetchWithOneRetry`, used by `pretendServerInstalled` (`:42-52`). The reset was seen once, in Story 19.7's full run against the dev stack, inside the stub during a `@moddb` test (`19-7-e2e-runs-in-ci.md`, Debug Log, Task 4.5).
- uvicorn 0.54.0 (`api/uv.lock:1512-1513`), started with no keep-alive option (`Dockerfile:91`); `uv run uvicorn --help` says `--timeout-keep-alive ... [default: 5]`.
- `ci.yml` `e2e` job (`:75-110`): checkout, mise, buildx, image build with `load: true`, `just install-web --frozen-lockfile` (`:97`), `just build-api` (`:98`), `just install-e2e-browsers` (`:99`), `just test-e2e-ci` (`:101`), the report artifact on failure (`:102-110`). No cache step. `just install-e2e-browsers` is `bunx playwright install --with-deps chromium` and `uv run playwright install chromium` (`Justfile:98-101`).
- Playwright versions: web `@playwright/test` 1.65.1 (`web/bun.lock:104`), API `playwright` 1.65.2 (`api/uv.lock:902-908`). Both install into `~/.cache/ms-playwright` on Linux.
- `playwright.config.ts`: `fullyParallel: true`, in CI one worker and two retries, locally several workers.

### ADR against the code

ADR-8 holds against the code. Two places where the story is more exact than the ADR, both reversible in review:

1. **Decision 3, the guard.** The ADR says the test skips "without the exported name". The story skips unless the name is exactly `vintagestory-manager-e2e`, so a stray `E2E_CONTAINER` in a developer's shell (or one naming the dev stack's `vintagestory-manager-dev`) can never point `docker exec` at a container that holds real data. `test-e2e-ci.sh` pins that the spec's constant and the script's `CONTAINER` are the same, so a rename of one fails the script tests instead of skipping the test in CI.
2. **Decision 5, the key.** The ADR says "the two Playwright versions the lock files resolve". The story reads them from the two installed CLIs, after `just install-web --frozen-lockfile` and `just build-api` have installed exactly what the locks resolve. It is the same value without parsing two lock formats (`bun.lock` has trailing commas, which `yq -p json` does not read).

### The seeded tree (Task 1)

- `Logs/Archive`, the ADR's example: it is what a game server writes, and it is empty. The API's file endpoints only list it. The Monitor-key specs are not affected: a Monitor key sees the root and `ModConfig` only (Story 19.1), and `file-browser-monitor-note.spec.ts:159-167` asks for `Logs/server-main.log`, which is refused by role (403) or by suffix (400, checked before the disk at `config_files.py:398-400`) whether `Logs` exists or not.
- `mkdir` runs after `docker start`, since `docker exec` needs a running container, and as the image's user, so the tree is owned by `vsmanager:vsmanager` like the files the game server writes. The `ls -ld` line puts the owner in the job log (AC 1); it prints no instance data (the container is throwaway).
- The new spec of Task 2 adds directories under `Logs` while the navigation spec may be running (locally several workers run in parallel). `findNestedPath` keeps the first deepest path it finds and the API sorts names by code point, so `Logs/Archive` ("A") stays ahead of any `e2e-new-...` ("e"): the navigation spec's path is the same with or without the new directory. Keep the new directory's name lower-case for that reason, and never create it under `Logs/Archive` (that would make a depth-3 path).
- Prototype (discarded): with the constant, the two `docker exec` lines and the export, `just lint-scripts` passed and the `test-e2e-ci.sh` assertions of Tasks 1.1 and 2.1 passed (21 of 21, with a prototype spec in place for the container-name check). Without Docker, the navigation spec was not run on the seeded stack; Task 1.4 decides.

### The new-directory test (Task 2)

A new file, not a test in `file-browser-navigation.spec.ts`: that spec promises to create nothing (AC 2). Steps:

```ts
import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
// ...
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER, pinned by test-e2e-ci.sh
const SERVERDATA = '/data/serverdata';                    // VS_DATA_DIR=/data in scripts/e2e-ci.sh
const PARENT = 'Logs';                                    // seeded by scripts/e2e-ci.sh

test('a directory created while the file manager is open is listed after a reload', async ({ page }) => {
  test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
  const name = `e2e-new-${randomUUID().slice(0, 8)}`;
  // serveConfigKey(page, API_KEY); goto /config; file-manager-tab; open PARENT; expect file-item-<name> count 0
  execFileSync('docker', ['exec', THROWAWAY_CONTAINER, 'mkdir', `${SERVERDATA}/${PARENT}/${name}`]);
  // page.reload(); file-manager-tab; open PARENT; click file-item-<name>;
  // path-breadcrumb-current has the name; file-list-empty is visible
});
```

- `execFileSync` with an argument array: no shell, no interpolation. `mkdir` without `-p`: the parent must be the seeded one, and a name that already exists fails loudly. The name is unique per attempt, so a CI retry creates its own.
- The skip message says why (`NOT_THROWAWAY`, for example "creates a directory with docker exec, so it runs only in the throwaway container of just test-e2e-ci (E2E_CONTAINER)"). It runs before anything touches the page or the disk.
- No clean-up step: the directory lives only in the throwaway container, which the script removes. Deleting it would add a second `docker exec` for no gain.
- Use the key and helper as the other specs do: `API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme'`, `serveConfigKey(page, API_KEY)` from `./config-js` (Epic 20 rules; `file-browser-navigation.spec.ts:23`, `:77`). `/config` is not behind the installed check, so no `pretendServerInstalled`.
- The "not listed before" assertion is part of the test: it shows that the reload, not a stale fixture, brings the directory in.
- Prototype (discarded): the spec above type-checked with `tsc --noEmit -p` on a copy of Story 20.3's `web/e2e/tsconfig.json` (0 errors), and `--list --grep-invert` counted 114 tests in 16 files, then 119 in 17 with the navigation tag removed.

### The dev-stack check (Task 1.5, AC 3)

- Run the navigation spec and the new spec against the dev stack that is already running on port 8080 with a game server's data, without starting or stopping anything: `cd web && bunx playwright test e2e/file-browser-navigation.spec.ts e2e/file-browser-new-directory.spec.ts`, with that stack's Admin key in `VS_API_KEY_ADMIN` (never printed, never committed). Expect 5 passed and 1 skipped with the message.
- Do not use `just test-e2e-web` for this check: it ends with `just docker stop` (`Justfile:89`), which stops a running game server, and run from a worktree it mounts the worktree's own `./data`, which has no game server's files. If no dev stack with a game server's data is running, record that and do not start the game server to get one.
- Before and after, list the directory tree of the data directory that stack mounts (`find <that checkout>/data/serverdata -type d | sort` into a scratch file outside the repository) and record only that the two lists are equal and how many directories they hold. Do not paste names: they are instance data. Take no screenshot.

### The cache (Task 3)

```yaml
      - run: just build-api
      # The key is the runner's system and the two Playwright versions, not the lock files,
      # so an unrelated dependency update keeps the cache
      - id: playwright
        run: echo "key=playwright-${ImageOS:?}-$RUNNER_ARCH-$(just playwright-versions)" >> "$GITHUB_OUTPUT"
      - uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
        with:
          path: ~/.cache/ms-playwright
          key: ${{ steps.playwright.outputs.key }}
      # Downloads only what the cache did not restore; --with-deps still installs system packages
      - run: just install-e2e-browsers
```

```just
# Print the Playwright versions of the web and the API (the e2e job's browser cache key)
playwright-versions:
    @echo "web-$(mise exec -C web -- bunx playwright --version | cut -d' ' -f2)-api-$(mise exec -C api -- uv run playwright --version | cut -d' ' -f2)"
```

- The SHA is the commit of the `v6.1.0` tag of `actions/cache` (`gh api repos/actions/cache/git/ref/tags/v6.1.0`, checked 2026-11-17; the latest release then). Re-check it at implementation and use the then-latest release's commit with its version comment, as Renovate's `pinGitHubActionDigestsToSemver` expects.
- `ImageOS` (for example `ubuntu24`) and `RUNNER_ARCH` are set by GitHub's hosted runners; `${ImageOS:?}` fails the step if it is not, rather than writing a key without the system. They change when `ubuntu-latest` moves to a new release, which is when the browsers' system libraries change. The weekly image version is left out on purpose.
- No `restore-keys`: a different Playwright version needs different browser builds, and a partial restore would only grow the cache.
- `actions/cache` saves in its post step only when the job succeeded (`post-if: success()` in its `action.yml`), so a red run never stores a half-downloaded directory. A cache made on a pull request is visible to re-runs of that pull request; one made on `main` to every pull request.
- Prototype (discarded): the step and the recipe passed `just lint-workflows` (actionlint), `test-docker-context.sh` (6/6, the pin check) and `test-release.sh` (133/133, the job list); `just playwright-versions` printed `web-1.65.1-api-1.65.2` on macOS.
- The repository's Actions cache also holds the `docker` job's layer cache (`type=gha`). Chromium and its headless shell are a few hundred MB; record the cache size from the job log (Task 3.5).

### Keep or remove the cache (Task 3.5, AC 8)

`--with-deps` runs `apt-get` on every run, cache or not, and that part may be most of the 43 s. The rule: keep the cache if the warm run's cache step plus `install-e2e-browsers` step is at least 15 s shorter than 43 s. Otherwise remove the cache step, the key step and the recipe in the same commit, drop the cache assertions from `test-e2e-ci.sh`, and record the numbers and the decision. 15 s is the story's threshold for "saves less than it costs to maintain" (ADR-8 decision 5); the maintainer can change it in review.

### The connection reset (Task 4)

Working explanation (ADR-8 decision 6): uvicorn closes a keep-alive connection that has been idle for 5 s; Playwright's `route.fetch()` runs in the test process and reuses a pooled connection; when the reuse lands just as the server closes the socket, the client sees `ECONNRESET` / "socket hang up". For a `GET` a retry on a new connection is safe, which is what browsers do.

The probe (a scratch spec, for example `web/e2e/zz-keepalive-probe.spec.ts`, never committed; run with `just test-e2e-ci e2e/zz-keepalive-probe.spec.ts` against the throwaway container, which runs the same `CMD` as the dev stack):

1. In one test with a long `test.setTimeout`, route `**/api/v1alpha1/server/status` with a handler that calls `route.fetch()` **without** the retry, counts and records any error, and fulfils or aborts.
2. From the page, `fetch` the status with the Admin key, wait a delay, fetch again; sweep the delay from 4.90 s to 5.10 s in 10 ms steps, then repeat the sweep (about 40 to 60 attempts per sweep).
3. Also run the whole CI set three times with the retry taken out locally (`fetchWithOneRetry` returning `route.fetch()` directly), counting resets: about 20 s per run, and closest to how the reset was first seen.

Stop condition and outcomes:

- **Reproduced** (any `ECONNRESET` or "socket hang up" from `route.fetch()`): record the attempts, the delay and the error text. If time is left in the box, one client-side fix may be tried, for example asking `route.fetch()` not to reuse the connection (a `connection: close` request header, if Playwright passes it on). It counts only if the probe then shows no reset in three times the attempts it took to reproduce. Then the retry may go; otherwise the comment states the cause and the retry stays as the right answer.
- **Not reproduced when the box ends:** the comment records the probe, the attempt count, the delays and the stack, and that the cause is still unknown; the retry stays.
- Either way: no new bead (ADR-8 decision 6), no change to the image's `CMD` or uvicorn options here. If the cause is found and a server-side setting (a longer `--timeout-keep-alive`) looks worth it, it goes under Follow-ups for the maintainer: it changes the product.

### Beads (Task 6.5, by the controller after merge)

- `VSS-3mr`: AAR (full template, size-m): navigation covered since Story 16.7 (PR #154) and now in CI, "new directory appears on refresh" covered by `file-browser-new-directory.spec.ts`; commit links; close.
- `VSS-029` "Web UI Test Coverage": close only once `VSS-37a` (Story 20.2) and `VSS-3mr` are both closed (`bd show VSS-029` shows 18 of 18). AAR names Stories 16.7, 20.2 and 20.5. If `VSS-37a` is still open, leave `VSS-029` open and report it.
- `VSS-571h`: stays open. A comment: parts 2 (seeded tree, 5 tests in CI), 3 (cache, with the numbers) and 4 (the reset, with the outcome) done in Story 20.5; part 1 in Story 20.6, which closes it.
- The dev agent changes no bead (the controller does all three after the merge).

### Existing tests that change (deliberately)

- `web/e2e/file-browser-navigation.spec.ts`: the tag, its comment and the header. No test body changes.
- `web/e2e/config-js.ts`: the comment above `fetchWithOneRetry`; the function itself only if Task 4 removes the cause.
- `scripts/tests/test-e2e-ci.sh`: new assertions (the seeded directory, the export, the spec's container name, `VS_DATA_DIR`, the cache step). The existing ones do not change; `TAGS` still names `@game-server` (`:26`).
- The CI set grows from 113 to 119 (re-count at implementation). The CI set's other specs see one more directory at the root of `serverdata`: `layout-widths.spec.ts` opens the File Manager tab (`:506`) and `monitor-password-redaction.spec.ts:113-115` clicks `serverconfig.json` in it; neither counts the items. Watch them in Task 1.4.
- No Vitest test, no pytest test, no API file.

### Not changed (do not "fix" these here)

- No file under `api/src/` or `web/src/`: no endpoint that creates a directory (ADR-8 decision 3, rejected), no refresh button in the File Manager.
- `TAGS` in `scripts/e2e-ci.sh` and the `@game-server` tag itself (the README keeps it). Story 20.6 changes the tags for `@moddb`.
- `just test-e2e-web`, `just test-e2e-api`, `just docker ...`, the compose files, the `Dockerfile` (its uvicorn `CMD` included).
- The `api`, `web`, `scripts`, `docker` and `semgrep` jobs, `release.yml`, the job's timeout, the retries and workers in `playwright.config.ts`.
- `pretendServerInstalled` beyond what Task 4 decides.

### API contract changes

None. No endpoint, field, status or error code changes. The story touches E2E specs, one script, its test, one recipe, one workflow job and documentation.

### Decisions for the maintainer

Each is written into the story and can be reversed in review:

1. The new-directory test runs only for the exact container name `vintagestory-manager-e2e`, not for any exported name (Dev Notes "ADR against the code" 1).
2. The cache key is read from the installed Playwright CLIs, not parsed from the lock files (ADR against the code 2).
3. The 15 s threshold for keeping the cache.
4. The time box of 60 minutes for the connection reset.
5. The seeded names `Logs/Archive`, and the new directory under `Logs`.

### Testing Requirements

- This story's tests are the E2E run, `scripts/tests/test-e2e-ci.sh` (red first in Tasks 1, 2 and 3) and the linters. Each task ends with `just test-scripts`; Tasks 1, 2 and 4 with `just test-e2e-ci`.
- `just typecheck-web` type-checks the specs (Story 20.3). After a spec edit also run `cd web && bunx playwright test --list`.
- No manual browser check: nothing an admin sees changes. The proof is the green `E2E tests` job.
- E2E runs never start or stop the game server, never send console commands, and take no screenshots. The only test that changes state does so in the throwaway container only.
- Tests never write into `dev/` or `./data`.

### Security Requirements

- `docker exec` from a test reaches only the container named `vintagestory-manager-e2e`, with a fixed command (`mkdir`) and arguments passed as an array, never through a shell.
- No secret in the workflow, the script or the specs; the keys stay the script's placeholders. The cache holds browser builds only. The job's permissions stay `contents: read`.
- The `ls -ld` log line and any probe output show only throwaway-container paths.

### Development Commands

- `just test-e2e-ci`, `just test-e2e-ci e2e/<spec>`, `just test-scripts test-e2e-ci.sh`, `just lint-scripts`, `just lint-workflows`, `just typecheck-web`, `just check`, `just playwright-versions`.
- `cd web && bunx playwright test --list --grep-invert "@moddb|@game-server|@install"`.
- `gh run view <id> --log`, `gh run rerun <id> --job <job-id>` (with the controller, Task 3.5).
- Run `ruff format` only on API files this story changes (none).

### Previous Story Intelligence

- **19.7:** built `scripts/e2e-ci.sh`, its test, the job and the README this story extends; its prototype habit (actionlint, ShellCheck, `--list`) is followed here. Its Debug Log records the one reset (Task 4.5) and 113 + 31 + 5 = 149. Its review: a completion note must be true of the code; record counts as they were, including a failing first run.
- **19.1:** a Monitor key sees the root and `ModConfig` only, so a seeded `Logs` changes nothing for the Monitor-key specs.
- **16.7:** the navigation spec and its read-only rule.
- **17.x/18.x:** a spec that changes real state needs a snapshot guard and must restore the dev stack exactly. This story avoids the case: the only state change is in the throwaway container, and the dev-stack check compares the tree before and after.
- **20.3:** recipes take `positional-arguments` (`"$@"`), `lint-scripts` uses globs (the new recipe has no arguments), `web/e2e/tsconfig.json` exists, and the report files are untracked, so a run leaves the tree clean.
- **20.4:** adds the `semgrep` job; the job-list guard in `test-release.sh` then names six jobs. This story adds steps, not a job.

### Git Intelligence

- Base `7f04ea2` (`docs(epic-20): record the maintainer's answers and use a mod database address setting`). Stories 20.1 to 20.4 land first.
- Planned commits: Task 1 `test(story-20.5/task-1): seed a nested directory so the file browser navigation tests run in ci`. Task 2 `test(story-20.5/task-2): a directory created while the file manager is open shows after a reload`. Task 3 `ci(story-20.5/task-3): cache the playwright browsers in the e2e job` (or `ci(story-20.5/task-3): record why the playwright browsers are not cached`). Task 4 `test(story-20.5/task-4): record what the e2e connection reset investigation found`. Task 5 `docs(story-20.5/task-5): seeded directories and the new-directory test in the e2e readme`. Task 6 `chore(story-20.5/task-6): move story 20.5 to review`.

### Project Structure Notes

- New: `web/e2e/file-browser-new-directory.spec.ts`.
- Modified: `scripts/e2e-ci.sh`, `scripts/tests/test-e2e-ci.sh`, `web/e2e/file-browser-navigation.spec.ts`, `web/e2e/config-js.ts`, `web/e2e/README.md`, `Justfile`, `.github/workflows/ci.yml`.
- `README.md` and `CLAUDE.md` need no change: neither names the tags or the CI count.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.5: The File Browser E2E Tests Run in CI]
- [Source: _bmad-output/planning-artifacts/prd.md] FR248, FR249, FR250, FR251 (`:810-813`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md#ADR-8], facts "E2E" and "CI"
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md] (section 2, risk line for Story 20.5)
- [Source: _bmad-output/implementation-artifacts/19-7-e2e-runs-in-ci.md], [18-2-install-and-version-change-keep-records-right.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-3mr`, `VSS-571h`, `VSS-029`; parent `VSS-lzgg`
- `project-context.md` (story size `:259`, commit format `:615-640`), `CLAUDE.md` (always `just`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. Prototypes, discarded: the script's seeding and export with the `test-e2e-ci.sh` assertions (`just lint-scripts`, `just test-scripts test-e2e-ci.sh` 21/21), the cache step and recipe (`just lint-workflows`, `test-docker-context.sh`, `test-release.sh`), and the new spec (type-checked with Story 20.3's E2E `tsconfig`; `--list` counts 114 and 119). No container was started and no E2E test was run.

### File List

## Change Log

- 2026-11-17: Story 20.5 created and validated (ready-for-dev).
