#!/usr/bin/env bash
# Tests for scripts/release.sh (Story 15.4) against temporary repositories with a bare remote.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

(cd "$(make_tmp)" && git-cliff --version && uv --version && bun --version) >/dev/null 2>&1 || {
    echo "$(basename "$0"): git-cliff, uv or bun do not run outside the repository; use just test-scripts" >&2
    exit 1
}

REPO_ROOT=$(cd "$SCRIPTS_DIR/.." && pwd)
HEADER_MARKER="<!-- git-cliff: end of header -->"

# Isolate git from the developer's config, hooks and signing (also for release.sh itself)
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
export UV_OFFLINE=1

g() { git -C "$WORK" -c core.hooksPath=/dev/null "$@"; }

commit() { g commit -q --allow-empty -m "$1"; }

# fixture [version] [with-changelog]: a project at <version> pushed to a bare remote;
# sets WORK (the clone) and REMOTE (the bare repository)
fixture() {
    local version=${1:-0.1.0} root
    root=$(make_tmp)
    REMOTE="$root/remote.git"
    WORK="$root/work"
    git init -q --bare -b main "$REMOTE"
    git init -q -b main "$WORK"
    mkdir -p "$WORK/api" "$WORK/web" "$WORK/scripts"
    printf '[project]\nname = "vintagestory-api"\nversion = "%s"\nrequires-python = ">=3.14"\ndependencies = []\n' \
        "$version" >"$WORK/api/pyproject.toml"
    (cd "$WORK/api" && uv lock --quiet)
    printf '{\n  "name": "web",\n  "version": "%s"\n}\n' "$version" >"$WORK/web/package.json"
    cp "$REPO_ROOT/cliff.toml" "$WORK/cliff.toml"
    if [[ ${2:-with-changelog} == with-changelog ]]; then
        printf '# Changelog\n\nIntro.\n%s\n\n' "$HEADER_MARKER" >"$WORK/CHANGELOG.md"
    fi
    g add -A
    commit "chore: initial project"
    g remote add origin "$REMOTE"
    g push -q origin main
}

# release <stdin answer> [args...]: run release.sh in WORK; sets OUT and STATUS
release() {
    local answer=$1
    shift
    OUT=$(cd "$WORK" && printf '%s\n' "$answer" | "$SCRIPTS_DIR/release.sh" "$@" 2>&1)
    STATUS=$?
}

push() { g push -q origin main; }

# tag_and_push <version>: a release tag on HEAD, as an earlier release would leave it
tag_and_push() {
    g tag -a "v$1" -m "v$1"
    g push -q origin "v$1"
}

state() { echo "$(g rev-parse HEAD) $(g tag | paste -sd, -) $(g status --porcelain | wc -l | tr -d ' ')"; }

assert_unchanged() {
    assert_eq "$1: local state unchanged" "$2" "$(state)"
    assert_eq "$1: remote unchanged" "$3" "$(git -C "$REMOTE" rev-parse main) $(git -C "$REMOTE" tag | paste -sd, -)"
}

remote_state() { echo "$(git -C "$REMOTE" rev-parse main) $(git -C "$REMOTE" tag | paste -sd, -)"; }

# --- A stable release, end to end ----------------------------------------------------

fixture 0.1.0
tag_and_push 0.1.0
commit "feat(story-2.1/task-1): add widget listing"
commit "fix(api): handle an empty widget list"
commit "docs: describe widgets"
push
before=$(state) remote_before=$(remote_state)

release "" --dry-run
assert_eq "dry run: exit" 0 "$STATUS"
assert_contains "dry run: computed version" "Release v0.2.0" "$OUT"
assert_contains "dry run: shows notes" "- Add widget listing" "$OUT"
assert_contains "dry run: says nothing changed" "Dry run: nothing changed." "$OUT"
assert_unchanged "dry run" "$before" "$remote_before"

release "y"
assert_eq "release: exit" 0 "$STATUS"
assert_eq "release: commit message" "chore(release): v0.2.0" "$(g log -1 --format=%s)"
assert_eq "release: one commit added" 1 "$(g rev-list --count "${before%% *}..HEAD")"
assert_eq "release: files in the commit" \
    "CHANGELOG.md api/pyproject.toml api/uv.lock web/package.json" \
    "$(g show --name-only --format= HEAD | sort | paste -sd ' ' -)"
assert_eq "release: annotated tag on the commit" "tag $(g rev-parse HEAD)" \
    "$(g cat-file -t v0.2.0) $(g rev-parse 'v0.2.0^{commit}')"
