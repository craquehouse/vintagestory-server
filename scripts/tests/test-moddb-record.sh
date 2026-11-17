#!/usr/bin/env bash
# scripts/moddb-record.py trims and reports as its manifest says (Story 20.6, Epic 20 ADR-9).
# The "live" mod database is scripts/moddb-replay.py on a free local port serving a made-up
# directory; the manifest copy and the output are in a temporary directory. Never calls the
# live mod database and never writes web/e2e/fixtures/moddb/.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

REPLAY="$SCRIPTS_DIR/moddb-replay.py"
RECORD="$SCRIPTS_DIR/moddb-record.py"

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

# serve <dir>: (re)start the replay on <dir> with the User-Agent logged
serve() {
    stop_server
    PORT=$(free_port)
    python3 "$REPLAY" --dir "$1" --host 127.0.0.1 --port "$PORT" --log-user-agent >"$REPLAY_LOG" 2>&1 &
    SERVER_PID=$!
    for _ in $(seq 1 50); do
        curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && return 0
        sleep 0.1
    done
    fail "replay starts" "$(cat "$REPLAY_LOG")"
    return 1
}

# record <manifest> <out> [args...]: run the recorder against the replay, output in $OUTPUT
record() {
    local manifest=$1 out=$2
    shift 2
    OUTPUT=$(python3 "$RECORD" --manifest "$manifest" --out "$out" \
        --base-url "http://127.0.0.1:$PORT" --pause 0 --timeout 10 "$@" 2>&1)
}

# json <python expression over `d`, the parsed file> <file>
json() {
    python3 -c "import json, sys; d = json.load(open(sys.argv[1])); print($1)" "$2"
}

live=$(make_tmp)
work=$(make_tmp)
out="$work/out"
REPLAY_LOG="$work/replay.log"

# The "live" answers: 45 mods that match "food", one kept by its slug, 5 that match nothing
python3 - "$live" <<'EOF'
import json, sys
from pathlib import Path

live = Path(sys.argv[1])
mods = []
for i in range(1, 46):
    mods.append({"modid": i, "name": f"Mod {i}", "summary": "Food things" if i % 3 else "x",
                 "author": "a", "tags": ["FOOD"] if i % 3 == 0 else [], "urlalias": f"m{i}",
                 "modidstrs": [f"m{i}"], "logo": f"https://moddbcdn.vintagestory.at/{i}.png"})
mods.insert(10, {"modid": 100, "name": "Kept by slug", "summary": "", "author": "b",
                 "tags": [], "urlalias": None, "modidstrs": ["keepme"], "logo": None})
for i in range(200, 205):
    mods.insert(i - 195, {"modid": i, "name": f"Other {i}", "summary": "", "author": "c",
                          "tags": ["Tools"], "urlalias": f"o{i}", "modidstrs": [], "logo": None})
(live / "api-mods.json").write_text(json.dumps({"statuscode": "200", "mods": mods}))
subset = [m for m in mods if m["modid"] in (1, 2, 200, 999)]
(live / "api-mods-v.json").write_text(json.dumps({"statuscode": "200", "mods": subset}))
releases = [{"releaseid": n, "fileid": n, "modversion": f"1.{n}"} for n in (5, 4, 3, 2, 1)]
(live / "api-mod-a.json").write_text(
    json.dumps({"statuscode": "200", "mod": {"modid": 1, "releases": releases}}))
(live / "api-gameversions.json").write_text(
    json.dumps({"statuscode": "200", "gameversions": [{"tagid": -1, "name": "1.22.0"}]}))
(live / "manifest.json").write_text(json.dumps({"requests": [
    {"request": "/api/mods", "file": "api-mods.json"},
    {"request": "/api/mods?gameversion=-1", "file": "api-mods-v.json"},
    {"request": "/api/mod/a", "file": "api-mod-a.json"},
    {"request": "/api/gameversions", "file": "api-gameversions.json"},
]}))
EOF

cat >"$work/manifest.json" <<'EOF'
{
  "source": "https://mods.vintagestory.at",
  "listing": { "keep_slugs": ["KeepMe"], "keep_terms": ["food"] },
  "requests": [
    { "request": "/api/mods", "file": "api-mods.json", "trim": "listing", "recorded": "", "specs": ["x"] },
    { "request": "/api/mods?gameversion=-1", "file": "api-mods-v.json", "trim": "listing-subset", "recorded": "", "specs": ["x"] },
    { "request": "/api/mod/a", "file": "api-mod-a.json", "trim": "releases-first-2", "recorded": "", "specs": ["x"] },
    { "request": "/api/gameversions", "file": "api-gameversions.json", "trim": "none", "recorded": "", "specs": ["x"] }
  ]
}
EOF

today=$(date -u +%Y-%m-%d)
serve "$live" || { finish; exit 1; }

# --- first recording ---
if record "$work/manifest.json" "$out"; then pass; else fail "first recording succeeds" "$OUTPUT"; fi
assert_contains "first recording is reported" "/api/mods: first recording" "$OUTPUT"
assert_contains "listing count per term" "kept 46 mods ('slug': 1, 'food': 45)" "$OUTPUT"

expected_ids=$(python3 -c "print([*range(1, 11), 100, *range(11, 46)])")
assert_eq "listing keeps the slug and the term matches, in order, and drops the rest" \
    "$expected_ids" "$(json '[m["modid"] for m in d["mods"]]' "$out/api-mods.json")"
