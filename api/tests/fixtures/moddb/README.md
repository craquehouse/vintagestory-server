# ModDB API fixtures

Trimmed `GET https://mods.vintagestory.at/api/mod/{key}` responses captured on 2026-11-09 for Story 14.0. They contain only public ModDB data.

Each mod keeps `modid`, `assetid`, `name`, `author`, `urlalias`, `side`, `type` and `lastreleased`. Each release keeps `releaseid`, `modversion`, `modidstr`, `filename`, `fileid`, `downloads`, `tags` and `created`, in the original newest-first order. Descriptions, screenshots, changelogs and CDN URLs were removed.

| File | Source | Releases | Cases covered |
|---|---|---|---|
| `mod_carryon.json` | `carryon` | First 12 of 89 | Release order differs from version order (`2.0.0-rc.1`, then `1.14.3`, then `2.0.0-pre.8`); pre-release mod versions; releases tagged for 1.22 |
| `mod_instruments.json` | `instruments` | All 33 | One entry spanning three modids (`instruments`, `vsinstruments`, `vsinstrumentsbase`); `modversion` `1.0.1` repeated under different modids; `urlalias` is `null` |
| `mod_egocaribautomapmarkers.json` | `egocaribautomapmarkers` | All 24 | Repeated `filename` values (`Auto Map Markers.zip`); filenames with spaces; a second modid (`egocaribresinmapmarkers`); `urlalias` (`automapmarkers`) that does not resolve as a lookup key |
| `mod_not_found.json` | `maltiezfirearms` | None | A mod removed from ModDB: the response is `{"statuscode": "404"}` with no `mod` key |

ModDB returns `statuscode` as a string. See `agentdocs/vintagestory-modapi.md` for the API reference.
