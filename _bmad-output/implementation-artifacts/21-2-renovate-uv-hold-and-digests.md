# Story 21.2: Renovate: the uv Hold and Digest Refreshes

Status: done

<!-- Implements FR264, FR265, Epic 21 ADR-2 and ADR-3. Beads: none (maintainer decisions 1 and 2; Matt, 2026-11-17). Epic 21 order 21.1 to 21.8, each stacked on the previous; this story touches no file under web/ and needs no other story's code (epics.md "Dependencies"). Line references were verified at 966204f (epic-21-planning; renovate.json, RELEASING.md, cliff.toml, Dockerfile, .mise.toml and scripts/tests/ are identical to 05436da, the commit the ADRs cite) and must be re-checked at implementation time: Story 21.1 edits the Justfile and CI, and 21.3 edits the README. Renovate configuration, script tests and documentation only: no file under api/ or web/ changes, no API contract change, no release note. No new dependencies. -->

## Story

As the **maintainer**,
I want **uv held like every other tool and image rebuilds kept out of the release notes**,
so that **Renovate's pull requests follow the organisation's rules and the release notes list only what a user would notice**.

## Acceptance Criteria

1. **Given** `renovate.json`
   **When** I read the uv rule
   **Then** it has no `minimumReleaseAge`, it still groups `uv` and `ghcr.io/astral-sh/uv` (`groupName`/`groupSlug` `uv`) as `chore(uv)`, and its `description` says the pull request opens with the Dockerfile half, fails `scripts/tests/test-docker-context.sh` until the `.mise.toml` half joins about a day later, and must not be merged before it holds both files and CI is green
   *(Covers FR264; ADR-2 decisions 1-3; Matt, 2026-11-17)*

2. **Given** `RELEASING.md`
   **When** I read what it says about Renovate and uv
   **Then** it says a uv pull request opens with only the Dockerfile change, that `scripts/tests/test-docker-context.sh` fails it for about a day until the `.mise.toml` change joins it, that this is expected, and that it must not be merged until it holds both files and CI is green; the `api/uv.lock` `revision` sentence is kept
   *(Covers FR264; Matt, 2026-11-17)*

3. **Given** `scripts/tests/test-docker-context.sh`
   **When** the story is done
   **Then** the file is unchanged (`git diff <base>..HEAD -- scripts/tests/test-docker-context.sh` is empty), so its uv version assertion (`:32-35`) still fails a uv pull request that holds one half
   *(Covers FR264; ADR-2 decision 4)*

