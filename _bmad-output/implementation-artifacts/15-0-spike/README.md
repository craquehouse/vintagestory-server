# Story 15.0 Spike: Release Toolchain

Evidence for `architecture/epic-15-release-engineering.md`. Run on 2026-11-10 with git-cliff 2.14.2, uv 0.13.7, bun 1.4.4 and actionlint 1.7.12 (all through `mise exec`, without changing `.mise.toml`). Nothing was pushed or published.

| File | What it is |
|---|---|
| `cliff.toml` | Draft git-cliff configuration; Story 15.3 moves it to the repository root |
| `sample-notes-epic-14.md` | Notes generated for Epic 14 (`e9358b9..f32fc26`) with `cliff.toml` |
| `bump_test.sh` | Builds a throwaway repository and records `--bumped-version` and notes for each case |
| `bump_test.out` | Output of `bump_test.sh` |
| `release.yml` | Draft release workflow; passes `actionlint`; not installed in `.github/workflows/` |

Rerun:

```bash
SP=_bmad-output/implementation-artifacts/15-0-spike
mise exec git-cliff@2.14.2 -- git cliff --config $SP/cliff.toml e9358b9..f32fc26 > $SP/sample-notes-epic-14.md
$SP/bump_test.sh $SP/cliff.toml "$TMPDIR/bumprepo" > $SP/bump_test.out
mise exec actionlint@1.7.12 -- actionlint $SP/release.yml
```

## 1. Changelog from this history (ADR-2)

- Scopes are hidden in the template, not by a preprocessor, so commit parsers can still see them. Shown only for the allowlist `api`, `web`, `docker`. Other scopes are inconsistent (`ui`, `frontend`, `container`, `deps`, `VSS`, `auth`) or BMAD bookkeeping (`story-*`: 270 of the ~420 `feat`/`fix` commits).
- Epic 14 range: 58 `feat`/`fix` commits. With the type and scope rules alone, all 58 appear, and about 15 are process entries ("Validate and move story 14.2 to review", "Record spike findings…", "Resolve low-severity review findings in ADRs…").
- Two safety-net parsers drop bookkeeping: scope `story-N.0` (preparation stories are research and docs) and messages matching `move story X.Y to review`. Result: 43 entries (`sample-notes-epic-14.md`). Remaining noise: "Fix line length in update rule tests", "Resolve code review findings for update checks".
- **Root cause:** the `dev-story` workflow (`_bmad/bmm/workflows/4-implementation/dev-story/instructions.xml` step 8) and `project-context.md` require every task commit to match `feat(story-X.Y/task-N)`, whatever the change. Filters cannot tell a user-facing task from a bookkeeping one. Readable notes need task commits typed by user impact (`feat`/`fix`/`perf` only for user-visible changes; `docs`, `test`, `chore`, `refactor` otherwise). This is a process decision for the maintainer.
- Non-conventional commits (merges, "Add renovate.json", "VSS-arp: …") are dropped with a "parse error" warning; expected with `filter_unconventional = true`.
- Breaking changes: both `type!:` and a `BREAKING CHANGE:` footer are detected, and `protect_breaking_commits = true` keeps a breaking commit of a skipped type (`refactor!: drop old endpoint` appears under Breaking Changes).
- Each entry links its commit: `https://github.com/craquehouse/vintagestory-server/commit/<sha>` built from `commit.id` in the template; no GitHub token needed.

## 2. Version bumps (ADR-2, ADR-3)

From `bump_test.out`, with `features_always_bump_minor = true`, `breaking_always_bump_major = false`:

| From | Commits | Next |
|---|---|---|
| no tags | anything | `v0.1.0` (`initial_tag`) |
| `v0.1.0` | `docs` only | `v0.1.0` (unchanged: nothing to release) |
| `v0.1.0` | `fix`, `perf` | `v0.1.1` |
| `v0.1.0` | + `feat` | `v0.2.0` |
| `v0.1.0` | + `refactor!` | `v0.2.0` |
| `v0.2.0` | `feat` with `BREAKING CHANGE` footer | `v0.3.0` |
| `v0.2.0` | explicit `--bump patch` / `minor` / `major` | `v0.2.1` / `v0.3.0` / `v1.0.0` |

- **Nothing to release:** `--bumped-version` returns the current tag unchanged. The release command must treat "next equals last tag" as nothing to release.
- **Pre-release tags:** with the default tag pattern, a `v0.3.0-rc.1` tag becomes the base: the next fix computes `v0.3.0-rc.2` and stable notes cover only commits after the rc. With `tag_pattern = "^v[0-9]+\.[0-9]+\.[0-9]+$"`, pre-release tags are invisible: bumps and `--unreleased` notes run from the last stable tag, so `v0.3.0`'s notes include everything since `v0.2.0`. `--ignore-tags` does not achieve this for `--unreleased`.
- `--latest` uses the newest matching tag in the repository, not `HEAD`; the workflow should take notes from `CHANGELOG.md` at the tag instead.

## 3. Version files and package metadata (ADR-1, ADR-3)

