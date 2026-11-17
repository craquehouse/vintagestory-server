#!/usr/bin/env bash
# Run the E2E tests CI runs, in two passes against throwaway containers (Stories 19.7, 20.6).
#
# First pass: a container from the image with a data directory that holds only the seeded
# web/e2e/fixtures/serverconfig.json and one seeded empty directory tree, placeholder keys
# and no game server; the untagged Playwright tests and the API's E2E tests run against it.
# Second pass: a replay container answers mod database requests from the recordings in
# web/e2e/fixtures/moddb/ (scripts/moddb-replay.py), and a second API container with
# VS_DEBUG=true and VS_MOD_DB_URL pointed at the replay runs the @moddb tests that are not
# @moddb-live or @install. Neither API container can reach the mod database, its image
# host or the vendor's version API (they resolve to loopback). Everything started is
# removed at the end, also after a failure. Never touches the dev stack, ./data or dev/.
#
# Usage: scripts/e2e-ci.sh [playwright args...]   (via `just test-e2e-ci`)
#   Arguments go to both Playwright runs; a run that then finds no test passes.
#   E2E_IMAGE        an image that is already built (CI sets it); unset builds vintagestory-server:e2e
#   E2E_PORT         first API container's host port, on 127.0.0.1 only (default 18080)
#   E2E_MODDB_PORT   second API container's host port, on 127.0.0.1 only (default 18081)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Placeholder keys, made up for this throwaway container. Never read from the environment:
# mise loads a developer's .env, which holds the real keys.
ADMIN_KEY="e2e-admin-placeholder-key"
MONITOR_KEY="e2e-monitor-placeholder-key"
CONTAINER="vintagestory-manager-e2e"
FIXTURE="web/e2e/fixtures/serverconfig.json"
# A directory inside another, as a game server writes, for the file browser navigation tests
SEEDED_DIR="Logs/Archive"
# Tests that need the live mod database, a game server, or install real mods (web/e2e/README.md)
TAGS='@moddb|@game-server|@install'
# Every external host the API calls; pointed at loopback so a call to one fails at once
BLOCKED_HOSTS=(mods.vintagestory.at api.vintagestory.at cdn.vintagestory.at moddbcdn.vintagestory.at)

# The second pass: the @moddb tests on recorded answers (Story 20.6, Epic 20 ADR-9)
REPLAY_CONTAINER="vintagestory-moddb-replay-e2e"
MODDB_CONTAINER="vintagestory-manager-e2e-moddb"
NETWORK="vintagestory-e2e"
REPLAY_PORT=8099
MODDB_DIR="web/e2e/fixtures/moddb"
MODDB_PORT="${E2E_MODDB_PORT:-18081}"
# The @moddb tests that stay local-only: they compare with live data or install a real mod
LIVE_ONLY_TAGS='@moddb-live|@install'

IMAGE="${E2E_IMAGE:-}"
PORT="${E2E_PORT:-18080}"
BASE_URL="http://127.0.0.1:$PORT"
MODDB_URL="http://127.0.0.1:$MODDB_PORT"

# remove_all: the three containers, then the network; what does not exist is skipped
remove_all() {
    docker rm -f "$CONTAINER" "$MODDB_CONTAINER" "$REPLAY_CONTAINER" >/dev/null 2>&1 || true
    docker network rm "$NETWORK" >/dev/null 2>&1 || true
}

cleanup() {
    local status=$?
    if ((status != 0)); then
        for name in "$CONTAINER" "$MODDB_CONTAINER" "$REPLAY_CONTAINER"; do
            if docker container inspect "$name" >/dev/null 2>&1; then
                echo "--- last 200 lines of the $name log ---"
                docker logs --tail 200 "$name" 2>&1 || true
            fi
        done
        if docker container inspect "$REPLAY_CONTAINER" >/dev/null 2>&1; then
            echo "--- requests the replay had no recording for ---"
            docker logs "$REPLAY_CONTAINER" 2>&1 | grep '^no_recording' || echo "(none)"
        fi
    fi
    remove_all
    [[ -n ${PYTEST_DATA_DIR:-} ]] && rm -rf "$PYTEST_DATA_DIR"
    exit "$status"
}
trap cleanup EXIT

if [[ -z $IMAGE ]]; then
    IMAGE="vintagestory-server:e2e"
    echo "Building $IMAGE..."
    docker build --platform linux/amd64 -t "$IMAGE" .
fi

add_hosts=()
for host in "${BLOCKED_HOSTS[@]}"; do
    add_hosts+=(--add-host "$host:127.0.0.1")
done

