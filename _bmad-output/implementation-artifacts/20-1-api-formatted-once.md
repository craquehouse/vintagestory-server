# Story 20.1: The API Is Formatted Once and Stays Formatted

Status: ready-for-dev

<!-- Implements FR234-FR236 and Epic 20 ADR-1. Beads: VSS-3asx (TOOLS-006), the formatting half only; the type-check half and closing the bead are Story 20.3. First story of Epic 20 (order 20.1 to 20.7, each stacked on the previous); it merges before any other implementation branch of the epic is cut. Line references were verified at 7f04ea2 (epic-20-planning; its api/, Justfile, scripts/, README.md and .github/ are identical to 3f1c6ea, the commit the ADRs cite) and must be re-checked at implementation time. Tooling and documentation only: no API behavior, web, Docker or E2E change. No new dependency. -->

## Story

As a **developer**,
I want **the whole API in the formatter's form and a check that keeps it there**,
so that **formatting a file I work on never adds changes that are not mine**.

## Acceptance Criteria

1. **Given** the API source and tests
   **When** `ruff format --check` runs over `api/`
   **Then** it reports no file that would be reformatted (`157 files already formatted` at the base commit's file count)
   *(Covers FR234)*

2. **Given** the format commit
   **When** I read it
   **Then** it holds only what `ruff format` wrote with the existing configuration (`line-length = 100`, `api/pyproject.toml:36`): only `api/**/*.py` files, no hand edit, no lint fix, no configuration change, and its subject is exactly `chore(story-20.1/task-1): format the API with ruff format`
   *(Covers FR234; Matt, 2026-11-17)*

3. **Given** the format commit's parent
   **When** a reviewer runs the same `ruff format` on it (`just build-api` then `just format-api`, which use the ruff that `api/uv.lock` pins)
   **Then** the resulting tree is identical to the format commit's tree (`git diff --exit-code <format-commit>` prints nothing and exits 0)
   *(Covers FR234)*

4. **Given** the API tests, `ruff check` and Pyright
   **When** they run before and after the format commit
   **Then** the results are the same: the same number of tests pass and none fails or is skipped, `ruff check` reports no finding, Pyright reports 0 errors and the same 3 known warnings (`VSS-1ar`, at new line numbers), and no `# noqa`, `# fmt:` or `# type:` comment was added
   *(Covers FR234)*

5. **Given** `just lint-api`
   **When** it runs
   **Then** it runs `ruff check` and then `ruff format --check`, and it exits non-zero when any API file is not formatted; arguments given to the recipe (`just lint-api --fix`) still reach `ruff check` only
   *(Covers FR235)*

6. **Given** a pull request that contains an unformatted API file
   **When** CI runs
   **Then** the `api` job fails at its `just lint-api` step, with no change to `.github/workflows/ci.yml`; `just check` fails the same way through `just lint`
   *(Covers FR235)*

7. **Given** the repository root
   **When** I read `.git-blame-ignore-revs`
   **Then** it names the format commit's full 40-character hash under a comment line that says what the commit is, and it was added in a separate commit of the same pull request (Task 2)
   *(Covers FR236)*

8. **Given** a fresh worktree set up with `scripts/worktree-setup.sh`
   **When** I run `git blame` on a line the format commit changed
   **Then** the format commit is skipped (blame names the commit before it), `git blame` still works on a branch that has no `.git-blame-ignore-revs`, and the README says which git setting does that and that GitHub's blame view reads the file by itself
   *(Covers FR236)*

9. **Given** the epic's branches
   **When** Story 20.1's pull request merges
   **Then** it is merged with a merge commit like every other (no squash, no rebase), no other implementation branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main` (`git merge-base --is-ancestor <hash> origin/main` exits 0)
   *(Covers FR236; Matt, 2026-11-17)*

10. **Given** every existing test, lint and type check
    **When** `just check` runs on the branch
    **Then** it passes; no test changes; no test run writes into the dev data directory (`dev/`); none of the story's commits appears in `just changelog`

## Tasks / Subtasks

<!-- Commit per task: type(story-20.1/task-N): ...; no feat/fix/perf in this story (nothing a user can see). Task 1's commit holds formatter output only; anything else found during it goes into Task 2 or 3, or into a follow-up. -->

- [ ] Task 1: Reformat the API in one commit + before/after checks (AC: 1, 2, 3, 4) (`VSS-3asx`)
  - [ ] 1.1: Base: the branch is cut from `main` after the Epic 20 planning pull request has merged (`git switch -c story/20-1-api-formatted-once origin/main`). `git status --short` is empty. `just build-api` (syncs the locked ruff, 0.17.5 at 7f04ea2; record `mise exec -C api -- uv run ruff --version` in the Debug Log, as the reviewer needs the same one)
  - [ ] 1.2: Baseline, recorded in the Debug Log: `mise exec -C api -- uv run ruff format --check . | tail -1` (75 would be reformatted, 82 already formatted at 7f04ea2); `just lint-api` ("All checks passed!"); `just typecheck-api` (`0 errors, 3 warnings`, with their file:line); `just test-api` (3334 passed at 7f04ea2). The suite needs `VS_API_KEY_ADMIN` set: a worktree set up with `scripts/worktree-setup.sh` has it in `.env`; otherwise prefix `VS_API_KEY_ADMIN=ci-placeholder-key` as CI does (`ci.yml:23-25`). Without it 87 tests error with `VS_API_KEY_ADMIN must be set`
  - [ ] 1.3: Run `just format-api` and nothing else. Not `just format`: it also runs an unpinned Prettier over `web/src` (`Justfile:186`, `:193-194`), which rewrites 279 web files (ADR-1 decision 7)
  - [ ] 1.4: Check the change is formatter output only: `git status --short` lists only ` M api/...py` lines (75 at 7f04ea2: 23 under `api/src`, 52 under `api/tests`); `git diff --shortstat` (663 insertions, 1466 deletions at 7f04ea2); `git diff -U0 | grep -E '^\+.*# (noqa|fmt:|type:)'` prints nothing; `mise exec -C api -- uv run ruff format --check .` now reports `157 files already formatted`
  - [ ] 1.5: After, same commands as 1.2: `just lint-api` clean; `just typecheck-api` `0 errors, 3 warnings`, the same three `reportUnknownVariableType` warnings (at 7f04ea2 they move from `test_mod_service.py:1640`, `:1719` and `test_mods_router.py:3099` to `:1627`, `:1704` and `:3046`); `just test-api` the same count, 0 failed; `git status --short` shows nothing under `dev/`. If any result differs, stop and report it (ADR-1 decision 6); do not edit code inside this commit and do not add a `# noqa`
  - [ ] 1.6: `git add api && git commit` with the subject `chore(story-20.1/task-1): format the API with ruff format` and a body that names the command and the version (`just format-api`, ruff 0.17.5 from api/uv.lock, line-length 100 unchanged) and the counts from 1.4. Record the full hash (`git rev-parse HEAD`) in the Debug Log

- [ ] Task 2: `git blame` skips the format commit + verification (AC: 7, 8) (`VSS-3asx`)
  - [ ] 2.1: New `.git-blame-ignore-revs` at the repository root (Dev Notes "The ignore file"): a comment line, then the full hash from 1.6 on its own line. Nothing else in the file
  - [ ] 2.2: `scripts/worktree-setup.sh`: a block before "Installing dependencies..." (`:89-91`) that sets `blame.ignoreRevsFile` with the `:(optional)` prefix when this Git supports it, and otherwise prints the command to run by hand (Dev Notes "The git setting"). Add item 3 to the header comment (`:5-7`). `just lint-scripts` passes (the script is in its list, `Justfile:153`)
  - [ ] 2.3: `README.md` "Install development tools" (`:90-97`): one short paragraph after `:97` (Dev Notes "README")
  - [ ] 2.4: Verify in a throwaway worktree (Dev Notes "Verifying blame"): run `scripts/worktree-setup.sh` there, `git blame` a joined line in a reformatted file and see the commit before the format commit; with `--ignore-revs-file ''` the format commit shows. Then `git blame` any file in a worktree whose branch has no `.git-blame-ignore-revs` (for example `git worktree add --detach <tmp> <format-commit>^`) and see it work. Remove the throwaway worktrees (`git worktree remove`); leave the git setting in place. Record the commands and what blame showed in the Debug Log
  - [ ] 2.5: Commit `chore(story-20.1/task-2): skip the API format commit in git blame`

- [ ] Task 3: `just lint-api` checks the format + red/green proof (AC: 5, 6)
  - [ ] 3.1: `Justfile` `lint-api` (`:143-145`): a second line `mise exec -C api -- uv run ruff format --check .` after the `ruff check . {{ARGS}}` line, without `{{ARGS}}` (Dev Notes "The recipe"). Comment: `# Lint API (ruff check, then ruff format --check) - optional args go to ruff check`
  - [ ] 3.2: Command lists: `CLAUDE.md:145` and `project-context.md:537` (`just lint-api --fix`): say it lints and checks the format, for example `# Lint API (ruff check + format check), auto-fix lint`. Add `just format-api  # Format the API (ruff format); just lint-api checks it` above `just format` in both formatting lists (`CLAUDE.md:159-160`, `project-context.md:545`). Do not change the `just format` lines or the recipe (Dev Notes "Not changed")
  - [ ] 3.3: Red/green: add two blank lines inside a function of one API test file (for example after the docstring of a test in `api/tests/test_health.py`; any file works), run `just lint-api`: it exits non-zero, `ruff check` passes first and `ruff format --check` names that file. Restore it with `git checkout -- <file>`; `just lint-api` passes; `just lint-api --fix` passes. Record the outputs' last lines in the Debug Log. No file of the red step is committed
  - [ ] 3.4: `.github/workflows/ci.yml` is not changed: the `api` job already runs `just build-api` then `just lint-api` (`ci.yml:29-30`), and `just check` reaches `lint-api` through `lint` (`Justfile:141`, `:179`). `git diff --stat origin/main -- .github` is empty
  - [ ] 3.5: Commit `chore(story-20.1/task-3): check the API's format in just lint-api`

- [ ] Task 4: Quality gate and review hand-off (AC: all)
  - [ ] 4.1: `just check` passes: ruff clean and formatted, Pyright 0 errors and the 3 known warnings (`VSS-1ar`), API tests as in 1.2, web 3349 passed and 4 skipped (`VSS-hnl`, Story 20.2's), script tests green. The diff adds no lint or type suppression and no `cast`. After the API suite `git status --short` shows nothing under `dev/`. `just changelog` shows none of this story's commits
  - [ ] 4.2: Reproduce the format commit as the reviewer will (AC 3, Dev Notes "Reproducing the format commit") and record the result in the Debug Log. Confirm the commit holds only `api/**/*.py`: `git show --name-only --format= <hash> | grep -v '^api/.*\.py$'` prints nothing
  - [ ] 4.3: Story status `review`, `just sprint set 20-1-api-formatted-once review`, PR to `main`. The PR description has: the format commit's hash and the reproduction steps; the before/after results from 1.2 and 1.5; "API contract changes: none"; "Merge with a merge commit; do not squash or rebase, or the hash in `.git-blame-ignore-revs` is lost"; "Merge before any other Epic 20 implementation branch is cut". Comment the PR link on `VSS-3asx`; the bead stays open (Story 20.3 closes it with the AAR)
  - [ ] 4.4: After the merge (maintainer or orchestrator): `git fetch origin && git merge-base --is-ancestor <hash> origin/main` exits 0 (AC 9), and GitHub's blame view of a reformatted file on `main` shows the line's earlier commit with the notice that revisions in `.git-blame-ignore-revs` are hidden

## Dev Notes

### What the formatter does here (prototype at 7f04ea2, discarded)

- `just format-api` (`Justfile:188-190`, `ruff format .` in `api/`) with ruff 0.17.5 (`api/uv.lock:1359-1360`; `api/pyproject.toml:25` asks for `ruff>=0.14.10`): `75 files reformatted, 82 files left unchanged`; `75 files changed, 663 insertions(+), 1466 deletions(-)`; `api/src` 23 files (+64/-111), `api/tests` 52 files (+599/-1355). The largest diffs: `tests/test_routers_config.py` (204 lines), `tests/test_mods_router.py` (194), `tests/test_mod_api.py` (182), `tests/test_versions_router.py` (147), `tests/test_api_settings.py` (125).
- Mostly joins: code was wrapped near 88 columns, and the formatter joins what fits in 100 (`api/pyproject.toml:35-36`, `[tool.ruff] line-length = 100`; there is no `[tool.ruff.format]` section).
- After it: `ruff check` "All checks passed!" (rules `E`, `F`, `I`, `UP`, `pyproject.toml:38-39`), Pyright `0 errors, 3 warnings` (the same three, lines moved as in Task 1.5), `just test-api` 3334 passed as before, `ruff format --check` `157 files already formatted`, no `# noqa`, `# fmt:` or `# type:` added. There is no `# fmt:` comment anywhere in `api/` today. `git status` showed nothing under `dev/`.
- The numbers are for 7f04ea2. If anything under `api/` lands on `main` before this story starts (for example a Renovate bump of ruff in `api/uv.lock`), the counts change: record the real ones, and the method stays the same.

### Reproducing the format commit (AC 3, Task 4.2, PR description)

```bash
git switch --detach <format-commit>^
just build-api                       # the ruff that api/uv.lock pins
just format-api
git diff --exit-code <format-commit> # nothing printed, exit 0: same tree
git checkout -- api && git switch -  # back to the branch
```

`git diff <commit>` compares the working tree with the commit; the only difference between parent and commit is under `api/`, so an empty diff means the trees are identical. `.ruff_cache/` is ignored (`.gitignore:72`).

### The ignore file (Task 2.1)

```
# chore(story-20.1/task-1): format the API with ruff format (Epic 20 ADR-1)
<full 40-character hash>
```

Git reads the file in the `fsck.skipList` format: one full object name per line, `#` comments allowed (`git help blame`, `--ignore-revs-file`). GitHub's blame view reads `.git-blame-ignore-revs` at the repository root by itself and says it hid revisions (GitHub docs, "Ignore commits in the blame view"); no setting on GitHub. The file is outside the Docker build: the Dockerfile copies only `web/` and `api/` paths (`Dockerfile:20`, `:27`, `:54`, `:61`).

The hash is known only after Task 1's commit exists, which is why it is a second commit. The project merges with merge commits (`CLAUDE.md` "Git Workflow"), so the hash stays valid on `main`. **Do not rebase the branch after Task 2.** If a rebase is unavoidable (the base moved), redo Task 1 on the new base (`just format-api` again, new commit) and update the hash; never edit the old hash by hand to a guess.

### The git setting (Task 2.2)

Verified with Git 2.54 at 7f04ea2:

- A plain `git config blame.ignoreRevsFile .git-blame-ignore-revs` breaks `git blame` on any branch that lacks the file: `fatal: could not open object name list: .git-blame-ignore-revs`. `git config` without `--worktree` writes the shared `.git/config` (this repository has `extensions.worktreeConfig=true`, which only affects `--worktree`), so running the setup in one worktree would break `git blame` in every other worktree still on a branch cut before this story, and in the main checkout until it is merged.
- With the value `:(optional).git-blame-ignore-revs` Git treats the setting as unset when the file does not exist (`git help config`, "pathname": "If prefixed with `:(optional)`, the configuration variable is treated as if it does not exist, if the named path does not exist"). Checked in a scratch repository with a linked worktree: blame works without the file, skips the listed commit with it, and the path is resolved from each worktree's root. Release notes place the prefix in Git 2.52; the script does not depend on the number, it probes.

The block (adapt the messages; keep `set -euo pipefail` happy):

```bash
# git blame skips the commits listed in .git-blame-ignore-revs (the one-time API reformat,
# Story 20.1). ":(optional)" keeps blame working on branches without the file; older Git
# does not know the prefix, so it is only set when this Git accepts it.
echo "Configuring git blame..."
if git -c blame.ignoreRevsFile=':(optional).git-blame-ignore-revs-probe' blame -L1,1 -- README.md >/dev/null 2>&1; then
    git config blame.ignoreRevsFile ':(optional).git-blame-ignore-revs'
    echo "  blame.ignoreRevsFile set"
else
    echo "  This Git does not support ':(optional)'; to skip the format commit in git blame, run:"
    echo "    git config blame.ignoreRevsFile .git-blame-ignore-revs"
fi
```

The probe names a file that never exists: a Git that knows the prefix ignores it and blame succeeds; an older Git fails to open it. Use `README.md` (tracked, at the root, where the script `cd`s at `:21-23`). The script runs in a repository by definition; no other guard is needed.

### README (Task 2.3)

After the paragraph at `README.md:97`, for example:

> `git blame` can skip formatting-only commits, listed in [`.git-blame-ignore-revs`](.git-blame-ignore-revs). GitHub's blame view does this by itself. Locally it needs the git setting `blame.ignoreRevsFile`, which `scripts/worktree-setup.sh` sets; in another clone run `git config blame.ignoreRevsFile ':(optional).git-blame-ignore-revs'` once (the `:(optional)` prefix keeps `git blame` working on branches without the file; on an older Git leave it out).

The README does not mention `scripts/worktree-setup.sh` anywhere today; this sentence is enough, no new section.

### Verifying blame (Task 2.4)

- Pick a line the format commit joined: `git show <hash> -- api/tests/test_routers_config.py | grep -m1 '^+'` gives one; `git blame -L <n>,<n> -- <file>` must not show `<hash>`, and `git blame --ignore-revs-file '' -L <n>,<n> -- <file>` must show it (the empty value clears the list).
- The setup script also runs `just install` and writes `.env` and `web/.env` in that worktree; that is expected. Run it in the throwaway worktree, not in the story worktree, so the story worktree's `.env` is not replaced.
- Do not run it in, or change, any other developer worktree. The setting it writes is shared and harmless (`:(optional)`).

### The recipe (Task 3.1)

```just
# Lint API (ruff check, then ruff format --check) - optional args go to ruff check
lint-api *ARGS:
    mise exec -C api -- uv run ruff check . {{ARGS}}
    mise exec -C api -- uv run ruff format --check .
```

- just runs recipe lines in order and stops at the first failure, so a lint finding is reported before the format check, and the recipe fails if either fails (AC 5).
- `{{ARGS}}` stays on `ruff check` only: `ruff format --check --fix` fails with `unexpected argument '--fix'` (checked). `just lint-api --fix` is documented (`CLAUDE.md:145`, `project-context.md:537`). How `{{ARGS}}` is quoted is Story 20.3's (ADR-5); do not change it here.
- `ruff format --check` prints a diff for each file it would change and exits 1 (ruff 0.17.5 output seen in the prototype), so CI's log shows what to fix. `.` in `api/` is the same scope as `just format-api` (`Justfile:190`); ruff's default excludes leave out `.venv`.
- CI: `api` job steps `just build-api`, `just lint-api`, `just typecheck-api`, `just test-api` (`.github/workflows/ci.yml:29-32`); the workflow is not edited (AC 6). `scripts/tests/test-release.sh:319-325` pins the job list and the `if:` lines only, so no script test changes.

### Commit types and release notes

- Task 1 `chore` (the subject is fixed by AC 2 and ADR-1 decision 1). Tasks 2 and 3 `chore` (tooling, `project-context.md:630`). Story file and bookkeeping `docs`/`chore`. No `style` (the project's type list, `project-context.md:623-631`, has none).
- `cliff.toml:40-49`: only `^feat`, `^fix`, `^perf` and breaking commits make notes; `{ message = ".*", skip = true }` hides everything else. `just changelog` must not list any 20.1 commit (Task 4.1).
- The image's Python files change bytes but not behavior; no release note, no version bump needed for this story alone.

### Existing tests that change

- None. No test reads the format, the `Justfile` `lint-api` line, `.git-blame-ignore-revs` or `scripts/worktree-setup.sh` (`grep -rn "lint-api\|worktree-setup\|blame" scripts/tests/` finds nothing). The API tests are reformatted by Task 1 but not edited; their count and results stay the same (AC 4).

### Not changed (do not "fix" these here)

- `api/pyproject.toml` ruff configuration (`line-length`, rules): ADR-1 decision 1.
- `.github/workflows/ci.yml`: ADR-1 decision 5, AC 6.
- `just format` and `just format-web` (unpinned Prettier over `web/src`, 279 files would change): ADR-1 decision 7. Listed as a follow-up below.
- The three Pyright warnings (`VSS-1ar`, Story 20.2), the four skipped web tests (`VSS-hnl`, Story 20.2), `VSS-6wj`.
- `{{ARGS}}` quoting in recipes (Story 20.3, ADR-5) and the E2E type-check half of `VSS-3asx` (Story 20.3, ADR-4).
- Notes in older story files that say "do not run `just format-api`" (for example `17-7-mods-navigation.md:161`, `18-2-...md` Development Commands): history, left as written. From this story on, `just format-api` is safe (ADR-1 consequences).
- Any lint finding or code smell seen in the diff: not in Task 1's commit. If `ruff check` or a test changes result after the format, stop and report (ADR-1 decision 6).

### ADR against the code

- **ADR-1 decision 4** says a clone needs `git config blame.ignoreRevsFile .git-blame-ignore-revs`, which `scripts/worktree-setup.sh` sets. That exact value breaks `git blame` (fatal error) on every branch without the file, and the setting is shared by all worktrees of the repository, so it would break blame in the other Epic 20 worktrees and in the main checkout until this story merges. The story sets `:(optional).git-blame-ignore-revs` when Git supports the prefix and prints the plain command otherwise (Dev Notes "The git setting"). The outcome ADR-1 asks for (blame skips the commit in a set-up worktree) is unchanged.
- **AC 9 "no other branch of the epic exists yet"**: at story creation the `draft/20-*` branches hold only story files (`_bmad-output/implementation-artifacts/`), which the format commit does not touch. They are not implementation branches; the AC is about branches that change code. Each later story re-checks its line numbers after this merge.
- Everything else in ADR-1 matches the code at 7f04ea2: `just lint-api` runs only `ruff check .` (`Justfile:145`), `just format-api` exists (`:189-190`), no `.git-blame-ignore-revs`, 75 of 157 files unformatted, CI's `api` job runs `just lint-api` (`ci.yml:30`).

### API contract changes

- None. No endpoint, field, error code or behavior changes; the reformat is whitespace, line breaks and quote style only, proven by the unchanged suite (AC 4).

### Testing Requirements

- This story adds no test. Its checks are the before/after comparison (Task 1), the reproduction (Task 4.2), the red/green run of `just lint-api` (Task 3.3) and the blame check (Task 2.4); each is recorded in the Debug Log with the command and its result.
- `just test-api` needs `VS_API_KEY_ADMIN` (Task 1.2). After every API run `git status --short` shows nothing under `dev/`.
- No E2E task: nothing a user or admin can see changes, and no Docker recipe is needed. Do not start the Docker stack or the game server for this story.

### Security Requirements

- No runtime change. The setup script writes one local git setting; it reads no secret and changes nothing outside the repository's `.git/config`. The format commit must not touch any file outside `api/` (Task 4.2).

### Development Commands

- `just build-api`, `just format-api` (Task 1 only, once), `just lint-api`, `just typecheck-api`, `just test-api`, `just lint-scripts`, `just check`, `just changelog`.
- Do not run `just format` (it runs Prettier over the web) or any formatter outside `api/`.

### Previous Story Intelligence

- **17.2, 18.2, 19.5:** earlier stories avoided `just format-api` because it reformatted unrelated code, and formatted only their own lines; 19.5's notes list files `ruff format` would change. This story ends that; after it every story of the epic may run `just format-api` on its files (Epic 20 maintainer rule).
- **18.x/19.x reviews:** a completion note must be true of the code (record measured numbers, not the prototype's); tests must not write into `dev/`; `feat`/`fix` subjects only for what an admin sees (none here); manual checks that need the maintainer stay unticked for the maintainer (4.4 is after the merge).
- **19.7:** the `api` job layout and the `if:` skip on release commits (`ci.yml:20-21`); `test-release.sh` guards the job list, untouched here.

### Git Intelligence

- Base for the story file: `7f04ea2` (`docs(epic-20): record the maintainer's answers and use a mod database address setting`) on `3f1c6ea` (`main`, release `v0.1.0-rc.5`). `git diff 3f1c6ea 7f04ea2 -- api Justfile scripts README.md .github` is empty.
- Planned commits: Task 1 `chore(story-20.1/task-1): format the API with ruff format`; Task 2 `chore(story-20.1/task-2): skip the API format commit in git blame`; Task 3 `chore(story-20.1/task-3): check the API's format in just lint-api`; Task 4 `chore(story-20.1/task-4): move story 20.1 to review` (story file and sprint status).

### Project Structure Notes

- New: `.git-blame-ignore-revs`.
- Modified: 75 files under `api/` (Task 1, formatter only); `scripts/worktree-setup.sh`, `README.md` (Task 2); `Justfile`, `CLAUDE.md`, `project-context.md` (Task 3); this story file.

### Follow-ups (not in this story)

- `just format` runs `just format-web`, an unpinned `bunx prettier --write` over `web/src` that would rewrite 279 files, and `CLAUDE.md`/`project-context.md` list `just format` as "Format all code". Anyone following the docs reformats the web. ADR-1 decision 7 keeps Prettier out of scope; a bead to remove or guard `format-web` (or drop it from `format`) is the maintainer's call.
- A Renovate bump of ruff can change its style (ruff publishes a new style guide yearly); such a pull request then fails `just lint-api` until `just format-api` is run in it. That is the check working; whether such reformat commits also go into `.git-blame-ignore-revs` is a convention to decide later.
- Story 20.2: the `VSS-1ar` warnings move to `test_mod_service.py:1627`, `:1704` and `test_mods_router.py:3046` after this story (measured at 7f04ea2).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.1: The API Is Formatted Once and Stays Formatted]
- [Source: _bmad-output/planning-artifacts/prd.md] FR234, FR235, FR236
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md#ADR-1] and "Facts Checked in the Code" (Lint, type check and recipes; CI)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md] (section 2, answered questions; ADR table)
- Beads: `VSS-3asx` (TOOLS-006), parent `VSS-lzgg` (Epic 20)
- `project-context.md` "Commit Message Format" (`:615-640`), `CLAUDE.md` "Git Workflow", `cliff.toml`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype at 7f04ea2 ran `just format-api` and then `ruff format --check`, `ruff check`, Pyright and the whole API suite (numbers in Dev Notes "What the formatter does here"), and checked `blame.ignoreRevsFile` with and without `:(optional)` in this repository and in a scratch repository with a linked worktree; it was then discarded.

### File List
