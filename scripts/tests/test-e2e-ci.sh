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

# The CI script and web/e2e/README.md name the same three tags (Story 19.7 AC 4, 7)
e2e_script="$ROOT/scripts/e2e-ci.sh"
e2e_readme="$ROOT/web/e2e/README.md"
script_tags=$(grep -E '^TAGS=' "$e2e_script" 2>/dev/null)
assert_eq "the script leaves out the three tags" "TAGS='@moddb|@game-server|@install'" "$script_tags"
for tag in @moddb @game-server @install; do
    if grep -qF -- "\`$tag\`" "$e2e_readme" 2>/dev/null; then pass; else fail "web/e2e/README.md explains $tag"; fi
done

# Placeholder keys only: constants in the script, never a VS_API_KEY* the caller set (mise
# loads a developer's .env, which holds real keys)
assert_eq "Admin key is the placeholder constant" 'ADMIN_KEY="e2e-admin-placeholder-key"' \
    "$(grep -E '^ADMIN_KEY=' "$e2e_script" 2>/dev/null)"
assert_eq "Monitor key is the placeholder constant" 'MONITOR_KEY="e2e-monitor-placeholder-key"' \
    "$(grep -E '^MONITOR_KEY=' "$e2e_script" 2>/dev/null)"
expanded=$(grep -nE '\$\{?VS_API_KEY' "$e2e_script" 2>/dev/null || true)
assert_eq "the script expands no VS_API_KEY* variable" "" "$expanded"
if [[ -f $e2e_script ]]; then pass; else fail "scripts/e2e-ci.sh exists"; fi

# The API E2E tests skip (and pytest passes) when the address does not answer, so the script
# checks /healthz again right before them and fails the run if the container is gone
web_line=$(grep -n 'test:e2e' "$e2e_script" 2>/dev/null | tail -1 | cut -d: -f1)
health_line=$(grep -n 'healthz' "$e2e_script" 2>/dev/null | tail -1 | cut -d: -f1)
pytest_line=$(grep -n 'pytest tests/e2e' "$e2e_script" 2>/dev/null | tail -1 | cut -d: -f1)
if [[ -n $web_line && -n $health_line && -n $pytest_line ]] \
    && ((web_line < health_line && health_line < pytest_line)); then
    pass
else
    fail "the script re-checks /healthz before the API E2E tests"
fi

# The throwaway container's serverdata holds a directory inside another, so the file
# browser's navigation tests run in CI (Story 20.5 AC 1)
assert_eq "the script seeds a nested directory" 'SEEDED_DIR="Logs/Archive"' \
    "$(grep -E '^SEEDED_DIR=' "$e2e_script" 2>/dev/null)"

# The new-directory spec runs only in the throwaway container: the script exports its name
# before Playwright starts, and the spec names the same container, so CI cannot skip it
# (Story 20.5 AC 5)
export_line=$(grep -nxF "export E2E_CONTAINER=\"\$CONTAINER\"" "$e2e_script" 2>/dev/null | cut -d: -f1)
if [[ -n $export_line && -n $web_line ]] && ((export_line < web_line)); then
    pass
else
    fail "the script exports E2E_CONTAINER before the Playwright tests"
fi
script_container=$(sed -nE 's/^CONTAINER="([^"]*)"$/\1/p' "$e2e_script" 2>/dev/null)
if [[ -n $script_container ]]; then pass; else fail "the script names its container in CONTAINER=\"...\""; fi
new_dir_spec="$ROOT/web/e2e/file-browser-new-directory.spec.ts"
spec_container=$(sed -nE "s/^const THROWAWAY_CONTAINER = '([^']*)';.*/\\1/p" "$new_dir_spec" 2>/dev/null)
assert_eq "the new-directory spec names the script's container" "$script_container" "$spec_container"
# The spec's /data/serverdata depends on it
assert_eq "the script still sets VS_DATA_DIR=/data" "1" \
    "$(grep -cE '^ +-e VS_DATA_DIR=/data \\$' "$e2e_script" 2>/dev/null)"

# The e2e job exists, has a timeout, and the workflow reads no secret (Story 19.7 AC 1, 2, 10)
ci="$ROOT/.github/workflows/ci.yml"
assert_eq "ci.yml e2e job has a timeout" "30" "$(yq '.jobs.e2e.timeout-minutes' "$ci")"
assert_eq "ci.yml e2e job runs just test-e2e-ci" "1" \
    "$(yq '[.jobs.e2e.steps[] | select(.run == "just test-e2e-ci")] | length' "$ci")"
secrets=$(grep -n 'secrets\.' "$ci" || true)
assert_eq "ci.yml reads no secret" "" "$secrets"

finish
