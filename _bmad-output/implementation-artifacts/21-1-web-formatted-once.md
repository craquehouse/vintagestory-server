# Story 21.1: The Web Is Formatted Once and Stays Formatted

Status: ready-for-dev

<!-- Implements FR260-FR263 and Epic 21 ADR-1 (maintainer decision 5, Matt, 2026-11-17). Beads: none. First story of Epic 21 (order 21.1 to 21.8, each stacked on the previous); it merges before any other web branch of the epic is cut. Line references were verified at 966204f (epic-21-planning; its web/, Justfile, .github/, README.md, CLAUDE.md and project-context.md are identical to 05436da, the commit the ADRs cite) and must be re-checked at implementation time. Tooling and documentation only: no API or web behavior change, no Docker or E2E change. One new dev dependency (Prettier, approved by the maintainer). -->

## Story

As a **developer**,
I want **the whole web in one formatter's form and a check that keeps it there**,
so that **formatting a file I work on never adds changes that are not mine**.

## Acceptance Criteria

1. **Given** `web/package.json` and `web/bun.lock`
   **When** I read them
   **Then** Prettier is a dev dependency at one exact version (`"prettier": "3.10.1"` at 966204f, no `^` or `~`), the lockfile resolves that version, and the scripts `format` (`prettier --write .`) and `format:check` (`prettier --check .`) run it over the web directory; the old `lint` script (`tsc --noEmit`) is gone
   *(Covers FR261; Matt, 2026-11-17)*

2. **Given** `web/.prettierrc.json`
   **When** I read it
   **Then** it sets `singleQuote: true`, `printWidth: 100` and `trailingComma: "es5"` and nothing else
   *(Covers FR261; ADR-1 decision 2)*

3. **Given** `web/.prettierignore`
   **When** Prettier runs over `web/`
   **Then** it covers the tracked `.ts`, `.tsx`, `.css` and `.json` files in `src`, `e2e`, `tests` and at the top of `web/` (320 files at 966204f with `.prettierrc.json`), and leaves out `e2e/fixtures/`, Markdown and HTML files, `public/`, `dist/`, `coverage/`, `playwright-report*/` and `test-results*/` (`prettier --file-info` reports `"ignored": true` for `e2e/fixtures/moddb/manifest.json`, `e2e/README.md`, `index.html` and `public/config.js`)
   *(Covers FR261; ADR-1 decisions 3 and 4)*

4. **Given** the web sources
   **When** `prettier --check .` runs in `web/`
   **Then** it prints `All matched files use Prettier code style!` and exits 0
   *(Covers FR260)*

5. **Given** the format commit
   **When** I read it
   **Then** it holds only what `prettier --write .` wrote in `web/` with the committed configuration: only `web/**/*.{ts,tsx,css,json}` files, no hand edit, no configuration change, no `// prettier-ignore`, and its subject is exactly `chore(story-21.1/task-2): format the web with prettier`
   *(Covers FR260; Matt, 2026-11-17)*

6. **Given** the format commit's parent (which already holds the dependency, the configuration, the ignore file and the scripts)
   **When** a reviewer runs the same command on it (`just install-web --frozen-lockfile`, then `bun run format` in `web/`)
   **Then** the resulting tree is identical to the format commit's tree (`git diff --exit-code <format-commit>` prints nothing and exits 0)
   *(Covers FR260)*

7. **Given** `just typecheck-web`, `just test-web` and `just build-web`
   **When** they run before and after the format commit
   **Then** the results are the same: the type check exits 0 both times, the same number of tests pass (3307 in 132 files at 966204f) and none fails or is skipped, and the build succeeds
   *(Covers FR260)*

8. **Given** the recorded mod database answers and the seeded config in `web/e2e/fixtures/`
   **When** the format commit is made
   **Then** no file under `web/e2e/fixtures/` has changed, and a file `just record-moddb` writes there is ignored by the check (an unformatted JSON file placed in `e2e/fixtures/moddb/` leaves `prettier --check .` at exit 0)
   *(Covers FR260, FR261)*

9. **Given** `just lint-web`
   **When** it runs
   **Then** it runs the format check (`bun run format:check`), exits non-zero and names the file when a covered file is not formatted, and no longer runs `tsc --noEmit` (the type check stays in `just typecheck-web` only)
   *(Covers FR262)*

