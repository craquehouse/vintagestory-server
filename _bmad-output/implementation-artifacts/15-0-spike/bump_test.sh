#!/usr/bin/env bash
# Story 15.0 spike: record git-cliff version bumps and breaking-change detection on a throwaway repository.
# Usage: bump_test.sh <cliff.toml>   (works in a fresh mktemp directory, removed on exit)
set -euo pipefail
CONFIG=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
CLIFF=(mise exec git-cliff@2.14.2 -- git cliff --config "$CONFIG")
# Same configuration with git-cliff's default tag pattern, which also matches pre-release tags
DEFAULT_PATTERN=(mise exec git-cliff@2.14.2 -- git cliff --config "$CONFIG" --tag-pattern 'v[0-9].*')
cd "$WORK"
git init -q -b main . && git config user.email spike@example.invalid && git config user.name spike
c() { git commit -q --allow-empty -m "$1"; }
next() { printf '%-55s -> %s\n' "$1" "$("${CLIFF[@]}" --bumped-version 2>/dev/null)"; }

c "chore: initial"
next "no tags, chore only"
c "feat(story-1.1/task-1): first feature"
next "no tags, one feat"
git tag -a v0.1.0 -m v0.1.0
next "tag v0.1.0, nothing new"
c "docs: readme"
next "v0.1.0 + docs"
c "fix(api): a fix"
next "v0.1.0 + fix"
c "perf: faster"
next "v0.1.0 + fix + perf"
c "feat(web): a feature"
next "v0.1.0 + fix + perf + feat"
c "refactor!: drop old endpoint"
next "v0.1.0 + ... + refactor! (breaking)"
git tag -a v0.2.0 -m v0.2.0
c "fix: x"
c "chore: y" && git commit -q --allow-empty -m "feat: z" -m "BREAKING CHANGE: removes q"
next "v0.2.0 + fix + feat w/ BREAKING CHANGE footer"
git tag -a v0.3.0-rc.1 -m v0.3.0-rc.1
next "v0.3.0-rc.1 tagged, nothing new"
c "fix: after rc"
next "v0.3.0-rc.1 + fix"
printf '%-55s -> %s\n' "v0.3.0-rc.1 + fix (default tag pattern)" "$("${DEFAULT_PATTERN[@]}" --bumped-version 2>/dev/null)"
for b in patch minor major; do printf '%-55s -> %s\n' "explicit --bump $b" "$("${CLIFF[@]}" --bump $b --bumped-version 2>/dev/null)"; done
echo
echo "== unreleased notes since v0.3.0-rc.1 =="
"${CLIFF[@]}" --unreleased --strip header 2>/dev/null | sed 's/ (\[.*//'
echo "== pre-release notes: unreleased tagged v0.3.0-rc.2 (since last stable) =="
"${CLIFF[@]}" --unreleased --tag v0.3.0-rc.2 --strip all 2>/dev/null | sed 's/ (\[.*//'
echo "== notes for v0.1.0..v0.2.0 =="
"${CLIFF[@]}" v0.1.0..v0.2.0 --strip all 2>/dev/null | sed 's/ (\[.*//'
git tag -a v0.3.0 -m v0.3.0
next "v0.3.0 tagged after rc"
c "fix: after v0.3.0"
echo "== --latest with one commit after v0.3.0 (HEAD is not the tag) =="
"${CLIFF[@]}" --latest --strip all 2>/dev/null | sed 's/ (\[.*//'