4. **Given** `renovate.json`
   **When** I read its rules
   **Then** exactly one rule matches `matchManagers: ["dockerfile"]` with `matchUpdateTypes: ["digest", "pinDigest"]` and sets `semanticCommitType: "chore"` (no scope, so the preset's `container` stays), it is the last entry of `packageRules`, and no rule that names `patch`, `minor` or `major` in `matchUpdateTypes` sets a commit type. The uv group's `chore(uv)` for all uv updates (Epic 20 ADR-10, Story 20.7) is the one existing exception and is unchanged
   *(Covers FR265; ADR-3 decisions 1-4; Matt, 2026-11-17)*

5. **Given** `just test-scripts`
   **When** it runs
   **Then** a new `scripts/tests/test-renovate.sh` passes, and fails if the uv rule regains a `minimumReleaseAge`, loses its group or `chore(uv)` type, if the digest rule is missing or not `chore`, or if a rule retypes a `patch`/`minor`/`major` update; and `scripts/tests/test-changelog.sh` shows that `chore(container): update image node digest (...)` produces no note while `fix(container): update image ... (10.0.14 → 10.0.15)` does
   *(Covers FR264, FR265)*

6. **Given** a digest refresh of `node:26-slim` (or another Dockerfile image) under the same tag
   **When** Renovate commits it after the merge
   **Then** the pull request title and commit subject start with `chore(container):`, and `just changelog` on a tree containing it shows no note for it. Recorded in the Completion Notes from the first such pull request (Renovate's local dry run cannot render commit messages; Dev Notes "What the dry run showed")
   *(Covers FR265; confirmed on the first such pull request after the merge)*

7. **Given** a new version tag of a Dockerfile image other than uv
   **When** Renovate commits it
   **Then** the subject keeps the preset's `fix(container):` (patch) or `feat(container):` (minor; `feat(container)!:` for major)
   *(Covers FR265; ADR-3 decision 3)*

8. **Given** the changed `renovate.json`
   **When** `renovate-config-validator --no-global` runs on it from a directory outside the repository
   **Then** it reports "Validating ... as repo config" and "Config validated successfully against 1 file(s)" with exit 0, the Renovate version is recorded, and `web/package.json`, `web/bun.lock` and the rest of the worktree are unchanged by the run (`git status --short` shows only the story's own edits)
   *(Covers FR264, FR265; ADR-2 decision 5, ADR-3 decision 5)*

9. **Given** pull request #185 (`chore(uv): Update uv (0.13.8 → 0.13.9)`, branch `renovate/uv`)
   **When** the story is done
   **Then** the story has not merged, closed, rebased or pushed to it, and the Completion Notes record its state at merge time and, if it was still open, what Renovate did with it under the new rule
   *(Planning note in epics.md; ADR-2 consequences)*

10. **Given** every existing test and check
    **When** `just check` runs
    **Then** it passes, with no lint or type suppression added; no commit of this story is `feat`, `fix` or `perf`, so `just changelog` shows no new entry from it

## Tasks / Subtasks

<!-- Commit per task: type(story-21.2/task-N): ... . Types are fixed for this story: chore (Tasks 1, 2: Renovate configuration with its tests, as Story 20.7 Task 2 and 66c4b21 "chore(renovate): ..."), docs (Task 3). No feat/fix/perf: nothing here is a release note (sprint-change-proposal-2026-11-17-epic-21.md section 2, "No note: Story 21.2 (chore, docs)"). Red first in Tasks 1 and 2. -->

- [x] Task 1: The uv rule keeps the preset's hold (AC: 1, 3, 5)
  - [x] 1.1: Red first. Create `scripts/tests/test-renovate.sh` with the header, the `uv` block of the Python check and the assertion of Dev Notes "The script test" (leave out the `digest` block and the "retypes" loop for now). `run.sh` calls `bash "$file"`, so the mode does not matter to it; make it executable like `test-docker-context.sh` and `test-changelog.sh` (`git ls-files -s` shows `100755`). Run `just test-scripts test-renovate.sh` against today's `renovate.json` and record in the Debug Log that it fails with exactly "the uv rule sets no minimumReleaseAge (the preset's hold applies)"
  - [x] 1.2: `renovate.json:32`: delete the line `"minimumReleaseAge": null,`. Change nothing else in the rule's keys (`matchDepNames`, `groupName`, `groupSlug`, `semanticCommitType`, `semanticCommitScope`, `commitMessagePrefix` stay as they are at `:29-35`)
  - [x] 1.3: `renovate.json:28`: replace the uv rule's `description` with the text of Dev Notes "The uv rule" (one JSON string, no line breaks, matching the file's style). Edit by hand; do not reformat the file with a JSON tool (Story 20.7 Task 2.1)
  - [x] 1.4: `python3 -m json.tool renovate.json >/dev/null`; `just test-scripts test-renovate.sh test-docker-context.sh` passes (`test-docker-context.sh` 10/10, unchanged)
  - [x] 1.5: Commit `chore(story-21.2/task-1): keep Renovate's one-day hold on uv updates`

- [x] Task 2: Digest refreshes of Dockerfile images are `chore(container)` (AC: 4, 5, 7)
  - [x] 2.1: Red first. Add the `digest` block and the "retypes" loop of Dev Notes "The script test" to `test-renovate.sh`. Run it and record that it fails with exactly "one rule types dockerfile digest and pinDigest updates chore"
  - [x] 2.2: Append the rule of Dev Notes "The digest rule" as the fourth and last entry of `packageRules` (after the uv rule, whose closing `}` is at `:36` today; add the `,`). Last, so that it is applied after every preset rule and after the uv rule (Dev Notes "Rule order")
  - [x] 2.3: `scripts/tests/test-changelog.sh`: add the block of Dev Notes "The changelog test" just before `# --- Version bumps on 0.x and pre-release tags` (`:108` today). It must pass without any change to `cliff.toml`
  - [x] 2.4: `just test-scripts` passes (all files; `test-renovate.sh` 1/1, `test-changelog.sh` 24/24, `test-docker-context.sh` 10/10). Negative checks, reverted afterwards and recorded: with `"minimumReleaseAge": null` put back the test fails on the uv line; with the digest rule's `semanticCommitType` set to `"fix"` it fails on the digest line; with a rule `{"matchManagers": ["dockerfile"], "matchUpdateTypes": ["patch"], "semanticCommitType": "chore"}` inserted before the digest rule it fails on "retypes" only (inserted after it, the "last entry" check fails too)
  - [x] 2.5: `just lint-scripts` passes (ShellCheck covers `scripts/tests/*.sh`)
  - [x] 2.6: Commit `chore(story-21.2/task-2): commit Dockerfile image digest refreshes as chore(container)`

- [x] Task 3: `RELEASING.md` (AC: 2)
  - [x] 3.1: Replace the first sentence of `RELEASING.md:57` ("Renovate updates uv in `.mise.toml` and the Dockerfile in one pull request.") with the paragraph of Dev Notes "RELEASING.md"; keep the rest of `:57` (the `api/uv.lock` `revision` sentence and "Dependency versions are not affected.") as it is, after the new text
  - [x] 3.2: `RELEASING.md:71`: after "Renovate moves the pins in pull requests, which CI builds and tests." add the release-note sentence of Dev Notes "RELEASING.md"
  - [x] 3.3: Read the result once in rendered form (`gh markdown-preview` is not needed; a plain read is enough) and check that no other line of `RELEASING.md` still says the two uv halves arrive at once (`grep -n "one pull request\|uv" RELEASING.md`)
  - [x] 3.4: Commit `docs(story-21.2/task-3): say a uv pull request waits a day for its .mise.toml half, and which image updates make a release note`

- [x] Task 4: Validate and record (AC: 6, 8, 9)
  - [x] 4.1: Renovate's validator, from a scratch directory outside the repository (it downloads Renovate into Bun's cache; nothing is added to the project): `cd <scratch dir> && bunx --package renovate renovate --version && bunx --package renovate renovate-config-validator --no-global <worktree>/renovate.json; echo "exit=$?"`. Expect "Validating <path>/renovate.json as repo config", "Config validated successfully against 1 file(s)", `exit=0`. Use `--no-global` and run under Node, not `bunx --bun` (Story 20.7 Task 2.2). Record the version and output in the Debug Log
  - [x] 4.2: `git status --short` in the worktree shows nothing the validator wrote (`web/package.json` and `web/bun.lock` unchanged)
  - [x] 4.3: Record the state of PR #185 read-only: `gh pr view 185 --json state,files,headRefOid,statusCheckRollup`. Do not merge, close, rebase, comment on or push to it. Write in the Completion Notes and the PR description what the maintainer should know (Dev Notes "Pull request #185")
  - [x] 4.4: `just semgrep` (needs the network) reports 0 findings with the new test file tracked (semgrep scans only tracked files, so run it after the Task 2 commit)

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `just check` passes; the diff adds no lint or type suppression; `git status --short` is clean after it
  - [x] 5.2: `just changelog` shows no entry from this story's commits (all `chore` or `docs`)
  - [x] 5.3: AC 3 check: `git diff <base>..HEAD -- scripts/tests/test-docker-context.sh cliff.toml Dockerfile .mise.toml` prints nothing
  - [x] 5.4: (status moves by the dev agent; PR by the controller) Story status `review`, `just sprint set 21-2-renovate-uv-hold-and-digests review`, PR against the previous story's branch while its PR is open, otherwise `main`. The PR description says: no API contract change, no release note; uv PRs will now be red for about a day by design; image digest refreshes become `chore(container)`; the validator output; the state of PR #185 and the timing note of Dev Notes "Pull request #185"
  - [ ] 5.5: After the merge (may be completed by the controller or the maintainer later; leave unchecked until observed): record in the Completion Notes (a) the first uv pull request under the new rule: did it open with the Dockerfile half only, did `test-docker-context.sh` fail it, and did the `.mise.toml` half join about a day later (ADR-2 consequences; if the held half never joins, report it to the maintainer for a new decision); (b) the first Dockerfile digest pull request: its title starts `chore(container):` (AC 6). No bead is closed by this story

