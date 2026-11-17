# Story 20.7: Reproducible Image Inputs and the Numbering Rule

Status: done

<!-- Implements FR255, FR256, FR257, Epic 20 ADR-10 and ADR-11. Beads: VSS-870 (INFRA-004), VSS-as6 (TOOLS-005), VSS-3q2s (DOCS-002, pulled in, Matt, 2026-11-17). Last story of Epic 20 (order 20.1 to 20.7, each stacked on the previous). Line references were verified at 7f04ea2 (epic-20-planning) and must be re-checked at implementation time: Stories 20.3 to 20.6 edit the Justfile, ci.yml and scripts/, and 20.6 adds VS_MOD_DB_URL, which Task 5 documents. Build, Renovate and documentation changes only: no file under api/src/ or web/src/ changes, no API contract change, no release note. No new dependencies. -->

## Story

As a **maintainer**,
I want **the image built from inputs that a commit names exactly, and the story numbering rule to say what we do**,
so that **a release build does not change without a commit, and the documentation stops contradicting the practice**.

## Acceptance Criteria

1. **Given** the Dockerfile
   **When** I read the line that copies uv
   **Then** it is `COPY --from=ghcr.io/astral-sh/uv:<version>@sha256:<digest> /uv /usr/local/bin/uv`, and `<version>` is the uv version `.mise.toml` pins (0.13.8 at 7f04ea2)
   *(Covers FR255; `VSS-870`)*

2. **Given** every `FROM` and `COPY --from` image in the Dockerfile (uv, `node:26-slim`, `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64`)
   **When** `just test-scripts` runs
   **Then** `scripts/tests/test-docker-context.sh` passes only if each of them ends in `@sha256:` and 64 hex digits and the uv tag equals the uv version in `.mise.toml`; the tags themselves are kept, and a reference to a build stage (`COPY --from=web-build`) is not counted as an image
   *(Covers FR255; Matt, 2026-11-17)*

3. **Given** the image built from the pinned Dockerfile
   **When** `just test-e2e-ci` runs locally and CI's `docker` and `e2e` jobs run on the pull request
   **Then** the build succeeds, uv in the image reports the `.mise.toml` version, and the E2E tests pass with the same counts as on the base branch
   *(Covers FR255)*

4. **Given** `renovate.json`
   **When** Renovate runs
   **Then** it proposes digest and version updates for the three images (the organisation preset is unchanged and already enables this once a digest is written), the uv image and the `uv` entry of `.mise.toml` move in one pull request (one new rule, group `uv`), the .NET runtime is still held below 11, the Python rule is unchanged, and the file passes Renovate's config validator
   *(Covers FR256; `VSS-870`)*

5. **Given** `RELEASING.md`
   **When** I read what a build is made from and what happens on a re-run of the image job
   **Then** it says which inputs are pinned (the three images by digest, bun by version, the API's dependencies by `uv.lock`, the web's by `bun.lock`), that `apt-get upgrade` stays and the system package layer can therefore still differ, so a re-run can push a different image digest, and that each run's attestations describe the digest that run pushed
   *(Covers FR255; Matt, 2026-11-17)*

6. **Given** `project-context.md`'s "Story Numbering" section
   **When** I read it
   **Then** it says a preparation story is numbered X.0, an epic without one starts at X.1, and a preparation story is optional; its table and historical note match what Epics 4 to 20 did (X.0 in Epics 4 to 8 and 13 to 16; 12.1 in Epic 12; no preparation story in Epics 9 to 11 and 17 to 20), and the Epic 13 retrospective item E13-A2 is kept as history
   *(Covers FR257; `VSS-as6`)*

