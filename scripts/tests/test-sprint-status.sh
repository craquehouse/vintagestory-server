#!/usr/bin/env bash
# Tests for scripts/sprint-status.sh `remove` (Epic 19 planning), and `set`, `retro-set` and
# `retro-add` (Story 20.3).
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# sprint_repo: a temporary repo layout holding a copy of the script and a sprint file;
# prints its directory. The script works on the repo it lives in, so it is copied.
sprint_repo() {
    local dir
    dir=$(make_tmp)
    mkdir -p "$dir/scripts" "$dir/_bmad-output/implementation-artifacts"
    cp "$SCRIPTS_DIR/sprint-status.sh" "$dir/scripts/"
    cat > "$dir/_bmad-output/implementation-artifacts/sprint-status.yaml" <<'EOF'
# Sprint status
development_status:
  epic-7: done
  epic-7-retrospective: optional
  7-1-old-story: done
  epic-8: backlog
  epic-8-retrospective: optional
  8-1-kept-story: backlog
  8-2-stale-story: backlog
retro_action_items:
  A1-stale-item: pending
EOF
    echo "$dir"
}

# run_sprint <dir> [args...]: sets OUT, ERR and STATUS
run_sprint() {
    local dir=$1
    shift
    OUT=$("$dir/scripts/sprint-status.sh" "$@" 2>"$dir/err")
    STATUS=$?
    ERR=$(<"$dir/err")
}

sprint_file() { cat "$1/_bmad-output/implementation-artifacts/sprint-status.yaml"; }

dir=$(sprint_repo)
run_sprint "$dir" remove 8-2-stale-story
assert_eq "remove a story: exit" 0 "$STATUS"
assert_contains "remove a story: says so" "Removed: 8-2-stale-story" "$OUT"
file=$(sprint_file "$dir")
assert_eq "remove a story: key gone" "0" "$(grep -c '8-2-stale-story' <<<"$file")"
assert_contains "remove a story: other story kept" "8-1-kept-story: backlog" "$file"
assert_contains "remove a story: epic kept" "epic-8: backlog" "$file"
assert_contains "remove a story: comment kept" "# Sprint status" "$file"

dir=$(sprint_repo)
run_sprint "$dir" remove A1-stale-item
assert_eq "remove a retro item: exit" 0 "$STATUS"
assert_eq "remove a retro item: key gone" "0" "$(sprint_file "$dir" | grep -c 'A1-stale-item')"

dir=$(sprint_repo)
before=$(sprint_file "$dir")
run_sprint "$dir" remove 9-9-missing
assert_eq "remove a missing key: exit" 1 "$STATUS"
assert_contains "remove a missing key: explains" "not found" "$ERR"
assert_eq "remove a missing key: file unchanged" "$before" "$(sprint_file "$dir")"

dir=$(sprint_repo)
before=$(sprint_file "$dir")
run_sprint "$dir" remove epic-8
assert_eq "remove an epic with stories: exit" 1 "$STATUS"
assert_contains "remove an epic with stories: names a story" "8-1-kept-story" "$ERR"
assert_eq "remove an epic with stories: file unchanged" "$before" "$(sprint_file "$dir")"

dir=$(sprint_repo)
run_sprint "$dir" remove 7-1-old-story
run_sprint "$dir" remove epic-7
assert_eq "remove an epic without stories: exit" 0 "$STATUS"
file=$(sprint_file "$dir")
assert_eq "remove an epic without stories: epic gone" "0" "$(grep -c 'epic-7' <<<"$file")"

dir=$(sprint_repo)
run_sprint "$dir" remove
assert_eq "remove without a key: exit" 1 "$STATUS"

# check_set <name> <expected exit> <message> <command> [args...]: run the command in a fresh
# repo; the exit code and the message (stdout or stderr) are as expected, and a refused
# command leaves the file unchanged
check_set() {
    local name=$1 expected=$2 message=$3 dir before
    shift 3
    dir=$(sprint_repo)
    before=$(sprint_file "$dir")
    run_sprint "$dir" "$@"
    assert_eq "$name: exit" "$expected" "$STATUS"
    assert_contains "$name: message" "$message" "$OUT$ERR"
    if [[ $expected != 0 ]]; then
        assert_eq "$name: file unchanged" "$before" "$(sprint_file "$dir")"
    fi
    FILE=$(sprint_file "$dir")
}

check_set "set a story" 0 "Updated: 8-1-kept-story -> review" set 8-1-kept-story review
assert_contains "set a story: written" "8-1-kept-story: review" "$FILE"
check_set "set a story to an epic-only status" 1 "Invalid story status 'optional'" \
    set 8-1-kept-story optional
check_set "set an epic" 0 "Updated: epic-8 -> in-progress" set epic-8 in-progress
assert_contains "set an epic: written" "epic-8: in-progress" "$FILE"
check_set "set an epic to a story-only status" 1 "Invalid epic status 'review'" set epic-8 review
check_set "set a retrospective to done" 0 "Updated: epic-8-retrospective -> done" \
    set epic-8-retrospective "done"
check_set "set a retrospective to optional" 0 "Updated: epic-8-retrospective -> optional" \
    set epic-8-retrospective optional
check_set "set a retrospective to an epic status" 1 "Invalid retrospective status 'in-progress'" \
    set epic-8-retrospective in-progress
check_set "retro-set an item" 0 "Updated retro item: A1-stale-item -> done" \
    retro-set A1-stale-item "done"
assert_contains "retro-set an item: written" "A1-stale-item: done" "$FILE"
check_set "retro-set an item to a retrospective status" 1 "Invalid retro status 'optional'" \
    retro-set A1-stale-item optional
check_set "set an empty status" 1 "Invalid story status ''" set 8-1-kept-story ""
check_set "set a status containing a space" 1 "Invalid story status 'review done'" \
    set 8-1-kept-story "review done"
check_set "retro-set a status containing a space" 1 "Invalid retro status 'pending done'" \
    retro-set A1-stale-item "pending done"
check_set "set a status with a glob character" 1 "Invalid story status 'rev*'" \
    set 8-1-kept-story 'rev*'
check_set "retro-add ignores a comment" 0 "Added retro item: A2-new -> pending" \
    retro-add A2-new "a comment"
assert_contains "retro-add: written" "A2-new: pending" "$FILE"

finish
