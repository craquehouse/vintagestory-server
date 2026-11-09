"""Story 14.0 Task 2: replace a mod under a running server, then test duplicate versions."""

import json
import subprocess
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:18080"
API = BASE + "/api/v1alpha1"
KEY = "spike-throwaway-key"  # Throwaway key for a disposable container; not a real credential
NAME = "vss-spike"
MODS = "/data/serverdata/Mods"
OLD = {"version": "5.0.2", "fileid": 87789}
NEW = {"version": "5.0.3", "fileid": 90054, "filename": "Auto Map Markers 5.0.3 - Vintage Story 1.22.zip"}
DEADLINE = time.time() + 900


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=None if body is None else json.dumps(body).encode())
    req.add_header("X-API-Key", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def sh(cmd):
    out = subprocess.run(["docker", "exec", NAME, "sh", "-c", cmd], capture_output=True, text=True, timeout=180)
    return (out.stdout + out.stderr).strip()


def state():
    return call("GET", "/server/status")[1]["data"]["state"]


def wait_for(states, label):
    while time.time() < DEADLINE:
        s = state()
        if s in states:
            print(f"  {label}: {s}", flush=True)
            return s
        time.sleep(2)
    raise SystemExit(f"timeout waiting for {states}")


def wait_log(pattern, since_lines):
    while time.time() < DEADLINE:
        lines = call("GET", "/console/history?lines=2000")[1]["data"]["lines"]
        new = lines[since_lines:] if len(lines) >= since_lines else lines
        if any(pattern in line for line in new):
            return lines
        time.sleep(3)
    raise SystemExit(f"timeout waiting for log {pattern!r}")


def console_len():
    return len(call("GET", "/console/history?lines=2000")[1]["data"]["lines"])


def mod_lines(lines):
    keys = ("egocarib", "Auto Map", "Found ", "sorted by dependency", "uplicate", "same id", "Exception", "rror", "arning")
    return [l[:170] for l in lines if any(k in l for k in keys) and "        " not in l]


def fetch_into_mods(fileid, filename):
    # Copy to a temporary name, then rename into place (the ADR-2 swap).
    script = (
        "import os, urllib.request\n"
        f"tmp = '{MODS}/.swap.tmp'\n"
        f"urllib.request.urlretrieve('https://mods.vintagestory.at/download?fileid={fileid}', tmp)\n"
        f"os.replace(tmp, '{MODS}/' + {filename!r})\n"
        "print('placed', os.path.getsize('" + MODS + "/' + " + repr(filename) + "))\n"
    )
    return sh(f"python3 - <<'PY'\n{script}PY")


subprocess.run(["docker", "run", "-d", "--rm", "--name", NAME, "--platform", "linux/amd64",
                "-p", "127.0.0.1:18080:8080", "-e", f"VS_API_KEY_ADMIN={KEY}", "vss-spike"],
               check=True, capture_output=True, timeout=60)
try:
    while time.time() < DEADLINE:
        try:
            if urllib.request.urlopen(BASE + "/healthz", timeout=5).status == 200:
                break
        except OSError:
            time.sleep(1)
    print("install server:", call("POST", "/server/install", {"version": "stable"})[0], flush=True)
    wait_for({"installed"}, "server install")
    code, body = call("POST", "/mods", {"slug": "egocaribautomapmarkers", "version": OLD["version"]})
    print("install mod 5.0.2:", code, {k: body.get("data", {}).get(k) for k in ("version", "filename", "compatibility")}, flush=True)
    old_filename = body["data"]["filename"]
    print("mods dir:", sh(f"ls -la '{MODS}'"), flush=True)

    n = console_len()
    print("start:", call("POST", "/server/start")[0], flush=True)
    lines = wait_log("now running on Port", n)
    print("== boot with 5.0.2:", *mod_lines(lines[n:]), sep="\n  ", flush=True)

    print("\n== SWAP WHILE RUNNING", flush=True)
    n = console_len()
    print(" ", fetch_into_mods(NEW["fileid"], NEW["filename"]), flush=True)
    print(" ", sh(f"rm -v '{MODS}/{old_filename}'"), flush=True)
    time.sleep(30)
    lines = call("GET", "/console/history?lines=2000")[1]["data"]["lines"]
    print("  state after 30s:", state(), "| new console lines:", len(lines) - n, flush=True)
    print(*[l[:170] for l in lines[n:]][-15:], sep="\n  ", flush=True)
    print("  server-main.log tail:", sh("tail -n 8 /data/serverdata/Logs/server-main.log 2>/dev/null | cut -c1-170"), flush=True)

    print("\n== RESTART", flush=True)
    n = console_len()
    print("  restart:", call("POST", "/server/restart")[0], flush=True)
    lines = wait_log("now running on Port", n)
    print("== boot with 5.0.3:", *mod_lines(lines[n:]), sep="\n  ", flush=True)

    print("\n== TWO VERSIONS PRESENT AT STARTUP", flush=True)
    print("  stop:", call("POST", "/server/stop")[0], flush=True)
    wait_for({"installed"}, "stopped")
    print(" ", fetch_into_mods(OLD["fileid"], old_filename), flush=True)
    print("  mods dir:", sh(f"ls '{MODS}'"), flush=True)
    n = console_len()
    print("  start:", call("POST", "/server/start")[0], flush=True)
    lines = wait_log("now running on Port", n)
    print(*mod_lines(lines[n:]), sep="\n  ", flush=True)
    print("  server-main.log mod lines:", sh("grep -iE 'egocarib|duplicate|same mod|multiple' /data/serverdata/Logs/server-main.log | tail -n 12 | cut -c1-200"), flush=True)
    print("  API mod list:", [(m["slug"], m["version"], m["filename"]) for m in call("GET", "/mods")[1]["data"]["mods"]], flush=True)
    print("  stop:", call("POST", "/server/stop")[0], flush=True)
finally:
    subprocess.run(["docker", "stop", "-t", "10", NAME], capture_output=True, timeout=60)
    print("container stopped", flush=True)
