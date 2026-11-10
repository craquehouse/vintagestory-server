#!/usr/bin/env bash
# Tests for cliff.toml (Story 15.3, Epic 15 ADR-2): which commits become release notes,
# how they are grouped and shown, and how the next version is computed.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# The fixtures run git-cliff from temporary directories, where a mise shim cannot resolve
# the pinned version; `mise exec` (just test-scripts) puts the real binary on PATH.
(cd "$(make_tmp)" && git-cliff --version) >/dev/null 2>&1 || {
    echo "$(basename "$0"): git-cliff does not run outside the repository; use just test-scripts" >&2
    exit 1
}

CONFIG="$SCRIPTS_DIR/../cliff.toml"
LINK="https://github.com/craquehouse/vintagestory-server/commit"

# g <repo> <git args...>: git isolated from the developer's config, hooks and signing
g() {
    local repo=$1
    shift
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -C "$repo" -c user.name=test -c user.email=test@example.invalid \
        -c commit.gpgsign=false -c tag.gpgsign=false -c core.hooksPath=/dev/null "$@"
}

new_repo() {
    local repo
    repo=$(make_tmp)
    g "$repo" init -q -b main
    echo "$repo"
}

# commit <repo> <message> [more -m paragraphs...]
commit() {
    local repo=$1
    shift
    local args=()
    for message in "$@"; do args+=(-m "$message"); done
    g "$repo" commit -q --allow-empty "${args[@]}"
}

cliff() {
    local repo=$1
    shift
    (cd "$repo" && git cliff --config "$CONFIG" "$@" 2>/dev/null)
}

# --- Notes: grouping, filtering, scopes, links ---------------------------------------

repo=$(new_repo)
commit "$repo" "chore: initial commit"
commit "$repo" "feat(story-1.1/task-1): add widget listing"
listing_sha=$(g "$repo" rev-parse HEAD)
commit "$repo" "fix(story-1.1/review): handle an empty widget list"
commit "$repo" "fix(ad-hoc): correct the widget title"
commit "$repo" "feat(api): expose the widget endpoint"
commit "$repo" "feat(web): show widgets on the dashboard"
commit "$repo" "feat(docker): label the image"
commit "$repo" "feat(ui): unlisted component scope"
commit "$repo" "perf: speed up widget listing"
for type in docs chore test ci build refactor style review; do
    commit "$repo" "$type(story-1.1/task-2): excluded $type commit"
done
commit "$repo" "feat(story-2.0/task-1): excluded preparation story"
commit "$repo" "feat(story-1.1/task-3): validate and move story 1.1 to review"
commit "$repo" "Add a non-conventional commit"
g "$repo" checkout -q -b topic
commit "$repo" "feat: add a feature on a branch"
g "$repo" checkout -q main
g "$repo" merge -q --no-ff topic -m "Merge pull request #1 from example/topic"
commit "$repo" "feat!: drop the legacy widget API"
commit "$repo" "fix: rename the widget setting" "BREAKING CHANGE: the old setting name is gone"
commit "$repo" "refactor!: remove the old config loader"
# Breaking beats the preparation-story skip: the breaking parser must stay first
commit "$repo" "feat(story-2.0/task-1)!: replace the widget store"

notes=$(cliff "$repo" --unreleased --strip header)
entries=$(grep '^- ' <<<"$notes" | sed 's/ (\[.*//')

assert_eq "group headings in order" \
    "### Breaking Changes|### Features|### Fixes|### Performance" \
    "$(grep '^### ' <<<"$notes" | paste -sd '|' -)"
assert_eq "unreleased heading" "## Unreleased" "$(grep '^## ' <<<"$notes")"

expected="- Drop the legacy widget API
- Rename the widget setting
- Remove the old config loader
- Replace the widget store
- Add widget listing
- **api:** Expose the widget endpoint
- **web:** Show widgets on the dashboard
- **docker:** Label the image
- Unlisted component scope
- Add a feature on a branch
- Handle an empty widget list
- Correct the widget title
- Speed up widget listing"
assert_eq "entries: included, grouped, scopes stripped except api/web/docker" "$expected" "$entries"

assert_contains "entry links its commit" \
    "- Add widget listing ([${listing_sha:0:7}]($LINK/$listing_sha))" "$notes"

for absent in excluded "Merge pull request" "non-conventional" "move story" "preparation story" \
    "story-1.1" "ad-hoc" "Initial commit"; do
    if [[ $notes == *"$absent"* ]]; then fail "notes omit '$absent'"; else pass; fi
done

# --- Version bumps on 0.x and pre-release tags ---------------------------------------

repo=$(new_repo)
commit "$repo" "chore: initial commit"
assert_eq "no tags: initial version" "v0.1.0" "$(cliff "$repo" --bumped-version)"
g "$repo" tag -a v0.1.0 -m v0.1.0
commit "$repo" "docs: only docs"
assert_eq "nothing releasable: unchanged" "v0.1.0" "$(cliff "$repo" --bumped-version)"
commit "$repo" "fix: a fix"
assert_eq "fix bumps patch" "v0.1.1" "$(cliff "$repo" --bumped-version)"
commit "$repo" "perf: faster"
assert_eq "perf bumps patch" "v0.1.1" "$(cliff "$repo" --bumped-version)"
commit "$repo" "feat: a feature"
assert_eq "feat bumps minor" "v0.2.0" "$(cliff "$repo" --bumped-version)"
g "$repo" tag -a v0.2.0 -m v0.2.0
commit "$repo" "refactor!: breaking change"
assert_eq "breaking bumps minor on 0.x" "v0.3.0" "$(cliff "$repo" --bumped-version)"
g "$repo" tag -a v0.3.0-rc.1 -m v0.3.0-rc.1
commit "$repo" "fix: after the release candidate"
assert_eq "pre-release tags are ignored by bumps" "v0.3.0" "$(cliff "$repo" --bumped-version)"
rc_notes=$(cliff "$repo" --unreleased --strip header)
assert_contains "notes since the last stable tag include commits before the rc" "Breaking change" "$rc_notes"
assert_contains "notes include commits after the rc" "After the release candidate" "$rc_notes"
assert_eq "explicit patch bump" "v0.2.1" "$(cliff "$repo" --bump patch --bumped-version)"
heading=$(cliff "$repo" --unreleased --tag v0.3.0 --strip header | head -1)
if [[ $heading =~ ^##\ \[0\.3\.0\]\ -\ [0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then pass; else
    fail "release heading is '## [X.Y.Z] - YYYY-MM-DD'" "got: $heading"
fi

finish
