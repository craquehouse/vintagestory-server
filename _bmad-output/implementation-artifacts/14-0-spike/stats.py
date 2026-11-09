"""Recompute Story 14.0's aggregate release statistics from committed data.

Run from the repository root: python3 _bmad-output/implementation-artifacts/14-0-spike/stats.py
"""

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
export = json.loads(Path("agentdocs/modlist-export.json").read_text())["mods"]
sample = json.loads((HERE / "sampled-releases.json").read_text())

multi = [m for m in export if len(m.get("modidstrs") or []) > 1]
alias = [m for m in export if m.get("urlalias") and m.get("modidstrs") and m["urlalias"] != m["modidstrs"][0]]
print(f"Mod list export: {len(export)} entries; {len(multi)} list several modids; {len(alias)} have a urlalias that differs from modidstrs[0]")

releases = [r for m in sample.values() for r in m.get("releases", [])]
print(f"Sampled: {len(sample)} mods ({sum(1 for m in sample.values() if m['statuscode'] != '200')} not found), {len(releases)} releases")
print(f"Filenames with spaces: {sum(' ' in r['filename'] for r in releases)}; with path separators: {sum(('/' in r['filename']) or ('\\\\' in r['filename']) for r in releases)}")
for slug, m in sample.items():
    rel = m.get("releases")
    if not rel:
        continue
    created = [r["created"] for r in rel]
    dup_versions = [v for v, n in Counter(r["modversion"] for r in rel).items() if n > 1]
    dup_files = [v for v, n in Counter(r["filename"] for r in rel).items() if n > 1]
    print(f"  {slug}: {len(rel)} releases, newest-first={created == sorted(created, reverse=True)}, "
          f"modids={sorted({r['modidstr'] for r in rel})}, repeated versions={dup_versions}, repeated filenames={dup_files}")
