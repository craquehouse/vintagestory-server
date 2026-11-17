# Story 20.4: Semgrep Locally and in CI

Status: review

<!-- Implements FR244-FR247, Epic 20 ADR-6 and ADR-7 (both accepted by Matt, 2026-11-17). Beads: VSS-djg (TOOLS-002, size-s), VSS-4ac (CICD-001, size-m). Stacked on Story 20.3 (stories run in order 20.1 to 20.7). Line references were verified at 7f04ea2 (epic-20-planning; its api/, web/, scripts/, Justfile and .github/ are identical to 3f1c6ea, the commit the ADRs cite) and must be re-checked at implementation time: Story 20.1 reformats api/src/vintagestory_api/services/server.py, Story 20.3 rewrites the Justfile's argument handling and the lint-scripts recipe, and Stories 20.1 and 20.3 edit ci.yml. One product code change (a keyword argument in the download checksum, same result). No API contract change, no release note, no new npm or Python dependency: semgrep runs through uvx and is not added to api/pyproject.toml. -->

## Story

As a **maintainer**,
I want **a static security scan on every pull request and one command to run it myself**,
so that **a risky pattern is caught when it is written, without old findings or noisy rules blocking unrelated work**.

## Acceptance Criteria

1. **Given** `just semgrep`
   **When** it runs
   **Then** it runs semgrep at one pinned version through `uvx`, with `--metrics=off`, the packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile`, over `api/src`, `web/src`, `.github`, `Dockerfile` and `scripts`, and exits non-zero on a finding (exit 1; exit 2 or more means semgrep could not run)
   *(Covers FR244; Matt, 2026-11-17)*

2. **Given** the scan's scope
   **When** I list the files semgrep scanned
   **Then** no test file is among them (`*.test.ts`, `*.test.tsx`, `scripts/tests/`, `web/src/test/`), the exclusions are in one `.semgrepignore` at the repository root, and no rule file is stored in the repository
   *(Covers FR244; Matt, 2026-11-17)*

3. **Given** the semgrep version
   **When** I look for it
   **Then** it is written in one place (`SEMGREP_VERSION="1.185.0"` in `scripts/semgrep.sh`), CI and the recipe both read it from there, Renovate has a rule that updates it, and a script test checks that the line has the form that rule matches
   *(Covers FR244)*

4. **Given** `just semgrep --baseline-commit origin/main`
   **When** it runs on a branch
   **Then** the arguments reach semgrep unchanged and only findings the branch adds are reported
   *(Covers FR244)*

5. **Given** `just lint`, `just check`, `just test-api` and `just test-web`
   **When** they run
   **Then** none of them runs semgrep
   *(Covers FR244; Matt, 2026-11-17)*

6. **Given** a pull request that adds a line a chosen rule matches
   **When** CI runs
   **Then** the `semgrep` job fails and its log names the rule, the file and the line
   *(Covers FR245; Matt, 2026-11-17)*

7. **Given** a pull request that adds no finding, while `main` has findings or the registry has new rules
   **When** CI runs
   **Then** the `semgrep` job passes
   *(Covers FR245; Matt, 2026-11-17)*

8. **Given** a push to `main` or a manual run
   **When** the `semgrep` job runs
   **Then** it scans the whole scope, uploads the results to GitHub code scanning as SARIF, and does not fail because of findings; it still fails when semgrep itself cannot run
   *(Covers FR245, FR246; Matt, 2026-11-17)*

9. **Given** `ci.yml`
   **When** I read it
   **Then** only the `semgrep` job has `security-events: write`, the workflow's default permission is still `contents: read`, every action is pinned by commit, and the job has the same release-commit skip `if:` as the others
   *(Covers FR246; Matt, 2026-11-17)*

10. **Given** `just test-scripts`
    **When** it runs
    **Then** `test-release.sh` expects the six jobs `api docker e2e scripts semgrep web`, checks the skip `if:` on each, and passes; `just lint-workflows` passes
    *(Covers FR246)*

11. **Given** `api/src/vintagestory_api/services/server.py`
    **When** semgrep runs with `p/python`
    **Then** the checksum code uses `hashlib.md5(usedforsecurity=False)`, the rule `insecure-hash-algorithm-md5` no longer matches, the scope has no finding, and no `nosemgrep` comment was added for it
    *(Covers FR247; Matt, 2026-11-17)*

12. **Given** `project-context.md`'s "No Silent Failures Rule"
    **When** I read it
    **Then** it states the one exception: `# nosemgrep: <rule-id> — <reason>` naming one rule, only for a verified false positive, each one checked in review, a bare `nosemgrep` never, and changing the code preferred where that states the intent better; and a script test fails on a `nosemgrep` comment in the scanned source that does not have that form
    *(Covers FR247; Matt, 2026-11-17)*

13. **Given** the CI job on the runner
    **When** it runs
    **Then** it finishes within five minutes, and the story records its time and, per pack, how many rules the engine could not run
    *(Covers FR245)*

14. **Given** a developer who has run `semgrep login` on their machine
    **When** they run `just semgrep`
    **Then** the scan uses the same registry rules as CI (the login is ignored), so a local result and the CI result can be compared
    *(Covers FR244; found while validating this story, Dev Notes "ADR against the code" 1)*

15. **Given** the story's pull request has merged and the first `semgrep` job has run on `main`
    **When** the maintainer opens Security > Code scanning
    **Then** the tool `Semgrep OSS` is listed with an analysis of `refs/heads/main`, and the open alerts are the findings of that scan (none are expected, because AC 11 fixes the only one)
    *(Covers FR246; manual check by the maintainer)*

## Tasks / Subtasks

<!-- Commit per task: type(story-20.4/task-N): ... with type build, ci, refactor, test, docs or chore. No feat, fix or perf: nothing here is visible to an admin, so nothing may reach the release notes. The md5 change is a refactor (Epic 20 ADR-7 decision 7). Six tasks: the epic's Renovate task is Task 2, and the epic's "prove the gate" task is folded into the last task because it can only run on the pull request. -->