## Dev Notes

### What changes, and why (verified at 966204f)

- `renovate.json:27-36` is the uv rule (Story 20.7): `matchDepNames: ["uv", "ghcr.io/astral-sh/uv"]`, `groupName`/`groupSlug` `uv`, `"minimumReleaseAge": null` (`:32`), `semanticCommitType` `chore`, `semanticCommitScope` `uv`, `commitMessagePrefix` `{{semanticCommitType}}({{semanticCommitScope}}):` (which drops the preset's `!` on a major). The file has a `customManagers` entry (`:6-15`, semgrep) and two other rules (Python `:17-21`, .NET `:22-26`); neither changes.
- The maintainer prefers the preset's hold (Epic 21 ADR-2, the answer to Story 20.7's open question). With `minimumReleaseAge: null` gone, the preset's "Hold mise tool updates until release assets have settled" rule (`autoMerge.json5`, `matchManagers: ["mise"]`, `minimumReleaseAge: "1 day"`) applies to the `.mise.toml` half. The Dockerfile half (`ghcr.io/astral-sh/uv`) has no hold: no preset rule holds `docker` updates, and GHCR gives no release timestamps anyway.
- The organisation preset's `semanticCommits.json5` types `digest` updates `fix` and scopes every `docker` datasource update `container` with the topic `image {{depName}}`. Since Story 20.7 all three Dockerfile images are pinned by digest (`Dockerfile:9`, `:36`, `:52`), so every rebuild of `node:26-slim` or the .NET runtime under its tag arrives as `fix(container): update image <name> digest (<old> → <new>)`, and `cliff.toml:46` (`{ message = "^fix", group = "<!-- 2 -->Fixes" }`) makes it a **Fixes** note ("Update image node digest (...)"; the `container` scope is not one of the shown scopes).
- `scripts/tests/test-docker-context.sh:32-35` compares `.mise.toml`'s `uv` (`.mise.toml:3`, `0.13.8`) with the uv image tag (`Dockerfile:52`). It is what fails a one-half uv pull request and must not change (ADR-2 decision 4).
- `RELEASING.md:57` says "Renovate updates uv in `.mise.toml` and the Dockerfile in one pull request." That stays true (one group, one branch), but no longer at the same moment.

### The organisation preset (read-only, `gh api repos/craquehouse/renovate-config/contents/<file>` at `021869b`, 2026-11-17)

