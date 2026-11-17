# Sprint Change Proposal: Tooling and Test Health (Epic 20)

**Date:** 2026-11-17
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (batch, non-interactive; scope approved before the workflow ran)
**Scope classification:** Minor
**Status:** Scope approved by Matt before planning. During planning, on 2026-11-17, Matt decided the one-time `ruff format` (first change of the epic, own commit, then the check in `just lint-api`; no Prettier for the web) and the semgrep design; those are written in as decided. Revised the same day with Matt's answers to the ten open questions (section 5): the mod database's address becomes a setting, `VS_MOD_DB_URL`, and CI points it at a plain-HTTP replay (the alternative to the first version's stand-in with a per-run certificate); the three pull-ins are approved; every other default stands. Seven stories, seventeen beads, and the old epic `VSS-029` closes. No question is open.

## 1. Issue Summary

**Trigger:** Epic 19 is done and on `main` (`3f1c6ea`, release `v0.1.0-rc.5`). The maintainer picked fourteen open beads for the next epic, all about the project's own tooling and tests: two from January 2026 that ask for semgrep, six follow-ups filed in Epics 15 to 19 about the checks and recipes, three about the web tests, two about the E2E suite, and one about the release image. The maintainer's backlog rule (2026-11-17) applies: the epic must draw the backlog down, and what planning finds goes into a story, not into a new bead.

**Problem:** The checks the project relies on have gaps and noise. `just check` prints three warnings and four skipped tests on every run, so a new one would not be noticed. It does not check the API's format (and most of the API is not formatted), the E2E specs' types, or one of the scripts. Two recipes mishandle quoted arguments, and every Playwright run dirties the working tree. No static security scan runs at all. CI leaves out 36 of the 149 browser tests. The release image is built from a `latest` tag. And one documented convention contradicts what the last four epics with a preparation story did.

**Evidence** (code at commit `3f1c6ea`; details and line references in `architecture/epic-20-tooling-and-test-health.md`):

- `ruff format --check` on `api/`: 75 of 157 files would be reformatted, about 2,000 changed lines (`line-length = 100`, `api/pyproject.toml:36`). `just lint-api` runs only `ruff check` (`Justfile:145`) (`VSS-3asx`).
- `just typecheck-api`: 0 errors, 3 warnings, at `api/tests/test_mod_service.py:1640` and `:1719` and `api/tests/test_mods_router.py:3099` (`VSS-1ar`; the bead's line numbers are older).
- The web suite: 133 files, 3,353 tests, 4 skipped: `FilterControls.test.tsx:156`, `use-browse-mods.test.tsx:247` and `:253` (empty placeholders), `ModTable.test.tsx:1056` (a real test) (`VSS-hnl`).
- **`VSS-37a` is already fixed.** Its three tests (`ModTable.test.tsx:456`, `:480`, `:506`) were re-enabled by commit `f393c3a` and pass; the bead was never closed.
- Web tests, measured: default pool 15.2 s; `vmThreads` 6.3 s with 111 failures in 4 files, from two causes: `Object.defineProperty(window, 'location', ...)` in three files and `delete global.document` in `cookies.test.ts` (`VSS-6wj`). One of the four files tests `Terminal.tsx`, which nothing else imports (`VSS-eh41`).
- `web/tsconfig.json` includes only `src` and `tests`; the 23 specs, `config-js.ts` and `playwright.config.ts` are never type-checked. Checked by hand: 0 errors today (`VSS-3asx`).
- `scripts/sprint-status.sh`: SC2076 at lines 93, 98, 103, 196 and SC2034 at line 216; `just lint-scripts` leaves the file out (`Justfile:151-153`) (`VSS-1eb`).
- Eighteen recipes interpolate `{{ARGS}}`, so quoted arguments are split again (`Justfile:35`, `:39` and others) (`VSS-6354`).
- `web/playwright-report/index.html` and `web/test-results/.last-run.json` are tracked; `playwright test --list` rewrote the first during this planning (`VSS-uw9z`).
- Semgrep is used nowhere. Trials with semgrep 1.185.0: one finding in the source (`hashlib.md5()` at `services/server.py:650`, a checksum of a vendor download); source-only scan under a minute locally; code scanning has never received an analysis (`VSS-4ac`, `VSS-djg`).
- `ci.yml` has five jobs, each with the release-commit skip `if:`; `scripts/tests/test-release.sh:319-325` pins the job list and each `if:`.
- E2E: 149 tests in 23 files; CI runs the 113 untagged ones; 31 are `@moddb`, 5 are `@game-server` (all in `file-browser-navigation.spec.ts`, which only needs a nested directory), 3 are also `@install`. The API has no endpoint that creates a directory, so "new directory appears on refresh" has no test (`VSS-571h`, `VSS-3mr`). The mod database address is a constant in the API (`services/mod_api.py:348-349`).
- `Dockerfile:51` copies uv from `ghcr.io/astral-sh/uv:latest`; `:9` and `:36` build on tags without digests; `:42` runs `apt-get upgrade` (`VSS-870`).
- `project-context.md:834-847` says preparation stories are never X.0 since Epic 12. Epics 13 to 16 used X.0, and `cliff.toml:43` relies on that (`VSS-as6`).

**Scope decisions (made by the maintainer):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-4ac`, `VSS-djg`, `VSS-37a`, `VSS-hnl`, `VSS-6wj`, `VSS-1ar`, `VSS-3asx`, `VSS-1eb`, `VSS-870`, `VSS-as6`, `VSS-uw9z`, `VSS-571h`, `VSS-6354`, `VSS-3mr`: 14 issues in 7 stories. The old epic `VSS-029` "Web UI Test Coverage" closes when `VSS-3mr` and `VSS-37a` are done |
| Backlog rule | The epic draws the backlog down. Findings go into a story; related open beads are proposed as pull-ins; the net bead change is reported |
| Ruff format (Matt, 2026-11-17) | One dedicated commit reformats the whole API and holds nothing else. It is the first change of the epic, while no branches are open. It goes into `.git-blame-ignore-revs`. Then `ruff format --check` joins `just lint-api`, which CI runs. Prettier for the web is not in scope |
| Pull-ins (Matt, 2026-11-17) | Approved: `VSS-eh41` into 20.2, `VSS-zhv3` into 20.6, `VSS-3q2s` into 20.7. 17 issues in 7 stories |
| Mod database address (Matt, 2026-11-17) | A setting for the mod database's base address, default `https://mods.vintagestory.at`; CI points it at a plain-HTTP replay container that serves trimmed real recordings. `https` is required, and `http` is accepted only with `VS_DEBUG=true`; validated at start-up. Recordings in `web/e2e/fixtures/moddb/`, `just record-moddb`, no scheduled live run, `@moddb-live` and `@install` stay local |
| Other answers (Matt, 2026-11-17) | `just semgrep` is not in `just check`; the new-directory test uses `docker exec` and skips elsewhere; under `vmThreads` the story stops and asks if a file cannot pass, with no per-file pool; digests for uv and both base images, `apt-get upgrade` kept and documented; preparation stories are X.0 |
| Semgrep (Matt, 2026-11-17) | Locally (`just semgrep`) and as a CI job, version pinned. Packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions`, `p/dockerfile`, fetched at run time; not `p/default`, no vendored rules. Pull requests fail only on findings they add (`--baseline-commit`); full scans of `main` report without blocking. SARIF to code scanning; only the semgrep job gets `security-events: write`. Scope `api/src`, `web/src`, `.github`, `Dockerfile`, `scripts`, not test files. The md5 finding is fixed with `usedforsecurity=False`. An inline `# nosemgrep: <rule-id> — <reason>` for a verified false positive is a documented exception to the no-suppressions rule |

**Grouping, and what changed from the suggested starting point:**

| Story | Beads | Why this grouping |
|---|---|---|
| 20.1 The API Is Formatted Once and Stays Formatted | `VSS-3asx` (formatting half) | Its own story and pull request: it is the first change (Matt), and a 2,000-line mechanical commit is reviewed by reproducing it, which only works when nothing else is in the pull request |
| 20.2 A Green, Quiet `just check` | `VSS-1ar`, `VSS-hnl`, `VSS-37a`, `VSS-6wj`, `VSS-eh41` (pulled in) | As suggested: test files and the Vitest configuration. `VSS-eh41` deletes a dead component whose test is one of the four that fail under `vmThreads` |
| 20.3 Lint and Type Checks Cover Everything | `VSS-3asx` (type-check half), `VSS-1eb`, `VSS-6354`, `VSS-uw9z` | As suggested, less the reformat: the `Justfile`, one script, `.gitignore`, a new tsconfig |
| 20.4 Semgrep Locally and in CI | `VSS-djg`, `VSS-4ac` | As suggested |
| 20.5 The File Browser E2E Tests Run in CI | `VSS-3mr`, `VSS-571h` (parts 2 to 4) | The suggested E2E story is split in two. This half is small and certain, and it is what closes `VSS-029` |
| 20.6 The Mod Database E2E Tests Run in CI | `VSS-571h` (part 1), `VSS-zhv3` (pulled in) | The recorded answers are the largest piece of the epic and the only one that changes the product (a new setting); alone, a delay in it holds nothing else back. `VSS-zhv3` documents the fields the recordings hold |
| 20.7 Reproducible Image Inputs and the Numbering Rule | `VSS-870`, `VSS-as6`, `VSS-3q2s` (pulled in) | As suggested. `VSS-3q2s` is documentation, and comes after 20.6 so the environment table can list the new setting |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 19 are done; none is invalidated. One new epic, Epic 20: Tooling and Test Health, with 7 stories. No resequencing.

**Story impact:** No existing story changes. Story 20.6 replaces Epic 19 ADR-14 decision 9 (recording was "a follow-up"), changes what the `@moddb` tag means, and makes the mod database's address a setting where Epic 19 left it a constant; Epic 18's and Epic 19's allow-lists for image hosts and links are not changed by it. Story 20.5 leaves the `@game-server` tag with no test. Story 20.7 corrects the numbering rule that the Epic 13 retrospective item (E13-A2) introduced.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR234-FR259; frontmatter |
| Epics | Add Epic 20; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-20-tooling-and-test-health.md` (facts, ADR-1 to ADR-11); index entry |
| UX spec | None |
| CI | `ruff format --check` through `just lint-api` (20.1); `just typecheck-web` in the `web` job (20.3); a sixth job, `semgrep`, with `security-events: write` (20.4); a browser cache, seeded directories and a replay container in the `e2e` job (20.5, 20.6) |
| Project rules | `project-context.md`: the stubbing pattern and skip patterns (20.2), the `nosemgrep` exception (20.4), the numbering rule (20.7) |
| Deployment and documentation | README and `.env.example` gain the optional `VS_MOD_DB_URL` (20.6); no deployment has to change |
| Beads | Epic `Epic 20: Tooling and Test Health` (`VSS-lzgg`) with the 17 in-scope issues as children; `VSS-37a` and `VSS-3mr` also stay children of `VSS-029` |

**Technical impact:**

- Almost nothing a user of the manager sees changes. There are two product code changes: `hashlib.md5(usedforsecurity=False)` in the download checksum (20.4), which behaves the same, and the optional `VS_MOD_DB_URL` setting (20.6), which changes nothing unless it is set. Story 20.2 also deletes a component nothing uses (`Terminal.tsx`). Story 20.2 may move the building of a WebSocket URL into a small function if the tests need it (ADR-2 decision 2). Story 20.7 changes which uv and base image builds the release image contains.
- Story 20.1 touches 75 API files in one commit. Every open API branch would conflict with it; none is open.
- New tools: semgrep, run through `uvx` at a pinned version (no new project dependency). New CI action uses: a SARIF upload and a cache, both pinned by commit.
- No response or route changes. One new optional setting (table below), which is the epic's only release note; every other commit is `chore`, `test`, `ci`, `build`, `docs` or `refactor`.
- `scripts/tests/test-release.sh` and `scripts/tests/test-docker-context.sh` guard the workflow's shape; Stories 20.4 and 20.7 update them in the same commits as the workflow and the Dockerfile.

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 20.6 | `VS_MOD_DB_URL` (new, optional) | The base address the API uses for mod database requests (`<base>/api`) and mod downloads (`<base>/download`). Default `https://mods.vintagestory.at`. Must be an `https` URL with a host and nothing else; `http` is accepted only with `VS_DEBUG=true`; a bad value stops start-up with an error naming the setting | Added setting |
| 20.6 | Start-up log | New warning `mod_db_url_overridden` when the address is not the default | Added |
| 20.6 | Image host allow-list, link rules, the web UI's links to mod pages | Unchanged; they do not follow the setting | None |
| 20.4 | Download checksum | `hashlib.md5(usedforsecurity=False)`; same result | None |

No response field, route, status code or existing setting changes. Nothing is breaking.

**Draft release-note text:** Features: `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`. Nothing else in the epic produces a release note.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 20 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Seven stories, all tied to existing beads. Effort medium, risk low except Story 20.6 (medium: it adds a setting to the product). |
| 2. Rollback | Not viable. Nothing completed has to be undone. |
| 3. MVP Review | Not needed. |

**Effort:** Medium. Four issues are size-m in beads (`VSS-4ac`, `VSS-6wj`, `VSS-571h`, `VSS-3mr`) and thirteen are size-s. Story 20.6 is the largest; Stories 20.1 and 20.7 are the smallest.

**Risks:**

- Story 20.1: the format commit conflicts with any API branch cut before it. It merges first, with nothing else open.
- Story 20.1: `.git-blame-ignore-revs` holds a hash, which a squash or a rebase would change. The project merges with merge commits; the story says so in the pull request.
- Story 20.2: a test rewritten to stub differently can stop testing what it tested. The story changes how the stub is set, not the assertions, and runs the files under both pools.
- Story 20.2: `vmThreads` behaves differently from forks for some native modules and can leak memory on long runs. Neither showed in planning's run.
- Story 20.3: changing how eighteen recipes pass arguments can break a recipe nobody tried. The story runs each recipe's documented examples.
- Story 20.4: the packs are fetched at run time, so a scan needs the network and the rules move. The pull request gate compares against the merge base with the same rules, so a moved rule cannot fail an unrelated pull request; `main`'s full scan does not block.
- Story 20.4: semgrep is pinned by version, not by digest, and installs its own dependencies at run time.
- Story 20.4: alerts in code scanning help only if someone reads them.
- Story 20.5: the new-directory test reaches into the container with `docker exec`, which ties one spec to the throwaway stack. It skips elsewhere, and a script test keeps CI from skipping it.
- Story 20.6: the new setting lets an operator send the API, and its mod downloads, to another host. The guard (`https` only, `http` only in debug mode, checked at start-up), the start-up warning and the unchanged browser-side allow-lists limit what a wrong value can do; the README says what the setting is for.
- Story 20.6: a mod database request that still used a constant would call the live service from CI. The live hosts stay blocked in both CI containers, so such a call fails the run at once.
- Story 20.6: the second pass runs its API container in debug mode. The first pass stays in production mode, so CI still tests the image as it runs in production.
- Story 20.6: six tasks, the project's limit; `create-story` should not add to them.
- Story 20.6: recordings go stale without anyone noticing until a live run fails. The manifest dates them and the refresh prints shape changes.
- Story 20.6: the recordings put public mod metadata (names, descriptions, authors) into the repository.
- Story 20.7: digest pins mean more Renovate pull requests (base image rebuilds). Each is built and tested by CI.
- Story 20.7: the image is repeatable in its named inputs, not bit for bit; `apt-get upgrade` stays.
- Stories 20.3 to 20.6 all edit the `Justfile`, and 20.4 to 20.6 all edit `ci.yml`; in parallel they would conflict.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR234-FR259 for Epic 20 (Tooling and Test Health)".

**New section after "Epic 19: API Security and Mod File Safety":**

```markdown
### Epic 20: Tooling and Test Health

#### Formatting

- FR234: Every Python file of the API is in `ruff format`'s form; the reformat is one commit that holds nothing else
- FR235: `just lint-api`, and through it CI and `just check`, fails when an API file is not formatted
- FR236: The reformat commit is listed in `.git-blame-ignore-revs`, so `git blame` skips it on GitHub and in a set-up worktree

#### A Quiet Check

- FR237: `just typecheck-api` reports 0 errors and 0 warnings, with no ignore comment and no lowered rule
- FR238: The web test suite reports 0 skipped tests; empty placeholders are gone and the remove-button loading state is tested
- FR239: The web tests run in Vitest's `vmThreads` pool and pass there locally and in CI

#### Lint and Type Check Coverage

- FR240: `just typecheck` and CI type-check the E2E specs and the Playwright configuration; the web build does not depend on them
- FR241: `just lint-scripts` checks every script, `scripts/sprint-status.sh` included, and that script passes ShellCheck with no directive
- FR242: Every `just` recipe that passes arguments on hands each argument to the tool as it was quoted, so `just test-api -k "a or b"` works
- FR243: Playwright's report and result files are not tracked and are ignored, so a local E2E run leaves the working tree clean

#### Static Analysis

- FR244: `just semgrep` runs a pinned semgrep with the packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile` over the source (`api/src`, `web/src`, `.github`, `Dockerfile`, `scripts`), not over test files, with metrics off
- FR245: In CI a pull request fails only on semgrep findings it adds; a full scan of `main` reports every finding and does not fail because of them
- FR246: The full scan's results are uploaded to GitHub code scanning as SARIF by a job that alone has `security-events: write`, with pinned actions and the release-commit skip
- FR247: The source has no open semgrep finding; a verified false positive may be marked with an inline `nosemgrep` comment that names one rule and gives a reason, as a documented exception to the no-suppressions rule

#### E2E Coverage in CI

- FR248: CI's E2E stack is seeded with a nested directory, and the file browser navigation tests run in CI
- FR249: An E2E test shows that a directory created while the file manager is open is listed after the page is loaded again
- FR250: CI's E2E job restores the Playwright browsers from a cache keyed by the Playwright versions
- FR251: The connection reset seen in the E2E server-status stub has a recorded cause or a record of what was tried, and its retry is explained or removed
- FR252: CI runs the E2E tests that need mod database answers against recorded answers, served by a replay that the API reaches through `VS_MOD_DB_URL`, with no request to the live service
- FR253: The recorded answers are files in the repository with a manifest of what was recorded and when, and one command refreshes them from the live mod database and reports changes in shape
- FR254: Tests that must compare with the live mod database or install a real mod are tagged and stay local-only; every spec still runs against the live service on a developer's machine

#### Image and Conventions

- FR255: Every image the Dockerfile builds from or copies from is pinned by digest, the uv version equals the one in `.mise.toml`, and a script test enforces both
- FR256: Renovate proposes updates for the pinned image digests and moves uv in the Dockerfile and in `.mise.toml` together
- FR257: The story numbering rule in `project-context.md` matches the practice: a preparation story is X.0, and an epic without one starts at X.1

#### The Mod Database's Address (Matt, 2026-11-17)

- FR258: `VS_MOD_DB_URL` sets the base address the API uses for mod database requests and mod downloads; it defaults to `https://mods.vintagestory.at`, and the image host allow-list, the link rules and the links the web UI builds do not follow it
- FR259: The address is validated at start-up: it must be an `https` URL with a host and nothing else, `http` is accepted only when `VS_DEBUG=true`, anything else stops start-up with an error that names the setting, and an address other than the default is logged as a warning
```

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** update entry "Added Epic 20 (7 stories) for Tooling and Test Health; FR234-FR259".

**FR Coverage Map:** rows FR234 to FR259 appended after FR233, each mapped to Epic 20.

**Story Summary:**

OLD:

```markdown
| **Total** | | **113** |
```

NEW:

```markdown
| Epic 20: Tooling and Test Health | 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7 | 7 |
| **Total** | | **120** |
```

### 4.3 Epic 20 Stories (appended to `epics.md`)

## Epic 20: Tooling and Test Health

**Goal:** `just check` is green and quiet, and what it checks is everything: the API's format, the E2E specs' types and every script. A static security scan runs on every pull request. CI runs the browser tests for the file browser and the mod database, not only the ones that need nothing. The release image is built from pinned inputs. Seventeen open beads and one old epic are closed.

**Architecture:** `architecture/epic-20-tooling-and-test-health.md` (ADR-1 to ADR-11, with the facts checked at `3f1c6ea`). There is no preparation story. Story 20.6 adds its setting and proves the path to the replay in its first two tasks before it records anything (ADR-9 decision 7).

**Decided by the maintainer (Matt, 2026-11-17):** the one-time `ruff format` of the API as the first change of the epic, with the check in `just lint-api` (ADR-1); Prettier for the web is not in scope; the semgrep design: pinned version, six registry packs, pull requests fail only on findings they add, full scans of `main` report without blocking, SARIF to code scanning, source only, and the inline `nosemgrep` exception for a verified false positive (ADR-6, ADR-7). The same day he answered the proposal's open questions: the mod database's address becomes a setting, `VS_MOD_DB_URL`, and CI points it at a plain-HTTP replay of recorded answers (ADR-9, the alternative to the first draft); the recordings are trimmed real answers; the three pull-ins are approved; and every other default stands (`just semgrep` outside `just check`, no scheduled live run, the `@moddb-live` tag, the `docker exec` new-directory test, stop and ask under `vmThreads`, digests for all three images with `apt-get upgrade` kept, X.0 for preparation stories).

**Order:** 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7.

**Dependencies:**

- Story 20.1 comes first and merges before any other branch of the epic is cut: it rewrites 75 API files, and every later API change (the fixtures in 20.2, the hash call in 20.4) is made on formatted code.
- Story 20.2 needs no other story's code. It comes second so that every later story starts from a `just check` with no warning and no skip.
- Story 20.3 comes before 20.4, 20.5 and 20.6: they add recipes to the `Justfile` and edit E2E specs, and from 20.3 on recipes pass arguments intact, specs are type-checked and a local E2E run leaves the tree clean.
- Story 20.4 comes after 20.1 (it edits `services/server.py`) and after 20.3 (its script is covered by the widened `just lint-scripts`). It adds a sixth job to `ci.yml` and updates the guard in `scripts/tests/test-release.sh`.
- Story 20.6 comes directly after 20.5: both edit `scripts/e2e-ci.sh`, its test, the `e2e` job and `web/e2e/README.md`.
- Story 20.7 needs no other story's code. It comes last because a digest change empties the image build cache that the `docker` and `e2e` jobs share, which would blur the timings Stories 20.5 and 20.6 record.
- Stories 20.3, 20.4, 20.5 and 20.6 all edit the `Justfile`, and 20.4, 20.5 and 20.6 all edit `ci.yml`; run them one after another.

**Beads:** seventeen in scope (the fourteen the maintainer picked and three pull-ins he approved on 2026-11-17: `VSS-eh41` in 20.2, `VSS-zhv3` in 20.6, `VSS-3q2s` in 20.7), each closed with an AAR by its story. `VSS-3asx` spans Stories 20.1 and 20.3 and closes with 20.3. `VSS-571h` spans Stories 20.5 and 20.6 and closes with 20.6. `VSS-37a` is already fixed in the code and is verified and closed in 20.2. The old epic `VSS-029` "Web UI Test Coverage" (16 of 18 done) closes in Story 20.5, when its last two children (`VSS-37a`, `VSS-3mr`) are closed.

**One product change:** Story 20.6 adds the optional setting `VS_MOD_DB_URL` (ADR-9). It is the only change of the epic that an operator can see, and its commit is a `feat(api)` with a release note.

### Current State

- 75 of the API's 157 Python files are not in `ruff format`'s form, and nothing checks the format
- `just check` prints three Pyright warnings and four skipped web tests on every run; the web tests spend 43% of their time creating jsdom environments
- `VSS-37a` is open although its three tests were re-enabled and pass
- The 23 E2E specs are never type-checked; `scripts/sprint-status.sh` is left out of ShellCheck; `just test-api -k "a or b"` fails; every Playwright run rewrites two tracked files
- No static security scan runs anywhere, and code scanning has never received a result
- CI leaves out 36 of 149 E2E tests: 31 that read the live mod database and 5 file browser tests that need a nested directory. "A new directory appears on refresh" has no test. A connection reset seen once in the E2E helper is retried and unexplained
- The Dockerfile copies uv from a `latest` tag and builds on two tags without digests
- `project-context.md` says preparation stories are never numbered X.0; the four epics after Epic 12 that had one numbered it X.0

### Target State

- The API is formatted, the format commit is skipped by `git blame`, and `just lint-api` and CI fail on an unformatted file
- `just check` ends with 0 Pyright warnings and 0 skipped tests, and the web tests run in the `vmThreads` pool
- `just typecheck` covers the E2E specs, `just lint-scripts` covers every script, recipes pass quoted arguments intact, and a Playwright run leaves the tree clean
- `just semgrep` and a CI job scan the source with a pinned semgrep; a pull request fails only on a finding it adds, and `main`'s findings are in code scanning
- CI runs the file browser tests on a seeded directory tree, a test for a directory created while the page is open, and the mod database tests against recorded answers, which the API reaches through the new `VS_MOD_DB_URL` setting
- Every image the Dockerfile uses is pinned by digest and Renovate moves the pins
- The story numbering rule says what the project does

---

### Story 20.1: The API Is Formatted Once and Stays Formatted

**Sprint key:** `20-1-api-formatted-once`
**Beads:** `VSS-3asx` (TOOLS-006), the formatting half; the bead stays open until Story 20.3
**FRs:** FR234, FR235, FR236

As a **developer**,
I want **the whole API in the formatter's form and a check that keeps it there**,
So that **formatting a file I work on never adds changes that are not mine**.

**Acceptance Criteria:**

**Given** the API source and tests
**When** `ruff format --check` runs over `api/`
**Then** it reports no file that would be reformatted

*(Covers FR234)*

**Given** the format commit
**When** I read it
**Then** it holds only what `ruff format` wrote with the existing configuration (`line-length = 100`): no hand edit, no lint fix, no configuration change, and its subject is `chore(story-20.1/task-1): format the API with ruff format`

*(Covers FR234; Matt, 2026-11-17)*

**Given** the format commit's parent
**When** a reviewer runs the same `ruff format` on it
**Then** the resulting tree is identical to the format commit's tree

*(Covers FR234)*

**Given** the API tests, `ruff check` and Pyright
**When** they run before and after the format commit
**Then** the results are the same: the same tests pass, no new lint finding, no new type error or warning, and no `# noqa` or `# fmt:` comment was added

*(Covers FR234)*

**Given** `just lint-api`
**When** it runs
**Then** it runs `ruff check` and then `ruff format --check`, and it fails when any API file is not formatted

*(Covers FR235)*

**Given** a pull request that contains an unformatted API file
**When** CI runs
**Then** the `api` job fails at `just lint-api`, with no change to the workflow file

*(Covers FR235)*

**Given** the repository root
**When** I read `.git-blame-ignore-revs`
**Then** it names the format commit's full hash with a comment line, and it was added in a separate commit of the same pull request

*(Covers FR236)*

**Given** a fresh worktree set up with `scripts/worktree-setup.sh`
**When** I run `git blame` on a reformatted API file
**Then** the format commit is skipped, and the README says which git setting does that

*(Covers FR236)*

**Given** the epic's branches
**When** Story 20.1's pull request merges
**Then** it is merged with a merge commit like every other, no other branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main`

*(Covers FR236; Matt, 2026-11-17)*

**Tasks:**

- [ ] Run `ruff format` over `api/` and commit the result alone; record the file and line counts and that the tests, `ruff check` and Pyright give the same results as before (Epic 20 ADR-1 decisions 1, 2 and 6) (`VSS-3asx`)
- [ ] `.git-blame-ignore-revs` with the commit's hash; `blame.ignoreRevsFile` in `scripts/worktree-setup.sh`; a line in the README (ADR-1 decision 4)
- [ ] `ruff format --check` in `just lint-api`; update the recipe comment and the command lists in `CLAUDE.md` and `project-context.md` (ADR-1 decision 5)

---

### Story 20.2: A Green, Quiet `just check`

**Sprint key:** `20-2-green-quiet-check`
**Beads:** `VSS-1ar` (TEST-003), `VSS-hnl` (TEST-004), `VSS-37a` (bug), `VSS-6wj` (TEST-005), `VSS-eh41` (UI-098; pulled in, Matt, 2026-11-17)
**FRs:** FR237, FR238, FR239

As a **developer**,
I want **`just check` to end with no warning and no skipped test, and the web tests to run faster**,
So that **a new warning or skip is seen the day it appears, and the check is quick enough to run every time**.

**Acceptance Criteria:**

**Given** `just typecheck-api`
**When** it runs
**Then** it prints `0 errors, 0 warnings`, the three fixtures (`test_mod_service.py` `mod_without_releases` and `mod_without_tags`, `test_mods_router.py` `mods_without_tags`) have a type annotation, no `# pyright: ignore` or `# type: ignore` was added, and no rule level in `pyproject.toml` changed

*(Covers FR237)*

**Given** the three empty placeholder tests (`FilterControls.test.tsx:156`, `use-browse-mods.test.tsx:247` and `:253`)
**When** the story is done
**Then** they are gone, and selecting a game version in the filter controls and filtering the browse list by game version each have a test with assertions, written here if none existed

*(Covers FR238)*

**Given** `ModTable.test.tsx` "shows loading state in remove button when removing"
**When** the web tests run
**Then** it runs and passes without `act` around the click, or the state is covered by a Playwright test and the unit test is deleted, and the story says which and why

*(Covers FR238)*

**Given** `just test-web`
**When** it runs
**Then** it reports 0 skipped tests

*(Covers FR238)*

**Given** `VSS-37a`'s three tests ("shows confirmation dialog when remove button is clicked", "closes dialog when cancel is clicked", "removes mod when confirm is clicked")
**When** the web tests run
**Then** all three run and pass, and the bead is closed with an AAR that names commit `f393c3a`, which re-enabled them

*(Covers FR238)*

**Given** `web/vitest.config.ts`
**When** I read it
**Then** it sets `pool: 'vmThreads'`, does not set `isolate: false`, and no test file is moved to another pool; if a file cannot be made to pass, the story stops and asks the maintainer

*(Covers FR239; Matt, 2026-11-17)*

**Given** the three files that failed under `vmThreads` and remain (`use-log-stream.test.ts`, `use-console-websocket.test.ts`, `cookies.test.ts`; the fourth, `Terminal.test.tsx`, is deleted with its dead component)
**When** the web tests run under `vmThreads` and under the forks pool
**Then** every test passes under both, no test redefines `window.location` with `Object.defineProperty` or deletes `global.document`, and the tests assert what they asserted before

*(Covers FR239)*

**Given** the web suite before and after the story
**When** I compare the test counts
**Then** the only tests that are gone are the ones this story deleted on purpose, and the story lists them

*(Covers FR239)*

**Given** CI's `web` job
**When** it runs on the story's pull request
**Then** `just test-web` passes, and the story records its time before (60 s) and after

*(Covers FR239)*

**Given** `project-context.md`
**When** I read its testing rules
**Then** it says how to stub a browser global so that the test passes under `vmThreads`, and its forbidden-pattern list names `it.skip` and `describe.skip`

*(Covers FR238, FR239)*

**Given** the pull-in `VSS-eh41`
**When** the story is done
**Then** `web/src/features/terminal/Terminal.tsx`, its test and the unused `checkVersionCompatibility` are removed, nothing imports them, the E2E spec `terminal.spec.ts` (which tests the Console page, not this component) still passes, and the bead is closed with an AAR

*(Covers FR239; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] Annotate the three fixtures; `just typecheck-api` at 0 warnings (Epic 20 ADR-3 decision 3) (`VSS-1ar`)
- [ ] Delete the three placeholders after checking the game version filter's tests, writing the missing ones; rewrite the remove-button loading test (ADR-3 decisions 1 and 2) (`VSS-hnl`)
- [ ] Run and record `VSS-37a`'s three tests; close the bead with its AAR (ADR-3 decision 4) (`VSS-37a`)
- [ ] Pull-in (Matt, 2026-11-17): remove `Terminal.tsx`, `Terminal.test.tsx` and `checkVersionCompatibility`; list the deleted tests (ADR-2 decision 3) (`VSS-eh41`)
- [ ] Read every failure under `vmThreads`; change the stubs in the three remaining files so they pass under both pools (ADR-2 decision 2) (`VSS-6wj`)
- [ ] `pool: 'vmThreads'` in `web/vitest.config.ts`; local and CI times; the stubbing pattern and the skip patterns in `project-context.md` (ADR-2 decisions 1 and 6, ADR-3 decision 5) (`VSS-6wj`)

---

### Story 20.3: Lint and Type Checks Cover Everything

**Sprint key:** `20-3-lint-and-typecheck-coverage`
**Beads:** `VSS-3asx` (TOOLS-006), the type-check half, closed here; `VSS-1eb` (TOOLS-004); `VSS-6354` (TOOLS-009); `VSS-uw9z` (TOOLS-008)
**FRs:** FR240, FR241, FR242, FR243

As a **developer**,
I want **the checks to cover the E2E specs and every script, and the recipes to do what I type**,
So that **a mistake in a spec or a script is caught by `just check`, and running the tools leaves no mess**.

**Acceptance Criteria:**

**Given** `web/e2e/tsconfig.json`
**When** I read it
**Then** it extends the web configuration, sees Node's types and not Vitest's or Vite's, and includes the E2E directory and `playwright.config.ts`

*(Covers FR240)*

**Given** a type error in an E2E spec or in `playwright.config.ts`
**When** `just typecheck-web`, `just typecheck` or `just check` runs
**Then** it fails and names the file

*(Covers FR240)*

**Given** CI's `web` job
**When** it runs
**Then** it runs `just typecheck-web`, and `bun run build` is unchanged, so a spec's type error cannot stop the image build

*(Covers FR240)*

**Given** the E2E specs today
**When** the new check runs
**Then** it passes with no `@ts-expect-error` or `@ts-ignore` added

*(Covers FR240)*

**Given** `scripts/sprint-status.sh`
**When** ShellCheck runs on it
**Then** it reports nothing, the file contains no `shellcheck disable` directive, and every command behaves as before

*(Covers FR241)*

**Given** the status checks that were rewritten
**When** `just test-scripts` runs
**Then** tests cover a valid and an invalid status for a story, an epic, a retrospective and a retro item

*(Covers FR241)*

**Given** `just lint-scripts`
**When** it runs
**Then** it checks every `.sh` file in `scripts/` and `scripts/tests/` through globs, so a new script is covered without editing the recipe

*(Covers FR241)*

**Given** `just test-api -k "a or b"`
**When** it runs
**Then** pytest receives `a or b` as one expression and selects the tests that match either

*(Covers FR242)*

**Given** every recipe that passes arguments on to a tool
**When** I call it with an argument that contains spaces
**Then** the tool receives it as one argument; a script test proves it without running the tool, and it holds for `just sprint retro-add <key> "a comment"`

*(Covers FR242)*

**Given** the recipes' existing uses (`just test-api tests/test_server.py -xvs`, `just docker logs`, `just release --dry-run`, `just dev-api --port 8001`)
**When** I run them
**Then** they behave as before

*(Covers FR242)*

**Given** the repository
**When** I run `git ls-files web/playwright-report web/test-results`
**Then** it prints nothing, and both directories are in `.gitignore` and `.dockerignore`

*(Covers FR243)*

**Given** a clean working tree
**When** I run Playwright (`--list`, a passing run, or a failing run)
**Then** `git status` is still clean

*(Covers FR243)*

**Given** a failed `e2e` job in CI
**When** I open the run
**Then** the Playwright report is still attached as an artifact

*(Covers FR243)*

**Tasks:**

- [ ] `web/e2e/tsconfig.json`; the `typecheck` script checks both projects; `just typecheck-web` in CI's `web` job; fix whatever the check finds in the specs (Epic 20 ADR-4) (`VSS-3asx`)
- [ ] Positional arguments in every recipe that forwards `*ARGS`; the script test; update the examples in the `Justfile` header and `CLAUDE.md` (ADR-5 decisions 1 and 2) (`VSS-6354`)
- [ ] Make `sprint-status.sh` ShellCheck-clean with `case` statements and no directive; tests for the rewritten checks (ADR-5 decision 3) (`VSS-1eb`)
- [ ] `just lint-scripts` over globs; remove the `VSS-1eb` comment (ADR-5 decision 4) (`VSS-1eb`)
- [ ] Untrack the two Playwright files; `.gitignore` and `.dockerignore`; remove the "restore the report files" notes from `web/e2e/README.md` and the agent documentation if any mention them (ADR-5 decision 5) (`VSS-uw9z`)

---

### Story 20.4: Semgrep Locally and in CI

**Sprint key:** `20-4-semgrep`
**Beads:** `VSS-djg` (TOOLS-002), `VSS-4ac` (CICD-001)
**FRs:** FR244, FR245, FR246, FR247

As a **maintainer**,
I want **a static security scan on every pull request and one command to run it myself**,
So that **a risky pattern is caught when it is written, without old findings or noisy rules blocking unrelated work**.

**Acceptance Criteria:**

**Given** `just semgrep`
**When** it runs
**Then** it runs semgrep at one pinned version through `uvx`, with `--metrics=off`, the packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile`, over `api/src`, `web/src`, `.github`, `Dockerfile` and `scripts`, and exits non-zero on a finding

*(Covers FR244; Matt, 2026-11-17)*

**Given** the scan's scope
**When** I list the files semgrep scanned
**Then** no test file is among them (`*.test.ts`, `*.test.tsx`, `scripts/tests/`), the exclusions are in one `.semgrepignore`, and no rule file is stored in the repository

*(Covers FR244; Matt, 2026-11-17)*

**Given** the semgrep version
**When** I look for it
**Then** it is written in one place, CI and the recipe both read it from there, Renovate has a rule that updates it, and a script test checks that the line has the form that rule matches

*(Covers FR244)*

**Given** `just semgrep --baseline-commit origin/main`
**When** it runs on a branch
**Then** the arguments reach semgrep and only findings the branch adds are reported

*(Covers FR244)*

**Given** `just lint`, `just check`, `just test-api` and `just test-web`
**When** they run
**Then** none of them runs semgrep

*(Covers FR244; Matt, 2026-11-17)*

**Given** a pull request that adds a line a chosen rule matches
**When** CI runs
**Then** the `semgrep` job fails and its log names the rule, the file and the line

*(Covers FR245; Matt, 2026-11-17)*

**Given** a pull request that adds no finding, while `main` has findings or the registry has new rules
**When** CI runs
**Then** the `semgrep` job passes

*(Covers FR245; Matt, 2026-11-17)*

**Given** a push to `main` or a manual run
**When** the `semgrep` job runs
**Then** it scans the whole scope, uploads the results to GitHub code scanning as SARIF, and does not fail because of findings

*(Covers FR245, FR246; Matt, 2026-11-17)*

**Given** `ci.yml`
**When** I read it
**Then** only the `semgrep` job has `security-events: write`, the workflow's default permission is still `contents: read`, every action is pinned by commit, and the job has the same release-commit skip `if:` as the others

*(Covers FR246; Matt, 2026-11-17)*

**Given** `just test-scripts`
**When** it runs
**Then** `test-release.sh` expects the six jobs `api docker e2e scripts semgrep web`, checks the skip `if:` on each, and passes; `just lint-workflows` passes

*(Covers FR246)*

**Given** `api/src/vintagestory_api/services/server.py`
**When** semgrep runs with `p/python`
**Then** the checksum code uses `hashlib.md5(usedforsecurity=False)`, the rule `insecure-hash-algorithm-md5` no longer matches, the scope has no finding, and no `nosemgrep` comment was added for it

*(Covers FR247; Matt, 2026-11-17)*

**Given** `project-context.md`'s "No Silent Failures Rule"
**When** I read it
**Then** it states the one exception: `# nosemgrep: <rule-id> — <reason>` naming one rule, only for a verified false positive, each one checked in review, a bare `nosemgrep` never, and changing the code preferred where that states the intent better

*(Covers FR247; Matt, 2026-11-17)*

**Given** the CI job on the runner
**When** it runs
**Then** it finishes within five minutes, and the story records its time and, per pack, how many rules the engine could not run

*(Covers FR245)*

**Tasks:**

- [ ] `scripts/semgrep.sh` (version, packs, paths, `--metrics=off`, arguments passed through), `.semgrepignore`, and the `just semgrep` recipe; record the scanned file count, findings, rule errors and time (Epic 20 ADR-6 decisions 1, 2, 4, 5, 6 and 7) (`VSS-djg`)
- [ ] The Renovate rule for the version and the script test that pins the line's form (ADR-6 decision 3) (`VSS-djg`)
- [ ] `hashlib.md5(usedforsecurity=False)` in `services/server.py`; confirm the rule stops matching; the existing checksum tests still pass (ADR-7 decision 7) (`VSS-4ac`)
- [ ] The `semgrep` job in `ci.yml`: baseline scan on pull requests, full scan and SARIF upload on `main`, job-level permissions, the skip `if:`; update `test-release.sh` to six jobs (ADR-7 decisions 1 to 4) (`VSS-4ac`)
- [ ] The `nosemgrep` exception in `project-context.md`; `just semgrep` in `CLAUDE.md` and the README's development section; a note in the story of how a finding is triaged (ADR-7 decisions 5, 6 and 8) (`VSS-4ac`)
- [ ] Prove the gate on the story's own pull request: a temporary commit that adds a matching line fails the job, and removing it passes; record both runs

---

### Story 20.5: The File Browser E2E Tests Run in CI

**Sprint key:** `20-5-file-browser-e2e-in-ci`
**Beads:** `VSS-3mr` (UI-030); `VSS-571h` (TEST-006), parts 2, 3 and 4, the bead stays open until Story 20.6. Closes the old epic `VSS-029`
**FRs:** FR248, FR249, FR250, FR251

As a **maintainer**,
I want **the file browser's browser tests to run on every pull request, including a directory that appears while I watch**,
So that **the file browser is covered in CI and the old test-coverage epic can close**.

**Acceptance Criteria:**

**Given** `just test-e2e-ci`
**When** it starts the throwaway container
**Then** the container's `serverdata` holds a directory inside another directory with made-up names, owned by the manager's user, beside the seeded `serverconfig.json`

*(Covers FR248)*

**Given** `file-browser-navigation.spec.ts`
**When** CI runs
**Then** its five tests run and pass, the spec carries no `@game-server` tag, and it still creates, changes and deletes nothing

*(Covers FR248)*

**Given** the same spec on the dev stack with a game server
**When** `just test-e2e-web` runs
**Then** it passes as before

*(Covers FR248)*

**Given** the file manager open on a directory in the throwaway stack
**When** a new directory is created in that directory from outside the page and the page is loaded again
**Then** the new directory is in the list and can be opened

*(Covers FR249)*

**Given** that test on a stack that is not the throwaway container
**When** it runs
**Then** it skips with a message that says why and changes nothing in that stack's data; `scripts/tests/test-e2e-ci.sh` checks that the CI script gives the test what it needs, so CI cannot skip it

*(Covers FR249; Matt, 2026-11-17)*

**Given** `VSS-3mr` and `VSS-37a` closed
**When** the story is done
**Then** the old epic `VSS-029` "Web UI Test Coverage" has no open child and is closed with an AAR that names Stories 16.7, 20.2 and 20.5

*(Covers FR249)*

**Given** the `e2e` job
**When** it runs a second time with the same Playwright versions
**Then** it restores the browsers from a cache and does not download them, the cache action is pinned by commit, and the key changes only when a Playwright version or the runner's system changes

*(Covers FR250)*

**Given** the cache
**When** the story measures the job
**Then** it records the browser step's time before (43 s) and after, and the cache is removed again if it saves nothing

*(Covers FR250)*

**Given** the connection reset in the server-status stub
**When** the investigation is done
**Then** the comment in `web/e2e/config-js.ts` states the cause if it was reproduced, or what was tried if it was not, and the single retry either stays with that reason or is removed because the cause is gone

*(Covers FR251)*

**Given** `web/e2e/README.md`
**When** I read it
**Then** it lists the seeded directories, says what the new test needs, and says that no test carries `@game-server` now and when the tag is still the right one

*(Covers FR248, FR249)*

**Tasks:**

- [ ] Seed the nested directory in `scripts/e2e-ci.sh`; pin it in `scripts/tests/test-e2e-ci.sh` (Epic 20 ADR-8 decision 1) (`VSS-571h`)
- [ ] Run `file-browser-navigation.spec.ts` on the seeded stack and remove its tag; check it on the dev stack (ADR-8 decision 2) (`VSS-571h`)
- [ ] The "new directory appears after a reload" test and what the script exports for it (ADR-8 decision 3) (`VSS-3mr`)
- [ ] Cache the Playwright browsers in the `e2e` job; times before and after (ADR-8 decision 5) (`VSS-571h`)
- [ ] The time-boxed investigation of the connection reset; the comment and the retry (ADR-8 decision 6) (`VSS-571h`)
- [ ] `web/e2e/README.md`; close `VSS-3mr` and then `VSS-029`, each with an AAR (ADR-8 decision 4)

---

### Story 20.6: The Mod Database E2E Tests Run in CI

**Sprint key:** `20-6-mod-database-tests-in-ci`
**Beads:** `VSS-571h` (TEST-006), part 1, closed here; `VSS-zhv3` (DOCS-001; pulled in, Matt, 2026-11-17)
**FRs:** FR252, FR253, FR254, FR258, FR259

As a **maintainer**,
I want **the tests that read the mod database to run in CI against recorded answers**,
So that **the mod pages are covered on every pull request, the same way every time, without calling the live service**.

**Acceptance Criteria:**

**Given** a deployment that does not set `VS_MOD_DB_URL`
**When** the API starts and talks to the mod database
**Then** it uses `https://mods.vintagestory.at` for its API calls and downloads exactly as before, and logs no warning about the address

*(Covers FR258; Matt, 2026-11-17)*

**Given** `VS_MOD_DB_URL` set to another `https` address
**When** the API lists mods, looks a mod up, reads the game version list or downloads a mod file
**Then** each request goes to that address (`<base>/api/...`, `<base>/download`), and the start-up log has one warning that names the scheme and host

*(Covers FR258, FR259)*

**Given** `VS_MOD_DB_URL` set to another address
**When** the API passes on a mod's logo, screenshots, homepage and source links, and the web UI builds a link to a mod's page
**Then** the image host allow-list and the link rules are the same as without the setting (only `moddbcdn.vintagestory.at` images, `https` links), and the web UI's links still point at `mods.vintagestory.at`

*(Covers FR258)*

**Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG` unset or false
**When** the API starts
**Then** start-up stops with an error that names `VS_MOD_DB_URL` and says plain HTTP is for testing and needs `VS_DEBUG=true`

*(Covers FR259; Matt, 2026-11-17)*

**Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG=true`
**When** the API starts
**Then** it starts, uses the address, and logs the warning

*(Covers FR259; Matt, 2026-11-17)*

**Given** a value that is not an absolute URL, has another scheme, has no host, or carries a user name, a password, a path, a query or a fragment
**When** the API starts
**Then** start-up stops with an error that names the setting and what is wrong; a single trailing `/` is accepted and ignored

*(Covers FR259)*

**Given** the README, `.env.example` and the release notes
**When** I read them
**Then** the setting is documented as optional, with its default, what it is for (a mirror of the same database, or tests), the `http` rule, and that mods are downloaded from that address; and the commit that adds it has the subject `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`

*(Covers FR258)*

**Given** the built image with the setting pointed at a stub, before anything is recorded
**When** the second task is done
**Then** the story has shown that the listing, the mod lookup, the game version list and the download reach the stub, that no request goes to the live host (which stays blocked in the container), and that a request the stub has no answer for is reported with its URL

*(Covers FR252)*

**Given** `just test-e2e-ci`
**When** it runs
**Then** its first pass is as before (the untagged tests against a container in production mode), and a second pass starts a replay container and a second API container with `VS_DEBUG=true` and `VS_MOD_DB_URL` set to the replay, runs the `@moddb` tests that are not `@moddb-live` or `@install` against it, and removes everything it started, also after a failure

*(Covers FR252)*

**Given** the CI run
**When** I look at where its requests go
**Then** neither API container nor the browser sends a request to the live mod database or its image host; the browser's image requests are answered by a placeholder

*(Covers FR252)*

**Given** two CI runs of the same commit
**When** I compare the `@moddb` tests' results
**Then** they are the same

*(Covers FR252)*

**Given** `web/e2e/fixtures/moddb/`
**When** I read it
**Then** it holds one file per recorded request and a manifest that gives each request, its recording date, how it was trimmed and which spec needs it; the answers are real ones, trimmed, with their image and link URLs unchanged, and nothing but what the mod database's public API returned

*(Covers FR253; Matt, 2026-11-17)*

**Given** `just record-moddb`
**When** I run it with network access
**Then** it fetches the manifest's requests from the live mod database, rewrites the recordings with the same trimming, and prints which fields appeared or disappeared since the last recording

*(Covers FR253)*

**Given** the 31 `@moddb` tests
**When** the story has run each against the recordings
**Then** each one either runs in CI, or carries `@moddb-live` (it compares with live data) or `@install` (it installs a real mod) with a one-line reason, and the story lists how many tests are in each group

*(Covers FR254; Matt, 2026-11-17)*

**Given** `just test-e2e-web` on a developer's machine
**When** it runs
**Then** every spec still runs against the live mod database, with no recordings and no setting involved, and no workflow runs them against the live service on a schedule

*(Covers FR254; Matt, 2026-11-17)*

**Given** `web/e2e/README.md`
**When** I read it
**Then** it explains the tags as they now are, the two passes, how the replay works, how and when to refresh the recordings, and which tests remain live-only

*(Covers FR253, FR254)*

**Given** the `e2e` job
**When** the story is done
**Then** it still finishes within its 30 minute limit, and the story records its time before (3 min 16 s) and after

*(Covers FR252)*

**Given** the pull-in `VSS-zhv3`
**When** the story is done
**Then** `agentdocs/vintagestory-modapi.md` documents the fields and filters the bead lists, checked against the recordings, and the bead is closed with an AAR

*(Covers FR253; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] The `VS_MOD_DB_URL` setting: validation at start-up, the warning, `ModApiClient` building both addresses from it, tests for every accepted and refused form and for the fixed allow-lists; README and `.env.example`; its own `feat(api)` commit (Epic 20 ADR-9 decisions 1 to 5) (`VSS-571h`)
- [ ] Prove the path in the built image against a stub: every mod database request and the download follow the setting, nothing reaches the live host, a missing answer names its URL (ADR-9 decision 7) (`VSS-571h`)
- [ ] The replay server script, the recording script and `just record-moddb`; the manifest; the first recordings for the requests the specs make (ADR-9 decisions 6, 8, 9 and 10) (`VSS-571h`)
- [ ] The second pass in `scripts/e2e-ci.sh` (network, replay container, second API container, cleanup), pinned in `scripts/tests/test-e2e-ci.sh`; images answered by a placeholder (ADR-9 decisions 6 and 13) (`VSS-571h`)
- [ ] Run each `@moddb` test on the recordings; retag (`@moddb-live`) with reasons; fix tests that fail for a fault of their own; `web/e2e/README.md`; job time before and after; close `VSS-571h` with an AAR (ADR-9 decisions 11 and 12)
- [ ] Pull-in (Matt, 2026-11-17): complete `agentdocs/vintagestory-modapi.md` from what was recorded (`VSS-zhv3`)

---

### Story 20.7: Reproducible Image Inputs and the Numbering Rule

**Sprint key:** `20-7-reproducible-image-and-conventions`
**Beads:** `VSS-870` (INFRA-004), `VSS-as6` (TOOLS-005), `VSS-3q2s` (DOCS-002; pulled in, Matt, 2026-11-17)
**FRs:** FR255, FR256, FR257

As a **maintainer**,
I want **the image built from inputs that a commit names exactly, and the story numbering rule to say what we do**,
So that **a release build does not change without a commit, and the documentation stops contradicting the practice**.

**Acceptance Criteria:**

**Given** the Dockerfile
**When** I read the line that copies uv
**Then** it names a version and a digest, and the version is the one `.mise.toml` pins

*(Covers FR255)*

**Given** every `FROM` and `COPY --from` image in the Dockerfile (uv, the Node build image and the .NET runtime image)
**When** `just test-scripts` runs
**Then** a test passes only if each has `@sha256:` and the uv tag equals the uv version in `.mise.toml`

*(Covers FR255; Matt, 2026-11-17)*

**Given** the image built from the pinned Dockerfile
**When** CI's `docker` and `e2e` jobs run
**Then** the build succeeds and the E2E tests pass against it

*(Covers FR255)*

**Given** `renovate.json`
**When** Renovate runs
**Then** it proposes digest and version updates for the three images, uv in the Dockerfile and in `.mise.toml` move in one pull request, and the .NET runtime is still held below 11

*(Covers FR256)*

**Given** `RELEASING.md`
**When** I read what happens on a re-run of the image job
**Then** it says which inputs are pinned, that `apt-get upgrade` stays and the system package layer can therefore still differ, and that each run's attestations describe the digest that run pushed

*(Covers FR255; Matt, 2026-11-17)*

**Given** `project-context.md`'s "Story Numbering" section
**When** I read it
**Then** it says a preparation story is numbered X.0, an epic without one starts at X.1, and its table and history match what Epics 4 to 20 did

*(Covers FR257; Matt, 2026-11-17)*

**Given** `cliff.toml`, the BMAD story template and the sprint keys
**When** the story is done
**Then** none of them changed, and they agree with the rule

*(Covers FR257)*

**Given** the pull-in `VSS-3q2s`
**When** the story is done
**Then** the environment table in `architecture/project-structure-boundaries.md` lists `VS_API_KEY`, `VS_CSP_MODE` and Story 20.6's `VS_MOD_DB_URL`, says what `VS_DEBUG` also serves and that it allows a plain-HTTP mod database address, does not list `VS_GAME_VERSION`, and the bead is closed with an AAR

*(Covers FR257; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] Pin the uv image by version and digest, and the two base images by digest; build and run the E2E set on the result (Epic 20 ADR-10 decisions 1 and 2) (`VSS-870`)
- [ ] The Renovate rule that groups uv; the script test for digests and the uv version (ADR-10 decisions 3 and 4) (`VSS-870`)
- [ ] `RELEASING.md`: what a re-run can and cannot change (ADR-10 decision 5) (`VSS-870`)
- [ ] Rewrite the "Story Numbering" section of `project-context.md` (ADR-11) (`VSS-as6`)
- [ ] Pull-in (Matt, 2026-11-17): the architecture's environment table, with `VS_MOD_DB_URL` (`VSS-3q2s`)

### 4.4 Architecture (`architecture/epic-20-tooling-and-test-health.md`, new)

| ADR | Decision | Story | Decided by |
|---|---|---|---|
| ADR-1 | One commit runs `ruff format` over the whole API and holds nothing else; it is the first change of the epic, its own story and pull request (reviewed by reproducing it); its hash goes into `.git-blame-ignore-revs`; `ruff format --check` joins `just lint-api`, which CI and `just check` run. No Prettier for the web | 20.1 | Matt, 2026-11-17 |
| ADR-2 | The web tests switch to `pool: 'vmThreads'` (15.2 s to 6.3 s locally). `Terminal.test.tsx` is deleted with its dead component (`VSS-eh41`) and the three other failing files change how they stub `location` and `document`; `isolate: false` is rejected; no file stays on another pool | 20.2 | Planner; decision 5 and the `VSS-eh41` pull-in confirmed by Matt, 2026-11-17 |
| ADR-3 | The three empty placeholder tests are deleted (with real tests where coverage is missing), the fourth is rewritten to pass, the Pyright warnings get annotations, `VSS-37a` is verified and closed. No ignore comment, no tool to forbid skips | 20.2 | Planner |
| ADR-4 | A `web/e2e/tsconfig.json` (Node types only) is checked by `just typecheck-web`, so `just typecheck`, `just check` and CI's `web` job cover the specs; the web build does not | 20.3 | Planner |
| ADR-5 | Recipes pass arguments as positional parameters (all eighteen that forward `*ARGS`); `sprint-status.sh` is made clean with `case` statements and `just lint-scripts` uses globs; the two Playwright output paths are untracked and ignored | 20.3 | Planner |
| ADR-6 | Semgrep runs through one script at a version pinned with `uvx semgrep==<version>` (uv is already pinned everywhere; a baseline scan needs the git history; no image pull), kept current by Renovate; six registry packs fetched at run time; source only, tests excluded by `.semgrepignore`; metrics off. Not part of `just check` | 20.4 | Matt, 2026-11-17 |
| ADR-7 | A sixth CI job: pull requests fail only on findings they add (`--baseline-commit`), `main` is scanned in full without failing, SARIF goes to code scanning from the one job with `security-events: write`; `test-release.sh` expects six jobs. Findings are fixed in code; a verified false positive may get an inline `nosemgrep` naming one rule with a reason, written into `project-context.md` as the one exception. The md5 finding is fixed with `usedforsecurity=False` | 20.4 | Matt, 2026-11-17 |
| ADR-8 | `e2e-ci.sh` seeds a nested directory, so the five file browser navigation tests lose `@game-server`; a new test creates a directory in the throwaway container with `docker exec` and expects it after a reload; `VSS-029` closes; the Playwright browsers are cached by version; the connection reset gets a time-boxed investigation with a keep-alive race as the working explanation | 20.5 | Planner; the `docker exec` test confirmed by Matt, 2026-11-17 |
| ADR-9 | A new optional setting `VS_MOD_DB_URL` (default `https://mods.vintagestory.at`) is the base for the API's mod database requests and downloads; the image host allow-list, the link rules and the web UI's links stay fixed. It is validated at start-up: `https` only, `http` only with `VS_DEBUG=true`, a warning when it is not the default. CI adds a second pass: a plain-HTTP replay container and a second API container in debug mode pointed at it, with the live hosts still blocked. Trimmed real recordings with their real image URLs and a manifest live in `web/e2e/fixtures/moddb/`; `just record-moddb` refreshes them; no scheduled live run; `@moddb-live` and `@install` stay local; images are stubbed in the browser | 20.6 | Matt, 2026-11-17 (the alternative to the first version) |
| ADR-10 | uv is copied from a version and digest that match `.mise.toml`; the two base images get digests; Renovate moves the pins and groups uv; a script test enforces it; `apt-get upgrade` stays and `RELEASING.md` says what can still differ | 20.7 | Matt, 2026-11-17 |
| ADR-11 | The numbering rule changes to match practice: a preparation story is X.0, an epic without one starts at X.1. Documentation only | 20.7 | Matt, 2026-11-17 |

The file also records the facts the decisions rest on, with file and line references.

### 4.5 Other Artifacts

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | `epic-20` (backlog), `epic-20-retrospective` (optional) and the seven story keys (backlog), via `scripts/sprint-status.sh` | Now |
| Beads | Epic `Epic 20: Tooling and Test Health` (`VSS-lzgg`), labels TOOLS and CICD; the 17 in-scope issues are its children (the three pull-ins were added on 2026-11-17 after Matt's approval). `VSS-37a` and `VSS-3mr` keep `VSS-029` as a parent too. No child bead's content was changed | Now, and per story |
| `architecture/index.md` | Entry for the Epic 20 ADRs | Now |
| `project-context.md`, `CLAUDE.md`, README, `.env.example`, `RELEASING.md`, `web/e2e/README.md`, `agentdocs/vintagestory-modapi.md`, `architecture/project-structure-boundaries.md` | The rules and commands the stories change | Stories 20.1 to 20.7 |
| `.github/workflows/ci.yml`, `Justfile`, `renovate.json`, `Dockerfile`, `scripts/` | As the stories say | Stories 20.1 to 20.7 |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 20.1 to 20.7 from `epics.md` and the Epic 20 ADRs, 20.1 first |
| Developer (`dev-story`) | Implement each story. In 20.1, the format commit holds nothing else and merges before any other branch is cut. In 20.4, update the job-list guard with the workflow. In 20.6, the setting is its own `feat(api)` commit, and the path to the replay is proved before recording |
| Reviewer (`code-review`) | Delegated review per story. For 20.1, reproduce the format commit and compare trees |
| Maintainer (Matt) | Reads code scanning alerts once 20.4 is on `main`; decides on the repository's secret scanning setting (below) |

**Decided by the maintainer during planning (Matt, 2026-11-17), not open:**

1. Ruff format: approved as one dedicated commit, first in the epic, into `.git-blame-ignore-revs`, then the check in `just lint-api`. Prettier for the web is not in scope. (ADR-1)
2. Semgrep: local recipe and CI job; pinned version; the six packs fetched at run time; pull requests fail only on findings they add; full scans of `main` do not block; SARIF to code scanning with `security-events: write` on that job only; source only; the md5 finding fixed in code; the inline `nosemgrep` exception. (ADR-6, ADR-7)

**Open questions for the maintainer.** Answered 2026-11-17: 3 changed to the alternative; 2 approved; all others confirmed as defaulted.

1. **Does `just semgrep` join `just check`? (ADR-6 decision 8)** Default: no. It needs the network and adds about a minute to a command run before every commit, and CI runs it on every pull request. *Confirmed: not in `just check` (Matt, 2026-11-17).*
2. **The three pull-ins.** Default: yes to all three. *Approved (Matt, 2026-11-17): `VSS-eh41` into 20.2, `VSS-zhv3` into 20.6, `VSS-3q2s` into 20.7. They are children of `VSS-lzgg` and their tasks are in the stories.*
3. **How recorded answers reach the API (ADR-9).** Default was a replay container at the mod database's own address with a per-run certificate and no product change. *Changed (Matt, 2026-11-17): the alternative. A setting for the mod database's base address, default the real one; CI points it at a plain-HTTP replay container. The guard must keep it from becoming a production foot-gun. Written as ADR-9: the setting is `VS_MOD_DB_URL`; `https` is required and `http` is accepted only with `VS_DEBUG=true`, checked at start-up; the API requests and the download follow it and everything given to a browser stays fixed.*
4. **Real recordings or hand-written answers (ADR-9 decision 8).** Default: trimmed real recordings. *Confirmed (Matt, 2026-11-17).*
5. **A scheduled run of the mod database tests against the live service (ADR-9 decision 11).** Default: none. *Confirmed (Matt, 2026-11-17).*
6. **Which mod database tests stay local-only (ADR-9 decision 12).** Default: tests that compare with live data (`@moddb-live`) and the three `@install` tests. *Confirmed (Matt, 2026-11-17).*
7. **The new-directory test (ADR-8 decision 3).** Default: the test creates the directory in the throwaway container with `docker exec` and skips on any other stack. *Confirmed (Matt, 2026-11-17).*
8. **Digests for the two base images, and `apt-get upgrade` (ADR-10 decisions 2 and 5).** Default: pin both base images by digest as well as uv; keep `apt-get upgrade` and document it. *Confirmed (Matt, 2026-11-17).*
9. **The numbering rule (ADR-11).** Default: "a preparation story is X.0; an epic without one starts at X.1". *Confirmed (Matt, 2026-11-17).*
10. **A file that cannot pass under `vmThreads` (ADR-2 decision 5).** Default: stop and ask; no per-file pool override. *Confirmed (Matt, 2026-11-17).*

**What the planner decided inside answer 3, for the maintainer to see:**

1. **The name is `VS_MOD_DB_URL`,** not the working name `VS_MOD_API_URL`: the value is the site's base address, and both `/api` and `/download` are built from it.
2. **CI runs the mod database tests as a second pass with a second API container.** The guard needs `VS_DEBUG=true` for a plain-HTTP address. Switching the one CI container to debug mode would have meant every E2E test runs against a debug-mode image (API documentation served, test routes mounted), and CI would no longer test the image as it runs in production. The first pass is therefore unchanged and only the `@moddb` pass uses a debug-mode container.
3. **The image host and the links do not follow the setting.** They are checks on what a browser is given, and recorded answers keep their real image URLs so those checks are tested on real values.

**For the maintainer, not a story:** GitHub secret scanning and push protection are disabled on the repository. Both are free for public repositories and are a repository setting, not code.

**Found during planning and handled inside the epic (no bead filed):**

1. `VSS-37a` is already fixed by commit `f393c3a`; Story 20.2 verifies and closes it.
2. The line numbers in `VSS-1ar`, `VSS-hnl` and `VSS-1eb` are out of date; the ADR file has the current ones.
3. The argument fault of `VSS-6354` is in eighteen recipes, including `just sprint`; Story 20.3 fixes all of them.
4. `node:26-slim` and the .NET runtime image have no digest either; Story 20.7 pins them (question 8).
5. No CI step would run the new E2E type check; Story 20.3 adds `just typecheck-web` to the `web` job.
6. A new CI job must update `scripts/tests/test-release.sh`; Story 20.4 does.
7. `.dockerignore` does not exclude the Playwright output directories; Story 20.3 adds them.
8. The game version filter that the three placeholder tests wait for exists; Story 20.2 checks its coverage before deleting them.

**Seen and left alone, with the reason (no bead filed):**

1. `just lint-web` and `just typecheck-web` run the same command, so `just check` type-checks the web twice. It costs seconds; a real web linter is a different piece of work (ADR-4).
2. The web is not formatted by Prettier (279 files) and `just format-web` runs an unpinned Prettier. Out of scope by the maintainer's decision.
3. The new setting should also appear in the architecture's environment table; that is `VSS-3q2s`'s table, and Story 20.7 adds it there.
4. Open beads that touch nearby files and are product work, not tooling: `VSS-759m` (casts in `VersionTable`), `VSS-vt4` (settings tabs and arrow keys), `VSS-o8s` (file browser paths with a slash). Not proposed.

**Planned net bead change (after the pull-ins were approved):** closed 18 (the 14 beads the maintainer picked, the 3 pull-ins and the old epic `VSS-029`). Opened 1 (the epic bead `VSS-lzgg`, which closes with the epic). Filed from planning: none. Net: 18 fewer open beads, from 50 open before the epic to 32 after it.

**Success criteria:**

- `ruff format --check` passes over the API, the format commit is alone and reproducible, and CI fails on an unformatted file
- `just check` ends with 0 Pyright warnings and 0 skipped web tests, and the web tests run under `vmThreads` locally and in CI
- A type error in an E2E spec fails `just check` and CI; ShellCheck covers every script; `just test-api -k "a or b"` works; a Playwright run leaves `git status` clean
- A pull request that adds a semgrep finding fails, one that adds none passes whatever `main` holds, and `main`'s results are in code scanning
- CI runs the file browser navigation tests, the new-directory test and the mod database tests on recordings, with no request to the live mod database
- With `VS_MOD_DB_URL` unset the API behaves as before; an `http` address without `VS_DEBUG=true`, or any malformed address, stops start-up with an error that names the setting
- Every image in the Dockerfile has a digest and a script test says so
- The numbering rule, `cliff.toml` and the story template agree
- Each of the 17 in-scope beads is closed with an AAR by its story, and `VSS-029` is closed
- `just check` and CI pass throughout

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: fourteen beads chosen by the maintainer after Epic 19, and three related ones pulled in on his approval. [x] 1.2 type: one bug (already fixed) and sixteen tooling, test, CI and documentation tasks. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete except Epic 19 ADR-14 decision 9 and the "never Story 0" rule. [x] 2.5 no resequencing; order inside Epic 20 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR234-FR259 added, MVP unaffected. [x] 3.2 architecture: new Epic 20 ADRs. [N/A] 3.3 UX spec: no change. [!] 3.4 CI: a sixth job with `security-events: write`, and guards in two script tests to update; one new optional setting, no deployment has to change |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1 scope approved before planning; ADR-1, ADR-6 and ADR-7 decided by Matt on 2026-11-17. [x] 6.2, 6.3 the ten open questions were answered by Matt on 2026-11-17 and are written in; the rewritten ADR-9 (the setting's name, the two passes, what follows the setting) is the planner's reading of his answer and has not been reviewed yet. [x] 6.4 handoff in section 5 |