10. **Given** a pull request that contains an unformatted web file
    **When** CI runs
    **Then** the `web` job fails at its `just lint-web` step (after `just install-web --frozen-lockfile`, before `just typecheck-web`); `just check` fails the same way through `just lint`; `scripts/tests/test-release.sh` still passes (the job list and the `if:` lines are unchanged)
    *(Covers FR262)*

11. **Given** `just format-web` and `just format`
    **When** they run on a formatted tree
    **Then** they use the pinned Prettier (`bun run format`, not `bunx` over `src` only) with the committed configuration and ignore file, and change no file (`git status --short` empty)
    *(Covers FR261)*

12. **Given** the repository root
    **When** I read `.git-blame-ignore-revs`
    **Then** it names the web format commit's full 40-character hash under a comment line, below the API entry, and it was added in a separate commit of the same pull request (Task 3)
    *(Covers FR263)*

13. **Given** the epic's branches
    **When** Story 21.1's pull request merges
    **Then** it is merged with a merge commit like every other (no squash, no rebase), no other web branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main` (`git merge-base --is-ancestor <hash> origin/main` exits 0)
    *(Covers FR263; Matt, 2026-11-17)*

14. **Given** every existing test, lint and type check
    **When** `just check` runs on the branch
    **Then** it passes; no test is added, removed or skipped; no test run writes into `dev/`; none of the story's commits appears in `just changelog`; `CLAUDE.md`, `project-context.md` and the README describe `just lint-web`, `just format-web` and `just format` as they now behave
    *(Covers FR261, FR262)*

## Tasks / Subtasks

<!-- Commit per task: type(story-21.1/task-N): ...; no feat/fix/perf in this story (nothing a user or admin can see). Task 2's commit holds formatter output only; anything found during it goes into Task 4 or into a follow-up. Tasks are tooling, so "+ tests" is the before/after comparison and the red/green runs below, recorded in the Debug Log. -->

- [ ] Task 1: Pin Prettier, its configuration, its ignore file and the scripts; no source file changes (AC: 1, 2, 3)
  - [ ] 1.1: Base: the branch is cut from `main` after the Epic 21 planning pull request has merged (`git switch -c story/21-1-web-formatted-once origin/main`). `git status --short` is empty. `npm view prettier version` (3.10.1 on 2026-11-17); use the current release and record it in the Debug Log. If it is not 3.10.1, the counts in Dev Notes change: record the real ones; the method stays the same
  - [ ] 1.2: `cd web && bun add -d -E prettier@<version>` (via `mise exec -C web --`). Check: `web/package.json` gains exactly one devDependency line `"prettier": "<version>"` in alphabetical order (between `jsdom` and `tailwindcss`, `web/package.json:29-30`); `web/bun.lock` gains the `prettier` entries (3 lines at 966204f); `git diff --stat` shows only those two files. Bun keeps `package.json` in Prettier's form (checked at 966204f)
  - [ ] 1.3: New `web/.prettierrc.json` and `web/.prettierignore` exactly as in Dev Notes "The configuration" and "The ignore file"
  - [ ] 1.4: `web/package.json` `scripts` (`:6-17`): add `"format": "prettier --write ."` and `"format:check": "prettier --check ."` after `typecheck`. Leave `lint` in place in this commit (Task 4 removes it with the recipe change, so `just lint-web` keeps working at every commit)
  - [ ] 1.5: Check the scope before committing: `mise exec -C web -- bunx prettier --version` prints the pinned version and `ls -l web/node_modules/.bin/prettier` points into `node_modules/prettier` (the local install, not a download); `mise exec -C web -- bun run format:check` exits 1 with `Code style issues found in 231 files` (at 966204f) and lists no file under `e2e/fixtures/`, no `.md`, no `.html`, nothing under `public/`; `prettier --file-info` on the four files of AC 3 prints `"ignored": true`; `.prettierrc.json` and `package.json` are not in the list (already formatted)
  - [ ] 1.6: Baseline, recorded in the Debug Log (run now, on this commit's tree): `just typecheck-web` exit 0; `just test-web` (`Test Files 132 passed (132)`, `Tests 3307 passed (3307)` at 966204f); `just build-web` succeeds. Optional, stronger: save `(cd web/dist && find . -type f | sort | xargs shasum)` for the comparison in 2.4
  - [ ] 1.7: Commit `chore(story-21.1/task-1): pin prettier for the web with its configuration` (`web/package.json`, `web/bun.lock`, `web/.prettierrc.json`, `web/.prettierignore`). `git show --stat HEAD` lists exactly these four files

- [ ] Task 2: Reformat the web in one commit + before/after checks (AC: 4, 5, 6, 7, 8)
  - [ ] 2.1: Run `mise exec -C web -- bun run format` and nothing else. Not `just format-web` or `just format`: until Task 4 they run an unpinned `bunx prettier` with no configuration over `web/src` only (`Justfile:230-232`)
  - [ ] 2.2: Check the change is formatter output only: `git status --short` lists only ` M web/...` lines, all `.ts`, `.tsx`, `.css` or `.json`; 231 files at 966204f (`web/src` 213, of which 23 in `src/components/ui`; `web/e2e` 17; `web/vitest.config.ts`; nothing under `web/tests`); `git diff --shortstat` (`231 files changed, 3852 insertions(+), 5924 deletions(-)` at 966204f); `git diff --name-only | grep -c fixtures` prints 0; `git diff -U0 | grep -E '^\+.*(prettier-ignore|eslint-disable|@ts-ignore|@ts-expect-error)'` prints nothing; `bun run format:check` in `web/` prints `All matched files use Prettier code style!`
  - [ ] 2.3: After, same commands as 1.6: `just typecheck-web` exit 0; `just test-web` the same counts, 0 failed, 0 skipped; `just build-web` succeeds; `git status --short` shows nothing under `dev/` and nothing outside `web/`. If any result differs, stop and report it (ADR-1 decision 9); do not edit code in this commit and do not add `// prettier-ignore`
  - [ ] 2.4: Optional, if 1.6 saved the hashes: compare the build (Dev Notes "The build before and after"). Expected: identical once the chunk hashes in file names and imports are normalised, except the `mods` chunk, where `Watch trailer{' '}` + `<span>` became one text child `Watch trailer ` (`web/src/features/mods/ModDetailPage.tsx:737-738`); the rendered text and the link's accessible name are the same, and `e2e/mod-detail-media.spec.ts` asserts that name
  - [ ] 2.5: `git add web && git commit` with the subject `chore(story-21.1/task-2): format the web with prettier` and a body that names the command and version (`bun run format` in web/, prettier <version> pinned in web/package.json, .prettierrc.json singleQuote/printWidth 100/trailingComma es5) and the counts from 2.2. Do not stage the story file or `sprint-status.yaml` in this commit. Record the full hash (`git rev-parse HEAD`) in the Debug Log

