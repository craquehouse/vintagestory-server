#!/usr/bin/env bash
#
# release.sh - Cut a release: choose the version, update the version files and
# CHANGELOG.md, commit, tag, and (after confirmation) push the commit and tag together.
# Pushing the tag starts the release workflow (Epic 15 ADR-3, ADR-4).
#
# Usage: scripts/release.sh [--dry-run] [patch|minor|major|X.Y.Z[-alpha.N|-beta.N|-rc.N]]
#
#   (no version)   next version computed from the commits since the last stable release
#   patch|minor|major
#                  bump the last stable release (from 0.0.0 when there is none)
#   X.Y.Z[-pre]    exactly this version; pre-releases must be explicit and leave
#                  CHANGELOG.md alone (it lists stable releases only)
#   --dry-run      show the version and notes, change nothing
#
# Runs in the current repository. Requires git, git-cliff, uv, bun and yq (run through
# `just release`, which provides them with mise). The push confirmation reads stdin.
# Repository git hooks do not run for the release commit, tag and push: the commit only
# touches version files, and a hook that writes to the tree would lose its writes if a
# failed release is rolled back.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REMOTE=origin
BRANCH=main
MARKER="<!-- git-cliff: end of header -->"
SEMVER='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-(alpha|beta|rc)\.(0|[1-9][0-9]*))?$'

die() {
    echo "release: $*" >&2
    exit 1
}

usage() {
    sed -n '3,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# --- Arguments -----------------------------------------------------------------------

dry_run=false
request=""
for arg in "$@"; do
    case "$arg" in
        --dry-run) dry_run=true ;;
        -h | --help)
            usage
            exit 0
            ;;
        -*) die "unknown option $arg (see --help)" ;;
        *)
            [[ -z $request ]] || die "more than one version given (see --help)"
            request=$arg
            ;;
    esac
done

# --- Preconditions -------------------------------------------------------------------

for tool in git git-cliff uv bun yq; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool not found; run through mise (just release)"
done

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository"
cd "$ROOT"

branch=$(git symbolic-ref --quiet --short HEAD || true)
[[ $branch == "$BRANCH" ]] || die "releases are cut from $BRANCH; you are on '${branch:-a detached HEAD}'"
[[ -z $(git status --porcelain) ]] || die "the working tree has changes; commit or stash them first"

git fetch --quiet --tags "$REMOTE" "$BRANCH" || die "cannot fetch $REMOTE/$BRANCH"
[[ $(git rev-parse HEAD) == $(git rev-parse "$REMOTE/$BRANCH") ]] ||
    die "$BRANCH differs from $REMOTE/$BRANCH; pull or push first"

"$SCRIPT_DIR/version.sh" "$ROOT" >/dev/null

# --- Version -------------------------------------------------------------------------

cliff() { git cliff --config "$ROOT/cliff.toml" "$@" 2>/dev/null; }

# semver_parts <version>: sets MAJOR MINOR PATCH PRE_RANK PRE_NUM (stable ranks highest)
semver_parts() {
    [[ $1 =~ $SEMVER ]] || return 1
    MAJOR=${BASH_REMATCH[1]} MINOR=${BASH_REMATCH[2]} PATCH=${BASH_REMATCH[3]}
    case "${BASH_REMATCH[5]}" in
        alpha) PRE_RANK=1 ;;
        beta) PRE_RANK=2 ;;
        rc) PRE_RANK=3 ;;
        *) PRE_RANK=4 ;;
    esac
    PRE_NUM=${BASH_REMATCH[6]:-0}
}

# newer <a> <b>: whether version a has higher SemVer precedence than b
newer() {
    local a b i
    semver_parts "$1" && a=("$MAJOR" "$MINOR" "$PATCH" "$PRE_RANK" "$PRE_NUM")
    semver_parts "$2" && b=("$MAJOR" "$MINOR" "$PATCH" "$PRE_RANK" "$PRE_NUM")
    for i in 0 1 2 3 4; do
        ((a[i] > b[i])) && return 0
        ((a[i] < b[i])) && return 1
    done
    return 1
}

