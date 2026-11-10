#!/usr/bin/env bash
#
# version.sh - Print the manager version and check that the version files agree.
#
# The version lives in api/pyproject.toml; web/package.json and the vintagestory-api
# entry in api/uv.lock must match it (Epic 15 ADR-1). package.json holds the SemVer
# spelling, and uv writes PEP 440, so pre-releases are compared after normalizing:
#   0.2.0-alpha.1 = 0.2.0a1, 0.2.0-beta.1 = 0.2.0b1, 0.2.0-rc.1 = 0.2.0rc1
# Only those pre-release forms are allowed.
#
# Usage: scripts/version.sh [repo-root]    (prints the SemVer version)
# Requires: yq (pinned in .mise.toml; run through `just version`)

set -euo pipefail

ROOT=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}

die() {
    echo "version: $*" >&2
    exit 1
}

command -v yq >/dev/null 2>&1 || die "yq not found; run through mise (just version)"

semver=$(yq -oy '.version // ""' "$ROOT/web/package.json")
pyproject=$(yq -p toml -oy '.project.version // ""' "$ROOT/api/pyproject.toml")
lock=$(yq -p toml -oy '[.package[] | select(.name == "vintagestory-api") | .version][0] // ""' "$ROOT/api/uv.lock")

pattern='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-(alpha|beta|rc)\.(0|[1-9][0-9]*))?$'
[[ $semver =~ $pattern ]] ||
    die "web/package.json version '$semver' is not X.Y.Z or X.Y.Z-alpha.N, -beta.N, -rc.N"

pep440="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.${BASH_REMATCH[3]}"
case "${BASH_REMATCH[5]}" in
    alpha) pep440+="a${BASH_REMATCH[6]}" ;;
    beta) pep440+="b${BASH_REMATCH[6]}" ;;
    rc) pep440+="rc${BASH_REMATCH[6]}" ;;
esac

[[ $pyproject == "$pep440" ]] ||
    die "api/pyproject.toml has '$pyproject'; web/package.json '$semver' needs '$pep440'"
[[ $lock == "$pep440" ]] ||
    die "api/uv.lock has '$lock' for vintagestory-api; expected '$pep440' (run: uv lock)"

echo "$semver"