- [ ] Task 3: `git blame` skips the web format commit (AC: 12)
  - [ ] 3.1: `.git-blame-ignore-revs` (2 lines today: the API comment and `da33a55e3d82aa09301a9bd52a7403d4ee730a07`): append a blank line, a comment line and the full hash from 2.5 (Dev Notes "The ignore file entry"). Nothing else changes in the file
  - [ ] 3.2: Verify: pick a line the format commit changed (`git show <hash> -- web/src/components/ui/switch.tsx | grep -m1 '^+'`, then find its number); `git blame -L <n>,<n> -- <file>` does not show `<hash>`, and `git blame --ignore-revs-file '' -L <n>,<n> -- <file>` does. This repository's shared `.git/config` already has `blame.ignoreRevsFile = :(optional).git-blame-ignore-revs` (Story 20.1); no setup script or README change is needed (ADR-1 decision 7). Record the commands and results in the Debug Log
  - [ ] 3.3: Commit `chore(story-21.1/task-3): skip the web format commit in git blame`

- [ ] Task 4: `just lint-web` checks the format, `just format-web` uses the pin, CI runs it + red/green proof (AC: 9, 10, 11, 14)
  - [ ] 4.1: `Justfile` `lint-web` (`:170-172`) and `format`/`format-web` (`:223-224`, `:230-232`) as in Dev Notes "The recipes". `format-api` (`:226-228`) is not changed. No recipe takes arguments, so no `[positional-arguments]` and no case in `scripts/tests/test-justfile-args.sh`
  - [ ] 4.2: `web/package.json`: remove the `"lint": "tsc --noEmit",` line (`:15`). Nothing else runs it (`git grep -n "run lint"` outside `_bmad*` finds only `Justfile:172`, which 4.1 changes). `typecheck` (`:16`) is unchanged and still runs both `tsc` passes
  - [ ] 4.3: `.github/workflows/ci.yml` `web` job (`:39-45`): add `- run: just lint-web` between `just install-web --frozen-lockfile` (`:42`) and `just typecheck-web` (`:43`). Nothing else in the workflow changes. `just lint-workflows` passes; `bash scripts/tests/test-release.sh` (or `just test-scripts`) still passes: it pins only the six job names and their `if:` (`scripts/tests/test-release.sh:319-325`)
  - [ ] 4.4: Command lists (Dev Notes "Documentation"): `CLAUDE.md` Validation (`:142-146`) and Formatting (`:159-161`); `project-context.md` Validation (`:561-565`), the format lines (`:572-573`) and a "Formatting" line in "Frontend (TypeScript)" (`:491-496`); `README.md` "Development commands" block (`:112-122`)
  - [ ] 4.5: Red/green (record the last lines in the Debug Log; commit nothing from it): (a) add a file `web/src/zz-unformatted.ts` containing `export const x = "a"` (no semicolon, double quotes); `just lint-web` exits 1 and prints `[warn] src/zz-unformatted.ts`; `just format-web` rewrites it to `export const x = 'a';`; delete the file; `just lint-web` exits 0. (b) put `{"a":1}` into `web/e2e/fixtures/moddb/zz.json`; `just lint-web` exits 0 (AC 8); delete it. (c) `just format` on the clean tree: `git status --short` empty (AC 11). (d) `just typecheck-web` still exits 0 and `just lint-web` prints no `tsc` line (AC 9)
  - [ ] 4.6: Commit `ci(story-21.1/task-4): check the web's format in just lint-web and CI` (`Justfile`, `web/package.json`, `.github/workflows/ci.yml`, `CLAUDE.md`, `project-context.md`, `README.md`)

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [ ] 5.1: `just check` passes: ruff clean and formatted, Pyright 0 errors, API tests pass, `just lint-web` clean, `just typecheck-web` exit 0, web 3307 passed in 132 files and 0 skipped (at 966204f), script tests green, `just lint-scripts` and `just lint-workflows` clean. The diff adds no lint or type suppression, no `// prettier-ignore` and no `cast`. After the run `git status --short` is empty and shows nothing under `dev/`. `just changelog` lists none of this story's commits
  - [ ] 5.2: Reproduce the format commit as the reviewer will (AC 6, Dev Notes "Reproducing the format commit") and record the result in the Debug Log. Confirm the commit holds only covered web files: `git show --name-only --format= <hash> | grep -vE '^web/.*\.(ts|tsx|css|json)$'` prints nothing, and `git show --name-only --format= <hash> | grep -c '^web/e2e/fixtures/'` prints 0
  - [ ] 5.3: Story status `review`, `just sprint set 21-1-web-formatted-once review`, commit `chore(story-21.1/task-5): move story 21.1 to review`. The PR to `main` (maintainer or orchestrator) has: the format commit's hash and the reproduction steps; the before/after results from 1.6 and 2.3; "API contract changes: none"; "Merge with a merge commit; do not squash or rebase, or the hash in `.git-blame-ignore-revs` is lost"; "Merge before any other Epic 21 web branch is cut"
  - [ ] 5.4: After the merge (maintainer or orchestrator): `git fetch origin && git merge-base --is-ancestor <hash> origin/main` exits 0 (AC 13), and GitHub's blame view of a reformatted web file on `main` shows the line's earlier commit with the notice that revisions in `.git-blame-ignore-revs` are hidden

