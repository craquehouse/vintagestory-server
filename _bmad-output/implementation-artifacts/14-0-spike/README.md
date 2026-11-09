# Story 14.0 spike evidence

Scripts and data behind the findings in `../14-0-epic-14-technical-preparation.md`, captured on 2026-11-09. Everything here is public ModDB data or output from a disposable container.

| File | Task | What it is |
|---|---|---|
| `moddb_probe.py` | 1 | Fetches 10 mods from the live ModDB API, checks release order and uniqueness, and parses downloaded archives with the project's own `modinfo.json` extractor |
| `probe-findings.json` | 1 | Output of `moddb_probe.py`, including per-archive version and modid comparisons |
| `sampled-releases.json` | 1 | The 10 captured responses, trimmed to release fields (`releaseid`, `modversion`, `modidstr`, `filename`, `fileid`, `tags`, `created`) |
| `stats.py`, `stats.txt` | 1 | Recomputes the story's aggregate figures from `sampled-releases.json` and `agentdocs/modlist-export.json`, and the output |
| `swap_test.py`, `swap_test.log` | 2 | Replaces a mod under a running server in a throwaway container, then starts the server with two versions present; full log |
| `webhook_probe.py` | 3 | Payload prototype checked against a local HTTP receiver |

## Re-running

From the repository root:

- `python3 _bmad-output/implementation-artifacts/14-0-spike/stats.py`: no network needed.
- `api/.venv/bin/python _bmad-output/implementation-artifacts/14-0-spike/moddb_probe.py <out_dir>`: calls the live ModDB API (about 25 requests) and downloads 12 small releases. Set `VS_API_KEY_ADMIN` to any value so the settings model loads.
- `api/.venv/bin/python _bmad-output/implementation-artifacts/14-0-spike/webhook_probe.py`: local only.
- `swap_test.py`: needs an image built with `docker build --platform linux/amd64 -t vss-spike .`. It runs a container named `vss-spike` on `127.0.0.1:18080` with no host volume, installs VintageStory and a mod over the network, and removes the container when done. Its API key is a throwaway for that container.

Results can differ on a later run as ModDB listings change.