# Arguments go to both runs; with a spec path one of them may find no test
no_tests=()
(($#)) && no_tests=(--pass-with-no-tests)

# start_api_container <name> <host port> [docker create args...]: an API container from
# $IMAGE with the placeholder keys, the blocked hosts, the seeded serverconfig.json and the
# seeded directory tree
start_api_container() {
    local name=$1 port=$2
    shift 2
    docker create --name "$name" --platform linux/amd64 \
        -p "127.0.0.1:$port:8080" \
        -e VS_API_KEY_ADMIN="$ADMIN_KEY" \
        -e VS_API_KEY_MONITOR="$MONITOR_KEY" \
        -e VS_API_KEY="$ADMIN_KEY" \
        -e VS_DATA_DIR=/data \
        "${add_hosts[@]}" \
        "$@" \
        "$IMAGE" >/dev/null
    docker cp "$FIXTURE" "$name:/data/serverdata/serverconfig.json"
    docker start "$name" >/dev/null
    docker exec --user root "$name" chown vsmanager:vsmanager /data/serverdata/serverconfig.json
    # As the image's user (vsmanager), so the tree is owned like the files a game server writes
    docker exec "$name" mkdir -p "/data/serverdata/$SEEDED_DIR"
    docker exec "$name" ls -ld "/data/serverdata/$SEEDED_DIR"
}

# wait_healthy <base url>: wait up to 60 seconds for <base url>/healthz
wait_healthy() {
    echo "Waiting for $1/healthz..."
    for i in $(seq 1 60); do
        if curl -sf "$1/healthz" >/dev/null 2>&1; then
            echo "API is ready"
            return 0
        fi
        if ((i == 60)); then
            echo "API did not answer /healthz within 60 seconds" >&2
            exit 1
        fi
        sleep 1
    done
}

# Leftovers of an earlier run that was killed
remove_all

echo "Starting $CONTAINER from $IMAGE on $BASE_URL..."
start_api_container "$CONTAINER" "$PORT"
wait_healthy "$BASE_URL"

export VS_API_KEY_ADMIN="$ADMIN_KEY"
export VS_API_KEY_MONITOR="$MONITOR_KEY"
unset VS_API_KEY
export E2E_BASE_URL="$BASE_URL"
export PLAYWRIGHT_BASE_URL="$BASE_URL"
# web/e2e/file-browser-new-directory.spec.ts creates a directory in this container only
export E2E_CONTAINER="$CONTAINER"
# A failed local run would otherwise serve the HTML report and never return
export PLAYWRIGHT_HTML_OPEN=never

failed=0
(cd web && bun run test:e2e --grep-invert "$TAGS" "${no_tests[@]}" "$@") || failed=1
# The API's E2E tests skip when the address does not answer, and pytest passes on all-skip,
# so a container that died during the web tests must fail the run here instead.
if ! curl -sf "$BASE_URL/healthz" >/dev/null 2>&1; then
    echo "API stopped answering /healthz before the API E2E tests" >&2
    failed=1
else
    # The API's E2E tests import the app, which reads VS_DATA_DIR; keep it off dev/ and ./data
    PYTEST_DATA_DIR=$(mktemp -d)
    (cd api && VS_DATA_DIR="$PYTEST_DATA_DIR" uv run pytest tests/e2e) || failed=1
fi

# --- Second pass: the @moddb tests on recorded answers; runs even when the first failed ---
echo "Starting $REPLAY_CONTAINER with the recordings in $MODDB_DIR..."
docker network create "$NETWORK" >/dev/null
# --no-healthcheck: the image's health check probes the API's port, which this one has not
docker create --name "$REPLAY_CONTAINER" --platform linux/amd64 \
    --network "$NETWORK" --no-healthcheck \
    "$IMAGE" python3 /tmp/moddb-replay.py --dir /tmp/moddb --port "$REPLAY_PORT" >/dev/null
docker cp scripts/moddb-replay.py "$REPLAY_CONTAINER:/tmp/moddb-replay.py"
docker cp "$MODDB_DIR" "$REPLAY_CONTAINER:/tmp/moddb"
docker start "$REPLAY_CONTAINER" >/dev/null
echo "Waiting for the replay..."
for i in $(seq 1 30); do
    if docker exec "$REPLAY_CONTAINER" python3 -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$REPLAY_PORT/healthz', timeout=2)" \
        >/dev/null 2>&1; then
        echo "Replay is ready"
        break
    fi
    if ((i == 30)); then
        echo "The replay did not answer /healthz within 30 seconds" >&2
        exit 1
    fi
    sleep 1
done

echo "Starting $MODDB_CONTAINER from $IMAGE on $MODDB_URL..."
start_api_container "$MODDB_CONTAINER" "$MODDB_PORT" \
    --network "$NETWORK" \
    -e VS_DEBUG=true \
    -e VS_MOD_DB_URL="http://$REPLAY_CONTAINER:$REPLAY_PORT"
wait_healthy "$MODDB_URL"

# Its own report and results directories, so a failed first pass keeps its report
(cd web && E2E_BASE_URL="$MODDB_URL" PLAYWRIGHT_BASE_URL="$MODDB_URL" E2E_MODDB_REPLAY=1 \
    PLAYWRIGHT_HTML_OUTPUT_DIR=playwright-report-moddb \
    bun run test:e2e --grep '@moddb' --grep-invert "$LIVE_ONLY_TAGS" \
    --output test-results-moddb "${no_tests[@]}" "$@") || failed=1

# A mod database request that did not follow VS_MOD_DB_URL went to a blocked host
if docker logs "$MODDB_CONTAINER" 2>&1 | grep -E 'mod_api_connection_error|mod_download_failed'; then
    echo "A mod database request did not go to the replay (see the lines above)" >&2
    failed=1
fi
if ((failed)); then exit 1; fi
