#!/usr/bin/env bash
# Guards the E2E set-up that CI runs (Story 19.7): specs take their key from the /config.js
# helper, the fixture holds made-up values, and the script and workflow hold no real key.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ROOT="$SCRIPTS_DIR/.."

# No spec sets the localStorage key the web stopped reading in Story 17.5 (FR230)
stale=$(grep -rnI "localStorage.setItem" "$ROOT/web/e2e" "$ROOT/api/tests/e2e" || true)
assert_eq "no E2E spec or fixture sets a localStorage key" "" "$stale"

# The seeded serverconfig.json holds made-up values only (Story 19.7 AC 5)
fixture="$ROOT/web/e2e/fixtures/serverconfig.json"
if yq -p json -e '.' "$fixture" >/dev/null 2>&1; then pass; else fail "the fixture parses as JSON"; fi
assert_eq "fixture ServerName" "E2E Fixture Server" "$(yq -p json '.ServerName' "$fixture" 2>/dev/null)"
assert_eq "fixture ServerDescription" "null" "$(yq -p json '.ServerDescription' "$fixture" 2>/dev/null)"
assert_eq "fixture Ip" "null" "$(yq -p json '.Ip' "$fixture" 2>/dev/null)"
assert_eq "fixture Password is the made-up one" "e2e-fixture-password" "$(yq -p json '.Password' "$fixture" 2>/dev/null)"

finish