- [x] Task 1: `scripts/semgrep.sh`, `.semgrepignore` and the `just semgrep` recipe + tests (AC: 1, 2, 4, 5, 14) (`VSS-djg`)
  - [x] 1.1: New `scripts/tests/test-semgrep.sh` (style of `scripts/tests/test-e2e-ci.sh`: `lib.sh` helpers `pass`, `fail`, `assert_eq`, `assert_contains`, `make_tmp`, `finish`; `scripts/tests/run.sh` picks up `test-*.sh` by itself). Red first, with the assertions of Dev Notes "Script tests" groups A, B and C. The test never runs semgrep and never needs the network: it puts a stub `uvx` first on `PATH`
  - [x] 1.2: New `scripts/semgrep.sh`, executable, exactly as in Dev Notes "The script"
  - [x] 1.3: New `.semgrepignore` at the repository root, exactly as in Dev Notes "The ignore file"
  - [x] 1.4: `Justfile`: the `semgrep *ARGS` recipe after `lint-workflows` (`Justfile:155-157`), in the argument form Story 20.3 gave the other recipes (Dev Notes "The recipe"). It is not a dependency of `lint`, `check`, `test`, `test-api` or `test-web`
  - [x] 1.5: `just lint-scripts` covers the new script and the new test. After Story 20.3 the recipe uses globs and nothing needs editing; if it still names files (`Justfile:151-153` at 7f04ea2), add `scripts/semgrep.sh`
  - [x] 1.6: Run `just semgrep --json-output=<a file outside the repository>` once. Expect exit 1 and one finding, the md5 rule in `services/server.py` (Task 3 removes it). Record in the Dev Agent Record: files scanned, rules run, findings, the count of `.errors` and `.skipped_rules` in the JSON, wall clock time, and that no path in `.paths.scanned` is a test file. Then record the per-pack numbers (Dev Notes "Measurements" has the command and what this story's validation measured)
  - [x] 1.7: Run `just semgrep --baseline-commit origin/main` on the branch and record the output's line "Scan was limited to files changed since baseline commit." and the result. `just test-scripts` and `just lint-scripts` pass

- [x] Task 2: The Renovate rule for the version + test (AC: 3) (`VSS-djg`)
  - [x] 2.1: Add group D of Dev Notes "Script tests" to `test-semgrep.sh`, red first
  - [x] 2.2: `renovate.json`: add `customManagers` next to `packageRules` (Dev Notes "The Renovate rule"). The two existing package rules do not change
  - [x] 2.3: Validate the file once without adding a dependency (Dev Notes "The Renovate rule" has the command). If the validator cannot run, say so in the completion notes; the Renovate Dashboard issue shows the dependency `semgrep` after the merge either way, and the maintainer checks it there

- [x] Task 3: The download checksum says it is not a security use + tests (AC: 11) (`VSS-4ac`)
  - [x] 3.1: `api/src/vintagestory_api/services/server.py:650`: `hashlib.md5()` becomes `hashlib.md5(usedforsecurity=False)`. Nothing else in `verify_checksum` (`:638-668`) changes: not the method name, the log events or the docstring. No `nosemgrep` comment
  - [x] 3.2: No test changes. `just test-api tests/server` passes (260 tests at 7f04ea2 with the change prototyped; `TestChecksumVerification` at `api/tests/server/test_install.py:308-334` covers the match and the mismatch). `just typecheck-api` and `just lint-api` pass, and after Story 20.1 `ruff format --check` passes for the file
  - [x] 3.3: `just semgrep` exits 0 with "0 findings". Record the output's summary line. From here on the scope has no finding
  - [x] 3.4: Commit as `refactor(story-20.4/task-3): ...` (not `fix`: nothing an admin sees changes)

- [x] Task 4: The `semgrep` job in `ci.yml` + tests (AC: 6, 7, 8, 9, 10, 13) (`VSS-4ac`)
  - [x] 4.1: Add group E of Dev Notes "Script tests" to `test-semgrep.sh`, and change `scripts/tests/test-release.sh:322`: the name becomes "ci.yml has its six jobs" and the expected list `api docker e2e scripts semgrep web`. The loop below it (`:323-325`) already checks every job's `if:`. Red first: both fail before 4.2
  - [x] 4.2: `.github/workflows/ci.yml`: add the job after `e2e` (the last job, `ci.yml:75-110` at 7f04ea2), exactly as in Dev Notes "The job". The top-level `permissions: contents: read` (`:10-11`) and the other five jobs do not change
  - [x] 4.3: `just lint-workflows`, `just lint-scripts` and `just test-scripts` pass. `scripts/tests/test-docker-context.sh:19-22` (every action pinned by a full commit SHA) and `scripts/tests/test-e2e-ci.sh:58-59` (the workflow reads no secret) pass unchanged
  - [x] 4.4: The workflow and the `test-release.sh` change are one commit, `ci(story-20.4/task-4): ...` (Epic 20 ADR-7 decision 1)

- [x] Task 5: The `nosemgrep` exception, the command in the docs, and the triage note + test (AC: 12) (`VSS-4ac`)
  - [x] 5.1: Add group F of Dev Notes "Script tests" to `test-semgrep.sh` (the form of every `nosemgrep` comment in the scanned source; none exists today)
  - [x] 5.2: `project-context.md`, section "8. No Silent Failures Rule" (`:218-255`): add the exception after the "Forbidden Patterns Without Justification" list (`:228-232`) and before "Good Example" (`:234`), with the text of Dev Notes "The exception text". The rest of the section does not change
  - [x] 5.3: `CLAUDE.md` command block, under "# Scripts and workflows" (`:162-165`): one line, `just semgrep` with "Static security scan (needs the network; not part of just check)". `README.md` "Development commands" (`:99-112`): one line for `just semgrep` in the code block, and one sentence below the block: CI runs the same scan on every pull request and fails only on findings the pull request adds; `main`'s findings are under Security > Code scanning
  - [ ] 5.4: The triage note of Dev Notes "How a finding is triaged" is already in this story. Copy its four steps into the PR description so the maintainer has them where the first alert will be discussed

- [ ] Task 6: Prove the gate on the pull request, quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes, and `just semgrep` exits 0. The diff adds no lint or type suppression, no `cast`, no `nosemgrep`, no skipped test and no dependency (`api/pyproject.toml`, `api/uv.lock`, `web/package.json` and `web/bun.lock` are unchanged). No rule file is in the repository. `git status --short` is clean (no `semgrep.sarif`, no JSON output)
  - [x] 6.2: Story status `review` and `just sprint set 20-4-semgrep review`; commit as `chore(story-20.4/task-6): ...`
  - [ ] 6.3: The controller pushes the branch and opens the pull request against `main` (the dev agent does not push or open it). CI runs only on pull requests that target `main` (`ci.yml:3-8`), so this needs Stories 20.1 to 20.3 merged first. Record the first run: the `Semgrep` job passes although the merge base still has the md5 finding (AC 7), its duration (AC 13: within five minutes), and the log's "Ran N rules on M files" line
  - [ ] 6.4: Prove the gate (AC 6), on the story's own pull request. Commit `ci(story-20.4/task-6): temporary finding to prove the semgrep gate` adds the file of Dev Notes "The gate proof" and nothing else. The `Semgrep` job must fail, and its log must name the rule `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5`, the file and line 5. Record the run URL. While that commit is the tip, start one manual run, `gh workflow run ci.yml --ref <branch>`: its `Semgrep` job must pass (findings do not fail a full scan) and upload (AC 8). Record the run URL and what `gh api "repos/craquehouse/vintagestory-server/code-scanning/analyses?ref=refs/heads/<branch>"` lists (tool `Semgrep OSS`, category `semgrep`, 1 result)
  - [ ] 6.5: Commit `ci(story-20.4/task-6): remove the temporary finding` deletes the file again (a plain commit, no force push, no history rewrite). The `Semgrep` job passes; record the run URL. Start the manual run once more and record that the analysis of the branch now has 0 results, so the proof leaves no open alert behind
  - [ ] 6.6: PR link on `VSS-djg` and `VSS-4ac`. The PR description says: no API contract change, no release note, the measurements, the four triage steps, the decisions of Dev Notes "Decisions for the maintainer", and the manual check of AC 15 for the maintainer after the merge
  - [ ] 6.7: After the merge (controller or maintainer): the push to `main` runs the full scan and the upload. AC 15 is confirmed by the maintainer in the browser, or with `gh api "repos/craquehouse/vintagestory-server/code-scanning/analyses?ref=refs/heads/main" --jq '.[0] | {tool: .tool.name, category, results_count, created_at}'`. Both beads are closed with an AAR after that, not before

## Dev Notes

### What is there today (verified at 7f04ea2)

- Semgrep is used nowhere: no recipe, no configuration, no `.semgrepignore`, no `nosemgrep` comment (`git grep -il semgrep` finds only planning documents and the beads export).
- `.github/workflows/ci.yml` has five jobs, `api`, `web`, `scripts`, `docker`, `e2e`. Top-level `permissions: contents: read` (`:10-11`). No job has its own `permissions`. Every job has `if: "${{ !startsWith(github.event.head_commit.message, 'chore(release): ') }}"` with the same comment line above it. Triggers: `pull_request` and `push` on `main`, and `workflow_dispatch` (`:3-8`). Every checkout is depth 1 (no `with:`).
- `scripts/tests/test-release.sh:319-325` pins the job list (`:322`, "ci.yml has its five jobs", `api docker e2e scripts web`) and each job's `if:`. With the new job and no other change, `just test-scripts` fails on exactly that one assertion (133 of 134 pass in `test-release.sh`; prototyped).
- `scripts/tests/test-docker-context.sh:19-22` fails on an action that is not pinned by a 40-character commit SHA. The line `uses: github/codeql-action/upload-sarif@<sha> # v4.39.3` passes it (prototyped).
- `scripts/tests/test-e2e-ci.sh:58-59` fails if `ci.yml` contains `secrets.`. The new job reads none.
- `Justfile`: `lint` is `lint-api lint-web lint-scripts lint-workflows` (`:141`), `check` is `lint typecheck test` (`:179`), `test` is `test-api test-web test-scripts` (`:29`). Recipes that take arguments interpolate `{{ARGS}}` (`:35`, `:39`, `:44`); Story 20.3 changes that to positional arguments.
- `.mise.toml` pins `uv = "0.13.8"`, so `uvx` is on the path wherever the mise action or `mise exec` runs. It also pins Python 3.14, and `uvx semgrep==1.185.0` installs and runs on it (67 packages, about 7 s the first time, then cached).
- `api/src/vintagestory_api/services/server.py:650`: `md5_hash = hashlib.md5()` inside `verify_checksum` (`:638-668`), called once at `:817` to compare a downloaded server archive with the checksum the vendor publishes. `api/tests/server/test_install.py:52` builds the expected value with `hashlib.md5(tarball_bytes).hexdigest()` (a test file, outside the scan).
- `renovate.json` extends `local>craquehouse/renovate-config` and has two `packageRules` and no `customManagers`. The organisation's preset auto-merges GitHub Actions updates on a branch; it has no rule for a custom manager, so a semgrep update arrives as a pull request.
- `project-context.md:218-255` is "8. No Silent Failures Rule". It does not mention semgrep.

### The script (Task 1.2)

```bash
#!/usr/bin/env bash
# Static security scan of the source with semgrep (Story 20.4, Epic 20 ADR-6).
#
# Runs one pinned semgrep through uvx with six registry packs, fetched at run time (needs
# the network), over the source. Files that only hold tests are left out by .semgrepignore.
# Exits 1 on a finding and 2 or more when semgrep could not run.
#
# Usage: scripts/semgrep.sh [semgrep scan args...]   (via `just semgrep`)
#   just semgrep --baseline-commit origin/main   only findings the branch adds
#   SEMGREP_REPORT_ONLY=1   report findings without failing (CI's full scan of main)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Renovate updates this line (renovate.json customManagers); test-semgrep.sh pins its form
SEMGREP_VERSION="1.185.0"
PACKS=(p/python p/typescript p/react p/secrets p/github-actions p/dockerfile)
PATHS=(api/src web/src .github Dockerfile scripts)

# The registry serves a logged-in user a different, larger rule set. CI is never logged in,
# so ignore a developer's `semgrep login` and scan with the rules CI uses.
export SEMGREP_SETTINGS_FILE=/dev/null
unset SEMGREP_APP_TOKEN

args=(scan --metrics=off)
[[ ${SEMGREP_REPORT_ONLY:-} == 1 ]] || args+=(--error)
for pack in "${PACKS[@]}"; do
    args+=(--config "$pack")
done

exec uvx "semgrep==$SEMGREP_VERSION" "${args[@]}" "$@" "${PATHS[@]}"
```

This text passed ShellCheck 0.11.0 and ran in a prototype at 7f04ea2. Why each part is there:

- **`scan` and `--error`.** `semgrep scan` exits 0 when it has findings unless `--error` is given. AC 1 needs the non-zero exit, so `--error` is the default.
- **`SEMGREP_REPORT_ONLY=1`.** The full scan of `main` must not fail on findings (AC 8). `--no-error` cannot be passed through for that: semgrep 1.185.0 refuses `--error` together with `--no-error` ("cannot be present at the same time", exit 2). So the script leaves `--error` out when the variable is `1`. Without `--error` semgrep still exits 2 when a pack cannot be fetched or the baseline commit does not exist, so "fails only when semgrep itself fails to run" holds.
- **`SEMGREP_SETTINGS_FILE=/dev/null` and no token.** See "ADR against the code" 1. With a login the same command ran 1,603 rules (1,313 of them "Pro rules"); without one, 290. `/dev/null` as the settings file was tested on macOS; semgrep prints nothing about it and reports "login status is False". If it misbehaves on Linux in CI, CI has no login anyway: make the export conditional on the file `~/.semgrep/settings.yml` existing, and say so in the completion notes.
- **`exec`** hands semgrep's exit code to the caller.
- **`"$@"` before the paths.** Extra options go to `semgrep scan`; the paths stay last. Extra positional arguments would be added to the targets, which nobody needs.
- **`--metrics=off`** is always passed. The log line "Not sending pseudonymous metrics since metrics are configured to OFF" confirms it.
- No `--quiet` and no `--verbose`: the default output names each finding's rule, file and line (AC 6) and ends with "Ran N rules on M files: K findings."

Exit codes measured: 0 no finding; 1 findings (with `--error`); 2 unknown pack, unknown baseline commit, or conflicting options.

### The ignore file (Task 1.3)

```gitignore
# Files that only hold tests are not scanned (Epic 20 ADR-6 decision 5).
# This file replaces semgrep's built-in ignore list. Semgrep reads only files tracked by git,
# so node_modules, .venv and build output need no entry.
*.test.ts
*.test.tsx
web/src/test/
scripts/tests/
```

- A `.semgrepignore` replaces semgrep's defaults, it does not add to them. Without the file, the defaults skip `scripts/tests/` and `web/src/test/` (10 files) but scan all 133 `*.test.ts(x)` files, which is where the time goes.
- `web/src/test/` holds one file, `web/src/test/mocks/use-game-config.ts`, a mock used only by tests. The ADR's list ends with "anything else that only holds tests"; this is that.
- `api/src/vintagestory_api/routers/test_rbac.py` is **not** a test file: it is the debug-only RBAC router that ships in the image. It stays in the scan. Do not add a `test_*` pattern.
- `api/tests`, `web/tests` and `web/e2e` are outside the five paths already.
- Result at 7f04ea2 with the script and this file added: 228 files scanned (web 156, api 62, scripts 7, `.github` 2, `Dockerfile` 1), 143 skipped by the ignore file.

### The recipe (Task 1.4)

After Story 20.3 the recipes that take arguments carry just's `positional-arguments` attribute and pass `"$@"`. Use exactly the form 20.3 gave `test-scripts` and `test-e2e-ci`. Expected:

```just
# Static security scan (semgrep, pinned in scripts/semgrep.sh); needs the network; not in `just check`
[positional-arguments]
semgrep *ARGS:
    mise exec -- ./scripts/semgrep.sh "$@"
```

Do not write `{{ARGS}}` in the new recipe even if a recipe 20.3 missed still does. Place it after `lint-workflows`, under a section comment of its own in the Justfile's style (`# SECURITY SCAN`), so nobody reads it as part of `lint`. If Story 20.3's argument test (ADR-5 decision 2) is driven by a list of recipes, add `semgrep` to the list.

### The Renovate rule (Task 2.2)

```json
  "customManagers": [
    {
      "customType": "regex",
      "description": "The semgrep version that scripts/semgrep.sh runs through uvx",
      "managerFilePatterns": ["/^scripts/semgrep\\.sh$/"],
      "matchStrings": ["SEMGREP_VERSION=\"(?<currentValue>\\d+\\.\\d+\\.\\d+)\""],
      "depNameTemplate": "semgrep",
      "datasourceTemplate": "pypi"
    }
  ],
```

- `managerFilePatterns` is the current name of the field that older Renovate versions called `fileMatch`; check the name against the Renovate documentation at implementation time (the Context7 MCP server, or docs.renovatebot.com) and use the one the validator accepts without a migration notice.
- Validate once: `mise exec -C web -- bunx --package renovate renovate-config-validator ../renovate.json`. This downloads Renovate into bun's cache and adds nothing to `web/package.json` or `web/bun.lock`; confirm both are unchanged afterwards. The `local>craquehouse/renovate-config` preset may not resolve without a token; a warning about the preset is not an error in this file.
- `semgrep` publishes several versions a week. That is the maintainer's to tune in the organisation preset if the pull requests become noise; this story adds no schedule and no grouping.
- The action `github/codeql-action` needs no rule: the built-in `github-actions` manager and `helpers:pinGitHubActionDigestsToSemver` already move SHA pins with a version comment.

### The job (Task 4.2)

```yaml
  semgrep:
    name: Semgrep
    # The release commit only changes version numbers; the tag's release workflow builds it
    if: "${{ !startsWith(github.event.head_commit.message, 'chore(release): ') }}"
    runs-on: ubuntu-latest
    timeout-minutes: 10
    # The only job that may write code scanning results; the workflow default stays contents: read
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          # --baseline-commit needs the merge base with main, which a depth-1 checkout lacks
          fetch-depth: 0
      - uses: jdx/mise-action@d5574b52816a478f9d4e6529a3f6ff17a8a36785 # v5.2.8
      # Pull request: fail only on a finding the pull request adds
      - if: ${{ github.event_name == 'pull_request' }}
        run: just semgrep --baseline-commit "$(git merge-base origin/main HEAD)"
      # main and manual runs: scan everything, report to code scanning, never fail on a finding
      - if: ${{ github.event_name != 'pull_request' }}
        run: just semgrep --sarif-output=semgrep.sarif
        env:
          SEMGREP_REPORT_ONLY: "1"
      - if: ${{ github.event_name != 'pull_request' }}
        uses: github/codeql-action/upload-sarif@33d7b85da1a04171e211befe2c739303b9a4c066 # v4.39.3
        with:
          sarif_file: semgrep.sarif
          category: semgrep
```

This text passed `just lint-workflows` (actionlint 1.7.12) and `test-docker-context.sh` in a prototype appended to `ci.yml` at 7f04ea2.

- **Pins.** `actions/checkout` and `jdx/mise-action` are the SHAs the other jobs use; copy them from the file as it stands when the task starts, in case Renovate moved them. `github/codeql-action` `v4.39.3` is commit `33d7b85da1a04171e211befe2c739303b9a4c066` (looked up with `gh api repos/github/codeql-action/tags` on 2026-11-17). Re-check with `gh api repos/github/codeql-action/git/ref/tags/<tag>` if a newer v4 tag exists at implementation time, and keep the `# vX.Y.Z` comment in the form the other pins have.
- **Permissions.** `permissions` on a job replaces the workflow default for that job, so `contents: read` is repeated. No other job gets a `permissions` key.
- **The skip `if:`** is the same string as the other five, with the same comment line. `github.event.head_commit` is empty on a pull request and on a manual run, so the job runs there.
- **Pull requests (AC 6, 7).** The checkout of a pull request is GitHub's merge commit of the branch into `main`. `fetch-depth: 0` fetches every branch, so `origin/main` exists and `git merge-base origin/main HEAD` is the commit of `main` the pull request is merged into. Semgrep then scans only the files that differ from that commit ("Scan was limited to files changed since baseline commit.") and reports a finding only if the baseline does not have it. Both sides are scanned with the rules fetched in this run, so a rule added to the registry yesterday cannot fail a pull request that did not touch the code it matches. A finding makes the step exit 1 and the log names rule, file and line.
- **No upload on a pull request** (Epic 20 ADR-7 decision 4): a fork's token is read-only, so the result is in the job log only. That means no code scanning annotation appears in a pull request's "Files changed" view and no "Code scanning results" check is added; the failed `Semgrep` job is the signal.
- **`main` and manual runs (AC 8).** `SEMGREP_REPORT_ONLY=1` leaves `--error` out, so findings give exit 0 and only a failure to run gives a non-zero exit. `--sarif-output` writes the file and keeps the readable log. The upload step then sends it. If the scan step fails, the upload is skipped and the job fails, which is right: there is no result to upload.
- **Manual run.** `gh workflow run ci.yml --ref <branch>` takes the full-scan path and uploads an analysis for that branch's ref. Such alerts show in Security > Code scanning only when the branch is chosen in the filter; the default view is `main`. Task 6.4 uses this to prove the upload before the merge.
- **The first run has nothing to compare with, and needs nothing.** The pull request gate compares two scans made in the same run; it never reads code scanning. On this story's own pull request the merge base still has the md5 finding and the branch has fixed it, so the job passes. Code scanning has never received an analysis for this repository; the first upload creates the tool entry, and no set-up step in the repository settings is needed for a public repository.
- **`category: semgrep`** names the analysis so a later tool's upload does not replace it.
- **Timeout** 10 minutes as a cap; AC 13 asks for under five and the expectation is under one (see "Measurements"). Nothing is cached: uv downloads semgrep (about 50 MB) on each run.
- **`security-events: write` also applies to this job on a pull request from a branch of this repository** (not from a fork). The job runs the pull request's `scripts/semgrep.sh`, so a pull request could upload a misleading analysis for its own ref. It cannot change `main`'s alerts, and every pull request is reviewed. Splitting the upload into a seventh job would narrow that; the epic fixes the job list at six, so it is listed under "Decisions for the maintainer".
- **Do not** add `continue-on-error`, `|| true`, a step that parses the SARIF, or a secret. Do not interpolate pull request text (title, branch name) into a `run:` step.

### Script tests (`scripts/tests/test-semgrep.sh`)

Header comment in the style of `test-e2e-ci.sh:1-6`, then `ROOT="$SCRIPTS_DIR/.."`. Each group is added by the task named, red first.

**A. What the script runs (Task 1; AC 1, 4, 14).** Make a directory with `make_tmp`, write a stub `uvx` into it that prints each argument on its own line and then the values of `SEMGREP_SETTINGS_FILE` and `SEMGREP_APP_TOKEN` into a file, and run `scripts/semgrep.sh` with that directory first on `PATH`. Assert, comparing the whole argument list as one string:

- `PATH="$stub:$PATH" SEMGREP_APP_TOKEN=x scripts/semgrep.sh --baseline-commit origin/main "a b"` gives exactly `semgrep==<version> scan --metrics=off --error --config p/python --config p/typescript --config p/react --config p/secrets --config p/github-actions --config p/dockerfile --baseline-commit origin/main`, then `a b` as one argument, then `api/src web/src .github Dockerfile scripts`. Take `<version>` from the script's `SEMGREP_VERSION` line so a Renovate update does not break the test.
- The stub saw `SEMGREP_SETTINGS_FILE=/dev/null` and no `SEMGREP_APP_TOKEN`.
- With `SEMGREP_REPORT_ONLY=1` and no arguments the list is the same without `--error` and without the extra arguments.
- The script exits with the stub's exit status (make the stub exit 1 once: the script exits 1).

The stub technique was prototyped at 7f04ea2 and gives exactly those lists.

**B. The scope (Task 1; AC 2).**

- `.semgrepignore` has the four patterns (compare its non-comment lines with the expected four).
- No tracked file is a semgrep rule file: `git -C "$ROOT" ls-files` has no path matching `(^|/)\.semgrep(/|\.ya?ml$)`, and every `--config` value the stub saw starts with `p/`.
- No file that only holds tests is scanned. Tracked files under the five paths, minus `git ls-files -ci --exclude-from=.semgrepignore -- <the five paths>`, must contain no path matching `\.test\.|/tests?/|/__tests__/|/mocks?/`. At 7f04ea2 that set has 228 paths (the same number semgrep reports) and none matches; `routers/test_rbac.py` rightly does not match. This is a tripwire for a new test directory under `web/src` or `scripts`. A file must be tracked (or at least added) to be counted, as with semgrep itself.

**C. Not part of the other recipes (Task 1; AC 5).** `just --justfile "$ROOT/Justfile" --dry-run check 2>&1` prints the commands of `lint`, `typecheck` and `test` and everything they depend on without running them (9 lines at 7f04ea2). Assert the output is not empty and does not contain `semgrep`. Assert that `just --justfile "$ROOT/Justfile" --show semgrep` contains `./scripts/semgrep.sh "$@"`. `just` is on the path because `just test-scripts` runs under `mise exec`.

**D. The version line and the Renovate rule (Task 2; AC 3).**

- Exactly one line of `scripts/semgrep.sh` matches `^SEMGREP_VERSION="[0-9]+\.[0-9]+\.[0-9]+"$`.
- `renovate.json` has exactly one custom manager with `datasourceTemplate` `pypi` and `depNameTemplate` `semgrep` (`yq -p json`, as `test-e2e-ci.sh:16-20` reads JSON).
- Its `managerFilePatterns` entry names `scripts/semgrep.sh`.
- Its `matchStrings[0]`, used as a Perl regular expression against the script, captures the same version as the line above: `RE="$pattern" perl -ne 'print "$+{currentValue}\n" if /$ENV{RE}/' scripts/semgrep.sh` (Perl understands Renovate's named group; `grep -E` does not; prototyped). This is the assertion that fails when someone reformats the version line.
- No other file holds a semgrep version: `git grep -nE 'semgrep==[0-9]' -- . ':!_bmad-output' ':!*.md'` is empty (the script builds the string from the variable), and `ci.yml` does not contain `semgrep==` or `uvx`.

**E. The job (Task 4; AC 8, 9, 10).** With `yq` on `ci.yml`, in the style of `test-e2e-ci.sh:53-59`:

- `.jobs.semgrep.permissions` is exactly `contents: read` and `security-events: write`.
- `.permissions` is exactly `contents: read`.
- No other job has a `permissions` key, and `security-events` appears exactly once in the file.
- `.jobs.semgrep.timeout-minutes` is `10`.
- The checkout step of the job has `fetch-depth: 0`.
- Exactly one step runs `just semgrep` with `--baseline-commit`, and its `if` names `pull_request`; exactly one step sets `SEMGREP_REPORT_ONLY` to `"1"` and passes `--sarif-output=semgrep.sarif`; the `upload-sarif` step's `sarif_file` is `semgrep.sarif` and its `if` is the same as the full scan's.
- `release.yml` does not mention semgrep (the release workflow is not changed).

The job list and the skip `if:` stay in `test-release.sh` (`:319-325`), where the release-commit rule lives.

**F. The exception's form (Task 5; AC 12).** Every line with `nosem` in the scanned source must have the documented form: `git grep -nE 'nosem' -- api/src web/src .github Dockerfile scripts ':!scripts/tests'` minus the lines matching `nosemgrep: [a-z0-9_-]+(\.[a-z0-9_-]+)+ — [^[:space:]]` must be empty. `scripts/semgrep.sh` as written above does not contain the word, so no exclusion other than `scripts/tests` is needed. None exists today, so the assertion passes from the start; prove it once by adding a bare `# nosemgrep` to a source line, seeing the test fail, and removing it. Why a test: semgrep itself honours a bare `nosemgrep` and a short rule name (measured, see "The exception text"), so the rule's form is not enforced by the tool.

### The exception text (Task 5.2)

Insert into `project-context.md` section 8, after the forbidden patterns list:

````markdown
**The one exception: a verified semgrep false positive** (Matt, 2026-11-17; Epic 20 ADR-7)

A semgrep finding is read first. If the code can be changed so that it is correct, or so that it says what it means, change the code (example: `hashlib.md5(usedforsecurity=False)` for a download checksum). Only a finding that is verified to be a false positive may be marked on its line:

```python
tar.extractall(target, filter=safe_filter)  # nosemgrep: <full-rule-id> — <reason>
```

(`// nosemgrep: <full-rule-id> — <reason>` in TypeScript.)

- It names exactly one rule, by the full ID semgrep prints. A bare `nosemgrep` is never allowed.
- The reason is on the same line and says why the rule is wrong here.
- Every such comment is looked at in code review; `scripts/tests/test-semgrep.sh` fails on one that does not have this form.
- No tracking issue is needed: a false positive has no fix to track.
- No baseline file and no list of accepted findings exists, and none may be added.

Every other suppression stays forbidden as described above.
````

Measured with semgrep 1.185.0 and `p/python` on a throwaway file (not in the repository): a comment with the full rule ID, an em dash and a reason suppresses that rule; a comment naming a different rule does not; a bare `# nosemgrep` and a short name (`insecure-hash-algorithm-md5`) both suppress too, which is why the form is checked by a test and by review. Do not add any `nosemgrep` comment in this story: the one finding is fixed in code (AC 11), and no chosen pack reports `tarfile-extractall-traversal` at `server.py:690` (ADR-7 decision 8; confirmed again in this story's validation: 0 findings after the md5 change).

### How a finding is triaged

1. Read it: the rule's page (the log prints a `https://sg.run/...` link), the line, and what reaches it.
2. If the code is wrong or unclear, change the code. This is the usual outcome.
3. If it is a verified false positive, mark the line with `# nosemgrep: <full-rule-id> — <reason>` under the rule in `project-context.md`. The reviewer checks the claim.
4. If a pack produces false positives again and again, do not collect comments: report it to the maintainer, who decides about the pack list (Epic 20 ADR-7 decision 5).

Where a finding shows up:

- **In a pull request:** the `Semgrep` job fails and its log names rule, file and line. Reproduce locally with `just semgrep --baseline-commit origin/main` (fetch first, and commit your work first: semgrep's help says a baseline scan aborts on unstaged changes).
- **On `main`:** Security > Code scanning, filter `tool:"Semgrep OSS"`. An alert opens when a full scan reports a finding (for example after the registry adds a rule) and closes by itself as "fixed" when a later scan of `main` no longer reports it. Nothing is blocked by an open alert; someone has to look. Semgrep's SARIF carries its own severity (shown as Error, Warning or Note), not a CVSS score.
- **A moved file:** the pull request scan matches findings by file path, so moving a file that has a marked or known finding can report it as new. Treat it as steps 1 to 3.
- **A registry outage** makes the scan exit 2 and fails the job on a pull request. Re-run the job; do not weaken the step.

### Measurements

Measured in this story's validation at 7f04ea2, on an Apple Silicon laptop, semgrep 1.185.0, without a login (what CI has), with the script and the ignore file above:

| | Rules fetched | Rules run | Files | Findings | Engine errors | Skipped rules |
|---|---|---|---|---|---|---|
| All six packs | 290 | 280 | 228 | 1 (md5), 0 after Task 3 | 0 | 0 |
| `p/python` | 151 | 151 | 61 | 1, then 0 | 0 | 0 |
| `p/typescript` | 74 | 74 | 152 | 0 | 0 | 0 |
| `p/react` | 4 | 4 | 152 | 0 | 0 | 0 |
| `p/secrets` | 43 | 43 | 228 | 0 | 0 | 0 |
| `p/github-actions` | 11 | 11 | 2 | 0 | 0 | 0 |
| `p/dockerfile` | 7 | 7 | 3 | 0 | 0 | 0 |

Wall clock: 3.3 to 3.5 s for the full scan once uv has semgrep cached, about 7 s more the first time. A baseline scan of a branch with one changed file: 2.6 s. Expect well under a minute on the runner, most of it the download.

To repeat the per-pack row (Task 1.6), one pack at a time, writing the JSON outside the repository:

```bash
SEMGREP_SETTINGS_FILE=/dev/null uvx semgrep==1.185.0 scan --metrics=off --config p/python \
  --json-output="$TMPDIR/semgrep-python.json" api/src web/src .github Dockerfile scripts
yq -p json -o json '{"errors": (.errors | length), "skipped": (.skipped_rules | length)}' "$TMPDIR/semgrep-python.json"
```

This is a measurement, not a second way to run the scan; nothing in the repository calls `uvx semgrep` except the script. "Rules the engine could not run" (AC 13) is `.errors` plus `.skipped_rules`. On the runner, record the job's duration and the log's "Ran N rules on M files" line (Task 6.3); the per-pack numbers are recorded locally, where the rules are the same because the login is ignored. If the runner's rule count differs from the local one, record both and say so.

### The gate proof (Task 6.4)

The temporary commit adds one file, `api/src/vintagestory_api/services/semgrep_gate_probe.py`:

```python
import hashlib


def digest(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()
```

Prototyped at 7f04ea2: `just semgrep --baseline-commit <merge base>` reports one finding, rule `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5`, in that file at line 5, exit 1, and does not report the old finding in `server.py`. Ruff and Pyright accept the file, and nothing imports it, so the other jobs stay green and only `Semgrep` fails. Do not use a line that looks like a credential to trigger `p/secrets`: the repository is public.

Both commits are `ci(story-20.4/task-6)` and stay in the history (the project merges without squashing); the type keeps them out of the release notes. The file must not exist at the tip that is reviewed and merged (Task 6.5), and `git grep -n semgrep_gate_probe` must be empty there.

### Existing tests that change (deliberately)

- `scripts/tests/test-release.sh:322`: the expected job list and the assertion's name (five becomes six). Nothing else in that file.
- New: `scripts/tests/test-semgrep.sh`. `just test-scripts` gains one file.
- If Story 20.3's argument test is list-driven, `semgrep` joins its list.
- No pytest test and no Vitest test changes. `api/tests/server/test_install.py` passes unchanged with the keyword argument (prototyped: `just test-api tests/server`, 260 passed; Pyright 0 errors on `server.py`; Ruff clean).
- `scripts/tests/test-docker-context.sh` and `scripts/tests/test-e2e-ci.sh` pass unchanged with the new job (prototyped).

### Not changed (do not "fix" these here)

- `just lint`, `just check`, `just test`, `just test-api`, `just test-web` and the `api`, `web`, `scripts`, `docker` and `e2e` jobs. Semgrep joins none of them (ADR-6 decision 8).
- `release.yml`. No scan runs on a tag.
- `.mise.toml`, `api/pyproject.toml`, `api/uv.lock`, `web/package.json`, `web/bun.lock`. Semgrep is not a project dependency.
- The pack list. Not `p/default`, `p/security-audit` or `p/owasp-top-ten`, and no rule written for this repository. If a pack looks too noisy or too thin, report it.
- `verify_checksum`'s name, signature, log events and callers, and the `md5` field of the version models. The vendor publishes MD5; the algorithm does not change.
- `tar.extractall` at `server.py:690`: no comment (ADR-7 decision 8).
- The two `unsafe-formatstring` hits `p/default` reports in `web/src/hooks/use-console-websocket.ts` and `use-log-stream.ts`: `p/default` is not used, so they are not findings of this scan.
- Secret scanning and push protection in the repository settings (the maintainer's decision, named in the change proposal).
- Branch protection, and making `Semgrep` a required check.
- `.dockerignore`: `.semgrepignore` and `scripts/` in the build context change nothing in the image (the Dockerfile copies named paths).

### API contract changes

None. No endpoint, field, status or error code changes. `hashlib.md5(usedforsecurity=False)` returns the same digest, so the install flow and its `CHECKSUM_MISMATCH` error path (`server.py:817-821`) behave as before. The story adds a script, an ignore file, a recipe, a Renovate rule, a workflow job, a script test and documentation.

### E2E and manual browser check

No E2E task and no manual browser check: nothing an admin sees or does changes, and no page, route or API answer differs. The proof is `test-semgrep.sh`, the existing checksum tests, the three recorded pull request runs (pass, fail on the temporary finding, pass) and the two manual runs of Task 6. Do not start the dev stack for this story.

The one manual check is the maintainer's, after the merge (AC 15): Security > Code scanning shows the tool `Semgrep OSS` with an analysis of `main`. Because the only finding is fixed in this story, the expected number of open alerts is zero; "no alerts" with the tool listed is the pass. Task 6.4 is what shows an alert actually being created (on the branch's ref, closed again by Task 6.5).

### ADR against the code

1. **The planning measurements were taken with a semgrep login, and CI has none.** The architecture's facts say 229 files in 56 s with 745 engine messages, 739 of them "rules that need the Pro engine". On the maintainer's machine `semgrep login` is active; with it the registry serves 1,603 rules for the six packs (1,313 marked "Pro rules") and the community engine cannot run many of them. Without a login, which is what the runner has, the same command fetches 290 rules, runs 280, takes about 3 s and reports 0 engine errors. The finding is the same one either way. Consequence for the design: `just semgrep` on a logged-in machine and the CI job would scan with different rules, which ADR-6 decision 1 ("the two places cannot drift apart") rules out. The script therefore ignores the login (AC 14). The ADR's time budget (five minutes) is met with a wide margin.
2. **ADR-7 decision 2 says `--error`, decision 3 says the full scan does not fail, and ADR-6 says one script.** `--error` and `--no-error` cannot both be passed, so the script has a report-only switch (`SEMGREP_REPORT_ONLY=1`) instead of an argument.
3. **ADR-6 decision 6 says the scan "exits non-zero on a finding" with no arguments.** True only with `--error`; plain `semgrep scan` exits 0. The script adds it.
4. **ADR-6 decision 5's exclusions do not add to semgrep's defaults, they replace them,** and `web/src/test/` is added under "anything else that only holds tests".
5. **The epic's manual check expects alerts after the first run on `main`.** With the md5 finding fixed there are none; the check is that the analysis is listed (AC 15), and the alert path is proved on the branch (Task 6.4).
6. **ADR-7 decision 6's comment form is not enforced by semgrep** (a bare `nosemgrep` works). A script test enforces it (AC 12).

None of these changes a decision the maintainer made; 1 and 2 add a mechanism the decisions need.

### Decisions for the maintainer

Each is written into the story and can be reversed in review:

1. `just semgrep` ignores a local `semgrep login`, so local and CI results match (AC 14). The alternative keeps the larger logged-in rule set locally and accepts that the two differ.
2. One job holds both the pull request scan and the upload, so `security-events: write` is also present on pull requests from branches of this repository. A seventh job for the upload would narrow it and change the job list the epic fixed at six.
3. The gate proof leaves two `ci` commits in the history (add and remove a probe file), as the epic's task describes. The alternative is a throwaway pull request that is closed unmerged.
4. `timeout-minutes: 10` on the job.
5. The exception text says no tracking issue is needed for a marked false positive, unlike the general rule's three conditions.
6. Renovate will open a pull request for each semgrep release it sees (several a week); no schedule or grouping is added here.

### Testing Requirements

- Tests are written with the task, red first: groups A to C with Task 1, D with Task 2, E with Task 4, F with Task 5. Each task ends with `just test-scripts` and `just lint-scripts`; Task 4 also with `just lint-workflows`; Task 3 with `just test-api tests/server`, `just typecheck-api` and `just lint-api`.
- `test-semgrep.sh` must pass with no network and must never call the real `uvx` (the stub is first on `PATH`; if the stub was not called, the test fails rather than falling through).
- The real scan is run by hand in Tasks 1.6, 1.7, 3.3 and 6.1 and by CI. Write semgrep's JSON or SARIF output outside the repository, or delete it before committing.
- No lint or type suppression, no `cast`, no skipped test. The only `nosemgrep` text the story adds is in documentation and in the test that checks the form.
- A completion note must be true of the code: record counts, times and run URLs as they were, including a first run that failed.

### Security Requirements

- No secret anywhere: the job reads none, semgrep runs without a token, and metrics are off.
- The job is the only holder of `security-events: write`; it does not use `pull_request_target`; it interpolates no pull request text into a shell step.
- The scan can be weakened by editing `scripts/semgrep.sh`, `.semgrepignore` or the job in a pull request. Those edits are visible in the diff, and reviewers should treat a change to any of the three as a change to the gate.
- Semgrep is pinned by version, not by digest, and uv resolves its dependencies at install time (accepted in ADR-6 decision 2). It reads the source and writes a report; it gets no secret and no write permission other than code scanning results.
- The SARIF and the job log are public on a public repository. `p/secrets` prints the matching line, so a real secret that reaches a pull request is shown in the log: that is a leak that already happened with the push, and the secret must be rotated, not hidden.

### Development Commands

- `just semgrep`, `just semgrep --baseline-commit origin/main`, `SEMGREP_REPORT_ONLY=1 just semgrep --sarif-output="$TMPDIR/semgrep.sarif"`.
- `just test-scripts test-semgrep.sh`, `just test-scripts test-release.sh`, `just lint-scripts`, `just lint-workflows`.
- `just test-api tests/server`, `just typecheck-api`, `just lint-api`, then `just check`.
- After Story 20.1, run `ruff format` on `services/server.py` after the change (the line stays well under the 100-character limit, so expect no reformatting). Do not run `just format-web`.
- Do not run Docker recipes or the E2E suite for this story.

### Previous Story Intelligence

- **20.1** formats the API. Line 650 of `server.py` may move; find the line by `hashlib.md5(`, which occurs once under `api/src`. From 20.1 on, `just lint-api` also checks the format.
- **20.3** gives recipes positional arguments, makes `just lint-scripts` use globs (`scripts/*.sh scripts/tests/*.sh`), and adds a script test for argument passing. Read its Completion Notes for the recipe form and the test's name before Task 1.4. It also removes the tracked Playwright report files, so nothing needs restoring after a run.
- **19.7** added the `e2e` job, `scripts/e2e-ci.sh` and `test-e2e-ci.sh`; this story follows its patterns (a script behind a recipe, a guard test that pins the workflow with `yq`, a manual run with `gh workflow run ci.yml --ref <branch>` when a branch is stacked). Its review added a guard that fails on the old script: write each assertion so that it fails on the code before the change.
- **15.x and commit `af7b936`** added the release-commit skip and the job-list guard in `test-release.sh`. A job without the `if:` would run on the release commit; the guard is what stops that.
- **17.x to 19.x reviews:** a `feat` or `fix` subject must describe something an admin can see (none here); a completion note must be true of the code; tests must not write into `dev/` (this story's tests write only under `make_tmp`).

### Git Intelligence

- Base `7f04ea2` (`docs(epic-20): record the maintainer's answers and use a mod database address setting`). Stories 20.1 to 20.3 land first.
- Planned commits: Task 1 `build(story-20.4/task-1): just semgrep scans the source with a pinned semgrep`. Task 2 `build(story-20.4/task-2): renovate keeps the semgrep version current`. Task 3 `refactor(story-20.4/task-3): mark the download checksum as not a security use`. Task 4 `ci(story-20.4/task-4): scan pull requests and main with semgrep`. Task 5 `docs(story-20.4/task-5): the nosemgrep exception and the semgrep command`. Task 6 `chore(story-20.4/task-6): validate and move story 20.4 to review`, then the two temporary `ci(story-20.4/task-6)` commits of the gate proof.

### Project Structure Notes

- New: `scripts/semgrep.sh` (executable), `.semgrepignore`, `scripts/tests/test-semgrep.sh`.
- Modified: `Justfile`, `renovate.json`, `.github/workflows/ci.yml`, `scripts/tests/test-release.sh`, `api/src/vintagestory_api/services/server.py` (one line), `project-context.md`, `CLAUDE.md`, `README.md`.
- Added and removed again within the story: `api/src/vintagestory_api/services/semgrep_gate_probe.py`.
- `semgrep.sarif` is written only on the runner. Do not add it to `.gitignore`: locally the output goes outside the repository.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.4: Semgrep Locally and in CI]
- [Source: _bmad-output/planning-artifacts/prd.md] FR244, FR245, FR246, FR247
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md#ADR-6, #ADR-7, #ADR-5 (decisions 1, 2 and 4), "Facts Checked in the Code" (CI, Semgrep)]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md] (section 2, the semgrep row and the risks for 20.4; section 5, question 1)
- [Source: project-context.md#8. No Silent Failures Rule, #Commit Message Format]
- [Source: _bmad-output/implementation-artifacts/19-7-e2e-runs-in-ci.md] (the job, the guard test and the manual run)
- Beads: `VSS-djg`, `VSS-4ac`, parent `VSS-lzgg`; maintainer rules `bd memories semgrep-exceptions`, `bd memories backlog-drawdown`

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- **Task 1.1 red:** `test-semgrep.sh` 12/22 before the script, ignore file and recipe existed (the 12 that passed are vacuous or C's "not in check/lint/test" checks); `test-justfile-args.sh` 40/42 with the new `semgrep|--baseline-commit|a b` case (`error: justfile does not contain recipe`). After 1.2-1.4: 23/23 and 42/42.
- **Task 1.6, `just semgrep --json-output=<scratch file>`** at c085e2f's tree: exit 1, "Ran 280 rules on 226 files: 1 finding." (290 Code rules fetched, all "Community"), the finding `python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5` at `services/server.py:652`. JSON: `.errors` 0, `.skipped_rules` 0, `.paths.scanned` 226 (web 154, api 62, scripts 7, `.github` 2, `Dockerfile` 1), none matching `\.test\.|/tests?/|/__tests__/|/mocks?/`. "Files matching .semgrepignore patterns: 145". Wall clock 6.4 s through `just` and `mise` (semgrep already in uv's cache).
- **Task 1.6 per pack** (the Dev Notes command, JSON outside the repository; "fetched" is the "Scanning N files ... with M Code rules" line):

  | Pack | Rules fetched | Rules run | Files | Findings | `.errors` | `.skipped_rules` |
  |---|---|---|---|---|---|---|
  | `p/python` | 151 | 151 | 61 | 1 | 0 | 0 |
  | `p/typescript` | 74 | 74 | 150 | 0 | 0 | 0 |
  | `p/react` | 4 | 4 | 150 | 0 | 0 | 0 |
  | `p/secrets` | 52 | 43 | 226 | 0 | 0 | 0 |
  | `p/github-actions` | 12 | 11 | 2 | 0 | 0 | 0 |
  | `p/dockerfile` | 7 | 7 | 3 | 0 | 0 | 0 |

  Rules the engine could not run (AC 13: `.errors` + `.skipped_rules`): 0 for every pack. The fetched-vs-run gaps for `p/secrets` and `p/github-actions` are rules for languages with no target file, not engine errors.
- **Task 1.7:** after committing Task 1, `git fetch origin main` (3f1c6ea) and `just semgrep --baseline-commit origin/main`: "Current version has 1 finding.", "Creating git worktree from 'origin/main' to scan baseline.", "Scan was limited to files changed since baseline commit.", "Ran 280 rules on 29 files: 0 findings.", exit 0, 6.9 s. Semgrep removed its temporary worktree (`git worktree list` unchanged).
- **Task 2.1 red:** `test-semgrep.sh` 27/30 (the three renovate.json assertions). The first draft's `git grep ... ':!_bmad-output'` failed with "Unimplemented pathspec magic '_'" and the assertion still passed because the error was swallowed; it now uses `:(exclude)...` and also asserts git grep's exit status is 1 (nothing found). 30/30 after 2.2.
- **Task 2.3, Renovate validator** (`mise exec -C web -- bunx --package renovate renovate-config-validator`, Renovate 44.251.0): without flags it validated the file "as global config"; with `--no-global`, "Validating ../renovate.json as repo config", "Config validated successfully", exit 0, no warning. A copy using `fileMatch: ["^scripts/semgrep\\.sh$"]` instead gave "WARN: Config migration necessary" with a diff, so `managerFilePatterns` is the current name. The `local>` preset produced no warning (the validator does not resolve presets). `web/package.json` and `web/bun.lock` compared byte-identical afterwards.
- **Task 3:** `just test-api tests/server` 260 passed; `just typecheck-api` 0 errors, 0 warnings; `just lint-api` "All checks passed!", "157 files already formatted"; `ruff format --check` on `server.py` "1 file already formatted". `just semgrep`: "Ran 280 rules on 226 files: 0 findings.", exit 0, 4.6 s.
- **Task 4.1 red:** `test-semgrep.sh` 33/45 (the 12 job assertions), `test-release.sh` 132/133 ("ci.yml has its six jobs"). After 4.2: 45/45 and 134/134; `just lint-workflows` and `just lint-scripts` pass; `test-docker-context.sh` 6/6 and `test-e2e-ci.sh` 18/18 unchanged. `just semgrep` with the new job staged (`.github` is in scope): 0 findings.
- **codeql-action pin:** `gh api repos/github/codeql-action/git/ref/tags/v4.39.3` is an annotated tag object `f3bbb05...` that peels to commit `33d7b85da1a04171e211befe2c739303b9a4c066`; v4.39.3 is still the newest v4 tag.
- **Task 5.1:** group F passed from the start (47/47). Proof: a bare `# nosemgrep` appended to the `server.py` md5 line made it fail (46/47, the line printed); the full form `# nosemgrep: python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5 — a reason` passed; the file was restored (`git status --short` clean).
- **Gate probe check (for Task 6.4, not committed to this branch):** in a detached scratch worktree outside the repository, a throwaway commit adding `api/src/vintagestory_api/services/semgrep_gate_probe.py` (Dev Notes "The gate proof"): `scripts/semgrep.sh --baseline-commit $(git merge-base origin/main HEAD)` exit 1, "Ran 280 rules on 30 files: 1 finding.", the md5 rule in that file at line 5 (`return hashlib.md5(data).hexdigest()`), and not the old `server.py` finding. `SEMGREP_REPORT_ONLY=1 ... --sarif-output=<scratch>` exit 0, "Ran 280 rules on 227 files: 1 finding.", SARIF tool `Semgrep OSS` with 1 result. Ruff check, Ruff format check and Pyright accept the file. The worktree was removed.
- **Task 6.1:** `just check` exit 0: Ruff clean, format clean, Pyright 0 errors and 0 warnings, API 3334 passed, web 3307 passed in 132 files (none skipped), script tests all pass (`test-semgrep.sh` 47/47, `test-release.sh` 134/134, `test-justfile-args.sh` 42/42). `just semgrep` exit 0, 0 findings. `api/pyproject.toml`, `api/uv.lock`, `web/package.json`, `web/bun.lock` and `.mise.toml` have no diff; no rule file is tracked; the only added `nosemgrep` text is in `project-context.md` and `test-semgrep.sh`; no suppression, `cast` or skip added; `git status --short` empty.

### Completion Notes List

- **Task 1 (VSS-djg):** `scripts/semgrep.sh` and `.semgrepignore` are the Dev Notes text unchanged. The `semgrep *ARGS` recipe sits after `lint-workflows` under its own `# SECURITY SCAN` section, with `[positional-arguments]` and `mise exec -- ./scripts/semgrep.sh "$@"`; it is not a dependency of any recipe. `test-justfile-args.sh` gained the case `semgrep|--baseline-commit|a b`. `just lint-scripts` already globs `scripts/*.sh scripts/tests/*.sh`, so it covers the new files with no edit. `test-semgrep.sh` groups A to C as specified; group C checks `--dry-run` of `check`, `lint`, `test`, `test-api` and `test-web` (not only `check`).
- **The `SEMGREP_SETTINGS_FILE=/dev/null` export is unconditional** as written; it is untested on the Linux runner until the PR's first run (Task 6.3).
- **`--metrics=off`:** the default output does not print the "Not sending pseudonymous metrics" line the Dev Notes mention; the flag's presence is asserted by `test-semgrep.sh` group A.
- **Counts differ from the story's 7f04ea2 numbers** because Story 20.2 removed web source files: 226 files scanned (story: 228), 145 skipped by `.semgrepignore` (story: 143), web 154 (story: 156). Rules run are the same (280). `p/secrets` and `p/github-actions` fetch 52 and 12 rules and run 43 and 11 (the story's table lists fetched = run).
- **Task 2 (VSS-djg):** `customManagers` as in Dev Notes, before `packageRules`; the two package rules are unchanged. Field name `managerFilePatterns` confirmed by the validator (see Debug Log). Group D as specified, plus an assertion that the `git grep` for pins exits 1.
- **Task 3 (VSS-4ac):** one line, `hashlib.md5(usedforsecurity=False)` at `services/server.py:652` (was `:650` before Story 20.1). No test changed, no `nosemgrep`.
- **Task 4 (VSS-4ac):** the job is the Dev Notes text, appended after `e2e`; the pins for checkout and mise-action match the other jobs. The workflow and the `test-release.sh` job list are one commit.
- **Task 5 (VSS-4ac):** the exception text is in `project-context.md` section 8 after the forbidden-patterns list and the E2E precondition-skip sentence Story 20.2 added, before "Good Example". One line in `CLAUDE.md` and one line plus one sentence in `README.md`. Task 5.4 (the triage steps in the PR description) is the controller's, since the dev agent opens no PR; unticked.
- **Script test counts:** `test-semgrep.sh` 47 (new), `test-justfile-args.sh` 42 (40 before), `test-release.sh` 134 (133 before), others unchanged: changelog 23, check-coverage 13, docker-context 6, e2e-ci 18, release-notes 12, sprint-status 57, version 23.
- **No E2E or dev-stack run:** the story rules them out (nothing an admin sees changes; no spec added or changed).
- **Left for the controller and maintainer:** Tasks 5.4 and 6.3 to 6.7 (push, PR, the first CI run and its duration, the gate proof, the manual `workflow_dispatch` runs, bead links and AARs, AC 15). By the controller's decision the gate proof is a separate throwaway pull request, not two commits on this branch; this branch has no probe commit.
- No API contract change, no new dependency, no `feat`/`fix` commit.
- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist at 7f04ea2. Prototypes, all discarded: `scripts/semgrep.sh` and `.semgrepignore` (ShellCheck passed; full scans with and without a login; a baseline scan over two temporary commits; SARIF output; exit codes), the stub `uvx` test, the scanned-set tripwire, the `semgrep` job appended to `ci.yml` (`just lint-workflows` passed; `just test-scripts` failed only on `test-release.sh`'s job list), the md5 keyword (`just test-api tests/server` 260 passed, Pyright and Ruff clean, semgrep 0 findings), the Perl check of the Renovate pattern, and the `nosemgrep` forms on a file outside the repository. Not run: the Renovate validator, and anything on a GitHub runner; the job's duration, the upload and the code scanning view are predictions until Task 6.

### File List

- `scripts/semgrep.sh` (new, executable)
- `.semgrepignore` (new)
- `scripts/tests/test-semgrep.sh` (new)
- `scripts/tests/test-justfile-args.sh`
- `scripts/tests/test-release.sh`
- `Justfile`
- `renovate.json`
- `api/src/vintagestory_api/services/server.py`
- `.github/workflows/ci.yml`
- `project-context.md`
- `CLAUDE.md`
- `README.md`
- `_bmad-output/implementation-artifacts/20-4-semgrep.md`

## Change Log

- 2026-11-17: Story 20.4 created and validated (ready-for-dev).
- 2026-11-17: Story 20.4 implemented (Tasks 1-5, 6.1-6.2); gate proof left to a throwaway pull request by the controller; moved to review.