assert_eq "listing keeps a kept mod unchanged" "https://moddbcdn.vintagestory.at/1.png" \
    "$(json 'd["mods"][0]["logo"]' "$out/api-mods.json")"
assert_eq "listing-subset keeps only the listing's mods" "[1, 2]" \
    "$(json '[m["modid"] for m in d["mods"]]' "$out/api-mods-v.json")"
assert_eq "releases-first-2 keeps the two newest" "[5, 4]" \
    "$(json '[r["fileid"] for r in d["mod"]["releases"]]' "$out/api-mod-a.json")"
assert_eq "none is the same JSON" "True" \
    "$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1])) == json.load(open(sys.argv[2])))' \
        "$live/api-gameversions.json" "$out/api-gameversions.json")"
assert_eq "files are indented with one space and end in a newline" "{" "$(head -c 1 "$out/api-gameversions.json")"
assert_eq "second line is indented with one space" ' "statuscode": "200",' "$(sed -n 2p "$out/api-gameversions.json")"
assert_eq "recorded dates are set" "['$today', '$today', '$today', '$today']" \
    "$(json '[e["recorded"] for e in d["requests"]]' "$work/manifest.json")"

assert_contains "requests carry the fixed User-Agent" "served GET /api/mods user_agent=moddb-fixture-recorder" \
    "$(cat "$REPLAY_LOG")"
if grep -v 'user_agent=moddb-fixture-recorder$' "$REPLAY_LOG" | grep -q '^served'; then
    fail "every request carries the fixed User-Agent" "$(cat "$REPLAY_LOG")"
else
    pass
fi

# --- a refresh with no change ---
record "$work/manifest.json" "$out"
assert_contains "no change in fields" "/api/gameversions: no change in fields" "$OUTPUT"

# --- the field report: one field appears, one disappears ---
python3 - "$live/api-mod-a.json" <<'EOF'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
for r in d["mod"]["releases"]:
    r["changelog"] = ""
    del r["modversion"]
json.dump(d, open(path, "w"))
EOF
serve "$live"
record "$work/manifest.json" "$out"
assert_contains "added field with collapsed list positions" "  + mod.releases[].changelog" "$OUTPUT"
assert_contains "removed field with collapsed list positions" "  - mod.releases[].modversion" "$OUTPUT"

# --- --only rewrites one file and leaves the others' bytes and dates ---
python3 - "$work/manifest.json" <<'EOF'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
for e in d["requests"]:
    e["recorded"] = "2000-01-01"
open(path, "w").write(json.dumps(d, indent=2) + "\n")
EOF
echo '{"edited": true}' >"$out/api-mods.json"
before_v=$(cksum <"$out/api-mods-v.json")
echo '{"old": true}' >"$out/api-gameversions.json"
record "$work/manifest.json" "$out" --only /api/gameversions
assert_eq "--only leaves another file's bytes" '{"edited": true}' "$(cat "$out/api-mods.json")"
assert_eq "--only leaves the subset's bytes" "$before_v" "$(cksum <"$out/api-mods-v.json")"
assert_eq "--only rewrites its file" "1.22.0" "$(json 'd["gameversions"][0]["name"]' "$out/api-gameversions.json")"
assert_eq "--only sets only its date" "['2000-01-01', '2000-01-01', '2000-01-01', '$today']" \
    "$(json '[e["recorded"] for e in d["requests"]]' "$work/manifest.json")"
if record "$work/manifest.json" "$out" --only /api/nothing; then
    fail "--only with an unknown request fails" "$OUTPUT"
else
    pass
fi

# --- a request that fails writes nothing ---
python3 - "$work/manifest.json" "$work/manifest-missing.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
d["requests"].append({"request": "/api/mod/missing", "file": "api-mod-missing.json",
                      "trim": "none", "recorded": "", "specs": ["x"]})
open(sys.argv[2], "w").write(json.dumps(d, indent=2) + "\n")
EOF
snapshot() { (cd "$out" && cksum ./*.json) ; cksum <"$work/manifest-missing.json"; }
before=$(snapshot)
if record "$work/manifest-missing.json" "$out"; then
    fail "a failed request stops the run" "$OUTPUT"
else
    pass
fi
assert_contains "the failure is named" "/api/mod/missing" "$OUTPUT"
assert_contains "the failure says nothing was written" "nothing was written" "$OUTPUT"
assert_eq "a failed run writes nothing" "$before" "$(snapshot)"
if [[ -e $out/api-mod-missing.json ]]; then fail "no file for the failed request"; else pass; fi

# --- a listing under 41 mods stops the run ---
python3 - "$work/manifest.json" "$work/manifest-thin.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
d["listing"]["keep_terms"] = ["other"]
open(sys.argv[2], "w").write(json.dumps(d, indent=2) + "\n")
EOF
thin_out=$(make_tmp)
if record "$work/manifest-thin.json" "$thin_out"; then
    fail "a thin listing stops the run" "$OUTPUT"
else
    pass
fi
assert_contains "the thin listing is named" "fewer than 41" "$OUTPUT"
assert_eq "a thin listing writes nothing" "" "$(ls "$thin_out")"

stop_server
finish
