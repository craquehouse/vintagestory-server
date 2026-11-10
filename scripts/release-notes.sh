#!/usr/bin/env bash
#
# release-notes.sh - Print the release notes for a version (Epic 15 ADR-4).
#
#   stable       its CHANGELOG.md section (required: `just release` writes it)
#   pre-release  its CHANGELOG.md section if one exists, otherwise notes generated with
#                git-cliff for everything since the last stable release
#
# Usage: scripts/release-notes.sh <X.Y.Z[-pre]>   (runs in the current repository)

set -euo pipefail

die() {
    echo "release-notes: $*" >&2
    exit 1
}

[[ $# -eq 1 ]] || die "usage: release-notes.sh <version>"
version=${1#v}
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || die "'$1' is not a version"

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository"
cd "$ROOT"

section=""
if [[ -f CHANGELOG.md ]]; then
    # Exact heading match: the version is never used as a regex
    section=$(awk -v h="## [$version]" '
        index($0, h) == 1 && substr($0, length(h) + 1, 1) ~ /^( |$)/ { on = 1; next }
        /^## \[/ { on = 0 }
        on
    ' CHANGELOG.md)
fi

if [[ -n ${section//[[:space:]]/} ]]; then
    printf '%s\n' "$section" | sed -e '/./,$!d'
elif [[ $version == *-* ]]; then
    command -v git-cliff >/dev/null 2>&1 || die "git-cliff not found; run through mise"
    git cliff --config "$ROOT/cliff.toml" --unreleased --tag "v$version" --strip all 2>/dev/null |
        sed -e '1{/^## /d;}' -e '/./,$!d'
else
    die "CHANGELOG.md has no section for $version; stable releases are cut with just release"
fi
