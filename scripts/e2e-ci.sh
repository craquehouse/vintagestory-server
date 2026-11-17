#!/usr/bin/env bash
# Run the E2E tests that carry no tag against a throwaway container (Story 19.7).
#
# Starts a container from the image with a data directory that holds only the seeded
# web/e2e/fixtures/serverconfig.json and one seeded empty directory tree, placeholder keys
# and no game server, waits for /healthz, runs the untagged Playwright tests and the API's
# E2E tests, and removes the container. Never touches the dev stack, ./data or dev/.
#
# Usage: scripts/e2e-ci.sh [playwright args...]   (via `just test-e2e-ci`)
#   E2E_IMAGE  an image that is already built (CI sets it); unset builds vintagestory-server:e2e
#   E2E_PORT   host port, published on 127.0.0.1 only (default 18080)
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
BLOCKED_HOSTS=(mods.vintagestory.at api.vintagestory.at cdn.vintagestory.at)

IMAGE="${E2E_IMAGE:-}"
PORT="${E2E_PORT:-18080}"
BASE_URL="http://127.0.0.1:$PORT"

cleanup() {
    local status=$?
    if ((status != 0)) && docker container inspect "$CONTAINER" >/dev/null 2>&1; then
        echo "--- last 200 lines of the $CONTAINER log ---"
        docker logs --tail 200 "$CONTAINER" 2>&1 || true
    fi
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
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

echo "Starting $CONTAINER from $IMAGE on $BASE_URL..."
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker create --name "$CONTAINER" --platform linux/amd64 \
    -p "127.0.0.1:$PORT:8080" \
    -e VS_API_KEY_ADMIN="$ADMIN_KEY" \
    -e VS_API_KEY_MONITOR="$MONITOR_KEY" \
    -e VS_API_KEY="$ADMIN_KEY" \
    -e VS_DATA_DIR=/data \
    "${add_hosts[@]}" \
    "$IMAGE" >/dev/null
docker cp "$FIXTURE" "$CONTAINER:/data/serverdata/serverconfig.json"
docker start "$CONTAINER" >/dev/null
docker exec --user root "$CONTAINER" chown vsmanager:vsmanager /data/serverdata/serverconfig.json
# As the image's user (vsmanager), so the tree is owned like the files a game server writes
docker exec "$CONTAINER" mkdir -p "/data/serverdata/$SEEDED_DIR"
docker exec "$CONTAINER" ls -ld "/data/serverdata/$SEEDED_DIR"

echo "Waiting for $BASE_URL/healthz..."
for i in $(seq 1 60); do
    if curl -sf "$BASE_URL/healthz" >/dev/null 2>&1; then
        echo "API is ready"
        break
    fi
    if ((i == 60)); then
        echo "API did not answer /healthz within 60 seconds" >&2
        exit 1
    fi
    sleep 1
done

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
(cd web && bun run test:e2e --grep-invert "$TAGS" "$@") || failed=1
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
if ((failed)); then exit 1; fi
