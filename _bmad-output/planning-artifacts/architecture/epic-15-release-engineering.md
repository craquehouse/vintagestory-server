# Epic 15: Release Engineering Architecture

_Added during the Epic 15 course correction (2026-11-10). Story 15.0 verified the assumptions marked below; evidence in `_bmad-output/implementation-artifacts/15-0-spike/README.md`._

## ADR-1: One Version, Kept in the Project Files

**Decision:** The `[project].version` in `api/pyproject.toml` is the product version. `web/package.json` holds the same value, and `api/uv.lock` records it. Only the release command (ADR-3) changes them.

- API: `__version__` comes from `importlib.metadata.version("vintagestory-api")`; `FastAPI(version=__version__)`; `/healthz` adds `data.version`.
- Web: Vite `define` injects `__APP_VERSION__` from `package.json`; the sidebar footer shows it.
- `just version` prints the version and fails if the two files disagree. The release workflow checks the tag against it (ADR-4).

**Rationale:** The version is hard-coded in four places that already disagree. The API and web ship in one image, so one version describes both.

**Consequences:** Between releases, `main` carries the last released version. Only tags publish images, so no published image is mislabeled; local builds show the last release.

**Status (15.0): Confirmed, with two changes.** Package metadata resolves inside the image and reports the `pyproject.toml` version.
- uv writes versions in PEP 440 form: `0.2.0-rc.1` becomes `0.2.0rc1` in `pyproject.toml`, `uv.lock` and package metadata, while `package.json` keeps SemVer. `just version` prints the SemVer form from `package.json` and checks that `pyproject.toml` equals its PEP 440 normalization (`-alpha.N`, `-beta.N`, `-rc.N` → `aN`, `bN`, `rcN`; other pre-release forms are rejected). For pre-releases the API reports the PEP 440 form.
- The image's `CMD uv run …` re-syncs at every start with the `dev` group, downloading packages from PyPI, so the API cannot start offline (`VSS-flj`). Story 15.1 installs the project at build time and starts without syncing.

## ADR-2: Changelog from Conventional Commits with git-cliff

**Decision:** git-cliff, pinned in `.mise.toml`, configured by `cliff.toml` at the repository root, generates `CHANGELOG.md` and release notes.

- Only conventional commits are used; non-conventional messages and merge commits are dropped.
- Groups, in order: Breaking Changes (any type marked with `!` or a `BREAKING CHANGE` footer), Features (`feat`), Fixes (`fix`), Performance (`perf`). All other types, including `chore(release)` commits, are skipped.
- Scopes are not shown, except an allowlist of component scopes that Story 15.0 settles from history (for example `api`, `web`). Story, task, review and `ad-hoc` scopes never appear.
- Each entry links to its commit on GitHub. Bead IDs in subjects are kept.
- Version bumps while on 0.x: features and breaking changes bump the minor version, fixes and performance changes bump the patch version. Revisit at 1.0.

**Changelog file:** `CHANGELOG.md` at the root, newest first. The `v0.1.0` section is a written summary of the product (Story 15.6); each later release prepends its generated section. The GitHub release notes for a tag are that version's section of `CHANGELOG.md` at the tag, so they always match what was committed, including the hand-written `v0.1.0`.

**Rationale:** About 95% of commits are already conventional. git-cliff is a single binary with first-class filtering, scope handling and version bumping.

**Status (15.0): Confirmed, with changes.**
- Scopes are hidden in the template (allowlist `api`, `web`, `docker`), not by a preprocessor, so parsers can still match on them.
- Safety-net parsers skip preparation stories (scope `story-N.0`) and "move story X.Y to review" commits.
- `tag_pattern` matches stable versions only (`^v[0-9]+\.[0-9]+\.[0-9]+$`): pre-release tags are invisible to git-cliff, so a stable release's notes and bump cover everything since the last stable release.
- With nothing releasable, `--bumped-version` returns the last tag unchanged.
- **Commit types by user impact (maintainer decision, 2026-11-10):** the `dev-story` workflow required `feat(story-X.Y/task-N)` for every task commit, which put bookkeeping in the notes (15 of 58 Epic 14 entries). Task commits now take the type that matches their user impact; `feat`/`fix`/`perf` only for user-visible changes. Updated in `project-context.md` and `dev-story/instructions.xml`.

## ADR-3: Release Command

**Decision:** `just release *ARGS` runs `scripts/release.sh` (bash, like `scripts/sprint-status.sh`). `just changelog` prints unreleased notes (`git cliff --unreleased`).

**Sequence:**
1. Check preconditions: on `main`, clean working tree, `git fetch` shows `HEAD` equal to `origin/main`, required tools present.
2. Choose the version: no argument uses `git cliff --bumped-version`; `patch`, `minor` or `major` bumps the last tag; `X.Y.Z[-pre]` is used as given. It must be valid SemVer, newer than the last tag and not already tagged. With no argument and nothing to release, stop.
3. Show the version and notes. `--dry-run` stops here.
4. Update `api/pyproject.toml` and `api/uv.lock`, `web/package.json`, and prepend the section to `CHANGELOG.md`. Run `just version` to confirm the files agree.
5. Commit `chore(release): vX.Y.Z` and create the annotated tag `vX.Y.Z`.
6. Ask for confirmation, then `git push --atomic origin main vX.Y.Z`.

