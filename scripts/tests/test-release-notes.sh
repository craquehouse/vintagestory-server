#!/usr/bin/env bash
# Tests for scripts/release-notes.sh (Story 15.5).
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

(cd "$(make_tmp)" && git-cliff --version) >/dev/null 2>&1 || {
    echo "$(basename "$0"): git-cliff does not run outside the repository; use just test-scripts" >&2
    exit 1
}

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid

WORK=$(make_tmp)
g() { git -C "$WORK" -c core.hooksPath=/dev/null "$@"; }
commit() { g commit -q --allow-empty -m "$1"; }

g init -q -b main
cp "$SCRIPTS_DIR/../cliff.toml" "$WORK/cliff.toml"
cat >"$WORK/CHANGELOG.md" <<'MD'
# Changelog

<!-- git-cliff: end of header -->

## [0.2.0] - 2026-12-01

### Features

- Second feature

## [0.10.0] - 2026-12-02

- Not 0.1.0

## [0.1.0] - 2026-11-20

First release, written by hand.
MD
g add -A
commit "chore: initial"
g tag -a v0.2.0 -m v0.2.0
commit "feat: after 0.2.0"
commit "fix: another fix"
g tag -a v0.3.0-rc.1 -m v0.3.0-rc.1

# notes <version>: sets OUT, ERR, STATUS
notes() {
    OUT=$(cd "$WORK" && script release-notes.sh "$1" 2>"$WORK/.err")
    STATUS=$?
    ERR=$(<"$WORK/.err")
    rm -f "$WORK/.err"
}

notes 0.2.0
assert_eq "stable: exit" 0 "$STATUS"
assert_eq "stable: its section without the heading" "### Features

- Second feature" "$OUT"

notes v0.1.0
assert_eq "leading v accepted; exact heading (not 0.10.0)" "First release, written by hand." "$OUT"

notes 0.3.0-rc.1
assert_eq "pre-release: exit" 0 "$STATUS"
assert_contains "pre-release: generated notes" "- After 0.2.0" "$OUT"
assert_contains "pre-release: generated notes" "- Another fix" "$OUT"
assert_eq "pre-release: starts at the first group (no version heading)" "### Features" "$(head -1 <<<"$OUT")"

g tag -a v0.3.0 -m v0.3.0
notes 0.4.0-rc.1
assert_eq "pre-release with nothing new: placeholder" \
    "No user-facing changes since the last stable release." "$OUT"
g tag -d v0.3.0 >/dev/null

notes 0.4.0
assert_eq "stable without a section: exit" 1 "$STATUS"
assert_contains "stable without a section: message" "no section for 0.4.0" "$ERR"

notes nonsense
assert_eq "invalid version: exit" 1 "$STATUS"
assert_contains "invalid version: message" "is not a version" "$ERR"

finish
