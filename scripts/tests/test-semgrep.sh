#!/usr/bin/env bash
# Guards the semgrep scan (Story 20.4, Epic 20 ADR-6 and ADR-7): what scripts/semgrep.sh
# runs, which files it scans, and that no other recipe runs it. Never runs semgrep and needs
# no network: a stub uvx is first on PATH.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ROOT="$SCRIPTS_DIR/.."
SEMGREP="$ROOT/scripts/semgrep.sh"
PACKS=(--config p/python --config p/typescript --config p/react --config p/secrets --config p/github-actions --config p/dockerfile)
TARGETS=(api/src web/src .github Dockerfile scripts)

# --- A. What the script runs (AC 1, 4, 14) ---

stub=$(make_tmp)
export STUB_LOG="$stub/args.log" STUB_ENV="$stub/env.log"
cat >"$stub/uvx" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$STUB_LOG"
{
    echo "SEMGREP_SETTINGS_FILE=${SEMGREP_SETTINGS_FILE-<unset>}"
    echo "SEMGREP_APP_TOKEN=${SEMGREP_APP_TOKEN-<unset>}"
} >"$STUB_ENV"
exit "${STUB_EXIT:-0}"
STUB
chmod +x "$stub/uvx"

# run_semgrep [args...]: run the script with the stub first on PATH; the logs start empty
run_semgrep() {
    rm -f "$STUB_LOG" "$STUB_ENV"
    PATH="$stub:$PATH" "$SEMGREP" "$@" >/dev/null 2>&1
}

version=$(sed -nE 's/^SEMGREP_VERSION="([^"]+)"$/\1/p' "$SEMGREP" 2>/dev/null)

SEMGREP_APP_TOKEN=x run_semgrep --baseline-commit origin/main "a b"
status=$?
assert_eq "the script exits with semgrep's status (0)" 0 "$status"
if [[ -f $STUB_LOG ]]; then pass; else fail "the script runs uvx"; fi
expected=$(printf '%s\n' "semgrep==$version" scan --metrics=off --error "${PACKS[@]}" \
    --baseline-commit origin/main "a b" "${TARGETS[@]}")
assert_eq "the script runs the pinned semgrep with the packs, the arguments and the paths" \
    "$expected" "$(cat "$STUB_LOG" 2>/dev/null)"
assert_eq "the script ignores a semgrep login" \
    "$(printf '%s\n' SEMGREP_SETTINGS_FILE=/dev/null 'SEMGREP_APP_TOKEN=<unset>')" \
    "$(cat "$STUB_ENV" 2>/dev/null)"

SEMGREP_REPORT_ONLY=1 run_semgrep
expected=$(printf '%s\n' "semgrep==$version" scan --metrics=off "${PACKS[@]}" "${TARGETS[@]}")
assert_eq "SEMGREP_REPORT_ONLY=1 leaves out --error" "$expected" "$(cat "$STUB_LOG" 2>/dev/null)"

STUB_EXIT=1 run_semgrep
assert_eq "the script exits with semgrep's status (1)" 1 "$?"

# --- B. The scope (AC 2) ---

ignore="$ROOT/.semgrepignore"
assert_eq ".semgrepignore has the four test patterns" \
    "$(printf '%s\n' '*.test.ts' '*.test.tsx' web/src/test/ scripts/tests/)" \
    "$(grep -vE '^[[:space:]]*(#|$)' "$ignore" 2>/dev/null)"

rule_files=$(git -C "$ROOT" ls-files | grep -E '(^|/)\.semgrep(/|\.ya?ml$)' || true)
assert_eq "no semgrep rule file is tracked" "" "$rule_files"
SEMGREP_REPORT_ONLY=1 run_semgrep
configs=$(grep -A1 -xF -- --config "$STUB_LOG" 2>/dev/null | grep -vxF -e --config -e -- || true)
not_registry=$(grep -v '^p/' <<<"$configs" || true)
assert_eq "every --config is a registry pack" "" "$not_registry"
assert_eq "six packs are passed" 6 "$(grep -c . <<<"$configs")"

# Tracked files under the paths minus the ignored ones: none may be a test file
if [[ -f $ignore ]]; then
    scanned=$(comm -23 <(git -C "$ROOT" ls-files -- "${TARGETS[@]}" | sort) \
        <(git -C "$ROOT" ls-files -ci --exclude-from="$ignore" -- "${TARGETS[@]}" | sort))
    tests_scanned=$(grep -E '\.test\.|/tests?/|/__tests__/|/mocks?/' <<<"$scanned" || true)
    assert_eq "no test file is in the scanned set" "" "$tests_scanned"
    assert_contains "the debug RBAC router is scanned" "routers/test_rbac.py" "$scanned"
else
    fail ".semgrepignore exists"
fi

# --- C. Not part of the other recipes (AC 5) ---

justfile="$ROOT/Justfile"
for recipe in check lint test test-api test-web; do
    plan=$(just --justfile "$justfile" --dry-run "$recipe" 2>&1)
    if [[ -n $plan ]]; then pass; else fail "just --dry-run $recipe prints its commands"; fi
    if [[ $plan != *semgrep* ]]; then pass; else fail "just $recipe does not run semgrep" "$plan"; fi