assert_eq "release: remote has the commit" "$(g rev-parse HEAD)" "$(git -C "$REMOTE" rev-parse main)"
assert_eq "release: remote has the tag" "$(g rev-parse v0.2.0)" "$(git -C "$REMOTE" rev-parse v0.2.0)"
assert_eq "release: version files agree" 0.2.0 "$("$SCRIPTS_DIR/version.sh" "$WORK")"
changelog=$(<"$WORK/CHANGELOG.md")
# --prepend rewrites everything above the marker with cliff.toml's header
assert_contains "release: section right below the header" "$HEADER_MARKER

## [0.2.0] - " "$changelog"
assert_eq "release: header from cliff.toml" "# Changelog" "$(head -1 "$WORK/CHANGELOG.md")"
assert_contains "release: notes in CHANGELOG.md" "- Add widget listing" "$changelog"
assert_contains "release: notes in CHANGELOG.md" "- **api:** Handle an empty widget list" "$changelog"

commit "fix: a later fix"
push
release "y"
assert_eq "second release: exit" 0 "$STATUS"
assert_contains "second release: patch bump" "Release v0.2.1" "$OUT"
section_order=$(grep -n '^## \[' "$WORK/CHANGELOG.md" | cut -d: -f2 | cut -c1-10 | paste -sd ' ' -)
assert_eq "second release: newest section first" "## [0.2.1] ## [0.2.0]" "$section_order"

# --- Version choice --------------------------------------------------------------------

for case in "patch 0.1.1" "minor 0.2.0" "major 1.0.0" "0.4.0 0.4.0" "v0.5.0 0.5.0"; do
    fixture 0.1.0
    tag_and_push 0.1.0
    commit "fix: something"
    push
    release "" --dry-run "${case% *}"
    assert_contains "requested ${case% *}" "Release v${case#* }" "$OUT"
done

fixture 0.1.0
tag_and_push 0.1.0
commit "docs: only docs"
push
before=$(state) remote_before=$(remote_state)
release "y"
assert_eq "nothing to release: exit" 1 "$STATUS"
assert_contains "nothing to release: message" "nothing to release" "$OUT"
assert_unchanged "nothing to release" "$before" "$remote_before"
release "" --dry-run patch
assert_contains "explicit bump still allowed" "Release v0.1.1" "$OUT"

# --- Pre-release, then the stable release ----------------------------------------------

fixture 0.1.0
tag_and_push 0.1.0
commit "feat: early feature"
push
changelog_before=$(<"$WORK/CHANGELOG.md")
release "y" 0.2.0-rc.1
assert_eq "pre-release: exit" 0 "$STATUS"
assert_eq "pre-release: PEP 440 in pyproject" 'version = "0.2.0rc1"' "$(grep '^version' "$WORK/api/pyproject.toml")"
assert_eq "pre-release: version files agree" 0.2.0-rc.1 "$("$SCRIPTS_DIR/version.sh" "$WORK")"
assert_eq "pre-release: CHANGELOG.md unchanged" "$changelog_before" "$(<"$WORK/CHANGELOG.md")"
assert_eq "pre-release: files in the commit" "api/pyproject.toml api/uv.lock web/package.json" \
    "$(g show --name-only --format= HEAD | sort | paste -sd ' ' -)"
assert_eq "pre-release: tag pushed" "$(g rev-parse v0.2.0-rc.1)" "$(git -C "$REMOTE" rev-parse v0.2.0-rc.1)"
commit "fix: after the release candidate"
push
release "" --dry-run 0.2.0-rc.1
assert_eq "older pre-release refused" 1 "$STATUS"
assert_contains "older pre-release: message" "already exists" "$OUT"
release "y"
assert_contains "stable after rc: version" "Release v0.2.0" "$OUT"
section=$(awk '/^## \[0.2.0\]/{on=1; next} /^## \[/{on=0} on' "$WORK/CHANGELOG.md")
assert_contains "stable after rc: includes pre-rc commits" "- Early feature" "$section"
assert_contains "stable after rc: includes post-rc commits" "- After the release candidate" "$section"

# --- Hand-written section and first release ----------------------------------------------

fixture 0.1.0
commit "feat: everything so far"
printf '## [0.1.0] - 2026-11-20\n\nFirst release, written by hand.\n' >>"$WORK/CHANGELOG.md"
g add CHANGELOG.md
commit "docs: write the 0.1.0 notes"
push
changelog_before=$(<"$WORK/CHANGELOG.md")
release "y" 0.1.0
assert_eq "hand-written section: exit" 0 "$STATUS"
assert_contains "hand-written section: shown as notes" "First release, written by hand." "$OUT"
assert_contains "hand-written section: source named" "existing section" "$OUT"
assert_eq "hand-written section: CHANGELOG.md unchanged" "$changelog_before" "$(<"$WORK/CHANGELOG.md")"
assert_eq "hand-written section: release commit even with no file changes" \
    "chore(release): v0.1.0" "$(g log -1 --format=%s)"
