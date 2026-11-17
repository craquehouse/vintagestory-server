#!/usr/bin/env bash
# Tests for scripts/sprint-status.sh `remove` (Epic 19 planning).
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

finish