done
assert_contains "just semgrep runs the script with its arguments" './scripts/semgrep.sh "$@"' \
    "$(just --justfile "$justfile" --show semgrep 2>&1)"

# --- D. The version line and the Renovate rule (AC 3) ---

assert_eq "the script has one SEMGREP_VERSION line of the form Renovate matches" 1 \
    "$(grep -cE '^SEMGREP_VERSION="[0-9]+\.[0-9]+\.[0-9]+"$' "$SEMGREP" 2>/dev/null)"

renovate="$ROOT/renovate.json"
semgrep_managers='[.customManagers[] | select(.datasourceTemplate == "pypi" and .depNameTemplate == "semgrep")]'
assert_eq "renovate.json has one custom manager for semgrep on PyPI" 1 \
    "$(yq -p json "$semgrep_managers | length" "$renovate" 2>/dev/null)"
assert_contains "the custom manager reads scripts/semgrep.sh" 'scripts/semgrep\.sh' \
    "$(yq -p json "$semgrep_managers | .[0].managerFilePatterns[]" "$renovate" 2>/dev/null)"
# Renovate's pattern, run by Perl (which knows the named group), finds the script's version
pattern=$(yq -p json "$semgrep_managers | .[0].matchStrings[0]" "$renovate" 2>/dev/null)
matched=$(RE="$pattern" perl -ne 'print "$+{currentValue}\n" if /$ENV{RE}/' "$SEMGREP" 2>/dev/null)
if [[ -n $version && $matched == "$version" ]]; then
    pass
else
    fail "Renovate's pattern captures the script's version" "pattern '$pattern' gave '$matched', version '$version'"
fi

# The version is written once: nothing else pins semgrep, and CI runs it through the recipe
pins=$(git -C "$ROOT" grep -nE 'semgrep==[0-9]' -- . ':(exclude)_bmad-output' ':(exclude)*.md' 2>&1)
assert_eq "no file pins a semgrep version (git grep finds nothing)" "1" "$?"
assert_eq "no file pins a semgrep version" "" "$pins"
ci="$ROOT/.github/workflows/ci.yml"
if ! grep -qE 'semgrep==|uvx' "$ci"; then pass; else fail "ci.yml runs semgrep only through just semgrep"; fi

# --- E. The job (AC 8, 9, 10) ---

assert_eq "the semgrep job may read the code and write code scanning results" \
    '{"contents":"read","security-events":"write"}' \
    "$(yq -o json -I0 '.jobs.semgrep.permissions' "$ci" 2>/dev/null)"
assert_eq "the workflow default permission is contents: read" '{"contents":"read"}' \
    "$(yq -o json -I0 '.permissions' "$ci" 2>/dev/null)"
assert_eq "no other job has its own permissions" "semgrep" \
    "$(yq '.jobs | to_entries | .[] | select(.value | has("permissions")) | .key' "$ci" 2>/dev/null | xargs)"
assert_eq "security-events appears once in ci.yml" 1 "$(grep -c 'security-events' "$ci")"
assert_eq "the semgrep job has a timeout" 10 "$(yq '.jobs.semgrep.timeout-minutes' "$ci" 2>/dev/null)"
assert_eq "the semgrep job checks out the full history" 0 \
    "$(yq '.jobs.semgrep.steps[] | select(.uses == "actions/checkout@*") | .with.fetch-depth' "$ci" 2>/dev/null)"

steps='.jobs.semgrep.steps[]'
pr_scan="$steps | select(.run == \"just semgrep *--baseline-commit*\")"
assert_eq "one step scans a pull request against its base" 1 \
    "$(yq "[$pr_scan] | length" "$ci" 2>/dev/null)"
assert_contains "the baseline scan runs on pull requests only" "github.event_name == 'pull_request'" \
    "$(yq "$pr_scan | .if" "$ci" 2>/dev/null)"
full_scan="$steps | select(.env.SEMGREP_REPORT_ONLY == \"1\")"
assert_eq "one step runs the report-only full scan" 1 "$(yq "[$full_scan] | length" "$ci" 2>/dev/null)"
assert_eq "the full scan writes semgrep.sarif" "just semgrep --sarif-output=semgrep.sarif" \
    "$(yq "$full_scan | .run" "$ci" 2>/dev/null)"
assert_eq "SEMGREP_REPORT_ONLY is the string 1" '"1"' \
    "$(yq -o json "$full_scan | .env.SEMGREP_REPORT_ONLY" "$ci" 2>/dev/null)"
upload="$steps | select(.uses == \"github/codeql-action/upload-sarif@*\")"
assert_eq "the upload sends semgrep.sarif" semgrep.sarif "$(yq "$upload | .with.sarif_file" "$ci" 2>/dev/null)"
full_if=$(yq "$full_scan | .if" "$ci" 2>/dev/null)
if [[ -n $full_if && $full_if != null ]]; then pass; else fail "the full scan has an if"; fi
assert_eq "the upload runs when the full scan runs" "$full_if" "$(yq "$upload | .if" "$ci" 2>/dev/null)"

if ! grep -qi semgrep "$ROOT/.github/workflows/release.yml"; then pass; else fail "release.yml does not run semgrep"; fi

finish