assert_eq "hand-written section: tag pushed" "$(g rev-parse v0.1.0)" "$(git -C "$REMOTE" rev-parse v0.1.0)"

fixture 0.1.0 without-changelog
commit "feat: first feature"
push
release "y"
assert_eq "first release: exit" 0 "$STATUS"
assert_contains "first release: initial version" "Release v0.1.0" "$OUT"
assert_contains "first release: CHANGELOG.md created with header" "$HEADER_MARKER" "$(<"$WORK/CHANGELOG.md")"
assert_contains "first release: section" "## [0.1.0] - " "$(<"$WORK/CHANGELOG.md")"

# --- Declined, failures and rollback -----------------------------------------------------

fixture 0.1.0
tag_and_push 0.1.0
commit "feat: a feature"
push
before=$(state) remote_before=$(remote_state)
release "n"
assert_eq "declined: exit" 1 "$STATUS"
assert_contains "declined: message" "release cancelled" "$OUT"
assert_unchanged "declined" "$before" "$remote_before"
release ""
assert_eq "no answer counts as no" 1 "$STATUS"
assert_unchanged "no answer" "$before" "$remote_before"

printf '# Changelog\n\nNo marker here.\n' >"$WORK/CHANGELOG.md"
g add CHANGELOG.md
commit "docs: break the changelog header"
push
before=$(state) remote_before=$(remote_state)
release "y"
assert_eq "missing marker: exit" 1 "$STATUS"
assert_contains "missing marker: message" "has no '$HEADER_MARKER' line" "$OUT"
assert_contains "missing marker: rolled back" "rolled back" "$OUT"
assert_unchanged "missing marker" "$before" "$remote_before"

fixture 0.1.0
tag_and_push 0.1.0
commit "feat: a feature"
push
printf '#!/bin/sh\necho "rejected by test hook" >&2\nexit 1\n' >"$REMOTE/hooks/pre-receive"
chmod +x "$REMOTE/hooks/pre-receive"
before=$(state) remote_before=$(remote_state)
release "y"
assert_eq "push rejected: exit" 1 "$STATUS"
assert_contains "push rejected: message" "push failed" "$OUT"
assert_unchanged "push rejected" "$before" "$remote_before"

# --- Preconditions -----------------------------------------------------------------------

fixture 0.1.0
tag_and_push 0.1.0
commit "feat: a feature"
push
expect_refused() {
    local name=$1 message=$2
    shift 2
    local before remote_before
    before=$(state) remote_before=$(remote_state)
    release "y" "$@"
    assert_eq "$name: exit" 1 "$STATUS"
    assert_contains "$name: message" "$message" "$OUT"
    assert_unchanged "$name" "$before" "$remote_before"
}

g checkout -q -b topic
expect_refused "not on main" "you are on 'topic'"
g checkout -q main

touch "$WORK/stray.txt"
expect_refused "untracked file" "working tree has changes"
rm "$WORK/stray.txt"
echo "# edit" >>"$WORK/cliff.toml"
expect_refused "modified file" "working tree has changes"
g checkout -q -- cliff.toml

commit "feat: not pushed yet"
expect_refused "ahead of the remote" "differs from origin/main"
g reset -q --hard HEAD~1

other=$(make_tmp)
git clone -q "$REMOTE" "$other/clone"
git -C "$other/clone" -c core.hooksPath=/dev/null commit -q --allow-empty -m "feat: elsewhere"
git -C "$other/clone" push -q origin main
expect_refused "behind the remote" "differs from origin/main"
g pull -q --ff-only origin main

expect_refused "tag exists" "tag v0.1.0 already exists" 0.1.0
expect_refused "older version" "is not newer than the last release v0.1.0" 0.0.9
expect_refused "invalid version" "is not X.Y.Z" 0.2
expect_refused "unsupported pre-release" "is not X.Y.Z" 0.2.0-preview.1
expect_refused "two versions" "more than one version" 0.2.0 0.3.0
expect_refused "unknown option" "unknown option --force" --force

printf '{\n  "name": "web",\n  "version": "0.0.9"\n}\n' >"$WORK/web/package.json"
g add web/package.json
commit "chore: desync the version files"
push
expect_refused "version files disagree" "api/pyproject.toml has '0.1.0'"

finish