## Dev Notes

### What the formatter does here (prototype at 966204f, discarded)

- `bun add -d -E prettier@3.10.1` in `web/`: one line in `package.json` (`"prettier": "3.10.1"`), 3 lines in `bun.lock`; `package.json` stays in Prettier's form. `bunx prettier --version` prints `3.10.1` and `node_modules/.bin/prettier -> ../prettier/bin/prettier.cjs`.
- With the configuration and ignore file below, `prettier --check .` in `web/` reports 231 files. `prettier --write .`: `231 files changed, 3852 insertions(+), 5924 deletions(-)`: `web/src` 213 files (+3383/-5545; 23 in `src/components/ui`, the shadcn files, which used double quotes and no semicolons), `web/e2e` 17 (+464/-378), `web/vitest.config.ts` (+5/-1), `web/tests` none, top-level JSON none. Nothing under `e2e/fixtures/`, no Markdown or HTML. Largest diffs: `src/components/ModCard.test.tsx` (398 lines), `ModCard.tsx` (332), `FileViewer.test.tsx` (314), `layout/ExpandableNavItem.test.tsx` (286), `ModTable.tsx` (275).
- Covered set: 330 tracked `.ts`/`.tsx`/`.json`/`.css` files under `web/` minus 11 in `e2e/fixtures/` = 319, plus the new `.prettierrc.json` = 320. Untracked (the one `.js`, `public/config.js`, is under `public/`); `bun.lock`, `.env.example`, `.gitkeep`, `.gitignore`, `.svg`, `.webp` have no Prettier parser and are skipped.
- After it: `just typecheck-web` exit 0; `just test-web` `132 passed` files, `3307 passed` tests (same as before); `just build-web` succeeds; `prettier --check .` clean. No `prettier-ignore`, `eslint-disable`, `@ts-ignore` or `@ts-expect-error` line added or removed. There is no `prettier-ignore` anywhere in `web/` today.
- Prettier 3 also reads `web/.gitignore` (it lists `coverage/`, `node_modules`, `dist`) by default; the root `.gitignore` (which lists `web/playwright-report*/` and `web/test-results*/`, `:104-108`) is not read when Prettier runs in `web/`. The ignore file therefore names the output directories itself, so the scope does not depend on which ignore files Prettier reads.
- The ADR's measurement (5,888 removed / 3,826 added, ADR-1 "Facts") was made on a copy of the tree; in the worktree it is 5,924 / 3,852 on the same 231 files. `git diff 05436da 966204f -- web` is empty, so the difference is the measurement, not the code. Record the real numbers.

