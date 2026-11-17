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
# (the first Playwright run, the first pass's /healthz re-check, then pytest; Story 20.6 adds
# a second run after them)
web_line=$(grep -n 'test:e2e' "$e2e_script" 2>/dev/null | head -1 | cut -d: -f1)
health_line=$(grep -nF "curl -sf \"\$BASE_URL/healthz\"" "$e2e_script" 2>/dev/null | tail -1 | cut -d: -f1)
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

# The recorded mod database answers the second pass replays (Story 20.6 AC 12): the manifest
# names every recording once, each with its date and the specs that need it, and the
# answers were not rewritten
moddb_dir="$ROOT/web/e2e/fixtures/moddb"
moddb_problems=$(python3 - "$moddb_dir" "$ROOT/web/e2e" <<'PY'
import json, re, sys
from pathlib import Path

moddb, specs = Path(sys.argv[1]), Path(sys.argv[2])
problems = []
try:
    manifest = json.loads((moddb / "manifest.json").read_text())
    entries = manifest["requests"]
except Exception as e:
    print(f"the manifest does not parse: {e}")
    sys.exit()
named = []
for entry in entries:
    request = entry.get("request", "?")
    for key in ("request", "file", "trim"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            problems.append(f"{request}: no {key}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("recorded", ""))):
        problems.append(f"{request}: recorded is not YYYY-MM-DD")
    if not entry.get("specs"):
        problems.append(f"{request}: names no spec")
    for spec in entry.get("specs", []):
        if not (specs / f"{spec}.spec.ts").is_file():
            problems.append(f"{request}: no spec web/e2e/{spec}.spec.ts")
    name = entry.get("file", "")
    named.append(name)
    try:
        body = (moddb / name).read_text()
        json.loads(body)
    except Exception:
        problems.append(f"{request}: {name} is missing or does not parse")
        continue
    for address in ("vintagestory-moddb-replay-e2e", "localhost", "127.0.0.1"):
        if address in body:
            problems.append(f"{name} holds {address}")
    if entry.get("trim") == "listing" and len(json.loads(body).get("mods", [])) < 41:
        problems.append(f"{name} holds fewer than 41 mods")
for path in sorted(moddb.glob("*.json")):
    if path.name != "manifest.json" and named.count(path.name) != 1:
        problems.append(f"{path.name} is named {named.count(path.name)} times in the manifest")
print("\n".join(problems))
PY
)
assert_eq "the mod database recordings match their manifest" "" "$moddb_problems"

# The second pass runs the @moddb tests on recorded answers (Story 20.6 AC 9, 10, 15)
assert_eq "the live-only tags" "LIVE_ONLY_TAGS='@moddb-live|@install'" \
    "$(grep -E '^LIVE_ONLY_TAGS=' "$e2e_script" 2>/dev/null)"
second_run=$(grep -n "test:e2e --grep '@moddb' --grep-invert \"\$LIVE_ONLY_TAGS\"" "$e2e_script" 2>/dev/null | cut -d: -f1)
if [[ -n $second_run ]]; then pass; else fail "the second run selects @moddb and leaves out \$LIVE_ONLY_TAGS"; fi
# The two docker create calls: the first container's, then the second's
first_start="^start_api_container \"\\\$CONTAINER\""
second_start="^start_api_container \"\\\$MODDB_CONTAINER\""
# Each call runs from its first line to the first line that does not end in a backslash
first_call=$(sed -n "\#$first_start#,/[^\\]\$/p" "$e2e_script" 2>/dev/null)
second_call=$(sed -n "\#$second_start#,/[^\\]\$/p" "$e2e_script" 2>/dev/null)
assert_eq "the first API container is started once" "1" "$(grep -c "$first_start" "$e2e_script")"
assert_eq "the second API container is started once" "1" "$(grep -c "$second_start" "$e2e_script")"
assert_contains "the second API container gets VS_DEBUG=true" "-e VS_DEBUG=true" "$second_call"
assert_contains "the second API container's VS_MOD_DB_URL is the replay" \
    "-e VS_MOD_DB_URL=\"http://\$REPLAY_CONTAINER:" "$second_call"
assert_contains "the second API container is on the replay's network" "--network \"\$NETWORK\"" "$second_call"
if [[ -n $first_call && $first_call != *VS_DEBUG* && $first_call != *VS_MOD_DB_URL* ]]; then
    pass
else
    fail "the first API container has neither VS_DEBUG nor VS_MOD_DB_URL" "$first_call"
fi
create_block=$(sed -n '/^start_api_container() {/,/^}/p' "$e2e_script" 2>/dev/null)
assert_contains "both API containers are created with the blocked hosts" "\"\${add_hosts[@]}\"" "$create_block"
for word in VS_DEBUG VS_MOD_DB_URL; do
    if [[ $create_block != *$word* ]]; then pass; else fail "the shared docker create sets no $word"; fi
done
assert_eq "the blocked hosts" \
    "BLOCKED_HOSTS=(mods.vintagestory.at api.vintagestory.at cdn.vintagestory.at moddbcdn.vintagestory.at)" \
    "$(grep -E '^BLOCKED_HOSTS=' "$e2e_script" 2>/dev/null)"
remove_block=$(sed -n '/^remove_all() {/,/^}/p' "$e2e_script" 2>/dev/null)
assert_contains "cleanup removes the three containers" \
    "docker rm -f \"\$CONTAINER\" \"\$MODDB_CONTAINER\" \"\$REPLAY_CONTAINER\"" "$remove_block"
assert_contains "cleanup removes the network" "docker network rm \"\$NETWORK\"" "$remove_block"
cleanup_block=$(sed -n '/^cleanup() {/,/^}/p' "$e2e_script" 2>/dev/null)
assert_contains "the exit trap runs remove_all" "remove_all" "$cleanup_block"
assert_eq "E2E_MODDB_REPLAY=1 is set once, for the second run" "1" \
    "$(grep -c 'E2E_MODDB_REPLAY=1' "$e2e_script")"
replay_line=$(grep -n 'E2E_MODDB_REPLAY=1' "$e2e_script" | head -1 | cut -d: -f1)
if [[ -n $replay_line && -n $second_run && -n $web_line ]] \
    && ((web_line < replay_line && replay_line <= second_run && second_run - replay_line <= 3)); then
    pass
else
    fail "E2E_MODDB_REPLAY=1 is set on the second Playwright run only"
fi
if grep -qF "process.env.E2E_MODDB_REPLAY !== '1'" "$ROOT/web/e2e/config-js.ts"; then
    pass
else
    fail "web/e2e/config-js.ts reads E2E_MODDB_REPLAY"
fi
# No workflow runs the E2E tests on a schedule (against the live mod database)
scheduled=$(grep -lE '^\s*schedule:' "$ROOT"/.github/workflows/*.yml 2>/dev/null \
    | xargs -r grep -lE 'test-e2e|playwright' 2>/dev/null || true)
assert_eq "no scheduled workflow runs E2E tests" "" "$scheduled"

# The e2e job exists, has a timeout, and the workflow reads no secret (Story 19.7 AC 1, 2, 10)
ci="$ROOT/.github/workflows/ci.yml"
assert_eq "ci.yml e2e job has a timeout" "30" "$(yq '.jobs.e2e.timeout-minutes' "$ci")"
assert_eq "ci.yml e2e job runs just test-e2e-ci" "1" \
    "$(yq '[.jobs.e2e.steps[] | select(.run == "just test-e2e-ci")] | length' "$ci")"

# The e2e job restores the Playwright browsers from a cache keyed by the two Playwright
# versions, before it installs them (Story 20.5 AC 7)
cache_index=$(yq '.jobs.e2e.steps | to_entries | map(select(.value.uses | test("^actions/cache@"))) | .[0].key // ""' "$ci")
install_index=$(yq '.jobs.e2e.steps | to_entries | map(select(.value.run == "just install-e2e-browsers")) | .[0].key // ""' "$ci")
if [[ -n $cache_index && -n $install_index ]] && ((cache_index < install_index)); then
    pass
else
    fail "ci.yml e2e job restores the browser cache before just install-e2e-browsers"
fi
assert_eq "the browser cache holds ~/.cache/ms-playwright" "true" \
    "$(i=${cache_index:-0} yq '.jobs.e2e.steps[env(i)].with.path == "~/.cache/ms-playwright"' "$ci")"
assert_eq "the browser cache key comes from the playwright step" "true" \
    "$(i=${cache_index:-0} want="\${{ steps.playwright.outputs.key }}" \
        yq '.jobs.e2e.steps[env(i)].with.key == strenv(want)' "$ci")"
secrets=$(grep -n 'secrets\.' "$ci" || true)
assert_eq "ci.yml reads no secret" "" "$secrets"

finish