- `default.json:3-15` extends `config:recommended`, `docker:enableMajor`, `helpers:pinGitHubActionDigestsToSemver` and the preset files `annotated.json5`, `autoMerge.json5`, `groups.json5`, `labels.json5`, `semanticCommits.json5`, plus `:automergeBranch`, `:dependencyDashboard`, `:disableRateLimiting`.
- `autoMerge.json5:11-19`: `matchManagers: ["mise"]`, `minimumReleaseAge: "1 day"` (the hold this story restores for uv). No rule there matches `dockerfile` or the `docker` datasource.
- `semanticCommits.json5`:
  - `:5-9` `major` → `feat`, prefix `{{semanticCommitType}}({{semanticCommitScope}})!:`; `:10-14` `minor` → `feat`; `:15-19` `patch` → `fix`;
  - `:20-24` **`digest` → `fix`**, `commitMessageExtra: "({{currentDigestShort}} → {{newDigestShort}})"`;
  - `:25-29` `matchDatasources: ["docker"]` → `semanticCommitScope: "container"`, `commitMessageTopic: "image {{depName}}"`;
  - `:40-46` `github-actions` → `ci(github-action)` (why ADR-3 decision 4 limits the new rule to the Dockerfile manager); `:54-60` `mise` → `chore(mise)`.
  - No rule names `pinDigest` (ADR-3 decision 2).
- Do not change the preset (Story 20.7 "Not changed"; ADR-3 is a repository rule).

### The uv rule (Task 1)

Keep every key except `minimumReleaseAge`. The `description` becomes (one string):

```
Move uv in the Dockerfile (ghcr.io/astral-sh/uv) and in .mise.toml (uv) in one pull request, so the image, development and CI use one uv (Epic 20 ADR-10). The preset holds the .mise.toml half for one day; GHCR gives no release timestamps, so the Dockerfile half is ready at once. The pull request therefore opens with the Dockerfile half only, and scripts/tests/test-docker-context.sh fails it until the .mise.toml half joins about a day later: that is expected, and it must not be merged before it holds both files and CI is green (Epic 21 ADR-2). A uv update is tooling, not a release note: chore, with no breaking mark
```

The old description's reasoning against the hold ("No release-age hold: ... the preset's one-day hold on mise tools exists for mise.lock, which this repository does not have") is removed: it is the decision ADR-2 reverses.

### The digest rule (Task 2)

```json
    {
      "description": "A new digest of a Dockerfile image under the same tag (a base image rebuild) is chore(container), not the preset's fix(container), so it adds no release note. A new tag is a patch, minor or major update and keeps the preset's fix or feat (Epic 21 ADR-3)",
      "matchManagers": ["dockerfile"],
      "matchUpdateTypes": ["digest", "pinDigest"],
      "semanticCommitType": "chore"
    }
```

- No `semanticCommitScope`, `commitMessageTopic` or `commitMessagePrefix`: the preset's `container` scope and `image <name>` topic are kept, giving `chore(container): update image node digest (e6bedef → 1a2b3c4)`. The preset's digest prefix has no `!`, so none is needed.
- A digest refresh of the uv image (`ghcr.io/astral-sh/uv` re-pushed under the same tag) matches both the uv rule and this one; both say `chore`, and this rule sets no scope, so the uv group keeps `chore(uv)`.

### Rule order

