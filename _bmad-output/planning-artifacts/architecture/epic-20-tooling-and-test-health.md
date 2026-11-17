# Epic 20: Tooling and Test Health - Architecture Decisions

Decisions from the Epic 20 course correction (2026-11-17). Epic 20 has no preparation story. Each fact was checked by reading or running the code at commit `3f1c6ea` (`main` after Epic 19, release `v0.1.0-rc.5`, with the CI skip on release commits); file and line references are to that commit. Where a story has to confirm something first, the ADR says so.

Decisions the maintainer made on 2026-11-17 are marked "Matt, 2026-11-17" and are not open: the one-time `ruff format` of the API and its place as the first change of the epic (ADR-1), that Prettier for the web is not in scope (ADR-1), and the whole semgrep design (ADR-6, ADR-7). The maintainer answered the open questions of the proposal the same day: every default stands except one, where he chose the alternative (ADR-9: the mod database's address becomes a setting), and he approved the three pull-ins (`VSS-eh41`, `VSS-zhv3`, `VSS-3q2s`). The status lines say which answer each ADR carries.

| Story | ADRs |
|---|---|
| 20.1 The API Is Formatted Once and Stays Formatted | ADR-1 |
| 20.2 A Green, Quiet `just check` | ADR-2, ADR-3 |
| 20.3 Lint and Type Checks Cover Everything | ADR-4, ADR-5 |
| 20.4 Semgrep Locally and in CI | ADR-6, ADR-7 |
| 20.5 The File Browser E2E Tests Run in CI | ADR-8 |
| 20.6 The Mod Database E2E Tests Run in CI | ADR-9 |
| 20.7 Reproducible Image Inputs and the Numbering Rule | ADR-10, ADR-11 |

## Facts Checked in the Code

**`just check` today.**

- `just check` is `lint typecheck test` (`Justfile:179`). `lint` is `lint-api lint-web lint-scripts lint-workflows` (`:141`); `typecheck` is `typecheck-api typecheck-web` (`:164`); `test` is `test-api test-web test-scripts` (`:29`).
- `just typecheck-api` prints `0 errors, 3 warnings`. All three are `reportUnknownVariableType` on dict-literal fixtures that hold an empty list: `api/tests/test_mod_service.py:1640` (`mod_without_releases`) and `:1719` (`mod_without_tags`), and `api/tests/test_mods_router.py:3099` (`mods_without_tags`). The lines in `VSS-1ar` (1589, 1668, 2424) are older. `api/pyproject.toml:56` sets the rule to `warning`.
- The web suite: 133 files, 3,353 tests, 3,349 passed and 4 skipped. The four `it.skip` are `web/src/components/FilterControls.test.tsx:156`, `web/src/hooks/use-browse-mods.test.tsx:247` and `:253` (three empty placeholders named "DISABLED (requires API enhancement)"), and `web/src/components/ModTable.test.tsx:1056` (a real test, "shows loading state in remove button when removing"). `FilterControls.tsx` has a game version filter today, so the placeholders' reason is out of date.
- **`VSS-37a` is already fixed in the code.** The three tests it names (`ModTable.test.tsx:456`, `:480`, `:506`, in `describe('remove mod (AC: 8)')`) are plain `it` and pass; commit `f393c3a` ("test: fix test warnings and enable skipped ModTable tests") re-enabled them. `just test-web src/components/ModTable.test.tsx`: 84 passed, 1 skipped (the one at `:1056`, which is `VSS-hnl`'s). The bead was never closed.
- `web/vitest.config.ts` sets no `pool`, so Vitest 5.1.0 uses forks. Measured on this commit: default pool 15.2 s wall clock, all passing, and Vitest reports "jsdom was created 133 times, 74.09s total, 43% of tracked time". With `--pool=vmThreads`: 6.3 s wall clock, 111 tests fail in 4 files: `src/hooks/use-log-stream.test.ts` (45), `src/hooks/use-console-websocket.test.ts` (36), `src/features/terminal/Terminal.test.tsx` (27), `src/lib/cookies.test.ts` (3).
- The failures have two causes. `TypeError: Cannot redefine property: location`: `Object.defineProperty(window, 'location', ...)` at `use-log-stream.test.ts:108` and 12 more places, `use-console-websocket.test.ts:108` and 12 more, `Terminal.test.tsx:151`. `TypeError: Cannot delete property 'document' of [object Window]`: `delete global.document` at `cookies.test.ts:100`, `:114`, `:136`.
- `web/src/features/terminal/Terminal.tsx` is imported only by its own test (`VSS-eh41`'s comment says the `/terminal` route went in Epic 11). Its test is one of the four failing files.
- In CI (run on `main`, 2026-11-17) `just test-web` took 60 s of the web job's 75 s.

**Lint, type check and recipes.**

- `web/tsconfig.json` has `"include": ["src", "tests"]`. Nothing type-checks `web/e2e/` (23 specs and `config-js.ts`, 5,304 lines) or `web/playwright.config.ts`. Checked with the same compiler options and `types: ["node"]`: 0 errors today.
- `web/package.json:15-16`: `lint` and `typecheck` are both `tsc --noEmit`, so `just lint-web` and `just typecheck-web` run the same command and `just check` type-checks the web twice. There is no ESLint. `build` is `tsc && vite build`.
- `ruff format --check` on `api/`: 75 of 157 files would be reformatted (23 of 61 under `src`, 52 of 96 under `tests`), about 2,000 changed lines. `api/pyproject.toml:36` sets `line-length = 100`. `just lint-api` runs only `ruff check .` (`Justfile:145`); `just format-api` exists (`:190`). There is no `.git-blame-ignore-revs`.
- For reference, not in scope: `bunx prettier --check` reports 279 unformatted files under `web/src`; Prettier is not a dependency and has no configuration (`just format-web`, `Justfile:194`, runs an unpinned `bunx prettier`).
- `just lint-scripts` names six paths and leaves `scripts/sprint-status.sh` out (`Justfile:151-153`). ShellCheck 0.11.0 on it: SC2076 at lines 93, 98, 103 and 196 (a quoted right-hand side of `=~`, used for a literal word match) and SC2034 at line 216 (`comment` unused in `cmd_retro_add`). The lines in `VSS-1eb` are two lower; the `remove` command added in Epic 19 moved them. `scripts/tests/test-sprint-status.sh` covers only `remove`.
- Recipes interpolate `{{ARGS}}` into the command line (`Justfile:35` `test-api`, `:39` `test-web`, and also `test-scripts`, `test-e2e-api`, `test-e2e-web`, `test-e2e-ci`, `coverage-api`, `coverage-web`, `lint-api`, `typecheck-api`, `dev-api`, `dev-web`, `install-api`, `install-web`, `docker`, `changelog`, `release`, `sprint`). The shell splits the result again, so `just test-api -k "a or b"` reaches pytest as `-k a or b`. `just sprint retro-add <key> "a comment"` has the same problem. `.mise.toml` pins just 1.59.0, which has the `positional-arguments` setting and attribute.
- `web/playwright-report/index.html` and `web/test-results/.last-run.json` are tracked. `.gitignore` has no entry for either directory. `bunx playwright test --list` rewrote `index.html` during this planning. The `e2e` job uploads both directories as an artifact on failure (`ci.yml:102-110`), which does not need them tracked.

**CI.**

- `.github/workflows/ci.yml` has five jobs: `api`, `web`, `scripts`, `docker`, `e2e`. The workflow's permissions are `contents: read` (`:10-11`). Every job has `if: "${{ !startsWith(github.event.head_commit.message, 'chore(release): ') }}"`.
- `scripts/tests/test-release.sh:319-325` pins that: the job list must be exactly `api docker e2e scripts web`, and every job's `if:` must be the skip expression. A new job must update the list and carry the `if:`.
- `scripts/tests/test-docker-context.sh:19-22` fails when a workflow action is not pinned to a full commit SHA.
- The `api` job runs `just lint-api` and `just typecheck-api`. The `web` job runs `just test-web` and `just build-web` and neither `lint-web` nor `typecheck-web`; `build-web` type-checks `src` and `tests` through `tsc`.
- Timings on `main`, 2026-11-17: `e2e` job 3 min 16 s, of which `just install-e2e-browsers` 43 s and `just test-e2e-ci` 1 min 47 s.
- GitHub code scanning has never received an analysis for this repository (the alerts API answers "no analysis found"). The repository is public. Secret scanning and push protection are disabled.

**Semgrep.**

- Semgrep is not used anywhere in the repository: no recipe, no configuration, no `nosemgrep` comment.
- Planning's trial, semgrep 1.185.0 (Community Edition), `--metrics=off`, eight registry packs (`p/python`, `p/typescript`, `p/react`, `p/dockerfile`, `p/github-actions`, `p/security-audit`, `p/secrets`, `p/owasp-top-ten`): over source only (229 files) 56 s wall clock and 1 finding; with the test files (389 files) 6 min 3 s and the same 1 finding. Most of the extra time is in large test files; 739 of the 745 engine messages were rules that need the Pro engine and three were rule timeouts.
- The maintainer's measurement (Matt, 2026-11-17), same version, over `api/src`, `web/src`, `web/e2e`, `.github`, `Dockerfile` and `scripts`: `p/python` 1 finding; `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile` 0 findings each.
- The one finding is `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` at `api/src/vintagestory_api/services/server.py:650`: `hashlib.md5()` computes the checksum the vendor publishes for a game download. It is an integrity check, not a security use.
- For reference only (Matt, 2026-11-17), `p/default` also reports `tarfile-extractall-traversal` at `server.py:690` (a false positive: the extraction uses a custom filter built on the `data` filter), two `unsafe-formatstring` hits at `web/src/hooks/use-console-websocket.ts:10` and `use-log-stream.ts:10`, a Dockerfile note and two hits in test files. `p/default` is not used.
- `project-context.md:218-250` ("No Silent Failures Rule") forbids suppressions unless each has an inline reason, a tracking issue and review approval; its list names `eslint-disable`, `@ts-ignore`, `pytest.skip`, `# noqa` and `# type: ignore`. The maintainer's own rule is stricter: no lint or type suppression to make an error go away.

**E2E.**

- `web/e2e/` has 23 spec files and 149 tests. Untagged (the CI set): 113 tests in 15 files. `@moddb`: 31 tests in 10 files. `@game-server`: 5 tests in 1 file. `@install`: 3 tests in 2 files, each also `@moddb`. The tags are explained in `web/e2e/README.md`.
- The `@moddb` tags are at `browse-game-version.spec.ts:168`, `install-file-conflict.spec.ts:82`, `mod-browse-state.spec.ts:128`, `installed-mod-any-modid.spec.ts:89`, `mod-browse-name-sort.spec.ts:105`, `installed-status.spec.ts:153` and `:205` (with `@install`), `mod-detail-bad-data.spec.ts:50`, `mods-navigation.spec.ts:55`, `mod-detail-media.spec.ts:382`, `mod-install-release.spec.ts:127` and `:219` (with `@install`).
- The only `@game-server` tag is `file-browser-navigation.spec.ts:108`. Its reason: `findNestedPath` (`:56-74`) needs a directory inside another under `serverdata`, which only a game server that has run creates. The spec is read-only and uses the Admin key.
- `scripts/e2e-ci.sh` starts one throwaway container (`vintagestory-manager-e2e`, `127.0.0.1:18080`), copies `web/e2e/fixtures/serverconfig.json` into it, and points `mods.vintagestory.at`, `api.vintagestory.at` and `cdn.vintagestory.at` at loopback with `--add-host` so any call to them fails at once. It runs Playwright with `--grep-invert '@moddb|@game-server|@install'`, then `api/tests/e2e` (one health test).
- The API has no endpoint that creates a directory in `serverdata`, and `FileManagerPanel.tsx` has no refresh control; "refresh" in `VSS-3mr` can only mean loading the page again. `VSS-3mr`'s comment (2026-11-14) says directory navigation is covered by `file-browser-navigation.spec.ts` and "new directory appears on refresh" is not.
- The mod database addresses are class constants: `BASE_URL = "https://mods.vintagestory.at/api"` and `DOWNLOAD_URL = "https://mods.vintagestory.at/download"` (`api/src/vintagestory_api/services/mod_api.py:348-349`). No setting changes them. The client is `httpx.AsyncClient` (`:399`), httpx 0.28.1, with no `verify` argument.
- `web/e2e/config-js.ts:21-33`: `fetchWithOneRetry` retries `route.fetch()` once because a full run against the dev stack once ended in `ECONNRESET`. The cause was not found. The API is served by uvicorn with its default settings (`Dockerfile:91`).
- `web/package.json:19` asks for `@playwright/test ^1.57.0`; `web/bun.lock` resolves 1.65.1. The API uses `pytest-playwright` (`api/pyproject.toml:22`). `just install-e2e-browsers` (`Justfile:99-101`) installs Chromium for both.

**Image.**

- `Dockerfile:51`: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`. `.mise.toml` pins uv 0.13.8 for development and CI.
- `Dockerfile:9`: `FROM node:26-slim` (a moving tag, build stage). `Dockerfile:36`: `FROM mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64` (a version tag with no digest; such tags are pushed again when the base system is patched). `Dockerfile:17` pins bun 1.4.4.
- `Dockerfile:41-46`: `apt-get update && apt-get upgrade -y && apt-get install ... python3.14 python3-pip`, with no package versions.
- `renovate.json` extends the organisation's preset, which is `config:recommended` with `helpers:pinGitHubActionDigestsToSemver` and without `docker:pinDigests`. Its two rules hold Python below 3.15 and the .NET runtime below 11.
- `RELEASING.md:75` says that re-running a failed release job pushes the image tags and attestations again.

**Story numbering.**

- `project-context.md:834-847` says epics always start at Story 1, never Story 0, and "Epic 12 onwards uses Story 1".
- `sprint-status.yaml`: preparation stories numbered X.0 in Epics 4, 5, 6, 7, 8, 13, 14, 15 and 16; numbered X.1 only in Epic 12. Epics 9, 10, 11, 17, 18 and 19 have no preparation story and start at X.1.
- `cliff.toml:43` skips commits whose scope is `story-X.0` ("preparation (X.0) stories") when it builds release notes. The BMAD story template says the same (`_bmad/bmm/workflows/4-implementation/create-story/template-api-spike.md:9`, `workflow.yaml:24`).

## ADR-1: The API Is Formatted Once, in One Commit, and the Check Keeps It So

**Status:** Accepted (Matt, 2026-11-17). Implemented by Story 20.1 (`VSS-3asx`, the formatting half).

**Context:** 75 of the API's 157 Python files are not in `ruff format`'s output form, so formatting any one file while working on it adds changes that have nothing to do with the work. Earlier epics avoided `just format-api` for that reason. Nothing checks the format.

**Decision:**

1. **One commit reformats the whole API** (Matt, 2026-11-17): `ruff format` over `api/`, with the configuration as it is (`line-length = 100`). The commit holds nothing else: no hand edit, no lint fix, no configuration change. Its subject is `chore(story-20.1/task-1): format the API with ruff format`; it is not a `feat` or `fix`, so it adds no release note.
2. **It is the first change of the epic** (Matt, 2026-11-17), made while no other branch is open, because it conflicts with any branch that edits an API file.
3. **It is its own story and its own pull request.** A reviewer cannot read 2,000 mechanical lines for meaning, and does not need to: the review reproduces the commit (check out its parent, run the same `ruff format`, compare the trees) and confirms that the test suite gives the same results before and after. Mixed with other changes, neither check would be possible.
4. **The commit's hash goes into a new `.git-blame-ignore-revs`** at the repository root, with a comment line naming it, in a second commit of the same pull request. The project merges pull requests with merge commits and never squashes or rebases them, so the hash stays valid on `main`. GitHub's blame view reads the file by itself; a clone needs `git config blame.ignoreRevsFile .git-blame-ignore-revs` once, which `scripts/worktree-setup.sh` sets and the README mentions.
5. **`just lint-api` gains `ruff format --check`** after `ruff check`. CI's `api` job already runs `just lint-api`, and `just check` runs it through `just lint`, so both fail on an unformatted file with no workflow change.
6. **`ruff check` must still pass after the format.** If the formatter and a lint rule disagree anywhere, the story reports it and does not add a `# noqa`.
7. **Prettier for the web is not in scope** (Matt, 2026-11-17). The 279 unformatted web files and the unpinned `just format-web` stay as they are.

**Consequences:**

- `git blame` on the API skips the format commit on GitHub, and locally once the setting is in place.
- Any branch cut before Story 20.1 merges must be rebuilt on top of it; none is open.
- From Story 20.1 on, every API commit of this epic and later is formatted, so `just format-api` is safe to run.

## ADR-2: Web Unit Tests Run in the `vmThreads` Pool

**Status:** Accepted. Matt confirmed decision 5 on 2026-11-17 and approved the pull-in of `VSS-eh41` (decision 3). Implemented by Story 20.2 (`VSS-6wj`, `VSS-eh41`).

**Context:** Creating a jsdom environment for each of the 133 test files is 43% of the tracked time. `vmThreads` creates it once per worker and keeps per-file isolation; measured, it cuts the local run from 15.2 s to 6.3 s. Four files fail under it because of how they stub browser globals.

**Decision:**

1. **Switch:** `pool: 'vmThreads'` in `web/vitest.config.ts`, once the suite passes under it.
2. **The four files change how they stub, not what they test.** The story reads every failure first (only two messages were seen in planning). `delete global.document` in `cookies.test.ts` becomes a stub that Vitest restores (`vi.stubGlobal` with `vi.unstubAllGlobals`). The `window.location` redefinitions in the two hook tests are replaced by whichever of these the story shows to work under both pools, in this order of preference: setting the document URL through the jsdom instance; `vi.stubGlobal('location', ...)`; or moving the URL building into a small pure function that takes the location as an argument and is tested directly. The third changes product code and is used only if the first two fail.
3. **`Terminal.test.tsx` is deleted with the dead `Terminal.tsx`** (`VSS-eh41`, pulled into Story 20.2; Matt, 2026-11-17), so three files are left to fix. Its 27 tests go with it and the story lists them as deleted on purpose.
4. **Rejected: `isolate: false`.** It shares module and DOM state between files, so a test can pass or fail depending on which file ran before it.
5. **Rejected as a permanent state: leaving some files on the forks pool** through a per-file pool setting. It keeps two ways of running tests and hides the stubs that do not work. If a file cannot be made to pass under `vmThreads`, the story stops and asks, and the switch does not merge until all files pass (Matt, 2026-11-17).
6. **Proof:** the suite passes under `vmThreads` locally and in CI, the count of tests does not drop (apart from tests deleted on purpose, which the story lists), and the story records the `just test-web` time in CI before (60 s) and after.

**Consequences:**

- A test that redefines a non-configurable global fails from now on; the stubbing pattern is written down in `project-context.md`'s testing section.
- `vmThreads` runs tests inside Node's `vm` contexts, which Vitest documents as able to leak memory on long runs and as behaving differently for some native modules. The run is short and the suite showed neither in planning; the story watches for both.

## ADR-3: Skipped Tests and Type Warnings Are Resolved, Not Hidden

**Status:** Accepted. Implemented by Story 20.2 (`VSS-hnl`, `VSS-1ar`, `VSS-37a`).

**Decision:**

1. **The three empty placeholders are deleted,** not turned into `it.todo`: they have no body, and the feature they wait for (a game version filter) exists. Before deleting, the story checks that selecting a game version in `FilterControls` and filtering by it in `use-browse-mods` each have a test with assertions; where one is missing, it writes that test in the placeholder's place.
2. **The fourth (`ModTable.test.tsx:1056`) is rewritten to pass:** the mocked request returns a promise the test resolves itself, the test waits for the disabled button with `findBy` or `waitFor`, and it does not wrap the click in `act`. If the state cannot be observed in jsdom after a real attempt, the state is covered by a Playwright test with a stubbed slow answer and the unit test is deleted; the story says which path it took and why.
3. **The three Pyright warnings are fixed with a type annotation** on each fixture (`dict[str, Any]` or a narrower type). No `# pyright: ignore`, and the rule's level in `pyproject.toml` does not change.
4. **`VSS-37a` needs no code change.** Story 20.2 runs the three tests, records the result and closes the bead with an AAR that names commit `f393c3a`.
5. **No tool is added to forbid `it.skip`.** `project-context.md`'s forbidden-pattern list gains `it.skip`, `test.skip` in unit tests and `describe.skip`, beside `pytest.skip`. A precondition skip inside an E2E test body (`test.skip(!MONITOR_KEY, ...)`) is a different thing and stays allowed.

**Consequences:** `just check` ends with 0 warnings from Pyright and 0 skipped tests from Vitest, so a new warning or skip is visible the day it appears.

## ADR-4: The E2E Specs Are Type-Checked by Their Own Project, Inside `just typecheck-web`

**Status:** Accepted. Implemented by Story 20.3 (`VSS-3asx`, the type-check half).

**Decision:**

1. **A new `web/e2e/tsconfig.json`** extends `../tsconfig.json`, sets `types` to `["node"]` (the specs must not see Vitest's globals or `vite/client`), and includes the directory and `../playwright.config.ts`. The strict options are inherited.
2. **`just typecheck-web` checks both projects:** the `typecheck` script in `web/package.json` becomes `tsc --noEmit && tsc --noEmit -p e2e/tsconfig.json`. So `just typecheck` and `just check` cover the specs with no new recipe name to remember.
3. **`build` does not change** (`tsc && vite build`). A type error in a spec must not stop the image build, which has nothing to do with the specs.
4. **CI:** the `web` job gains a `just typecheck-web` step. Today no CI step would run the new check: the job runs only the tests and the build.
5. **Any error the check finds is fixed in the spec.** No `@ts-expect-error`. Planning's check found none.

**Consequences:** `just check` and CI fail on a type error in a spec or in the Playwright configuration. The web is still type-checked twice by `just check` (`lint-web` and `typecheck-web` run the same script); that costs a few seconds and is left alone, since replacing `lint-web` with a real linter is a different piece of work.

## ADR-5: Recipes Pass Arguments Intact, ShellCheck Covers Every Script, and Playwright Output Is Not Tracked

**Status:** Accepted. Implemented by Story 20.3 (`VSS-6354`, `VSS-1eb`, `VSS-uw9z`).

**Decision:**

1. **Arguments are passed as positional parameters.** Every recipe that hands `*ARGS` to a tool gets just's `positional-arguments` attribute and uses `"$@"` in place of `{{ARGS}}`, so each argument reaches the tool as the caller quoted it. This covers all eighteen recipes listed in the facts, not only `test-api` and `test-web`: the fault is the same in each, and `just sprint retro-add <key> "a comment"` is a case the project uses. In `docker COMMAND *ARGS` the command is `$1` and the rest follow.
2. **Proof without running a tool:** a script test calls the Justfile with a stub in place of the tool (or an equivalent check that needs no installed project) and asserts that an argument with spaces arrives as one argument. The story also runs `just test-api -k "a or b" --collect-only -q` and `just test-web -t "a b"` once and records the output.
3. **`sprint-status.sh` becomes ShellCheck-clean without a directive.** The four literal word matches become `case` statements, and the unused `comment` parameter is either used as the command's help describes or removed with its help text. Its behaviour does not change; `scripts/tests/test-sprint-status.sh` gains tests for the status checks that are rewritten (valid and invalid values for a story, an epic, a retrospective and a retro item).
4. **`just lint-scripts` uses globs:** `shellcheck -x scripts/*.sh scripts/tests/*.sh`. A new script is covered without editing the recipe, and the comment about `VSS-1eb` goes.
5. **Playwright's output is not tracked:** `git rm --cached` for `web/playwright-report/index.html` and `web/test-results/.last-run.json`, and `web/playwright-report/` and `web/test-results/` in `.gitignore`. The CI artifact upload reads the files from disk and is not affected. `.dockerignore` gets the same two paths so a local report never enters the build context.

**Consequences:** A local E2E run leaves the working tree clean. Agents no longer need to restore the two files after a run.

## ADR-6: Semgrep Runs from a Pinned Version with Six Registry Packs over the Source

**Status:** Accepted (Matt, 2026-11-17), decision 8 included. Implemented by Story 20.4 (`VSS-djg`).

**Decision:**

1. **Semgrep runs locally and in CI through one script** (Matt, 2026-11-17): `scripts/semgrep.sh`, called by a new `just semgrep` recipe. The script holds the version, the packs, the paths and the options, so the two places cannot drift apart, and ShellCheck covers it.
2. **The version is pinned with `uvx semgrep==<version>`,** starting at 1.185.0, the version both measurements used. Why this and not the official image by digest: `uv` is already pinned in `.mise.toml` and present on every developer machine and in every CI job that uses the mise action, so the same command runs in both places with nothing new to install; `--baseline-commit` needs the git history, which a container only gets through a mounted repository and a `safe.directory` exception; and the image is a large pull on every CI run. The cost: the pin is a version, not a digest, and semgrep's own dependencies are resolved when it is installed. That is accepted for a tool that reads the code and writes a report.
3. **Renovate keeps the version current** through a custom manager in `renovate.json` that reads the version line of `scripts/semgrep.sh` (datasource `pypi`, package `semgrep`). A script test asserts that the line exists in the form the manager matches.
4. **The packs** (Matt, 2026-11-17): `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions`, `p/dockerfile`, fetched from the registry at run time. Not `p/default`, and no rule file is copied into the repository. Fetching at run time means a run needs the network and the rules can change between runs; ADR-7 decision 2 is what makes that safe for pull requests.
5. **The scope** (Matt, 2026-11-17): `api/src`, `web/src`, `.github`, `Dockerfile`, `scripts`. Not test files: `web/src/**/*.test.ts`, `web/src/**/*.test.tsx`, `scripts/tests/` and anything else that only holds tests is excluded by a `.semgrepignore` at the repository root. `api/tests`, `web/tests` and `web/e2e` are outside the listed paths already.
6. **Options:** `--metrics=off` always. The script passes extra arguments through, so `just semgrep --baseline-commit origin/main` works locally. With no arguments it scans the whole scope and exits non-zero on a finding.
7. **Time and noise budget.** Today: one finding in the whole scope, and under a minute locally. The CI job must finish within five minutes; the story measures it on the runner and reports before changing the packs if it does not. The story also records how many rules the engine could not run (rules written for the Pro engine, timeouts) for each pack; a rule that cannot run is not a finding and does not fail the run, and the number is written down so a jump is noticed.
8. **`just semgrep` is not part of `just lint` or `just check`** (Matt, 2026-11-17). It needs the network and adds about a minute, `just check` is run before every commit, and CI runs semgrep on every pull request anyway. The answer to `VSS-djg`'s question is also no for `test-api` and `test-web`: a static scan is not a test.

**Consequences:** One new script, one recipe, one ignore file, one Renovate rule. A developer without network access cannot run `just semgrep`; nothing else depends on it.

## ADR-7: Pull Requests Fail Only on Findings They Add, `main` Is Scanned in Full, and a False Positive May Be Marked Inline

**Status:** Accepted (Matt, 2026-11-17). Implemented by Story 20.4 (`VSS-4ac`).

**Decision:**

1. **A new `semgrep` job in `ci.yml`,** with the same release-commit skip `if:` as the other five jobs. `scripts/tests/test-release.sh` is updated in the same commit: the job list becomes `api docker e2e scripts semgrep web` (six jobs), and its loop already checks each job's `if:`.
2. **On a pull request the job fails only on findings the pull request adds** (Matt, 2026-11-17): the scan runs with `--baseline-commit` set to the merge base with `main` and with `--error`. The checkout needs the history for that (`fetch-depth: 0`). Because both sides are scanned with the same rules, a rule that the registry added yesterday cannot fail a pull request that did not touch the code it matches.
3. **On a push to `main` and on a manual run the job scans everything and does not fail on findings** (Matt, 2026-11-17). It fails only when semgrep itself fails to run.
4. **Results go to GitHub code scanning as SARIF** (Matt, 2026-11-17), uploaded by the full scan of `main`. Only this job gets `security-events: write` (with `contents: read`); the workflow's default stays `contents: read`. The upload action is pinned by commit like every other action, which `scripts/tests/test-docker-context.sh` enforces. A pull request from a fork has a read-only token and cannot upload; the pull request scan therefore reports in the job log and does not upload.
5. **Triage.** A finding is read and then one of three things happens, in this order of preference: the code is changed so that it is correct or says what it means; or, for a verified false positive, the line gets an inline comment (decision 6); or the story reports that the pack is too noisy and the pack list is reconsidered with the maintainer. A baseline file or an allow-list of accepted findings is not used: it would hide real findings as easily as false ones, and the pull request gate does not need one.
6. **The inline exception** (Matt, 2026-11-17): `# nosemgrep: <rule-id> — <reason>` (or `//` in TypeScript) naming exactly one rule is allowed, only for a verified false positive, and each one is looked at in review. A bare `nosemgrep` without a rule ID is not allowed. This is a documented exception to the project's no-suppressions rule, and Story 20.4 writes it into `project-context.md`'s "No Silent Failures Rule" with these conditions. Where changing the code states the intent better, the code is changed instead.
7. **The one finding today is fixed in the code** (Matt, 2026-11-17): `hashlib.md5(usedforsecurity=False)` at `services/server.py:650`, which says that the hash checks a download against the vendor's published checksum. The story confirms that the rule no longer matches. The commit is a `refactor`: nothing a user sees changes.
8. **If a chosen pack ever reports `tarfile-extractall-traversal` at `server.py:690`,** that line gets the inline comment with the reason that the extraction uses a custom filter built on the `data` filter (Matt, 2026-11-17). No chosen pack reports it today, so no comment is added now.

**Consequences:**

- The repository's Security tab shows semgrep's alerts for `main` from the first full scan on.
- A finding that a rule update produces in old code appears as an alert on `main` and blocks nobody; someone has to look at the alerts.
- A finding can be marked in the source with a reason. The review of each mark is the control; the rule in `project-context.md` says so.

## ADR-8: The CI Stack Is Seeded with Directories, a Test Creates One While the Page Is Open, and the Browsers Are Cached

**Status:** Accepted. Matt confirmed decision 3 on 2026-11-17. Implemented by Story 20.5 (`VSS-3mr`, and parts 2, 3 and 4 of `VSS-571h`).

**Decision:**

1. **`scripts/e2e-ci.sh` creates a nested directory in the throwaway container** before the tests (for example `Logs/Archive` under `/data/serverdata`, owned by `vsmanager`), beside the `serverconfig.json` it already copies. The names are made up and chosen to look like what a game server writes.
2. **`file-browser-navigation.spec.ts` loses its `@game-server` tag** once its five tests pass on that stack. The spec stays read-only and keeps discovering the path through the API, so it still runs unchanged on a stack with a real game server.
3. **"A new directory appears on refresh" is tested by creating the directory from outside the API** (Matt, 2026-11-17). The script exports the container's name; the test creates a uniquely named empty directory in the throwaway container with `docker exec` while the file manager is open, reloads the page, and expects the directory in the list. It never runs against a stack whose data it must not touch: without the exported name the test skips with a message, as the Monitor-key tests already do (`file-browser-monitor-note.spec.ts:140`), and `scripts/tests/test-e2e-ci.sh` pins that the script exports the name, so the CI run cannot skip it silently. Rejected: an API endpoint that creates directories (a product feature nobody asked for, added for a test) and writing into `./data` on the dev stack (the specs never change a developer's data).
4. **With that test, `VSS-3mr` is complete** (navigation since Story 16.7, the new directory now), and with `VSS-37a` closed in Story 20.2 the old epic `VSS-029` "Web UI Test Coverage" has no open child. Story 20.5 closes `VSS-029` with an AAR that names the two stories.
5. **The Playwright browsers are cached in the `e2e` job** with a cache action pinned by commit. The key is the two Playwright versions the lock files resolve (`web/bun.lock`, `api/uv.lock`) and the runner's operating system, not the whole lock files, so an unrelated dependency update keeps the cache. `--with-deps` installs system packages that the cache does not hold, so the job keeps a step for them. The install step takes 43 s today; the story records the time after and removes the cache again if it saves less than it costs to maintain.
6. **The connection reset gets a time-boxed investigation.** The working explanation: uvicorn closes an idle keep-alive connection after its default five seconds, and Playwright's `route.fetch()` reuses a pooled connection at the moment the server closes it, which is a reset on the client side and safe to retry for a `GET`. The story tries to reproduce it (a stub that fetches, waits just over the keep-alive time and fetches again, repeated). If it reproduces, the comment in `config-js.ts` states the cause and the retry stays as the right answer. If it does not within the time box, the comment records what was tried and that the cause is still unknown. Either way no new bead is opened for it.

**Consequences:** CI runs 119 tests where it ran 113 (the five navigation tests and the new one). The `@game-server` tag has no test left; the README keeps the tag and says so, since the next test that needs a running game server will need it.

## ADR-9: The Mod Database's Address Is a Setting, and CI Points It at Recorded Answers

**Status:** Accepted (Matt, 2026-11-17). The maintainer chose the address setting over the first draft's stand-in at the mod database's own address with a per-run certificate, confirmed trimmed real recordings, no scheduled live run and the `@moddb-live` tag. Implemented by Story 20.6 (part 1 of `VSS-571h`). Replaces Epic 19 ADR-14 decision 9, which named recording as the next step.

**Context:** 31 tests in 10 files read the live mod database through the API and are left out of CI. Locally they are flaky against the live service (two different failures in two full runs on 2026-11-17). What these tests are worth is that the real API code handles real mod database data in a real browser, so the recording has to be served to the API, not to the page: a stub in the browser (`page.route`) would skip the API code under test. The mod database's address is two class constants today (`services/mod_api.py:348-349`).

**Decision:**

1. **A new optional setting, `VS_MOD_DB_URL`** (Matt, 2026-11-17; `Settings.mod_db_url`), holds the base address of the mod database. Its default is `https://mods.vintagestory.at`, so a deployment that does not set it behaves exactly as today. The working name was `VS_MOD_API_URL`; `VS_MOD_DB_URL` is used because the value is the site's base address, not the address of its `/api` path, and the documentation calls the service "the mod database".
2. **What follows the setting: the API calls and the download.** `ModApiClient` builds `<base>/api` and `<base>/download` from the setting in place of the two constants. Both are the mod database's own host today, and they must move together: a replay or a mirror that answered the listing but sent the download to the live host would be half a replacement, and in CI it would be a call to the live service. A download still follows redirects wherever that server sends it, as today.
3. **What stays fixed: everything a browser is given.** The image host allow-list (`MOD_MEDIA_HOSTS`, `moddbcdn.vintagestory.at`; Epic 18 ADR-1), the link rules for logo, homepage and source URLs (Epic 19 ADR-12), the links the web UI builds to a mod's page on `mods.vintagestory.at`, and the form of a mod URL that install-by-URL accepts do not read the setting. Those are checks on what reaches a `src` or an `href`, and an address setting must not be a way to widen them. The game server's own `ModDbUrl` in `serverconfig.json` is a different thing and is not touched.
4. **The guard, checked once at start-up** (Matt, 2026-11-17). The value must be an absolute URL with the scheme `https`, a host, no user name or password, no query and no fragment, and no path beyond an optional trailing `/`. The scheme `http` is accepted only when `VS_DEBUG=true`. Anything else stops start-up with an error that names `VS_MOD_DB_URL`, says what is wrong and, for `http`, says that plain HTTP is for testing and needs `VS_DEBUG=true`; this is the same behaviour as a bad `VS_CSP_MODE`. The check reads the `VS_DEBUG` the process started with; switching debug logging on at run time does not change it, since the address is read once. Why `VS_DEBUG`: it already marks a deployment as not for production (it serves the API documentation and the role test routes, and the README says to leave it off outside development), so it adds no second "test mode" switch.
5. **A start-up warning whenever the address is not the default** (`mod_db_url_overridden`, with the scheme and host and nothing else), so an operator who set it by mistake, or inherited it, sees it in the log. The README and `.env.example` say what the setting is for (a mirror of the same database, or tests), that mods are downloaded from that address and run by the game server, and that it should otherwise be left unset.
6. **CI runs the mod database tests as a second pass with its own API container.** `scripts/e2e-ci.sh` keeps its first pass as it is: the untagged tests against a container in production mode with the live hosts blocked. For the second pass it creates a Docker network, starts a replay container on it that serves the recordings over plain HTTP, and starts a second API container from the same image with `VS_DEBUG=true` and `VS_MOD_DB_URL` pointing at the replay container; then it runs the `@moddb` tests that are not `@moddb-live` or `@install` against that second container. The live hosts stay blocked in the second container too, so a call that does not follow the setting fails at once. Why two passes: the guard needs debug mode for `http`, and running every E2E test in debug mode would stop CI from testing the image as it runs in production. The replay server is a small script with no dependency outside the Python standard library, run from the image the job has already built; a request it has no recording for is answered 404 with a body that names the URL, which the API turns into its usual 502.
7. **The first tasks add the setting and prove the path before anything is recorded:** the setting with its validation and tests; then, in the built image with the setting pointed at a stub, that the listing, the mod lookup, the game version list and the download all go to the stub and none goes to the live host, and that a missing recording is reported with its URL.
8. **The recordings live in `web/e2e/fixtures/moddb/`:** one file per recorded request and a manifest that lists each request, the date it was recorded and the spec that needs it. They are trimmed real answers (Matt, 2026-11-17): recorded from the live mod database and trimmed by the recording script in a way the manifest states (the full listing has more than 9,000 mods; the recording keeps the mods the specs name and enough others for paging and sorting to mean something). They hold what the mod database's public API returns, which includes mod names, descriptions and authors' names, and nothing else.
9. **The recorded answers keep the real image and link URLs.** They are not rewritten to point at the replay server, so they pass Epic 18's and Epic 19's allow-lists unchanged and the API code that applies those lists is tested on real values.
10. **One command refreshes the recordings:** `just record-moddb` runs a script that fetches the manifest's requests from the live mod database, applies the same trimming, and rewrites the files. The diff of a refresh is what shows a change in the mod database's shape: the script prints the fields that appeared or disappeared since the previous recording. A refresh is a normal pull request.
11. **Keeping in step with the real mod database:** the same specs still run against the live service on a developer's machine with `just test-e2e-web`, which uses no recordings and no setting. No scheduled workflow runs them against the live service (Matt, 2026-11-17): the live tests are flaky today and a red scheduled run would mostly report that. `web/e2e/README.md` says when to refresh (when a live run fails on data, and before a release that changes mod database handling).
12. **Which tests keep needing the live service** (Matt, 2026-11-17). A test whose point is to compare with live data (for example `browse-game-version.spec.ts:168`, "live: the cards agree with the browse response") and the three `@install` tests (which download and install a real mod's archive) stay local-only. A new tag `@moddb-live` marks the first kind; `@install` keeps its meaning. `@moddb` then means "needs mod database answers, recorded or live", and CI runs those tests. The story runs each of the 31 tests against the replay and decides test by test; a test that fails on recordings because of what it needs, not because of a fault, gets `@moddb-live` with a one-line reason.
13. **Images are not recorded.** Mod logos and screenshots are loaded by the browser from the real image host named in the recorded answers. In the CI run the specs answer those requests with a small placeholder through `page.route`, so the run sends no traffic to the live hosts and does not depend on them.
14. **Rejected.** The first draft's stand-in at the mod database's own address (a per-run certificate authority trusted through `SSL_CERT_FILE`): no product change, and more moving parts in the test script than the setting costs in the product (Matt, 2026-11-17). Stubbing in the browser: it is what the untagged specs already do and does not test the API. Accepting `http` for any host without a condition: a mistyped address would then send mod downloads over plain HTTP in production.

**Consequences:**

- The product gains one optional setting. It is a new configuration surface in code that Epic 19 restricted to known hosts; the guard, the warning and the fixed browser-side allow-lists are what keep it from loosening those restrictions. An operator who sets it chooses where mods are downloaded from.
- This is a change to the API's configuration and gets a release note: `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`.
- The API keeps its caches (the listing in memory, downloads on disk by file ID) without regard to the address. Changing the address on a deployment with existing data can mix the two sources' files; the README says to use an address that serves the same database.
- CI's E2E job starts three containers and runs up to 28 more tests; the story records the job time before (3 min 16 s) and after.
- Recordings go stale silently until someone refreshes them or a live run fails. The manifest's date makes their age visible.
- `scripts/e2e-ci.sh` grows a network, a replay container and a second API container, all removed by its existing cleanup. `scripts/tests/test-e2e-ci.sh` pins the new pieces.

## ADR-10: Every Image the Dockerfile Uses Is Pinned by Digest, and Renovate Moves the Pins

**Status:** Accepted (Matt, 2026-11-17): digests for uv and both base images, and `apt-get upgrade` kept and documented. Implemented by Story 20.7 (`VSS-870`).

**Decision:**

1. **uv is copied from a tag and digest:** `ghcr.io/astral-sh/uv:<version>@sha256:<digest>`, with the version `.mise.toml` pins (0.13.8 today), so the image, development and CI use one uv.
2. **The two base images get a digest too** (Matt, 2026-11-17): `node:26-slim@sha256:...` and `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64@sha256:...`. They are in the same file and have the same fault: a tag that is pushed again changes the build without a commit. The tags stay as they are, so the .NET rule in `renovate.json` keeps working.
3. **Renovate keeps the pins current.** Its Dockerfile manager reads `FROM` and `COPY --from` references and, once a digest is written, opens a pull request when the tag's digest changes or a newer version exists. `renovate.json` gains one rule that groups the uv image with the `uv` entry of `.mise.toml`, so they move in one pull request. The organisation's preset does not pin digests by itself and is not changed.
4. **A script test holds the rule:** `scripts/tests/test-docker-context.sh` asserts that every `FROM` and `COPY --from` image in the Dockerfile has `@sha256:` and that the uv tag equals the uv version in `.mise.toml`.
5. **`apt-get upgrade` stays** (Matt, 2026-11-17). It brings security fixes that are newer than the base image, and removing it trades them for repeatability. With the three digests pinned, the apt layer (the upgrade and the unpinned `python3.14` install) is the only input left that can differ between two builds of the same commit. Making it repeatable would mean installing from a dated Ubuntu snapshot and moving that date regularly, which is a larger change than this bead and has its own upkeep. `RELEASING.md` says plainly what is and is not repeatable: a re-run of the image job uses the same uv and base images, may pick up newer system packages, and can therefore push a different digest, and each run's attestations describe the digest that run pushed.

**Consequences:**

- Base image updates, including security rebuilds under the same tag, arrive as Renovate pull requests that CI builds and tests, where today they arrive unseen with the next build.
- The Docker layer cache in CI is invalidated when a digest moves, not at random.
- The release image is repeatable in its named inputs, not bit for bit.

## ADR-11: A Preparation Story Is Story X.0; an Epic Without One Starts at X.1

**Status:** Accepted (Matt, 2026-11-17). Implemented by Story 20.7 (`VSS-as6`). Documentation only.

**Context:** `project-context.md` says the first story is always Story 1 and that Story 0 is deprecated since Epic 12. Epic 12 is the only epic that followed it. Epics 13, 14, 15 and 16 numbered their preparation story X.0, `cliff.toml` relies on that to keep preparation commits out of the release notes, and the BMAD story template says X.0. Epics 17 to 20 have no preparation story.

**Decision:**

1. **The rule changes to match the practice.** The "Story Numbering" section of `project-context.md` says: an epic that needs a preparation story (research, a spike, architecture work before the first feature) numbers it X.0; an epic that needs none starts at X.1; a preparation story is optional and is added only when the planning says what it must find out.
2. **Why the rule and not the practice:** nine epics used X.0 and one used X.1; the release notes configuration and the BMAD template already assume X.0; done stories cannot be renumbered; and X.0 says at a glance that the story ships nothing a user sees.
3. **The section's table and historical note are rewritten** to say what happened: Epics 4 to 8 and 13 to 16 used X.0, Epic 12 used 12.1, Epics 9 to 11 and 17 to 20 had no preparation story. The reference to the Epic 13 retrospective item stays as history.
4. **Nothing else changes:** no file under `_bmad/` (it already says X.0), no sprint key, no story file.

**Consequences:** The rule, the release tooling and the story template say the same thing.