A failure or a declined confirmation before step 6 completes resets `main` to the starting commit and deletes the tag. The tree was clean at step 1, so nothing else is lost.

**Rationale:** The command does not run `just check`: the release commit differs from the commit CI tested only in version files and the changelog, and the release workflow builds the image from the tag.

**Status (15.0): Confirmed, with changes.**
- Version files: `uv version X.Y.Z --no-sync` (in `api/`) changes only the version in `pyproject.toml` and `uv.lock`; `bun pm version X.Y.Z --no-git-tag-version` (in `web/`) changes only `package.json`.
- "Nothing to release": stop when the computed version equals the last stable tag.
- Pre-releases need an explicit version (`just release 0.3.0-rc.1`; allowed forms `-alpha.N`, `-beta.N`, `-rc.N`). They update the version files, commit and tag, but do not change `CHANGELOG.md`, which lists stable releases only. To finish a pre-release cycle, release the stable version explicitly or let the bump compute it from the last stable tag.

## ADR-4: Tag-Triggered Release Workflow

**Decision:** `.github/workflows/release.yml` runs on pushed tags `v*`, one run per tag, never cancelled. Its jobs:

1. **verify** (`contents: read`): the tag equals `v` + the version from `just version`. For a stable version, the notes are its `CHANGELOG.md` section; for a pre-release, `git cliff --unreleased --tag <tag>` (everything since the last stable release).
2. **image** (`contents: read`, `packages: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`): log in to GHCR with `GITHUB_TOKEN`; `docker/metadata-action` produces tags `{{version}}`, `{{major}}.{{minor}}` and `latest` (pre-releases get only `{{version}}`) and the OCI labels; `docker/build-push-action` builds `linux/amd64` and pushes with its own `provenance` and `sbom` off; `actions/attest` attests build provenance for the pushed digest; `anchore/sbom-action` generates an SPDX SBOM for the digest and `actions/attest` attests it.
3. **release** (`contents: write`): `gh release create vX.Y.Z --verify-tag --notes-file`, with `--prerelease` for pre-release versions, and the SBOM attached.

The GitHub release is created last, so a failed build publishes no release. Actions are pinned to commit SHAs and kept current by Renovate, as in CI. `ci.yml` is unchanged: pull requests and `main` still build without pushing.

**Consequences:** The first push creates the GHCR package. Making it public is a one-time manual step in the organization's package settings; the `org.opencontainers.image.source` label links it to the repository. Users verify with `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:X.Y.Z --owner craquehouse`.

**Status (15.0): Confirmed, with changes.** `actions/attest` replaces `actions/attest-build-provenance` (now a wrapper) and `actions/attest-sbom` (deprecated); it needs `artifact-metadata: write`. buildx's default provenance is turned off so the signed GitHub attestations are the only ones and the image index has no attestation manifests. Tag rules come from the metadata-action README; the release-candidate run in Story 15.5 confirms them. Pinned versions and the draft workflow (passes `actionlint`; runnable once Stories 15.1, 15.3 and 15.4 add `just version`, git-cliff in `.mise.toml`, `cliff.toml` and `CHANGELOG.md`) are in the spike.

## ADR-5: Runtime Web Configuration

**Decision:** The API serves `GET /config.js`, unauthenticated, as `application/javascript` with `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin` and `X-Content-Type-Options: nosniff`:

```js
window.__VSM_CONFIG__ = {"apiKey": "..."};
```

- `index.html` loads it with a classic `<script src="/config.js">` before the module bundle. The route is registered with the frontend, ahead of the SPA fallback.
- The key comes from `VS_API_KEY`; if that is unset, from `VS_API_KEY_ADMIN`. This matches the existing compose default. Setting it to the Monitor key gives a read-only UI.
- The web client uses `window.__VSM_CONFIG__?.apiKey`, then `import.meta.env.VITE_API_KEY`, then an empty string. A placeholder `web/public/config.js` defines an empty config for the Vite dev server and tests; in the image, the API route takes precedence over it.
- The Dockerfile drops `ARG VS_API_KEY` and `VITE_API_KEY`; `docker-compose.dev.yaml` drops the build argument.

**Rationale:** One published image must work for every deployment. Chosen over a login screen as the smaller change.

**Consequences:** Exposure is unchanged from today: anyone who can load the page receives the key. The README states this; deployments should stay on a trusted network or behind authentication. The image itself no longer contains a key. The key is never logged.

**Status (15.0):** No assumption to verify; Story 15.2 checks it in a browser.

**Status (15.2): Confirmed, with one addition.** A classic `<script src>` skips CORS, so without a header any other site's page could include `/config.js` and read the key, which the old module bundle (CORS-mode) did not allow. `Cross-Origin-Resource-Policy: same-origin` blocks that (verified in a browser: `ERR_BLOCKED_BY_RESPONSE.NotSameOrigin`). A `VS_API_KEY` that matches neither role key logs `web_api_key_matches_no_role` at start-up.