Renovate applies `packageRules` in order, later rules overriding earlier ones, with the preset's rules first. Confirmed in planning from the resolved configuration of a dry run (Dev Notes "What the dry run showed"): the preset's rules were entries 0-16 (`semanticCommits.json5`'s `digest` → `fix` at 11), the repository's Python, .NET, uv and digest rules 17-20. Keep the digest rule last.

### The script test (Tasks 1.1 and 2.1)

`scripts/tests/test-renovate.sh` (new). The Python heredoc reads JSON as `test-e2e-ci.sh:83` does; `python3 -I` because it needs nothing from the current directory. Task 1.1 adds everything except the block marked `# Task 2` and the final loop; Task 2.1 adds them.

```bash
#!/usr/bin/env bash
# Pins the Renovate rules of Epic 21 ADR-2 and ADR-3 in renovate.json: the uv group keeps
# the preset's one-day hold (no minimumReleaseAge of its own) and is chore(uv); a digest
# refresh of a Dockerfile image is chore, and no rule retypes a version update.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

problems=$(python3 -I - "$SCRIPTS_DIR/../renovate.json" <<'PY'
import json, sys

try:
    rules = json.load(open(sys.argv[1]))["packageRules"]
except Exception as e:
    print(f"renovate.json does not parse: {e}")
    sys.exit()
problems = []

uv = [r for r in rules if sorted(r.get("matchDepNames", [])) == ["ghcr.io/astral-sh/uv", "uv"]]
if len(uv) != 1:
    problems.append(f"one rule groups uv and ghcr.io/astral-sh/uv (found {len(uv)})")
else:
    r = uv[0]
    if "minimumReleaseAge" in r:
        problems.append("the uv rule sets no minimumReleaseAge (the preset's hold applies)")
    for key, want in (("groupName", "uv"), ("semanticCommitType", "chore"), ("semanticCommitScope", "uv")):
        if r.get(key) != want:
            problems.append(f"the uv rule has {key} {want!r}, not {r.get(key)!r}")

# Task 2
digest = [r for r in rules if r.get("matchManagers") == ["dockerfile"]
          and sorted(r.get("matchUpdateTypes", [])) == ["digest", "pinDigest"]]
if len(digest) != 1 or digest[0].get("semanticCommitType") != "chore" or rules[-1] is not digest[0]:
    problems.append("one rule types dockerfile digest and pinDigest updates chore")

for r in rules:
    versions = {"patch", "minor", "major"} & set(r.get("matchUpdateTypes", []))
    if versions and "semanticCommitType" in r:
        problems.append(f"a rule retypes {sorted(versions)} updates: {r.get('description', r)}")

print("\n".join(problems))
PY
)
assert_eq "renovate.json: the uv hold and the digest rule (Epic 21 ADR-2, ADR-3)" "" "$problems"

finish
```

- The "retypes" loop looks only at rules that name version update types. The uv rule names none (it types every uv update, by dependency); that is the existing exception of AC 4.
- Prototyped in planning (then discarded): with the final `renovate.json` 1/1; against today's file 0/1 with the two expected lines; ShellCheck clean; `just semgrep` 0 findings (the file was untracked then, so Task 4.4 runs it again).
- Do not put these checks in `test-docker-context.sh`: AC 3 requires that file unchanged.

### The changelog test (Task 2.3)

```bash
# --- Renovate's image updates (Epic 21 ADR-3) -----------------------------------------

repo=$(new_repo)
commit "$repo" "chore: initial commit"
commit "$repo" "chore(container): update image node digest (e6bedef → 1a2b3c4)"
commit "$repo" "fix(container): update image mcr.microsoft.com/dotnet/runtime (10.0.14 → 10.0.15)"
notes=$(cliff "$repo" --unreleased --strip header)
assert_eq "an image version update is a note, a digest refresh is not" \
    "- Update image mcr.microsoft.com/dotnet/runtime (10.0.14 → 10.0.15)" \
    "$(grep '^- ' <<<"$notes" | sed 's/ (\[.*//')"
```

Uses the file's own `new_repo`, `commit` and `cliff` helpers (`test-changelog.sh:26-46`) and the same `sed` that strips the commit link (`:78`). Prototyped: 24/24 (23 before).

### RELEASING.md (Task 3)

Replace the first sentence of `:57` with:

> Renovate updates uv in `.mise.toml` and the Dockerfile in one pull request, but not at the same moment. The `.mise.toml` change is held for a day, like every mise tool of the organisation's Renovate preset; the Dockerfile's uv image has no release date Renovate can read, so it is proposed at once. The pull request therefore opens with only the Dockerfile change, and `scripts/tests/test-docker-context.sh` fails it, because the two uv versions differ, until Renovate adds the `.mise.toml` change about a day later. That is expected. Do not merge a uv pull request until it changes both files and CI is green.

Then the existing "After such an update, the release commit may also change the `revision` line ..." sentences, unchanged.

Add to `:71`, after "Renovate moves the pins in pull requests, which CI builds and tests.":

> A new version of an image is committed as `fix(container)` or `feat(container)` and is a release note; a new digest under the same tag (a rebuild of the base image) is `chore(container)` and is not.

### What the dry run showed (planning, 2026-11-17)

A scratch copy (outside the repository) of the `Dockerfile`, `.mise.toml` and the changed `renovate.json`, with `local>` replaced by `github>` presets (the `local` platform cannot resolve `local>` presets), a zero digest on `node:26-slim` and `semanticCommits: "enabled"`, run with Renovate 44.251.0 `--platform=local --dry-run=lookup` and `--dry-run=full`:

- Updates found: `node` digest, `mcr.microsoft.com/dotnet/runtime` digest, `ghcr.io/astral-sh/uv` patch 0.13.9 (no `releaseTimestamp`), `.mise.toml` `uv` patch 0.13.9 (`releaseTimestamp` 2026-11-17T09:57:55Z, `pendingChecks: true`).
- For branch `renovate/uv`: "Branch is not pending, removing pending upgrades". That is ADR-2 decision 2 observed, not only reasoned: the group branch is built with the Dockerfile half alone while the `.mise.toml` half is held.
- The resolved rule order (Dev Notes "Rule order").
- The `local` platform stops after branching, so the dry run does not render commit messages or PR titles. AC 6 and 7 are therefore confirmed by the rules (preset `:20-29`, the new rule last), by the changelog test, and on the first real pull request (Task 5.5).

The dev agent need not repeat this dry run; the validator (Task 4.1) is required.

### Pull request #185

Open on 2026-11-17 (`renovate/uv`, both `.mise.toml` and `Dockerfile`, all six CI checks green). Under the new rule its `.mise.toml` half (uv 0.13.9, released 2026-11-17T09:57:55Z) is pending until about 2026-11-18T10:00Z. If this story merges before then while #185 is still open and unmodified, Renovate's next run is expected to rebuild `renovate/uv` with the Dockerfile half only (red) and add the `.mise.toml` half back after the hold. After that time the new rule changes nothing for #185. Whether to merge #185 first is the maintainer's call; the story only records what happened (AC 9, Task 4.3, Task 5.5).

### Existing tests that change

- `scripts/tests/test-changelog.sh`: gains one block (one assertion; 23 → 24). No existing assertion changes.
- `scripts/tests/test-renovate.sh`: new. `run.sh` picks it up by its `test-*.sh` glob; CI's `scripts` job runs `just test-scripts` (`.github/workflows/ci.yml:58`) and `just lint-scripts` (`:56`). No test pins the list of script test files (`test-release.sh` pins job names, not steps).
- `scripts/tests/test-docker-context.sh`: unchanged (AC 3).
- No API, web or E2E test changes.

### E2E

None. Nothing a user or admin sees in the running product changes (Renovate configuration, tests and release documentation only), so there is no spec and no manual check against the dev stack.

### Not changed (do not "fix" these here)

- The organisation preset `craquehouse/renovate-config` (read-only here).
- `Dockerfile:50-51`'s comment "Renovate moves both together": still true in the sense of one pull request, and a Dockerfile edit is outside this story's files.
- `scripts/tests/test-docker-context.sh` (AC 3) and `cliff.toml` (the new behaviour needs no cliff change).
- The uv rule's `commitMessagePrefix` and `chore(uv)` type, the Python and .NET rules, the semgrep custom manager.
- The preset's `feat(container)!:` for a major image update (for example `41d6f25 feat(container)!: Update image node (22.23.4 → 26.13.0)`): a major base image change can matter to users; ADR-3 decision 3 keeps it.
- PR #185 (AC 9).

### API contract changes

None. No route, response field, error code or setting changes.

### ADR against the code

- ADR-3 and the epic's AC "no rule changes the type of a `patch`, `minor` or `major` update of a Dockerfile image" overlook the uv rule (Story 20.7), which types every update of `ghcr.io/astral-sh/uv`, version updates included, `chore(uv)`. That is intended (uv is tooling; Epic 20 ADR-10) and stays; AC 4 names it as the one exception, and the script test checks only rules that name version update types.
- ADR-2 decision 2 was reasoned in Story 20.7; the planning dry run observed it (Dev Notes "What the dry run showed"). Nothing in ADR-2 is wrong against the code.

### Testing Requirements

- `just test-scripts` (all script tests), `just lint-scripts`, `just check`, `just semgrep` once (network).
- Renovate config validator once (Task 4.1).
- No test writes into `dev/` or the repository; `test-changelog.sh` and `test-renovate.sh` use temporary directories or only read files.

### Security Requirements

- Renovate's hold is a supply-chain control: it keeps a just-published tool version out for a day. The uv pull request is red for that day on purpose; do not relax `test-docker-context.sh` or add `minimumReleaseAge: null` back to get a green PR.
- No instance-specific value in the story, PR or Completion Notes.

### Development Commands

```bash
just test-scripts test-renovate.sh test-changelog.sh test-docker-context.sh
just test-scripts
just lint-scripts
cd <scratch dir> && bunx --package renovate renovate-config-validator --no-global <worktree>/renovate.json
gh pr view 185 --json state,files,headRefOid,statusCheckRollup   # read-only
just semgrep
just check
just changelog
```

### Previous Story Intelligence

- Story 20.7 added the uv rule and asked the maintainer whether he preferred the hold (its "ADR against the code", second bullet); this story carries out his answer. It also reported the `fix(container)` digest notes as a follow-up (its "Not changed", third bullet); ADR-3 is that follow-up.
- 20.7 Task 2.2's validator recipe works as written (re-run in planning: Renovate 44.251.0, exit 0). Run it from outside the repository so `bunx` touches no project file.
- 20.7's review: a completion note must be true of the code; record the actual validator version and output and what Renovate actually did, not this story's expectations.
- A `feat`/`fix` subject must describe something an admin can see; every commit here is `chore` or `docs`.

### Git Intelligence

- Renovate commits in history: `2f2d40f chore(mise): Update tool uv (0.13.7 → 0.13.8)`, `41d6f25 feat(container)!: Update image node (22.23.4 → 26.13.0)`, `0383a11 fix(container): update image mcr.microsoft.com/dotnet/runtime (8.0.30 → 8.0.33)`. No digest refresh has been committed yet; PR #185 is the first uv group pull request.

### Project Structure Notes

Files touched: `renovate.json`, `scripts/tests/test-renovate.sh` (new), `scripts/tests/test-changelog.sh`, `RELEASING.md`, this story file. Nothing under `api/`, `web/`, `.github/`, `_bmad/`; no `Dockerfile`, `.mise.toml` or `cliff.toml` change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.2: Renovate: the uv Hold and Digest Refreshes]
- [Source: _bmad-output/planning-artifacts/prd.md] FR264, FR265 (`:842-843`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md] "Facts Checked in the Code" (Renovate today), ADR-2, ADR-3
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md] ADR-10
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] section 2 (release notes: "No note: Story 21.2"), risks for 21.2
- [Source: _bmad-output/implementation-artifacts/20-7-reproducible-image-and-conventions.md] Dev Notes "Renovate", "ADR against the code", Task 2.2
- Organisation preset `craquehouse/renovate-config` at `021869b`: `default.json`, `autoMerge.json5`, `semanticCommits.json5`, `groups.json5`
- Renovate docs: `packageRules` order, `minimumReleaseAge` (GHCR has no release timestamps)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Task 1.1 (red): `just test-scripts test-renovate.sh` against the base `renovate.json`: 0/1, `expected '', got 'the uv rule sets no minimumReleaseAge (the preset's hold applies)'`. After 1.2-1.3: `test-renovate.sh` 1/1, `test-docker-context.sh` 10/10; `python3 -m json.tool renovate.json` clean.
- Task 2.1 (red): with the digest block and the "retypes" loop added: 0/1, `expected '', got 'one rule types dockerfile digest and pinDigest updates chore'`. After 2.2-2.3: `just test-scripts` all green (`test-renovate.sh` 1/1, `test-changelog.sh` 24/24, `test-docker-context.sh` 10/10). `cliff.toml` unchanged.
- Task 2.4 negative checks, each on the final `renovate.json` and restored byte for byte afterwards (`cmp` against a scratch copy): `"minimumReleaseAge": null` put back in the uv rule: 0/1 on the uv line only; the digest rule's `semanticCommitType` set to `"fix"`: 0/1 on the digest line only; `{"matchManagers": ["dockerfile"], "matchUpdateTypes": ["patch"], "semanticCommitType": "chore"}` inserted before the digest rule: 0/1 on "a rule retypes ['patch'] updates" only; appended after it: 0/1 on both the digest line ("last entry") and "retypes".
- Task 2.5: `just lint-scripts` clean (ShellCheck on `scripts/tests/*.sh`, ruff, pyright).
- Task 4.1: from a scratch directory outside the repository, `bunx --package renovate renovate --version` → `44.251.0`; `bunx --package renovate renovate-config-validator --no-global <worktree>/renovate.json` → ` INFO: Validating <worktree>/renovate.json as repo config`, ` INFO: Config validated successfully against 1 file(s)`, `exit=0` (run under Node, not `--bun`).
- Task 4.2: `git status --short` afterwards showed only `_bmad-output/implementation-artifacts/sprint-status.yaml` (the `just sprint set` of the story start); `web/package.json` and `web/bun.lock` unchanged.
- Task 4.3: `gh pr view 185 --json state,mergedAt,mergeCommit,files,headRefOid,statusCheckRollup` (read-only): `MERGED` at 2026-11-17T22:17:52Z, merge commit `a7e2e62`, head `14d5c28`, files `.mise.toml` and `Dockerfile`, all six checks SUCCESS (API tests, Web tests and build, Release scripts, Docker image, E2E tests, Semgrep).
- Task 4.4: `just semgrep` after the Task 2 commit (test file tracked): "Ran 280 rules on 228 files: 0 findings."
- Task 5.1: `just check` exit 0: API 3387 passed; web 132 files, 3307 tests passed; pyright 0 errors, 0 warnings; script tests all green. No suppression in the diff (`grep` for nosemgrep/noqa/type: ignore/pyright: ignore/eslint-disable/shellcheck disable over `git diff 38990a2..HEAD`: none).
- Task 5.2: `just changelog` shows no entry from `c6a81e8`, `b410baa` or `1253446` (all `chore`/`docs`).
- Task 5.3: `git diff 38990a2..HEAD -- scripts/tests/test-docker-context.sh cliff.toml Dockerfile .mise.toml` prints nothing.

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive, base 966204f) and validated against the create-story checklist. Prototypes, discarded: the two `renovate.json` changes (Renovate 44.251.0 validator, `--no-global` from a scratch directory: "Validating ... as repo config", "Config validated successfully against 1 file(s)", exit 0; worktree unchanged apart from the edit); `test-renovate.sh` (1/1 on the new file, 0/1 with both expected lines on today's); the changelog block (24/24); ShellCheck clean; `just semgrep` 0 findings; a Renovate dry run in a scratch copy (Dev Notes "What the dry run showed"). No E2E.
- Implemented 2026-11-17 on `story/21-2-renovate-uv-hold-and-digests` (stacked on Story 21.1). Task 1: the uv rule in `renovate.json` no longer sets `minimumReleaseAge`, so the preset's one-day hold on mise tools applies to the `.mise.toml` half; its `description` now says the pull request opens with the Dockerfile half, is failed by `scripts/tests/test-docker-context.sh` until the `.mise.toml` half joins about a day later, and must not be merged before it holds both files and CI is green. All other keys of the rule are unchanged (`groupName`/`groupSlug` `uv`, `chore(uv)`, the `commitMessagePrefix`).
- Task 2: a fourth and last `packageRules` entry types `dockerfile` `digest` and `pinDigest` updates `chore`, with no scope, topic or prefix, so the preset's `container` scope and `image <name>` topic stay. No rule that names `patch`, `minor` or `major` sets a commit type; the uv rule's `chore(uv)` for every uv update is the one existing exception. `scripts/tests/test-renovate.sh` (new, mode 100755) pins both rules and the "no retyping" rule; it reads only `renovate.json` and does not depend on any uv version number. `scripts/tests/test-changelog.sh` gains one block (23 → 24) showing that `chore(container): update image node digest (...)` makes no note and `fix(container): update image ... (10.0.14 → 10.0.15)` does, with `cliff.toml` unchanged.
- Task 3: `RELEASING.md` says a uv pull request opens with only the Dockerfile change, is failed by `test-docker-context.sh` for about a day until the `.mise.toml` change joins, that this is expected, and not to merge it until it changes both files and CI is green; the `api/uv.lock` `revision` sentence is kept. The "What the image is built from" bullet now says a new image version is `fix(container)`/`feat(container)` and a release note, a new digest under the same tag is `chore(container)` and is not. No other line of `RELEASING.md` says the uv halves arrive together.
- Task 4 / AC 8: Renovate 44.251.0 config validator, `--no-global` from a scratch directory: "Validating ... as repo config", "Config validated successfully against 1 file(s)", exit 0; the worktree was unchanged by the run.
- AC 9, pull request #185 (`chore(uv): Update uv (0.13.8 → 0.13.9)`, `renovate/uv`): merged before this story, by the maintainer's decision, after the story was drafted (state `MERGED`, 2026-11-17T22:17:52Z, merge commit `a7e2e62` on `main`; both `.mise.toml` and `Dockerfile`; all six CI checks green). This story did not merge, close, rebase, comment on or push to it. Because it merged under the old rule, the new rule changes nothing for it; the Dev Notes timing note (a rebuilt red `renovate/uv` if the story merged first) no longer applies. The merge is not on this story's base (stacked on 21.1, which branches from before `a7e2e62`), so this branch still has uv 0.13.8 in `Dockerfile` and `.mise.toml`; the story leaves both files untouched (Task 5.3) and they come from `main` when the stack merges.
- No API contract change, no release note (all commits `chore` or `docs`), no E2E (nothing in the running product changes), no new dependency.
- Left for after the merge (Task 5.5, unchecked): (a) the first uv pull request under the new rule (Dockerfile half only, `test-docker-context.sh` red, `.mise.toml` half joining about a day later; if it never joins, a new maintainer decision is needed); (b) the first Dockerfile digest pull request's title starting `chore(container):` (AC 6). AC 6 and AC 7 are confirmed now only by the rules and the changelog test, not by a real Renovate pull request.

### File List

- `renovate.json` (modified: uv rule `description`, `minimumReleaseAge` removed; new digest rule)
- `scripts/tests/test-renovate.sh` (new)
- `scripts/tests/test-changelog.sh` (modified: one block)
- `RELEASING.md` (modified: `:57`, `:71`)
- `_bmad-output/implementation-artifacts/21-2-renovate-uv-hold-and-digests.md` (this story)

## Senior Developer Review (AI)

**Date:** 2026-11-17
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `38990a2..32022e6`
**Outcome:** Approve

**Summary:** ACs 1-5 and 7-10 met; AC 6 is post-merge by design. Every Renovate claim was verified against the live org preset (read with `gh api`):
- the one-day mise hold now reaches the `.mise.toml` uv half;
- the last-entry digest rule overrides the preset's `digest: fix` while keeping the `container` scope;
- version bumps keep `fix`/`feat`;
- GitHub Actions digest PRs stay `ci(github-action)`, which is not a release note;
- a uv-image digest refresh keeps `chore(uv)`.

The validator (Renovate 44.251.0, `--no-global`) passed, and four negative `renovate.json` variants each failed `test-renovate.sh` on the expected line. Reviewer ran `just test-scripts`, `just lint-scripts` and `just changelog` (no story commit listed), and checked PR #185 (merged at `a7e2e62` before this story).

### Action Items

- [x] [Low] L1 the new `RELEASING.md` sentence said every image version update is a release note, which is untrue for uv, a `chore(uv)` update since Story 20.7. Fixed by the controller: the sentence names the `node` and .NET images, and says a uv version update is `chore(uv)` and makes no note. The story's Dev Notes text had the same imprecision.
- Info: AC 6 and the real-PR half of AC 7 wait for the first uv and digest PRs after merge (Task 5.5).

## Change Log

- 2026-11-17: Story 21.2 created and validated (ready-for-dev).
- 2026-11-17: Implemented (Tasks 1-4, 5.1-5.4); status review. Task 5 stays open: 5.5 waits for the first uv and digest pull requests after the merge.
- 2026-11-17: Code review (GLM-5.3-Flash): approved; L1 fixed by the controller. Status done; Task 5.5 after merge.