### The configuration (Task 1.3)

`web/.prettierrc.json`:

```json
{
  "singleQuote": true,
  "printWidth": 100,
  "trailingComma": "es5"
}
```

Everything else is Prettier's default and matches the code (semicolons, two spaces, `arrowParens: "always"`, `jsxSingleQuote: false`, so JSX attributes keep double quotes). No `overrides`, no `plugins` (ADR-1 decision 2; no Tailwind class sorting plugin: it would be a second dependency and reorders class strings).

### The ignore file (Task 1.3)

`web/.prettierignore`:

```
# Recorded mod database answers and the seeded config, written by scripts
# (just record-moddb); reformatting them would fight the recorder
e2e/fixtures/

# Prose and the page shell: not code style
*.md
*.html

# Static files, and build, coverage and Playwright output
public/
dist/
coverage/
playwright-report*/
test-results*/
```

`node_modules` is always ignored by Prettier. `scripts/moddb-record.py:217` writes the fixtures with `json.dumps(indent=1)` and `:268` the manifest with `indent=2`; Prettier would rewrite both, which is why `e2e/fixtures/` is out (AC 8).

### The build before and after (Task 2.4, optional)

At 966204f the build after the format differs from the one before only (a) in the chunk hashes in file names and in the `import` lines that name them, and (b) in the `mods` chunk, where Prettier joined `Watch trailer{' '}` and the `<span className="sr-only">` onto one line (`ModDetailPage.tsx:737-738`): the JSX children `"Watch trailer"`, `" "` became `"Watch trailer "`. The DOM text and the accessible name ("Watch trailer (opens in a new tab)") are the same. This is Prettier's documented JSX whitespace handling, not a behavior change; do not hand-edit it back (AC 5). A short way to compare: copy `web/dist` before and after, replace `-[A-Za-z0-9_-]{8}\.(js|css)` with `-HASH.\1` in names and contents, and compare file by file.

### Reproducing the format commit (AC 6, Task 5.2, PR description)

```bash
git switch --detach <format-commit>^
just install-web --frozen-lockfile       # the prettier that web/bun.lock pins
mise exec -C web -- bun run format       # NOT just format-web: at the parent it is still the old bunx recipe
git diff --exit-code <format-commit>     # nothing printed, exit 0: same tree
git checkout -- web && git switch -      # back to the branch
```

The parent's `just format-web` (`Justfile:230-232` until Task 4) runs `bunx prettier --write "src/**/*.{ts,tsx,css,json}"`: it would find the local Prettier and the configuration, but it covers `src` only and would leave the 18 files outside `src` unchanged, so the trees would differ. The `format` script is the command of record. `web/node_modules/` is not tracked; `git diff` compares only tracked files.

