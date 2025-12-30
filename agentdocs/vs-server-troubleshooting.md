# VintageStory Server Troubleshooting

Reference documentation for known VintageStory dedicated server behaviors, quirks, and troubleshooting steps.

## Configuration File Behavior

### Environment Variables vs serverconfig.json

**Issue:** VintageStory uses command-line arguments (like `--dataPath`) on first startup to generate `serverconfig.json`, but then ignores those arguments in favor of the config file values on subsequent runs.

**Symptom:** Changing environment variables or command-line arguments has no effect on paths like `ModPaths` or `SaveFileLocation`.

**Example:** If the server was first started with `--dataPath ../data/serverdata`, the config file will contain:
```json
"ModPaths": [
  "Mods",
  "../data/serverdata/Mods"
],
"SaveFileLocation": "../data/serverdata/Saves/default.vcdbs"
```

Later changing to `--dataPath /data/serverdata` will NOT update these paths automatically.

**Resolution:**
1. Manually edit `serverconfig.json` to correct the paths
2. Use absolute paths for reliability: `/data/serverdata/Mods`, `/data/serverdata/Saves/...`
3. Or use correct relative paths from the server installation directory (e.g., from `/data/server`, use `../serverdata/Mods`)

**Prevention:** Ensure the correct `--dataPath` value is used on the very first server startup before any config files are generated.

---

## Path Resolution

### ModPaths are Relative to Server Installation Directory

The `ModPaths` array in `serverconfig.json` contains paths that are resolved relative to the server installation directory (where `VintagestoryServer.dll` is located), NOT the current working directory or data directory.

**Example:** If server is installed at `/data/server/`:
- `"Mods"` resolves to `/data/server/Mods` (core game mods)
- `"../serverdata/Mods"` resolves to `/data/serverdata/Mods` (user mods)

### Double-Path Bug

**Symptom:** Log shows paths like `/data/data/serverdata/Mods (Not found?)`

**Cause:** Incorrect relative path in `serverconfig.json` such as `"../data/serverdata/Mods"` which from `/data/server` resolves to `/data/data/serverdata/Mods`.

**Fix:** Change to either:
- Absolute: `"/data/serverdata/Mods"`
- Correct relative: `"../serverdata/Mods"`

---

## Mod Loading

### Mod File Extensions

- Active mods: `.zip`
- Disabled mods: `.zip.disabled`

VintageStory only loads files with `.zip` extension. The API uses the `.disabled` suffix convention to toggle mods without deleting them.

### Mod Search Order

VintageStory searches mod directories in the order specified in `ModPaths`. The first entry is typically the server installation's `Mods/` directory (core mods), and subsequent entries are for user-installed mods.

---

## Logging

### Log Location

Server logs are written to `{dataPath}/Logs/`:
- `server-main.log` - Primary server log
- `server-event.log` - Game events
- `server-debug.log` - Debug output (if enabled)

### Useful Log Patterns

Check mod loading:
```
grep "Will search the following paths for mods" server-main.log
grep "Found .* mods" server-main.log
```

Check for path issues:
```
grep "Not found" server-main.log
```