- **Inside the image** (`docker build --target final`, amd64 under emulation): `importlib.metadata.version("vintagestory-api")` returns `0.1.0`, both with `uv run --no-sync` and after `uv run`'s own sync. ADR-1 holds.
- **Bug found (`VSS-flj`):** the build-time `uv sync --frozen --no-dev` runs before `src/` is copied, so the project is not importable from the build-time install, and the CMD `uv run uvicorn …` re-syncs at every container start using the default groups, which include `dev`. It reinstalls the project and downloads pytest, playwright, coverage, respx and other dev packages from PyPI. With `--network none`, start-up fails with a DNS error (`respx … was included because vintagestory-api:dev depends on respx`). The image needs network access to start, starts slower, and runs with dev packages installed.
- **`uv version X.Y.Z --no-sync`** sets `[project].version` and the matching `uv.lock` entry; on a scratch copy the diff was exactly those two lines (no dependency changes). It normalizes to PEP 440: `0.2.0-rc.1` is written as `0.2.0rc1`, and package metadata reports `0.2.0rc1`.
- **`bun pm version X.Y.Z --no-git-tag-version`** sets `web/package.json` only; no commit, no tag, `bun.lock` unchanged. It keeps SemVer form (`0.2.0-rc.1`).
- Consequence: for pre-releases the two files hold different spellings of one version. Version checks must compare the PEP 440 normalization (SemVer `-alpha.N`, `-beta.N`, `-rc.N` → `aN`, `bN`, `rcN`); the API reports the PEP 440 form.

## 4. GHCR publishing and attestations (ADR-4)

Latest releases and commit SHAs on 2026-11-10 (for pinning):

| Action | Release | SHA |
|---|---|---|
| `docker/login-action` | v4.8.0 | `8aa5831fb8d48d8f76594c7ddde61ae58019f550` |
| `docker/metadata-action` | v6.2.0 | `dc802804100637a589fabce1cb79ff13a1411302` |
| `docker/setup-buildx-action` | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` |
| `docker/build-push-action` | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` |
| `actions/attest` | v4.2.2 | `1e69f48acb82d1966a394da916b4c1698aa569d6` |
| `anchore/sbom-action` | v0.24.3 | `66cbf4bc1f1c0d2edc94016e65bc221b6bb0ad6c` |
| `actions/upload-artifact` | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| `actions/download-artifact` | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` |

- **Attestation action changed:** `actions/attest-build-provenance` v4 is a wrapper around `actions/attest`, whose README says new workflows should use `actions/attest`; `actions/attest-sbom` is deprecated in its favor. `actions/attest` with only a subject creates build provenance; with `sbom-path` it creates an SBOM attestation. For an image: `subject-name: ghcr.io/craquehouse/vintagestory-server` (no tag), `subject-digest` from build-push-action's `digest` output, `push-to-registry: true`.
- **Permissions** for the image job: `contents: read`, `packages: write`, `id-token: write`, `attestations: write`, and `artifact-metadata: write` (needed by `actions/attest`'s storage record, which defaults on with `push-to-registry`). Release job: `contents: write`.
- **Availability:** artifact attestations are available for public repositories on every plan; this repository is public.
- **Verify:** `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:X.Y.Z --owner craquehouse` (or `-R craquehouse/vintagestory-server`).
- **metadata-action** with `type=semver,pattern={{version}}` and `type=semver,pattern={{major}}.{{minor}}` and default `latest=auto`: `v0.2.3` → `0.2.3`, `0.2`, `latest`; `v0.1.0` → `0.1.0`, `0.1`, `latest`; `v0.2.0-rc.1` → `0.2.0-rc.1` only (README: "Pre-release … will only extend `{{version}}`"; its semver example for a beta tag lists no `latest`). No `{{major}}` pattern is used, so the README's "major version zero" caveat does not apply. Give `{{version}}` the higher `priority` so the `org.opencontainers.image.version` label is the full version. Labels include `source`, `version`, `revision`, `created` (NFR18). These are from the README; Story 15.5's release-candidate run confirms them.
- **buildx attestations:** on a public repository build-push-action adds `mode=max` provenance by default and no SBOM. The draft sets `provenance: false` and `sbom: false` so the signed GitHub attestations are the single source, and the image index carries no attestation manifests.
- **SBOM:** `anchore/sbom-action` with `image: <image>@<digest>`, `format: spdx-json`, `output-file`, and `upload-artifact: false`, `upload-release-assets: false` (it would otherwise try to upload on its own); the workflow attests the file and attaches it to the release.
- **Package visibility:** a package first published from a workflow with `GITHUB_TOKEN` is private and linked to the workflow's repository automatically. Making it public is a manual step: package settings → Danger Zone → Change visibility → Public (irreversible). If a package of the same name already exists unlinked, `GITHUB_TOKEN` cannot push to it. Verify on GHCR before the first release (the earlier `gh api` lookup returned 404 for this package, but that token lacked `read:packages`).
- **Draft workflow:** `release.yml` runs verify → image → release, each with its own least-privilege permissions, all actions SHA-pinned; `actionlint` reports no issues.
