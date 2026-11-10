"""Story 14.0 Task 1: verify ModDB release behavior against the live API.

Run with the API virtualenv so modinfo.json is parsed by the project's own code:
    api/.venv/bin/python moddb_probe.py <out_dir>
"""

import json
import sys
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path

from vintagestory_api.services.mod_api import check_compatibility
from vintagestory_api.services.mod_state import ModStateManager

OUT = Path(sys.argv[1])
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "vintagestory-server-spike/14.0"}

SAMPLE = [
    "primitivesurvival", "betterruins", "carryon", "expandedfoods", "smithingplus",
    "maltiezfirearms", "egocaribautomapmarkers", "instruments", "hudclock", "vsimgui",
]
DOWNLOAD = {"carryon", "smithingplus", "maltiezfirearms", "egocaribautomapmarkers", "hudclock", "instruments"}
MAX_BYTES = 25 * 1024 * 1024
GAME_VERSION = "1.22.7"


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def download(fileid, dest):
    url = f"https://mods.vintagestory.at/download?fileid={fileid}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        size = int(r.headers.get("Content-Length") or 0)
        if size > MAX_BYTES:
            return None, size, r.geturl()
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return None, len(data), r.geturl()
        dest.write_bytes(data)
        return dest, len(data), r.geturl()


results = {}
with tempfile.TemporaryDirectory() as tmp:
    manager = ModStateManager(state_dir=Path(tmp) / "state", mods_dir=Path(tmp) / "mods")
    for slug in SAMPLE:
        time.sleep(0.5)
        data = get_json(f"https://mods.vintagestory.at/api/mod/{slug}")
        (RAW / f"{slug}.json").write_text(json.dumps(data))
        if data.get("statuscode") != "200":
            results[slug] = {"statuscode": data.get("statuscode")}
            continue
        mod = data["mod"]
        rel = mod["releases"]
        created = [r.get("created") for r in rel]
        info = {
            "releases": len(rel),
            "ordered_newest_first_by_created": created == sorted(created, reverse=True),
            "ordered_newest_first_by_releaseid": [r["releaseid"] for r in rel] == sorted((r["releaseid"] for r in rel), reverse=True),
            "duplicate_modversions": [v for v, n in Counter(r.get("modversion") for r in rel).items() if n > 1],
            "duplicate_filenames": [v for v, n in Counter(r.get("filename") for r in rel).items() if n > 1],
            "modidstrs_in_releases": sorted({r.get("modidstr") for r in rel}),
            "empty_tags": sum(1 for r in rel if not r.get("tags")),
            "prerelease_tags": sorted({t for r in rel for t in r.get("tags", []) if "-" in t})[:6],
            "file_extensions": sorted({Path(r.get("filename", "")).suffix for r in rel}),
            "compat_vs_1_22_7": Counter(check_compatibility(r, GAME_VERSION) for r in rel),
            "lookup_by_urlalias_matches": None,
            "downloads": [],
        }
        alias = mod.get("urlalias")
        if alias and alias != slug:
            time.sleep(0.5)
            other = get_json(f"https://mods.vintagestory.at/api/mod/{alias}")
            info["lookup_by_urlalias_matches"] = other.get("mod", {}).get("assetid") == mod.get("assetid")
        if slug in DOWNLOAD:
            for r in [rel[0], rel[len(rel) // 2]] if len(rel) > 1 else rel[:1]:
                time.sleep(0.5)
                dest = Path(tmp) / f"dl_{r['fileid']}{Path(r['filename']).suffix or '.bin'}"
                path, size, final_url = download(r["fileid"], dest)
                row = {"modversion": r["modversion"], "modidstr": r.get("modidstr"), "filename": r["filename"],
                       "bytes": size, "cdn_name": final_url.rsplit("/", 1)[-1]}
                if path is None:
                    row["skipped"] = "too large"
                elif path.suffix != ".zip":
                    row["skipped"] = "not a zip"
                else:
                    modinfo = manager._extract_modinfo_from_zip(path)
                    row["modinfo_modid"] = (modinfo or {}).get("modid") or (modinfo or {}).get("modID")
                    row["modinfo_version"] = (modinfo or {}).get("version")
                    row["version_matches"] = row["modinfo_version"] == r["modversion"]
                    row["modid_matches"] = (str(row["modinfo_modid"]).lower() == str(r.get("modidstr")).lower())
                info["downloads"].append(row)
        results[slug] = info

(OUT / "findings.json").write_text(json.dumps(results, indent=2, default=dict))
print(json.dumps(results, indent=1, default=dict))