### The ignore file entry (Task 3.1)

```
# chore(story-20.1/task-1): format the API with ruff format (Epic 20 ADR-1)
da33a55e3d82aa09301a9bd52a7403d4ee730a07

# chore(story-21.1/task-2): format the web with prettier (Epic 21 ADR-1)
<full 40-character hash>
```

Git reads the file in the `fsck.skipList` format (one object name per line, `#` comments, blank lines skipped); checked with Git 2.54 at 966204f with a blank line between entries. The hash is known only after Task 2's commit exists, which is why it is a separate commit. The project merges with merge commits (`CLAUDE.md` "Git Workflow"). **Do not rebase the branch after Task 2.** If a rebase is unavoidable (the base moved), redo Task 2 on the new base (`bun run format` again, new commit) and update the hash; never edit the hash by hand.

### The recipes (Task 4.1)

```just
# Check the web's format (Prettier, pinned in web/package.json); just format-web fixes it
lint-web:
    mise exec -C web -- bun run format:check
```

```just
# Format all code (ruff format for the API, Prettier for the web)
format: format-api format-web
```

```just
# Format the web (Prettier, pinned in web/package.json, with web/.prettierrc.json)
format-web:
    mise exec -C web -- bun run format
```

- `bun run` resolves `prettier` from `web/node_modules/.bin`, so it is always the pinned version; it fails ("command not found") if `just install-web` has not run, as `just typecheck-web` does without TypeScript. Do not use `bunx prettier` in a recipe: when the package is missing it downloads the latest release instead of failing.
- `prettier --check` prints `[warn] <file>` for each unformatted file and exits 1, so CI's log names the files to fix; `prettier --write` lists every file it visits with a timing, which is fine for a local recipe.
- `just check` is `lint typecheck test` (`Justfile:217`) and `lint` includes `lint-web` (`:162`): after this story `just check` runs the format check once and the web type check once (`typecheck-web`, `:209-210`), not `tsc --noEmit` twice.
- `just format` is safe on a formatted tree: `format-api` (ruff, `:226-228`) and `format-web` change nothing (AC 11; Story 20.1's follow-up about `just format` is closed by this).

### CI (Task 4.3)

```yaml
      - run: just install-web --frozen-lockfile
      - run: just lint-web
      - run: just typecheck-web
      - run: just test-web
      - run: just build-web
```

The format check runs first among the checks: it is the fastest and its failure is the most common on a new branch. The `e2e` and `docker` jobs are unchanged. The Docker `web-build` stage (`Dockerfile:20-28`) installs dev dependencies with `bun install --frozen-lockfile` and copies `web/`, so Prettier and the two dotfiles are in the build stage only; the final image copies only `/app/dist` (`Dockerfile:66`). `.dockerignore` needs no change.

### Documentation (Task 4.4)

- `CLAUDE.md` Validation (`:142-146`): after `just lint-api --fix` add `just lint-web                                # Check the web's format (Prettier)`. Formatting (`:159-161`): after `just format-api` add `just format-web                              # Format the web (Prettier, pinned); just lint-web checks it`; change `just format` to `# Format the API and the web (ruff format, Prettier)`. Keep the column alignment of the block.
- `project-context.md`: the same three lines at `:561-565` and `:572-573` (that block's alignment). In "Frontend (TypeScript)" (`:491-496`), after `**Booleans:**`, add one line: `**Formatting:** Prettier, pinned in \`web/package.json\` with \`web/.prettierrc.json\`; run \`just format-web\` on the files you change; \`just lint-web\` and CI check it`. The exact pin is the exception to the "Exact version pins without rationale" row (`project-context.md` "Anti-Patterns to Avoid"): a formatter's output changes between versions (ADR-1 decision 1); one clause in that line says so.
- `README.md` "Development commands" block (`:112-122`): after `just test-web` add `just format       # Format the API (ruff) and the web (Prettier); just check checks both`, aligned like its neighbours.
- No other file mentions `lint-web`, `format-web` or `bun run lint` outside `_bmad*` history (`git grep` at 966204f).

### Commit types and release notes

- Tasks 1, 2, 3 `chore` (tooling; Task 2's subject is fixed by AC 5); Task 4 `ci` (the workflow change, with the recipe and documentation it needs); Task 5 `chore`. The story file is `docs`. The change proposal (section 2, "No note") lists 21.1 as `chore`, `ci`, `docs`.
- `cliff.toml` makes notes from `feat`, `fix`, `perf` and breaking commits only; `just changelog` must not list any 21.1 commit (Task 5.1). The image's JavaScript bundle changes bytes (Task 2.4) but not behavior; no release note.

### Existing tests that change

- None is edited. 17 E2E specs and helpers under `web/e2e/` and 108 unit test files under `web/src` are reformatted by Task 2 (formatter output only); their count and results stay the same (AC 7). The E2E specs are not run in this story; `just typecheck-web` type-checks them (`web/e2e/tsconfig.json`).
- `scripts/tests/test-release.sh:319-325` reads `ci.yml`'s job names and `if:` lines only; adding a step changes neither. `scripts/tests/test-justfile-args.sh` covers argument-forwarding recipes; `lint-web`, `format` and `format-web` take no arguments. No script test reads `web/package.json`'s scripts.

### Not changed (do not "fix" these here)

- `web/tsconfig.json`, `web/e2e/tsconfig.json`, the `typecheck` script and `just typecheck-web`: the type check stays as Story 20.3 left it.
- No ESLint or other linter, no Prettier plugin, no editor settings (`.vscode/`), no pre-commit hook: ADR-1 adopts Prettier only.
- The API (`format-api`, `lint-api`, `api/`), `scripts/worktree-setup.sh` and the README's `git blame` paragraph (`README.md:106`, already generic).
- `renovate.json`: Renovate keeps an exact pin exact; an update that changes the output fails `just lint-web` until `just format-web` is run in its pull request (ADR-1 decision 1, change proposal "Risks"). No rule is added.
- Markdown in `web/e2e/README.md` and `web/index.html`: ignored by decision (ADR-1 decision 4).
- Any code smell, unused import or long string seen in the diff: not in Task 2's commit, and not in this story.
- Notes in older story files about `just format`/`just format-web` (for example `20-1-api-formatted-once.md` "Follow-ups"): history, left as written.

### ADR against the code

- ADR-1 matches the code at 966204f: `just lint-web` runs `bun run lint` = `tsc --noEmit` (`Justfile:171-172`, `web/package.json:15`); `just format-web` is `bunx prettier --write "src/**/*.{ts,tsx,css,json}"` (`Justfile:231-232`); `format: format-api format-web` (`:224`); CI's `web` job has no `just lint-web` (`ci.yml:39-45`); `.git-blame-ignore-revs` holds the API entry only; `blame.ignoreRevsFile` is `:(optional).git-blame-ignore-revs`.
- Two refinements, not contradictions: (1) the ADR's line counts are 5,888/3,826; the worktree gives 5,924/3,852 for the same 231 files (Dev Notes above). (2) The ADR says `lint-web` replaces the `tsc --noEmit` it shares with `typecheck-web`; the story also removes the then-unused `lint` script from `web/package.json` (Task 4.2), so no script runs a half type check under a misleading name.
- AC 13 "no other web branch of the epic exists yet": the `draft/21-*` branches hold only story files under `_bmad-output/`, which the format commit does not touch. They are not web branches.

### API contract changes

- None. No endpoint, field, error code or behavior changes. The web change is whitespace, line breaks, quotes, semicolons and trailing commas only, proven by the unchanged type check, unit tests and build (AC 7) and the build comparison (Task 2.4).

### Testing Requirements

- This story adds no test. Its checks are the before/after comparison (Tasks 1.6 and 2.3), the reproduction (Task 5.2), the red/green runs (Task 4.5) and the blame check (Task 3.2); each is recorded in the Debug Log with its command and result.
- Web unit tests run in Vitest's `vmThreads` pool (Story 20.2); none is skipped. After every run `git status --short` shows nothing under `dev/`.
- **No E2E task:** nothing a user or admin can see changes (the only bundle difference is one JSX text node split, Task 2.4, with the same rendered text and accessible name). Do not start the Docker stack or the game server, and do not run `just test-e2e-ci` or `just record-moddb` (it needs the network and rewrites the fixtures). CI's `E2E tests` job runs on the pull request and covers the reformatted specs.

### Security Requirements

- No runtime change. Prettier is a dev dependency, installed only in the Docker build stage and in development; it reads and writes files under `web/` only. The format commit must not touch any file outside `web/` (Task 5.2). No instance-specific data in any file or log recorded in the story.

### Development Commands

- Task 1: `mise exec -C web -- bun add -d -E prettier@<version>`, `just install-web --frozen-lockfile`, `mise exec -C web -- bun run format:check`.
- Task 2 (once): `mise exec -C web -- bun run format`. Before and after: `just typecheck-web`, `just test-web`, `just build-web`.
- Task 4 on: `just lint-web`, `just format-web`, `just format`, `just lint-workflows`, `just test-scripts`, `just check`, `just changelog`.
- Do not run `just format` or `just format-web` before Task 4: they are the old unpinned recipe until then.

### Previous Story Intelligence

- **20.1 (the model for this story):** one formatter-only commit reproducible from its parent, the hash added in a second commit, the check added after; `.git-blame-ignore-revs` and the `:(optional)` git setting exist, so this story adds an entry only. Its follow-up said `just format` would rewrite the web with an unpinned Prettier; Task 4 closes that.
- **20.3:** added `tsc -p e2e/tsconfig.json` to `typecheck` and put `just typecheck-web` into CI's `web` job; the `[positional-arguments]` rule for argument-forwarding recipes (none here). Its CI layout (`install-web --frozen-lockfile` first) is kept.
- **20.2:** web tests in `vmThreads`, 0 skipped (`VSS-hnl` resolved there; the suite reports 3307 passed and no skip at 966204f).
- **18.x/19.x/20.x reviews:** a completion note must be true of the code (record measured numbers, not this story's prototype numbers); tests must not write into `dev/`; `feat`/`fix` subjects only for what an admin sees (none here); manual steps that need the maintainer stay unticked (5.4 is after the merge).
- **Epic 21 rule:** stories 21.2 to 21.8 run Prettier on the web files they change; this story makes `just format-web` the way to do it.

### Git Intelligence

- Base for the story file: `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`) on `05436da` (`main`, release `v0.1.0-rc.6`). `git diff 05436da 966204f -- web Justfile .github README.md CLAUDE.md project-context.md` is empty.
- Planned commits: `chore(story-21.1/task-1): pin prettier for the web with its configuration`; `chore(story-21.1/task-2): format the web with prettier`; `chore(story-21.1/task-3): skip the web format commit in git blame`; `ci(story-21.1/task-4): check the web's format in just lint-web and CI`; `chore(story-21.1/task-5): move story 21.1 to review`.

### Project Structure Notes

- New: `web/.prettierrc.json`, `web/.prettierignore`.
- Modified: `web/package.json`, `web/bun.lock` (Tasks 1 and 4); 231 web source and test files (Task 2, formatter output only); `.git-blame-ignore-revs` (Task 3); `Justfile`, `.github/workflows/ci.yml`, `CLAUDE.md`, `project-context.md`, `README.md` (Task 4); this story file and `sprint-status.yaml` (Task 5).

### Follow-ups (not in this story)

- None that fits elsewhere. Whether a Renovate Prettier update's reformat commit also goes into `.git-blame-ignore-revs` is a convention for the maintainer to decide when the first one comes (the same open point Story 20.1 left for ruff).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.1: The Web Is Formatted Once and Stays Formatted]
- [Source: _bmad-output/planning-artifacts/prd.md] FR260, FR261, FR262, FR263
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md#ADR-1] and "Facts Checked in the Code" (Web formatting today)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] (section 2: decision 5, CI and project rules impact, risks, release-note types)
- [Source: _bmad-output/implementation-artifacts/20-1-api-formatted-once.md] (method, blame setting, follow-up on `just format`)
- `project-context.md` "Commit Message Format" (`:643-660`), "Frontend (TypeScript)" (`:491-496`); `CLAUDE.md` "Git Workflow"; `cliff.toml`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive, base 966204f) and validated against the create-story checklist. A throwaway prototype in the story worktree pinned Prettier 3.10.1 with `bun add -d -E`, added the configuration and ignore file above, ran `prettier --write .` in `web/` and then the type check, the unit tests, the build and a hash-normalised comparison of the build (numbers in Dev Notes "What the formatter does here" and "The build before and after"); it also checked `prettier --file-info` on the ignored paths, a red/green run of `prettier --check` in `src` and in `e2e/fixtures`, that `bun pm version` (used by `scripts/release.sh:198`) leaves `package.json` in Prettier's form, and a `.git-blame-ignore-revs` with a blank line between entries. It was then discarded.

### File List