7. **Given** `cliff.toml`, the BMAD story template and the sprint keys
   **When** the story is done
   **Then** none of them changed (`git diff <base>..HEAD -- cliff.toml _bmad/ _bmad-output/implementation-artifacts/sprint-status.yaml` is empty apart from the dev agent's status moves made with `just sprint`), and they agree with the rule
   *(Covers FR257)*

8. **Given** the pull-in `VSS-3q2s`
   **When** the story is done
   **Then** the environment table in `architecture/project-structure-boundaries.md` lists `VS_API_KEY`, `VS_CSP_MODE` and Story 20.6's `VS_MOD_DB_URL`, says `VS_DEBUG` also serves `/docs`, `/redoc`, `/openapi.json` and the RBAC test routes and allows a plain-HTTP mod database address, does not list `VS_GAME_VERSION`, points to the README for the full list, and the bead is closed with an AAR
   *(Covers FR257; pulled in, Matt, 2026-11-17)*

9. **Given** every existing test and check
   **When** `just check` runs
   **Then** it passes, with no lint or type suppression added; no commit of this story is `feat`, `fix` or `perf`, so `just changelog` shows no new entry from it

## Tasks / Subtasks

<!-- Commit per task: type(story-20.7/task-N): ... . Types are fixed for this story: build (Task 1), chore (Task 2), docs (Tasks 3-5). No feat/fix: nothing here is a release note. Red first in Task 1. -->

- [x] Task 1: Pin the three images by digest, uv to the `.mise.toml` version, and the script test that holds it (AC: 1, 2, 3) (`VSS-870`)
  - [x] 1.1: Red first. `scripts/tests/test-docker-context.sh`: add the assertions of Dev Notes "The script test" between the workflow-pin assertion (`:19-22`) and `finish` (`:24`). Run `just test-scripts test-docker-context.sh` against the unpinned Dockerfile and record in the Debug Log that it fails on "every Dockerfile image is pinned by digest" (listing all three images) and on the uv tag (`got ''`)
  - [x] 1.2: Look up the digests on the day you implement (Dev Notes "Digests"), read-only: `docker buildx imagetools inspect <image>:<tag>` for `ghcr.io/astral-sh/uv:<mise uv version>`, `node:26-slim` and `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64` (or whatever `.NET 10` tag the Dockerfile has after Renovate). Use the top-level `Digest:` line (the multi-platform index for uv and node; the .NET tag is a single amd64 manifest, so its digest is that manifest's). Record the three digests and the date in the Debug Log
  - [x] 1.3: `Dockerfile:9` → `FROM node:26-slim@sha256:<digest> AS web-build`; `:36` → `FROM mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64@sha256:<digest> AS final`; `:51` → `COPY --from=ghcr.io/astral-sh/uv:0.13.8@sha256:<digest> /uv /usr/local/bin/uv`. Keep each tag exactly; change no other line. Update the comment at `:50` to say the uv version must equal `.mise.toml`'s and Renovate moves both together, and the one at `:35` only if it no longer reads right (it names Renovate's hold, which still applies)
  - [x] 1.4: `just test-scripts` passes (all files). Negative checks, reverted afterwards: with `uv:latest` restored the new assertions fail; with the uv tag changed to another version the uv assertion fails. `just lint-scripts` passes
  - [x] 1.5: Build and run the CI E2E set on the pinned image: `just test-e2e-ci` (it builds `--platform linux/amd64` as its own throwaway image and container on port 18080 and does not touch the dev stack on 8080). Record the test counts and compare them with the base branch's last CI run. Then confirm uv in the built image: `docker run --rm --platform linux/amd64 --entrypoint uv vintagestory-server:e2e --version` prints the `.mise.toml` version (`scripts/e2e-ci.sh:42-46` builds and keeps that tag when `E2E_IMAGE` is unset; its cleanup removes only the container). Do not rebuild or restart the dev stack; do not start or stop the game server
  - [x] 1.6: Commit `build(story-20.7/task-1): pin the Dockerfile's images by digest and copy the uv that .mise.toml pins` (Dockerfile and the script test together, as the epic plan requires)

- [x] Task 2: The Renovate rule that groups uv (AC: 4) (`VSS-870`)
  - [x] 2.1: `renovate.json`: append the rule of Dev Notes "Renovate" as the third entry of `packageRules` (`:6-17`), after the .NET rule. Edit by hand and keep the existing rules' formatting (one-line arrays); do not reformat the file with a JSON tool
  - [x] 2.2: Validate: `python3 -m json.tool renovate.json >/dev/null`, and Renovate's own validator run from a scratch directory outside the repo (it downloads Renovate; nothing is added to the project): `cd <scratch dir> && bunx --package renovate renovate-config-validator --no-global <repo>/renovate.json` → "Validating renovate.json as repo config ... Config validated successfully". Use `--no-global` (without it, Renovate 44 validates a named file as global config) and run under Node, not `bunx --bun` (Bun 1.4.4 crashed running Renovate 44 in planning). Record the Renovate version (`bunx --package renovate renovate --version`)
  - [x] 2.3: Do not change the organisation preset (`craquehouse/renovate-config`) or add `docker:pinDigests`: the digests are written by Task 1 and the preset's `config:recommended` keeps existing digests current (Dev Notes "Renovate")
  - [x] 2.4: Commit `chore(story-20.7/task-2): move uv in the Dockerfile and .mise.toml in one Renovate pull request`

- [x] Task 3: `RELEASING.md`: what a build is made from and what a re-run can change (AC: 5) (`VSS-870`)
  - [x] 3.1: Add a short subsection "What the image is built from" at the end of "What the workflow publishes" (after `:67`, before "First release" at `:69`), with the content of Dev Notes "RELEASING.md"
  - [x] 3.2: The re-run bullet (`:75`): add that the re-run builds the image again, so it can push a different digest when Ubuntu has published package updates since the first run (the apt layer), and the attestations it pushes describe that digest; link to the new subsection
  - [x] 3.3: `:57` ("After Renovate updates uv ..."): say Renovate updates uv in `.mise.toml` and the Dockerfile in one pull request; keep the `uv.lock` `revision` sentence
  - [x] 3.4: Commit `docs(story-20.7/task-3): say what the release image is built from and what a re-run can change`

- [x] Task 4: Rewrite the "Story Numbering" section of `project-context.md` (AC: 6, 7) (`VSS-as6`)
  - [x] 4.1: Replace `project-context.md:834-847` (from `### Story Numbering` to the "Historical Note" paragraph, up to but not including `### File List Tracking` at `:849`) with the text of Dev Notes "The numbering section". Keep the heading and its place under "Story Conventions"
  - [x] 4.2: Check the history against `sprint-status.yaml` before committing: `grep -nE '^\s+[0-9]+-(0|1)-' _bmad-output/implementation-artifacts/sprint-status.yaml` (Dev Notes "Numbering history" has the output at 7f04ea2)
  - [x] 4.3: `git grep -n -i "story 0\|never Story 0\|uses Story 1"` over `project-context.md`, `CLAUDE.md`, `README.md`, `RELEASING.md` and `agentdocs/` prints nothing that contradicts the rule. Do not edit `cliff.toml`, anything under `_bmad/`, any story file or any sprint key (AC 7)
  - [x] 4.4: Commit `docs(story-20.7/task-4): a preparation story is X.0 and an epic without one starts at X.1`

- [x] Task 5: Pull-in: the architecture's environment table, with `VS_MOD_DB_URL` (AC: 8) (`VSS-3q2s`)
  - [x] 5.1: Confirm Story 20.6 has landed on this branch's base: `grep -n mod_db_url api/src/vintagestory_api/config.py` finds the setting, and `README.md`'s Configuration table has a `VS_MOD_DB_URL` row. If not, stop and ask: the row must describe the setting as it was merged
  - [x] 5.2: `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md:462-468`: replace the three-row table with the table of Dev Notes "The environment table", taking the `VS_MOD_DB_URL` wording (default, `http` rule, what follows it) from the merged README row so the two agree. `VS_GAME_VERSION` is not listed today; check it stays out
  - [x] 5.3: Commit `docs(story-20.7/task-5): list VS_API_KEY, VS_CSP_MODE and VS_MOD_DB_URL in the architecture's environment table`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes; the diff adds no lint or type suppression and no `cast`; `git status --short` is clean after it
  - [x] 6.2: `just changelog` shows no entry from this story's commits (all are `build`, `chore` or `docs`)
  - [x] 6.3: AC 7 check: `git diff <base>..HEAD --stat -- cliff.toml _bmad/` prints nothing
  - [ ] 6.4: (status moves done by the dev agent; PR by the controller) Story status `review`, `just sprint set 20-7-reproducible-image-and-conventions review`, PR against the previous story's branch while its PR is open, otherwise `main`. The PR description says: no API contract change, no release note, the three digests and the date they were read, that the uv rule clears the preset's one-day hold for uv (Dev Notes "ADR against the code"), and that the digest change empties the shared image build cache once (the first CI run of the PR builds without cache, so its `docker` and `e2e` times are not comparable with 20.5 and 20.6's)
  - [ ] 6.5: CI on the PR: `Docker image` and `E2E tests` jobs pass (AC 3); record the run URL, the E2E test counts and the job time in the Completion Notes
  - [ ] 6.6: Close the three beads, each with an AAR first (`bd comments add`, then `bd close`, then `bd sync`; abbreviated AAR for these size-s beads) once the PR is merged or as the maintainer directs. `VSS-870`'s AAR names the three digests and the Renovate rule; `VSS-as6`'s names the decision (X.0); `VSS-3q2s`'s lists the rows added

## Dev Notes

### What changes, and why (verified at 7f04ea2)

- `Dockerfile:51` copies uv from `ghcr.io/astral-sh/uv:latest`, so the image's uv moves without a commit and can differ from the `uv = "0.13.8"` that `.mise.toml:3` pins for development and CI.
- `Dockerfile:9` `FROM node:26-slim` (a moving major-version tag, build stage only) and `Dockerfile:36` `FROM mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64` (a version tag that Microsoft pushes again when the base system is patched) have no digest. Either can change a build without a commit.
- `Dockerfile:41-48`: `apt-get update && apt-get upgrade -y && apt-get install ... python3.14 python3-pip` with no versions. **This stays** (ADR-10 decision 5, Matt, 2026-11-17): it brings security fixes newer than the base image. After this story it is the only input that can differ between two builds of one commit, and `RELEASING.md` says so.
- `Dockerfile:17` pins bun by version (`bun@1.4.4`, the same as `.mise.toml:4`). It is not an image and is not in scope; it is listed in `RELEASING.md` as a pinned input.
- `project-context.md:834-847` says epics never use Story 0 and that "Epic 12 onwards uses Story 1". Only Epic 12 did; Epics 13 to 16 used X.0, `cliff.toml:43` skips `story-X.0` scopes from release notes, and the BMAD template says X.0 (`_bmad/bmm/workflows/4-implementation/create-story/template-api-spike.md:9`, `workflow.yaml:24`).
- `project-structure-boundaries.md:462-468` lists three variables; it lacks `VS_API_KEY` (Epic 19 ADR-5), `VS_CSP_MODE` (ADR-6) and the debug-only docs (ADR-7), and Story 20.6's `VS_MOD_DB_URL`.

### Digests (read on 2026-11-17, for orientation only; read them again)

`docker buildx imagetools inspect`, top-level `Digest:`:

| Reference | Digest | Kind |
|---|---|---|
| `ghcr.io/astral-sh/uv:0.13.8` | `sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85` | OCI index (linux/amd64, linux/arm64 + attestations) |
| `node:26-slim` | `sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc` | OCI index (amd64, arm64, ...) |
| `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64` | `sha256:d507d1e0c1ec47006d52220262709c3ac1d39c1fa87bda6a9aa7930b04341450` | single Docker v2 manifest, amd64 only (the `-amd64` tag) |

- Pin the **index** digest for uv and node, not a per-platform manifest digest: Renovate tracks the digest of the tag, which is the index. The .NET tag has no index, so its single manifest digest is what Renovate tracks.
- `node:26-slim` is re-pushed often (its index was created 2026-11-11). Expect a different digest from the one above; that is the reason for the pin.
- The build is `linux/amd64` everywhere (`ci.yml:70` and `:92`, `release.yml:90`, `scripts/e2e-ci.sh:46`). On an arm64 Mac the build runs under emulation, as it does today.
- Planning prototype (discarded): the Dockerfile with these three pins built with `docker build --platform linux/amd64` (all three references resolved, every later layer cached, so the pinned digests were the ones the tags already pointed at), and `uv --version` in the image printed `uv 0.13.8 (x86_64-unknown-linux-musl)`. The prototype image was removed. No E2E run was made in planning.

### The script test (Task 1.1)

Add to `scripts/tests/test-docker-context.sh`, before `finish` (it already defines `dockerfile` at `:15` and sources `lib.sh` for `pass`, `fail`, `assert_eq`):

```bash
# Every image the Dockerfile builds from or copies from is pinned by digest, and the uv
# image's tag is the uv version .mise.toml pins (Epic 20 ADR-10)
images=$(sed -nE 's/^FROM[[:space:]]+([^[:space:]]+).*/\1/p; s/^COPY[[:space:]]+--from=([^[:space:]]+).*/\1/p' "$dockerfile")
stages=$(sed -nE 's/^FROM[[:space:]].*[[:space:]]AS[[:space:]]+([^[:space:]]+).*/\1/p' "$dockerfile")
external=$(grep -vxF -f <(printf '%s\n' "$stages") <<<"$images" || true)
assert_eq "the Dockerfile uses three images" 3 "$(grep -c . <<<"$external")"
unpinned=$(grep -vE '@sha256:[0-9a-f]{64}$' <<<"$external" || true)
assert_eq "every Dockerfile image is pinned by digest" "" "$unpinned"
mise_uv=$(sed -nE 's/^uv[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$SCRIPTS_DIR/../.mise.toml")
uv_tag=$(sed -nE 's|^ghcr\.io/astral-sh/uv:([^@]+)@.*|\1|p' <<<"$external")
if [[ -n $mise_uv ]]; then pass; else fail ".mise.toml pins uv"; fi
assert_eq "the uv image tag is the uv version .mise.toml pins" "$mise_uv" "$uv_tag"
```

- `COPY --from=web-build` names a build stage, not an image; the `stages` filter removes it. The count assertion (3) makes a parse that finds nothing, or a fourth image added without thought, fail instead of passing vacuously.
- The stage name is matched with an uppercase `AS`, as the Dockerfile writes it; no case-insensitive `sed` flag (they differ between GNU and BSD `sed`, and the tests run on macOS and in CI on Ubuntu).
- Prototyped in planning at 7f04ea2 on macOS: against the pinned Dockerfile 10/10 passed; against the unpinned one 8/10 (the digest assertion listed all three images, the uv assertion got `''`); with `uv:0.13.7@...` 9/10 (the uv assertion). `just lint-scripts` (ShellCheck 0.11.0, `-x`) passed. The 20.3 widening of `lint-scripts` covers this file already (`scripts/tests/*.sh`).
- This is a tripwire like the existing workflow-pin check (`:19-22`), not a substitute for the build: Task 1.5 builds and runs the image.

### Renovate (Task 2)

What exists:

- `renovate.json:3-5` extends `local>craquehouse/renovate-config` (its `default.json`): `config:recommended`, `docker:enableMajor`, `helpers:pinGitHubActionDigestsToSemver`, and the preset files `annotated`, `autoMerge`, `groups`, `labels`, `semanticCommits`; plus `:automergeBranch`, `:dependencyDashboard`, `:disableRateLimiting`. No `docker:pinDigests`.
- `config:recommended`'s Dockerfile manager reads `FROM` and `COPY --from` images. Once a reference carries a digest, Renovate updates the digest when the tag is re-pushed and the tag and digest together for a new version; `docker:pinDigests` only matters for adding pins Renovate has not been given, which Task 1 writes by hand. So the preset needs no change (ADR-10 decision 3).
- The preset's `autoMerge.json5` holds every mise tool update for one day (`minimumReleaseAge: "1 day"`, `matchManagers: ["mise"]`). Its comment gives the reason: `mise lock` run before a release's assets are uploaded records no download URL and breaks `mise install --locked`. This repository has no `mise.lock` (only `.mise.toml`; CI installs with `jdx/mise-action`), so that reason does not apply here.
- Renovate cannot age a GHCR image: GHCR returns no release timestamps, and with the default `minimumReleaseAgeBehaviour: "timestamp-required"` an update that has a `minimumReleaseAge` but no timestamp is held **indefinitely** (Renovate docs, "Minimum Release Age": GHCR, Quay and ECR are listed as unsupported; the default was read from `lib/config/options/index.ts` on 2026-11-17).
- The preset's `semanticCommits.json5` types Docker updates `fix(container)` (patch, digest) and `feat(container)` (minor; `feat(container)!` for major), and mise updates `chore(mise)`. git-cliff turns `feat`/`fix` into release notes (`cliff.toml:45-46`; the `container` scope is hidden but the entry is kept), as already happened for `0383a11 fix(container): update image mcr.microsoft.com/dotnet/runtime (8.0.30 → 8.0.33)`.
- The preset's `groups.json5` matches `.mise/config.toml`, not this repo's `.mise.toml`; it has no rule for uv and is not involved.
- Renovate names the dependencies: Dockerfile manager, depName `ghcr.io/astral-sh/uv` (image name without tag or digest); mise manager, depName `uv` (from the mise registry).

The rule, appended after the .NET rule (keep the existing two rules byte for byte):

```json
    {
      "description": "Move uv in the Dockerfile (ghcr.io/astral-sh/uv) and in .mise.toml (uv) in one pull request, so the image, development and CI use one uv (Epic 20 ADR-10). No release-age hold: GHCR gives no release timestamps, so a hold would keep the image half back for ever or let it open alone; the preset's one-day hold on mise tools exists for mise.lock, which this repository does not have. A uv update is tooling, not a release note: chore, with no breaking mark",
      "matchDepNames": ["uv", "ghcr.io/astral-sh/uv"],
      "groupName": "uv",
      "groupSlug": "uv",
      "minimumReleaseAge": null,
      "semanticCommitType": "chore",
      "semanticCommitScope": "uv",
      "commitMessagePrefix": "{{semanticCommitType}}({{semanticCommitScope}}):"
    }
```

Why each key:

- `matchDepNames` + `groupName`/`groupSlug`: one branch and pull request (`renovate/uv`) for both files. Repository rules apply after the preset's, so these keys win.
- `minimumReleaseAge: null`: the two halves must become ready at the same moment, and the image half cannot be aged. Left alone, the preset's one-day hold applies to the mise half only, so the group would open with only the Dockerfile change and fail Task 1's test (uv tag ≠ `.mise.toml`) for a day. A one-day hold on both is worse: the GHCR half would then be held for ever (`timestamp-required`), and with `minimumReleaseAgeBehaviour: "timestamp-optional"` it would again open alone. Clearing the hold for uv only is safe here because the hold's reason is `mise.lock`, which this repository does not have. If a `mise.lock` is ever added, revisit this rule. This is a deliberate exception to the organisation preset for one tool; the maintainer sees it in the PR (Task 6.4).
- `semanticCommitType`/`Scope`/`commitMessagePrefix`: without them a uv minor release would be committed as `feat(container): ...` from the Docker half and appear under **Features** in the release notes, though uv in the image is not something a user sees (`CLAUDE.md`: commit types are release notes). The prefix overrides the preset's major-update `!:` prefix the same way the preset's own mise rule does.
- Base image digest updates (`node`, `.NET`) are deliberately not touched: see "Not changed".

Validated in planning (a copy of `renovate.json` with this rule, in a scratch directory outside the repo): Renovate 44.251.0, `bunx --package renovate renovate-config-validator --no-global renovate.json` → "Validating renovate.json as repo config ... Config validated successfully against 1 file(s)". Use the current Renovate in Task 2.2 (no version pin needed; it is a one-off check, not a dependency).

### RELEASING.md (Task 3)

Content for "What the image is built from" (wording is the dev's; keep it short and plain):

- Pinned, so a re-run uses the same: the three images by digest (`node` for the web build, the .NET runtime base, the uv binary), bun by version, the API's Python packages by `api/uv.lock` and the web's by `web/bun.lock`; uv's version is the one `.mise.toml` pins, and a script test (`scripts/tests/test-docker-context.sh`) fails if any image loses its digest or the uv versions differ. Renovate moves the pins in pull requests that CI builds and tests.
- Not pinned: the system packages. The image runs `apt-get upgrade` and installs `python3.14` from Ubuntu without versions, so it picks up security fixes newer than the base image. Two builds of one commit can therefore differ in that layer.
- So a re-run of the image job builds again and can push a different image digest under the same tags; each run's provenance and SBOM attestations describe the digest that run pushed (a user verifying an image checks the attestation of the digest they pulled, as the README describes).

### The numbering section (Task 4)

Replace `project-context.md:834-847` with (wording may be tightened; the facts may not change):

```markdown
### Story Numbering

**A preparation story is Story X.0. An epic without one starts at Story X.1.**

A preparation story (research, a spike, architecture work before the first feature) is optional. Add one only when the planning says what it must find out; it ships nothing a user sees, and X.0 says so at a glance. Feature stories are numbered from X.1 either way.

| Epic | First story |
|------|-------------|
| Needs preparation | `13-0-epic-13-technical-preparation`, then `13-1-...` |
| Needs none | `17-1-mod-detail-pages-cannot-fail-on-bad-data` |

**Why X.0:** the release notes configuration (`cliff.toml`) keeps `story-X.0` commits out of the notes, the BMAD story template names the spike Story X.0, and done stories cannot be renumbered.

**History:** Epics 4 to 8 and 13 to 16 numbered their preparation story X.0. Epic 12 numbered it 12.1, following the Epic 13 retrospective item E13-A2 ("Eliminate Story 0 naming"), which this rule replaces (Epic 20 ADR-11). Epics 9 to 11 and 17 to 20 had no preparation story and started at X.1. Epics 1 to 3 predate preparation stories.
```

- Keep the table in the same Markdown style as the rest of the file (pipes, header separator). No ✅/❌ emoji needed.
- E13-A2 is recorded in `_bmad-output/implementation-artifacts/epic-13-retro-2026-01-14.md:125` and marked done in `epic-12-retro-2026-01-18.md:47` (the Epic 13 retrospective predates Epic 12's by date; that is history, not a fault to fix).

### Numbering history (`sprint-status.yaml` at 7f04ea2)

`grep -nE '^\s+[0-9]+-(0|1)-' sprint-status.yaml`: X.0 keys for Epics 4, 5, 6, 7, 8, 13, 14, 15, 16; `12-1-epic-12-technical-preparation` for Epic 12; first keys `9-1`, `10-1`, `11-1`, `17-1`, `18-1`, `19-1`, `20-1` with no preparation story; Epics 1 to 3 start at `X-1` (initial build-out). This matches ADR-11 decision 3.

### The environment table (Task 5)

`project-structure-boundaries.md:462-468` today:

```
| `VS_API_KEY_ADMIN`   | Yes      | Admin API key                  |
| `VS_API_KEY_MONITOR` | No       | Read-only API key              |
| `VS_DEBUG`           | No       | Enable debug logging           |
```

New table (descriptions condensed from `README.md:77-82` and Story 20.6's README row; check them against the merged code: `config.py` `Settings` at `:17-33`, `main.py:323-325` for `/docs`, `/redoc`, `/openapi.json`, `main.py:374-375` for the RBAC test router):

| Variable | Required | Description |
|---|---|---|
| `VS_API_KEY_ADMIN` | Yes | Admin API key |
| `VS_API_KEY_MONITOR` | No | Read-only API key |
| `VS_API_KEY` | For the web UI | Key the API serves to the web UI at `/config.js` (Epic 19 ADR-5); unset, the web UI shows a set-up message |
| `VS_CSP_MODE` | No | `enforce` (default), `report-only` or `off` for the web UI's Content-Security-Policy (Epic 19 ADR-6); any other value stops start-up |
| `VS_DEBUG` | No | Debug logging; also serves `/docs`, `/redoc` and `/openapi.json` and the RBAC test routes (Epic 19 ADR-7), and allows a plain-HTTP `VS_MOD_DB_URL`. For development only |
| `VS_MOD_DB_URL` | No | Base address of the mod database for API requests and mod downloads (default `https://mods.vintagestory.at`; Epic 20 ADR-9). `https` only, `http` only with `VS_DEBUG=true`; the image hosts and links shown to a browser do not follow it |

Add one line under the table: the full list, with `VS_CORS_ORIGINS`, `VS_DATA_DIR`, `VS_LOG_LEVEL` and the rest, is in the README's Configuration table and `.env.example`. `VS_GAME_VERSION` is not in today's table and must not be added (removed in Epic 19, FR209).

### Existing tests that change

- `scripts/tests/test-docker-context.sh`: gains four assertions (Task 1.1). No existing assertion changes. It fails against the Dockerfile at 7f04ea2 by design (red first), and passes after Task 1.3.
- No API, web or E2E test changes. No other script test reads the Dockerfile (`grep -rn Dockerfile scripts/ .github/workflows/` at 7f04ea2: only `test-docker-context.sh:15-16`).

### E2E

There is no user-visible change, so no new spec. The E2E check of this story is that the existing CI set passes against the image built from the pinned Dockerfile: locally with `just test-e2e-ci` (a throwaway container on `127.0.0.1:18080`, built from the worktree; it does not touch the dev stack on 8080 and starts no game server) in Task 1.5, and in CI's `e2e` job in Task 6.5. Compare the counts with the previous story's CI run (after Stories 20.5 and 20.6 the set is larger than 19.7's 113 + 3). No screenshots.

### Manual check

None beyond Task 1.5 (uv version in the built image). Nothing in the running product changes.

### Not changed (do not "fix" these here)

- `apt-get upgrade` and the unpinned `python3.14`/`python3-pip` (ADR-10 decision 5). A dated Ubuntu snapshot is a larger change with its own upkeep.
- The organisation preset `craquehouse/renovate-config` (its `groups.json5` path `.mise/config.toml`, its commit types). ADR-10 decision 3: not changed.
- Renovate's commit type for base image digest updates (`fix(container)`): a re-pushed `node:26-slim` (build stage only) will now arrive as a pull request whose commit becomes a **Fixes** release note. Not changed here; reported as a follow-up (see "ADR against the code").
- `Dockerfile:17` (`npm install -g bun@1.4.4`) and its pairing with `.mise.toml`'s bun: not an image, not in ADR-10.
- `project-context.md:21` ("Base Container: `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64`"): still true; the tag is kept.
- `cliff.toml`, `_bmad/` (template and `workflow.yaml` already say X.0), every sprint key and story file (ADR-11 decision 4).
- The rest of `project-structure-boundaries.md` (its compose snippets at `:207-266` without `VS_API_KEY`, the Dockerfile summary at `:428-436` naming Ubuntu 24.04, Python 3.12, .NET 8 and bun 1.3.5): stale, but outside `VSS-3q2s`'s table. Reported as a follow-up.
- The image tags the release workflow pushes, the attestations, and `ci.yml`'s jobs and cache settings.

### API contract changes

None. No route, response field, error code or setting changes. (Story 20.6's `VS_MOD_DB_URL` is documented here, not added.)

### ADR against the code

- ADR-10 decision 3 describes the preset as "`config:recommended` with `helpers:pinGitHubActionDigestsToSemver` and without `docker:pinDigests`". It also extends `docker:enableMajor` and a `semanticCommits` preset that types Docker digest and patch updates `fix(container)` and minor updates `feat(container)`. Two consequences the ADR does not state: (a) without a commit type in the uv rule, a uv minor release would become a **Features** release note; this story sets `chore(uv)` in its rule (Dev Notes "Renovate"); (b) base image digest refreshes, which this story makes visible as pull requests, will each become a **Fixes** release note. (b) is left as it is: a .NET base rebuild is a security update users may care about, and whether a build-stage `node` digest belongs in the notes is the maintainer's call (follow-up).
- ADR-10 decision 3 does not mention the preset's one-day hold on mise updates or that GHCR images cannot be aged. With the hold applying to one half only, the uv group would open with only the Dockerfile half and fail Task 1's test for a day; a hold on both would hold the GHCR half for ever. The rule clears the hold for uv (`minimumReleaseAge: null`), justified by the absence of a `mise.lock` (Dev Notes "Renovate"). Ask the maintainer in the PR whether he prefers the alternative: keep the hold and accept a red uv pull request for its first day.

### Testing Requirements

- `just test-scripts` (all script tests), `just lint-scripts`, `just check`.
- `just test-e2e-ci` once locally on the pinned Dockerfile (Task 1.5); CI `docker` and `e2e` jobs on the PR (Task 6.5).
- Renovate config validator once (Task 2.2).
- No test may write into `dev/`; this story runs no API test that could.

### Security Requirements

- Digest pins are a supply-chain control: the image's inputs change only through a reviewed commit. Never pin by copying a digest from anywhere but `docker buildx imagetools inspect` (or the registry) on the day of the change.
- No instance-specific value (server name, password, key) in the story, the PR or the AAR.

### Development Commands

```bash
docker buildx imagetools inspect ghcr.io/astral-sh/uv:0.13.8   # read-only
just test-scripts test-docker-context.sh
just test-scripts
just lint-scripts
just test-e2e-ci
just check
just changelog
```

### Previous Story Intelligence

- 19.7 built `scripts/e2e-ci.sh` (throwaway container, `--platform linux/amd64`, vendor hosts blocked) and the `e2e` job; Stories 20.5 and 20.6 extend it. This story only changes what the image is built from; it does not touch the script or the job.
- 19.7's review: tripwire tests pin values in the repo's style (`test-release.sh`), and a guard should fail on the old file (here: red first in Task 1.1).
- 15.5's review is where `VSS-870` came from (re-runs can push a different digest); 15.2 wrote `test-docker-context.sh` for the build context.
- Learnings that apply: a completion note must be true of the code (record the actual digests and counts, not the planning ones); a `feat`/`fix` subject must describe something an admin can see, which is why every commit here is `build`, `chore` or `docs`.

### Git Intelligence

- Renovate commits already in history: `2f2d40f chore(mise): Update tool uv (0.13.7 → 0.13.8)`, `41d6f25 feat(container)!: Update image node (22.23.4 → 26.13.0)`, `0383a11 fix(container): update image mcr.microsoft.com/dotnet/runtime (8.0.30 → 8.0.33)`, `66c4b21 chore(renovate): hold the .NET runtime below 11 ...` (the last is the style for a hand edit of `renovate.json`).

### Project Structure Notes

Files touched: `Dockerfile`, `scripts/tests/test-docker-context.sh`, `renovate.json`, `RELEASING.md`, `project-context.md`, `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`, this story file. Nothing under `api/`, `web/`, `.github/`, `_bmad/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.7: Reproducible Image Inputs and the Numbering Rule]
- [Source: _bmad-output/planning-artifacts/prd.md] FR255, FR256, FR257
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md#ADR-10, #ADR-11, "Facts Checked in the Code" (Image, Story numbering)]
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md] ADR-5 (`VS_API_KEY`), ADR-6 (`VS_CSP_MODE`), ADR-7 (docs follow `VS_DEBUG`)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md] answers 8 and 9, pull-in 2, "Seen and left alone" 3
- [Source: _bmad-output/implementation-artifacts/19-7-e2e-runs-in-ci.md]
- Organisation preset: `craquehouse/renovate-config` (`default.json`, `autoMerge.json5`, `semanticCommits.json5`, `groups.json5`), read 2026-11-17

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive

### Debug Log References

- Task 1.1 (red, before the Dockerfile change): `just test-scripts test-docker-context.sh` → 8/10. "every Dockerfile image is pinned by digest" got `node:26-slim`, `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64`, `ghcr.io/astral-sh/uv:latest`; "the uv image tag is the uv version .mise.toml pins" expected `0.13.8`, got `''`.
- Task 1.2, digests read 2026-11-17 with `docker buildx imagetools inspect` (top-level `Digest:`), the same as at planning:
  - `ghcr.io/astral-sh/uv:0.13.8` → `sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85` (OCI index)
  - `node:26-slim` → `sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc` (OCI index)
  - `mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64` → `sha256:d507d1e0c1ec47006d52220262709c3ac1d39c1fa87bda6a9aa7930b04341450` (single Docker v2 manifest)
- Task 1.4 negative checks (Dockerfile restored from a copy afterwards): `uv:latest` → 8/10 (digest assertion lists `ghcr.io/astral-sh/uv:latest`, uv assertion got `''`); `uv:0.13.7@sha256:...` → 9/10 (uv assertion got `0.13.7`). `just lint-scripts` passed.
- Task 1.5: `just test-e2e-ci` on the pinned Dockerfile: first pass 119 passed, API E2E 3 passed, replay pass 27 passed, exit 0; the same counts as Story 20.6's CI run 44137431816 (119 + 3, 27). `docker run --rm --platform linux/amd64 --entrypoint uv vintagestory-server:e2e --version` → `uv 0.13.8 (x86_64-unknown-linux-musl)`. The `vintagestory-server:e2e` image was removed afterwards; the dev stack was not rebuilt or restarted.
- Task 2.2: `python3 -m json.tool` OK; from a scratch directory, `bunx --package renovate renovate-config-validator --no-global <repo>/renovate.json` → "Validating ... as repo config", "Config validated successfully against 1 file(s)"; Renovate 44.251.0.
- Task 4.2: the `sprint-status.yaml` grep matches Dev Notes "Numbering history". Task 4.3: the only hit is the new History line quoting E13-A2.

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive, base 7f04ea2) and validated against the create-story checklist. Prototypes, discarded: the three pins in the Dockerfile (built `--platform linux/amd64` with a distinct tag, uv 0.13.8 confirmed in the image, image removed); the script test (10/10 pinned, 8/10 unpinned, 9/10 with a wrong uv tag; ShellCheck clean); the Renovate rule (Renovate 44.251.0 validator, `--no-global`: "Config validated successfully"). No E2E run in planning.

- Implemented 2026-11-17. Line numbers had moved since 7f04ea2 (the story section is now `project-context.md:862-876`; `renovate.json`'s `packageRules` is at `:16-27` after a `customManagers` block for semgrep); the edits went to the same places.
- Task 1: the three images pinned by digest with tags kept, uv at the `.mise.toml` version 0.13.8, the uv comment says the versions must match and Renovate moves both. Four assertions added to `test-docker-context.sh` (red first, then 10/10).
- Task 2: the uv rule appended as the third `packageRules` entry, as drafted (`minimumReleaseAge: null`, `chore(uv)`); the existing rules are unchanged. Open question for the maintainer: keep the one-day hold and accept a red uv pull request on its first day, instead of clearing the hold for uv?
- Task 3: `RELEASING.md` has "What the image is built from" (pinned inputs, the apt layer that is not pinned, a re-run can push another digest and its attestations describe that digest), the re-run bullet links to it, and the uv sentence says Renovate moves `.mise.toml` and the Dockerfile in one pull request.
- Task 4: "Story Numbering" rewritten with the drafted text.
- Task 5: the environment table has the six rows of Dev Notes; the `VS_MOD_DB_URL` row follows the README row and `.env.example` (mirror of the same database, listings and downloads, `https` with a host only, `http` only with `VS_DEBUG=true`, other values stop start-up, images and mod page links do not follow it). `VS_GAME_VERSION` is not listed. Deviation: the line under the table does not say the README has "the full list with `VS_LOG_LEVEL`": `VS_LOG_LEVEL` and the other tuning settings exist in `config.py` but the README and `.env.example` do not document them, so the line names `VS_CORS_ORIGINS` and `VS_DATA_DIR` and says the rest have defaults and are undocumented.
- Task 5, backlog drawdown at the controller's direction (overrides "Not changed"): in the same file, both compose snippets now match `docker-compose.yaml` and `docker-compose.dev.yaml` (`VS_API_KEY`, `VS_API_KEY_ADMIN` default `changeme`, 42420 tcp and udp), and the Dockerfile summary names node 26, bun 1.4.4, the .NET 10 Resolute base, Python 3.14, the digest pins and uv from `.mise.toml`. Docs only; committed with Task 5 (the commit subject names only the table).
- Task 6: `just check` green: API 3,387 passed, web 3,307 passed in 132 files (0 skipped), Pyright 0 errors 0 warnings, all script tests passed (`test-docker-context.sh` 10/10). No suppression or `cast` in the diff. `just changelog` shows no entry from this story. `git diff 6448965..HEAD -- cliff.toml _bmad/` is empty. Not done here (controller): the PR (6.4), CI `Docker image` and `E2E tests` (6.5), and closing the beads after merge (6.6). No bead was changed.

- CI (controller, 2026-11-17, PR #184), run https://github.com/craquehouse/vintagestory-server/actions/runs/44140309114 on `7f10069`: all six jobs green. `Docker image` built the pinned image for linux/amd64 (1 min 13 s), and `E2E tests` passed both passes (4 min 14 s). This first run built without the shared layer cache for the new digests, so its times are not comparable with 20.5 and 20.6. Bead closes (VSS-870, VSS-as6, VSS-3q2s) are after merge.

### File List

- `Dockerfile`
- `scripts/tests/test-docker-context.sh`
- `renovate.json`
- `RELEASING.md`
- `project-context.md`
- `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`
- `_bmad-output/implementation-artifacts/20-7-reproducible-image-and-conventions.md`

## Senior Developer Review (AI)

**Date:** 2026-11-17
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `6448965..7f10069`
**Outcome:** Approve

**Summary:** All nine ACs are met with verified evidence. The reviewer re-read the three digests from the registries the same day. All were current for their tags and the right kind: indexes for uv and node, the single amd64 manifest for .NET. It reproduced every negative case of the script test in a scratch tree, and every variant fails closed. It re-ran Renovate's config validator (44.251.0) itself and checked the org preset through `gh api`. It confirmed the numbering history against `sprint-status.yaml` and every environment-table claim against `config.py` and `main.py`. Reviewer ran `just lint`, `just lint-scripts`, `just test-scripts` (`test-docker-context.sh` 10/10) and the validator.

### Action Items

- [x] [Minor] M1 the record said "five" new assertions; there are four (corrected).
- [x] [Minor] M2 and Info I3: `project-structure-boundaries.md` still said `ci.yaml` and summarised CI as three jobs. Fixed by the controller under the backlog-drawdown rule: the block now names `ci.yml` and its six jobs as they are.
- [x] Dev follow-up, folded in by the controller under backlog drawdown: the working tuning settings `VS_DATA_DIR` (table), `VS_CONSOLE_HISTORY_LINES`, `VS_DISK_SPACE_WARNING_THRESHOLD_GB` and `VS_MOD_CACHE_MAX_SIZE_MB` are now in the README's Configuration table and `.env.example`. `Settings.log_level` (`VS_LOG_LEVEL`) is NOT documented, because nothing reads it: the log level follows `VS_DEBUG` (`main.py:170`). That is reported to the maintainer as a question (remove the field or make it work).
- Info, not changed: the script test does not require a tag for node and .NET (Renovate handles digest-only references; tags are kept); hypothetical future Dockerfile shapes (`--platform`, ARG-substituted references) fail closed.

## Change Log

- 2026-11-17: Story 20.7 created and validated (ready-for-dev).
- 2026-11-17: Tasks 1-5 implemented, quality gate green; status review.
- 2026-11-17: Code review (GLM-5.3-Flash): approved; M1, M2 and I3 fixed, tuning settings documented. CI green on PR #184. Status done.
