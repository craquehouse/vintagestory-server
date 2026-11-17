#!/usr/bin/env bash
# scripts/moddb-replay.py answers from its manifest only (Story 20.6, Epic 20 ADR-9). Runs the
# server on a free local port against a made-up directory; needs python3 and curl, no network.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

REPLAY="$SCRIPTS_DIR/moddb-replay.py"

free_port() {
    python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

SERVER_PID=""
stop_server() {
    if [[ -n $SERVER_PID ]]; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
        SERVER_PID=""
    fi
    return 0
}
trap 'stop_server; cleanup_tmp' EXIT

# start_server <dir> <log> [args...]: start the replay on a free port and wait for /healthz
start_server() {
    local dir=$1 log=$2
    shift 2
    PORT=$(free_port)
    python3 "$REPLAY" --dir "$dir" --host 127.0.0.1 --port "$PORT" "$@" >"$log" 2>&1 &
    SERVER_PID=$!
    for _ in $(seq 1 50); do
        curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && return 0
        sleep 0.1
    done
    fail "replay starts" "$(cat "$log")"
    return 1
}

# status <path> [curl args...]: the HTTP status of a request to the running replay
status() {
    local path=$1
    shift
    curl -s -o /dev/null -w '%{http_code}' "$@" "http://127.0.0.1:$PORT$path"
}

dir=$(make_tmp)
printf '{"statuscode": "200", "mods": [{"modid": 1}]}\n' >"$dir/api-mods.json"
printf '{"statuscode": "200", "mods": []}\n' >"$dir/api-mods-version.json"
printf 'PK\003\004 not really a zip' >"$dir/file.zip"
cat >"$dir/manifest.json" <<'EOF'
{
  "requests": [
    { "request": "/api/mods", "file": "api-mods.json" },
    { "request": "/api/mods?gameversion=-5&b=2", "file": "api-mods-version.json" },
    { "request": "/download?fileid=7", "file": "file.zip", "status": 201, "content_type": "application/zip" }
  ]
}
EOF

log="$dir/replay.log"
if start_server "$dir" "$log"; then
    body=$(curl -s "http://127.0.0.1:$PORT/api/mods")
    assert_eq "JSON answer byte for byte" "$(cat "$dir/api-mods.json")" "$body"
    assert_eq "JSON answer status" 200 "$(status /api/mods)"
    assert_eq "JSON content type" "application/json" \
        "$(curl -s -o /dev/null -w '%{content_type}' "http://127.0.0.1:$PORT/api/mods")"

    assert_eq "query matches with its parameters in another order" \
        "$(cat "$dir/api-mods-version.json")" \
        "$(curl -s "http://127.0.0.1:$PORT/api/mods?b=2&gameversion=-5")"

    assert_eq "own status" 201 "$(status '/download?fileid=7')"
    assert_eq "own content type" "application/zip" \
        "$(curl -s -o /dev/null -w '%{content_type}' "http://127.0.0.1:$PORT/download?fileid=7")"
    curl -s -o "$dir/got.zip" "http://127.0.0.1:$PORT/download?fileid=7"
    if cmp -s "$dir/file.zip" "$dir/got.zip"; then pass; else fail "binary answer byte for byte"; fi

    assert_eq "unknown path is 404" 404 "$(status '/api/mod/unknown?x=1')"
    missing=$(curl -s "http://127.0.0.1:$PORT/api/mod/unknown?x=1")
    assert_eq "404 body names the path and query" "No recording for GET /api/mod/unknown?x=1" "$missing"
    assert_contains "404 body is plain text" "text/plain" \
        "$(curl -s -o /dev/null -w '%{content_type}' "http://127.0.0.1:$PORT/api/mod/unknown")"
    assert_eq "a query the manifest lacks is 404" 404 "$(status '/api/mods?gameversion=-6')"

    assert_eq "/manifest.json is not served" 404 "$(status /manifest.json)"
    assert_eq "/api-mods.json is not served" 404 "$(status /api-mods.json)"
    assert_eq "/../manifest.json is not served" 404 "$(status /../manifest.json --path-as-is)"

    assert_eq "POST is 405" 405 "$(status /api/mods -X POST)"
    assert_eq "DELETE is 405" 405 "$(status /api/mods -X DELETE)"

    stop_server
    assert_contains "log has a served line" "served GET /api/mods" "$(cat "$log")"
    assert_contains "log has a no_recording line" "no_recording GET /api/mod/unknown?x=1" "$(cat "$log")"
fi

# --log-user-agent adds the User-Agent to each line
if start_server "$dir" "$log" --log-user-agent; then
    curl -s -o /dev/null -A "test-agent/1" "http://127.0.0.1:$PORT/api/mods"
    stop_server
    assert_contains "user agent logged on request" "served GET /api/mods user_agent=test-agent/1" "$(cat "$log")"
fi

# refuses <name> <manifest> <message>: the server exits non-zero at start with <message>
refuses() {
    local bad
    bad=$(make_tmp)
    printf '{}\n' >"$bad/a.json"
    printf '%s\n' "$2" >"$bad/manifest.json"
    local out code
    out=$(timeout 10 python3 "$REPLAY" --dir "$bad" --port "$(free_port)" 2>&1)
    code=$?
    if [[ $code -ne 0 && $code -ne 124 ]]; then pass; else fail "$1: exits non-zero" "exit $code: $out"; fi
    assert_contains "$1: message" "$3" "$out"
}

refuses "missing file" '{"requests": [{"request": "/api/mods", "file": "nope.json"}]}' "missing file: nope.json"
refuses "file with a slash" '{"requests": [{"request": "/api/mods", "file": "../a.json"}]}' "unsafe file"
refuses "file with a slash inside" '{"requests": [{"request": "/api/mods", "file": "sub/a.json"}]}' "unsafe file"
refuses "same request twice" \
    '{"requests": [{"request": "/api/mods?b=1&a=2", "file": "a.json"}, {"request": "/api/mods?a=2&b=1", "file": "a.json"}]}' \
    "recorded twice"
refuses "manifest does not parse" '{"requests": [' "cannot read"

finish
