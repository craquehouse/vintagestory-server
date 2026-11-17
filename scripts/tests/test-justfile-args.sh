#!/usr/bin/env bash
# Every Justfile recipe that forwards arguments passes each one intact (Story 20.3, FR242):
# `just test-api -k "a or b"` gives pytest one argument, `a or b`. Runs the real just on a
# copy of the Justfile with stubs for mise, docker, curl and sprint-status.sh, so no tool,
# container or test suite runs.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ROOT="$SCRIPTS_DIR/.."
JUST=$(command -v just)

dir=$(make_tmp)
mkdir -p "$dir/bin" "$dir/scripts"
cp "$ROOT/Justfile" "$dir/Justfile"
export ARGLOG="$dir/args.log"

# Each stub logs its name, then each argument on its own line, then `--`
for stub in bin/mise bin/docker bin/curl scripts/sprint-status.sh; do
    cat >"$dir/$stub" <<'STUB'
#!/usr/bin/env bash
{
    basename "$0"
    printf '%s\n' "$@"
    echo --
} >>"$ARGLOG"
STUB
    chmod +x "$dir/$stub"
done

# run_just [args...]: run just in the copy with the stubs first on PATH; the log starts empty
run_just() {
    : >"$ARGLOG"
    (cd "$dir" && PATH="$dir/bin:$PATH" API_PORT=8000 WEB_PORT=5173 "$JUST" "$@" >/dev/null 2>&1)
}

# assert_logged <name> <line>: the log has <line> as one whole line
assert_logged() {
    if grep -qxF -- "$2" "$ARGLOG"; then pass; else fail "$1" "no line '$2' in: $(tr '\n' ' ' <"$ARGLOG")"; fi
}

# One case per recipe: the recipe and its arguments, the last of which must arrive whole
cases=(
    'test-api|-k|a or b'
    'test-web|-t|a b'
    'test-scripts|a b'
    'test-e2e-api|-k|a or b'
    'test-e2e-web|-g|a b'
    'test-e2e-ci|-g|a b'
    'test-e2e|-k|a or b'
    'coverage-api|-k|a or b'
    'coverage-web|-t|a b'
    'lint-api|--select|a b'
    'typecheck-api|a b'
    'dev-api|--host|a b'
    'dev-web|--host|a b'
    'install-api|--group|a b'
    'install-web|--filter|a b'
    'docker|logs|a b'
    'changelog|--tag|a b'
    'release|a b'
    'sprint|retro-add|A1-key|a comment'
)
for entry in "${cases[@]}"; do
    IFS='|' read -r -a words <<<"$entry"
    last=${words[${#words[@]} - 1]}
    run_just "${words[@]}"
    status=$?
    # A recipe that fails after logging its arguments (e.g. a later line splitting them) fails here
    assert_eq "just ${words[0]} exits 0 with the stubs" 0 "$status"
    assert_logged "just ${words[0]} passes '$last' as one argument" "$last"
done

# No argument passes no empty argument
run_just test-api
assert_eq "just test-api with no argument passes none" \
    "$(printf '%s\n' mise exec -C api -- uv run pytest --ignore=tests/e2e --)" "$(<"$ARGLOG")"

# Both halves of `just docker restart` get the argument
run_just docker restart "a b"
assert_eq "just docker restart passes 'a b' to stop and to start" "2" "$(grep -cxF 'a b' "$ARGLOG")"

finish