# Release tags reachable from HEAD, newest first
release_tags=()
while IFS= read -r tag; do
    [[ ${tag#v} =~ $SEMVER ]] && release_tags+=("${tag#v}")
done < <(git tag --list 'v*' --merged HEAD)
newest="" last_stable=""
for version in ${release_tags[@]+"${release_tags[@]}"}; do
    [[ -z $newest ]] || newer "$version" "$newest" && newest=$version
    if [[ $version != *-* ]] && { [[ -z $last_stable ]] || newer "$version" "$last_stable"; }; then
        last_stable=$version
    fi
done

case "$request" in
    "")
        version=$(cliff --bumped-version) || true
        [[ -n $version ]] || die "git cliff could not compute the next version"
        version=${version#v}
        [[ -n $last_stable && $version == "$last_stable" ]] &&
            die "nothing to release: no feat, fix, perf or breaking commits since v$last_stable"
        ;;
    patch | minor | major)
        # Computed here: git-cliff does not bump when nothing is releasable
        semver_parts "${last_stable:-0.0.0}"
        case "$request" in
            patch) version="$MAJOR.$MINOR.$((PATCH + 1))" ;;
            minor) version="$MAJOR.$((MINOR + 1)).0" ;;
            major) version="$((MAJOR + 1)).0.0" ;;
        esac
        ;;
    *) version=${request#v} ;;
esac

[[ $version =~ $SEMVER ]] ||
    die "'$version' is not X.Y.Z or X.Y.Z-alpha.N, -beta.N, -rc.N"
tag="v$version"
[[ -z $(git tag --list "$tag") ]] || die "tag $tag already exists"
[[ -z $newest ]] || newer "$version" "$newest" ||
    die "$version is not newer than the last release v$newest"

prerelease=false
[[ $version == *-* ]] && prerelease=true

# --- Notes ---------------------------------------------------------------------------

# changelog_section <version>: the CHANGELOG.md section for a version, without its heading
changelog_section() {
    [[ -f CHANGELOG.md ]] || return 0
    awk -v h="## [$1]" '
        index($0, h) == 1 && substr($0, length(h) + 1, 1) ~ /^( |$)/ { on = 1; next }
        /^## \[/ { on = 0 }
        on
    ' CHANGELOG.md
}

existing_section=$(changelog_section "$version")
if [[ -n $existing_section ]]; then
    notes=$existing_section
    notes_source="CHANGELOG.md (existing section)"
else
    notes=$(cliff --unreleased --tag "$tag" --strip header)
    notes_source="generated"
fi

echo "Release $tag$($prerelease && echo " (pre-release)")"
echo "Notes ($notes_source):"
echo
echo "$notes"
echo

if $dry_run; then
    echo "Dry run: nothing changed."
    exit 0
fi

# --- Changes, commit, tag, push ------------------------------------------------------

start=$(git rev-parse HEAD)
pushed=false

rollback() {
    local status=$?
    if ! $pushed; then
        git tag -d "$tag" >/dev/null 2>&1 || true
        git reset --quiet --hard "$start"
        echo "release: rolled back; $BRANCH is at ${start:0:7} and no tag was kept" >&2
    fi
    exit "$status"
}
trap rollback EXIT

output=$(cd api && uv version "$version" --no-sync 2>&1) || die "uv version $version failed: $output"
output=$(cd web && bun pm version "$version" --no-git-tag-version --allow-same-version 2>&1) ||
    die "bun pm version $version failed: $output"
[[ $("$SCRIPT_DIR/version.sh" "$ROOT") == "$version" ]] || die "version files do not agree on $version"

files=(api/pyproject.toml api/uv.lock web/package.json)
if ! $prerelease && [[ -z $existing_section ]]; then
    if [[ -f CHANGELOG.md ]]; then
        grep -qF -- "$MARKER" CHANGELOG.md || die "CHANGELOG.md has no '$MARKER' line to add notes below"
        cliff --unreleased --tag "$tag" --prepend CHANGELOG.md >/dev/null ||
            die "git cliff could not update CHANGELOG.md"
    else
        cliff --unreleased --tag "$tag" --output CHANGELOG.md >/dev/null ||
            die "git cliff could not create CHANGELOG.md"
    fi
    files+=(CHANGELOG.md)
fi

git add -- "${files[@]}"
# --allow-empty: releasing the version already in the files with a hand-written section
# (v0.1.0) changes nothing, but every release still gets its own commit for the tag
unhooked() { git -c core.hooksPath=/dev/null "$@"; }
unhooked commit --quiet --allow-empty -m "chore(release): $tag" || die "commit failed"
unhooked tag -a "$tag" -m "$tag" || die "tag failed"

echo "Committed $(git rev-parse --short HEAD) chore(release): $tag and tagged $tag."
read -r -p "Push $tag to $REMOTE? [y/N] " answer || answer=""
case "$answer" in
    y | Y | yes | YES) ;;
    *) die "release cancelled" ;;
esac

unhooked push --quiet --atomic "$REMOTE" "$BRANCH" "$tag" || die "push failed"
pushed=true
trap - EXIT
echo "Pushed $tag. The release workflow publishes it."
