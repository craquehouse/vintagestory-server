# Vintage Story Server Directory Structure and Layout

**Based on:** v1.21.6 (Latest Stable)
**Analysis Date:** December 27, 2025
**Platform:** Linux x64

## Overview

This document provides a comprehensive analysis of the Vintage Story dedicated server directory structure, file layout, and configuration. It is based on a fresh installation of v1.21.6 downloaded from official Vintage Story servers.

**Quick Reference:**
- [Top-Level Structure](#top-level-structure)
- [Server Files](#server-files)
- [Libraries](#libraries)
- [Assets](#assets)
- [Mods Directory](#mods-directory)
- [Configuration](#configuration)
- [Data Directory](#data-directory)
- [Server Startup](#server-startup)

---

## Top-Level Structure

```
.local/                              # Server installation root
│
├── VintagestoryServer.dll             # Main server executable (92 KB)
├── VintagestoryServer.runtimeconfig.json  # .NET runtime config (381 B)
├── VintagestoryServer.deps.json      # Dependencies manifest (39 KB)
├── VintagestoryAPI.dll               # Modding API library (1.9 MB)
├── VintagestoryAPI.xml              # API documentation (XML)
├── VintagestoryLib.dll              # Core game library (2.8 MB)
├── server.sh                        # Init/service script (11 KB)
├── credits.txt                      # Credits and legal (10 KB)
│
├── Lib/                            # Dependency libraries (~90 files)
├── Mods/                           # BASE GAME MODS ONLY (⚠️ SEE WARNING)
├── assets/                         # Game assets (read-only)
│   ├── game/                       # Survival mode assets
│   ├── creative/                    # Creative mode assets
│   └── survival/                   # Survival mode assets
│
└── vs_server_linux-x64_1.21.6.tar.gz  # Downloaded archive (43 MB)
```

**Total Size:** ~105 MB (extracted)

---

## Server Files

### Core Executables

| File | Size | Description |
|------|-------|-------------|
| `VintagestoryServer.dll` | 92 KB | Main server executable (.NET assembly) |
| `VintagestoryServer.runtimeconfig.json` | 381 B | .NET 8.0 runtime configuration |
| `VintagestoryServer.deps.json` | 39 KB | Dependency manifest for .NET loader |

### Core Libraries

| File | Size | Description |
|------|-------|-------------|
| `VintagestoryLib.dll` | 2.8 MB | Core game logic, world management, server engine |
| `VintagestoryAPI.dll` | 1.9 MB | Public API for mod development |
| `VintagestoryAPI.xml` | - | XML documentation for API (used by IDEs) |

### Other Files

| File | Size | Description |
|------|-------|-------------|
| `server.sh` | 11 KB | Service management script (init.d compatible) |
| `credits.txt` | 10 KB | Credits, licensing, and legal information |
| `current_version` | - | Created by API, tracks installed version |

---

## Libraries

The `Lib/` directory contains all runtime dependencies required by the server.

### System Libraries

Microsoft .NET runtime and framework libraries:

- `System.Drawing.Common.dll` - Graphics and imaging
- `System.ServiceModel.dll` - WCF services
- `System.ServiceModel.Primitives.dll` - WCF primitives
- `System.Private.ServiceModel.dll` - WCF implementation
- `Microsoft.CodeAnalysis.CSharp.dll` - C# compiler services
- `Microsoft.Data.Sqlite.dll` - SQLite database provider

### Native Libraries

Platform-specific shared libraries (*.so):

| File | Purpose |
|------|---------|
| `libzstd.so` | Zstandard compression |
| `libSkiaSharp.so` | Graphics rendering (Skia) |
| `libopenal.so.1` | OpenAL audio |
| `libe_sqlite3.so` | SQLite database engine |

### Third-Party Libraries

| Library | Purpose |
|---------|---------|
| `Mono.Cecil.dll` + related | Code manipulation and patching |
| `Newtonsoft.Json.dll` | JSON serialization/deserialization |
| `protobuf-net.dll` | Protocol buffers serialization |
| `SharpAvi.dll` + SkiaSharp | Video recording support |
| `OpenTK.*.dll` (multiple) | OpenGL bindings for rendering |
| `ICSharpCode.SharpZipLib.dll` | ZIP archive handling |
| `SQLitePCLRaw.*.dll` (multiple) | Portable SQLite wrapper |
| `JsonDiffPatch.dll` | JSON patching format support |
| `0Harmony.dll` | Runtime patching framework |
| `Tavis.JsonPatch.dll` | JSON Patch (RFC 6902) |
| `CommandLine.dll` | Command-line argument parsing |
| `DnsClient.dll` | DNS client for network resolution |
| `AnimatedGif.dll` | Animated GIF support |

### GTK/GDK Libraries (Linux UI)

Graphics-related libraries for Linux:

| File | Purpose |
|------|---------|
| `GtkSharp.dll` | GTK# bindings |
| `GdkSharp.dll` | GDK (GIMP Drawing Kit) |
| `CairoSharp.dll` | Cairo graphics library |
| `AtkSharp.dll` | ATK accessibility toolkit |
| `GioSharp.dll` | GIO I/O library |
| `PangoSharp.dll` | Pango text layout library |
| `GLibSharp.dll` | GLib utility library |
| `xplatforminterface.dll` | Cross-platform interface |

### PDB Files (Debug Symbols)

All major DLLs have corresponding `.pdb` files:
- `VintagestoryServer.pdb`
- `VintagestoryLib.pdb`
- `VintagestoryAPI.pdb`
- Various library PDBs in `Lib/`

These are for debugging and can be safely ignored in production.

---

## Assets

The `assets/` directory contains all game assets. These are **read-only** and should not be modified.

### assets/game/ - Main Survival Assets

```
assets/game/
├── blocktypes/               # Block definitions and properties
├── entities/                 # Entity templates and behaviors
├── config/                  # Game configuration files
├── lang/                    # Localization (34 directories)
├── music/                   # Game music
├── shaderincludes/           # Shared shader code
├── shaders/                 # GLSL shaders (86 directories)
├── shapes/                  # 3D models
├── sounds/                  # Sound effects
└── textures/                # Textures and images
    ├── environment/          # Environment textures
    ├── gui/                # UI textures
    └── ...
```

#### Key Configuration Files

Located in `assets/game/config/`:

| File | Size | Description |
|------|-------|-------------|
| `remaps.json` | 183 KB | Block/item remapping for version updates |
| `remapentities.json` | 9.8 KB | Entity remapping for version updates |
| `weather.json` | 704 B | Weather configuration |
| `colormaps.json` | 273 B | Color mapping definitions |
| `creativetabs.json` | 639 B | Creative mode tabs |
| `seraphrandomizer.json` | 3.4 KB | Random seed configuration |

**Configuration Subdirectories:**
- `weatherpatterns/` - Weather pattern definitions (10 files)
- `windpatterns/` - Wind pattern definitions (7 files)
- `weatherevents/` - Weather event definitions (7 files)

#### Shaders

The `shaders/` directory contains 86 shader subdirectories with GLSL shader code for:
- Block rendering
- Entity rendering
- Weather effects
- Water rendering
- Particle systems
- UI elements

#### Localization

The `lang/` directory contains translations in 34 languages including:
- English (en)
- German (de)
- Russian (ru)
- French (fr)
- Spanish (es)
- Italian (it)
- Ukrainian (uk)
- And more...

### assets/creative/ - Creative Mode Assets

Similar structure to `assets/game/` but with creative-mode-specific assets:
- Block definitions
- Item definitions
- Creative UI elements
- God-mode tools

### assets/survival/ - Survival Mode Assets

Survival-mode-specific assets:
- Hunger/thirst mechanics
- Death and respawn logic
- Progressive crafting
- Entity survival behaviors

---

## Mods Directory

⚠️ **CRITICAL WARNING:**

The `Mods/` directory in the server installation is **reserved for base game mods only**.

**DO NOT add custom mods to this directory!**

### Base Game Mods (Installed by Default)

| File | Size | Description |
|------|-------|-------------|
| `VSSurvivalMod.dll` | 3.1 MB | Survival game mechanics and systems |
| `VSCreativeMod.dll` | 166 KB | Creative mode functionality |
| `VSEssentials.dll` | 815 KB | Core essential systems |

### do_not_add_mods_here.txt

This file contains the warning:
```
This place is reserved for base game mods only
(VSSurvivalMod VSCreativeMod and VSEssentials).

Do not use it for other mods, instead put other mods
in VintageStoryData/Mods folder.
```

### Proper Mod Management

**Custom mods should be placed in:**
- `data/Mods/` (preferred, if `--dataPath` is used)
- `VintageStoryData/Mods/` (legacy location)

**Recommended Setup for Updates:**

```bash
# Create persistent data directory
mkdir -p data/Mods

# Create symlink from server root Mods to data/Mods
# This allows mods to persist across server updates
rm -rf Mods
ln -s data/Mods Mods
```

**Benefits:**
1. When you download a new server version and extract it, the `Mods/` directory would be overwritten
2. With the symlink, extraction sees `Mods/` as a symlink and doesn't overwrite it
3. Your custom mods are preserved
4. Base game mods are loaded from `assets/` directory anyway

---

## Configuration

### Runtime Configuration

Configuration is split between:

1. **Static configuration** - Files in `assets/game/config/` (defaults, read-only)
2. **Runtime configuration** - Generated files in `data/` (writable)

### Server Configuration Files (Generated)

Located in `data/config/` (or `VintageStoryData/`):

| File | Purpose |
|------|---------|
| `serverconfig.json` | Main server settings (IP, port, password, whitelist) |
| `playerdata.json` | Individual player data |
| `playerclaims.json` | Land claim registry |
| `players.json` | Player registry and authentication |
| `worldconfig.json` | World-specific settings |
| `config.json` | Additional configuration |

### First Run Behavior

On first server start:
1. `serverconfig.json` is created with defaults
2. `Generated/` directory is created
3. `Logs/` directory is created
4. World generation prompts for seed/world settings

---

## Data Directory

The `--dataPath` argument specifies where persistent data is stored.

**Default:** If not specified, data is stored relative to server executable.

**Recommended:** Use absolute path to `--dataPath`:
```bash
dotnet VintagestoryServer.dll --dataPath /path/to/data
```

### Data Directory Structure

```
data/                           # Persistent storage (--dataPath)
│
├── Mods/                       # Custom mods directory
│   ├── [custom-mod-1].dll
│   └── [custom-mod-2].dll
│
├── config/                      # Runtime configuration
│   ├── serverconfig.json
│   ├── playerdata.json
│   ├── playerclaims.json
│   ├── players.json
│   └── worldconfig.json
│
├── Generated/                   # Generated content
│   └── worlds/               # World saves
│       └── [world-name]/
│           ├── chunkdata/      # Chunk data
│           ├── entities.db     # Entity database
│           └── mapdb/         # Map data
│
├── Logs/                       # Server logs
│   ├── server-main.log         # Main log
│   ├── server-exceptions.log   # Exception log
│   └── server-debug.txt       # Debug output
│
└── VintageStoryData/          # Alternative (legacy) location
    └── Mods/                 # Legacy mod directory
```

### Key Points

1. **Generated/worlds/** - All world saves are here
2. **Logs/** - Essential for troubleshooting
3. **config/** - Writable configuration (NOT assets/game/config)
4. **Mods/** - Custom mods (persisted across updates)

---

## Server Startup

### Command Line

**Basic:**
```bash
dotnet VintagestoryServer.dll --dataPath /path/to/data
```

**With options:**
```bash
dotnet VintagestoryServer.dll \
  --dataPath /path/to/data \
  --port 42420 \
  --ip 0.0.0.0
```

### server.sh Script

The included script provides service management:

**Features:**
- User/group management
- Screen session management
- Graceful shutdown with `/stop` command
- Process monitoring
- Command execution via screen

**Configuration (in file):**
```bash
USERNAME='vintagestory'            # User to run as
VSPATH='/home/vintagestory/server' # Server directory
DATAPATH='/var/vintagestory/data'   # Data directory
SCREENNAME='vintagestory_server'    # Screen session name
```

**Usage:**
```bash
./server.sh start     # Start server
./server.sh stop      # Stop server
./server.sh status    # Check status
./server.sh restart   # Restart server
./server.sh command "/help"  # Execute command
```

### Docker Integration

The server can be run in Docker with proper volume mounting:

```yaml
volumes:
  - ./data:/data          # Persistent data
  - ./server:/server      # Server files
```

**Key mounts:**
- `/server` - Server installation (can be replaced on updates)
- `/data/Mods` → `/server/Mods` (symlink) - Persisted mods

---

## Version Information

### Version File

The `assets/version-1.21.6.txt` file contains version information:

```bash
cat assets/version-*.txt
```

This is useful for:
- Verifying installation
- Checking compatibility
- Debugging version-specific issues

### API Version Discovery

Vintage Story provides version information via API:

```bash
curl -s https://api.vintagestory.at/stable.json | jq 'keys[0]'
# Returns: "1.21.6"
```

### Tracking Installed Version

The API service creates a `current_version` file in the server directory:

```bash
cat /path/to/server/current_version
# Output: 1.21.6
```

This is useful for:
- Update detection
- Automation scripts
- Version verification

---

## File Sizes Reference

### Downloaded Archive

- **Size:** 43 MB
- **Format:** tar.gz
- **Contents:** ~105 MB when extracted

### Extracted Sizes

| Component | Size |
|-----------|-------|
| Server DLLs | ~4.8 MB |
| Lib/ | ~35 MB |
| Assets (game) | ~55 MB |
| Assets (creative/survival) | ~8 MB |
| Mods (base) | ~4.1 MB |
| **Total** | **~105 MB** |

### Individual DLLs

| File | Size |
|------|-------|
| VintagestoryLib.dll | 2.8 MB |
| VintagestoryAPI.dll | 1.9 MB |
| VSSurvivalMod.dll | 3.1 MB |
| VSEssentials.dll | 815 KB |
| VSCreativeMod.dll | 166 KB |
| VintagestoryServer.dll | 92 KB |

---

## Security and Best Practices

### File Permissions

**Recommended:**
```bash
# Server runs as non-root user
sudo useradd -r -s /bin/false vintagestory

# Set ownership
sudo chown -R vintagestory:vintagestory /path/to/server
sudo chown -R vintagestory:vintagestory /path/to/data

# Permissions
chmod 755 /path/to/server
chmod 750 /path/to/data
```

### Directory Separation

**Why separate server/ and data/?**

1. **Easy updates:** Replace `server/` directory without touching `data/`
2. **Backup simplicity:** Back up `data/` only (contains all world data)
3. **Security:** Server files can be read-only, data files writable

### Backup Strategy

```bash
# Backup only persistent data
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# Exclude temporary files
tar -czf backup_$(date +%Y%m%d).tar.gz \
  --exclude='data/Logs/*.log' \
  --exclude='data/Generated/worlds/*/tmp' \
  data/
```

---

## Troubleshooting

### Missing .NET Runtime

**Symptom:** Server won't start, missing `dotnet` command.

**Solution:**
```bash
# Check if installed
dotnet --list-runtimes | grep "Microsoft.NETCore.App 8.0"

# If not found, install
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --runtime aspnetcore --channel 8.0
```

### Mods Not Loading

**Symptom:** Custom mods not appearing in game.

**Checklist:**
1. Are mods in `data/Mods/`, not server `Mods/`?
2. Does `data/Mods/` exist and have proper permissions?
3. Check `data/Logs/server-main.log` for mod loading errors
4. Verify mod compatibility with server version

### Port Already in Use

**Symptom:** Server fails to start, "port already in use" error.

**Check:**
```bash
netstat -tulpn | grep 42420
lsof -i :42420
```

**Solution:**
- Change port in `data/config/serverconfig.json`
- Kill process using port
- Check for other server instances

### Configuration Not Applied

**Symptom:** Changes to `serverconfig.json` not taking effect.

**Solution:**
- **Restart server** after configuration changes
- Check file is in `data/config/`, not `assets/game/config/`
- Verify JSON syntax (no trailing commas, etc.)

---

## Additional Resources

- **[Server Commands Guide](server-commands.md)** - Complete command reference
- **[Server Installation](server-installation.md)** - API implementation details
- **Vintage Story Wiki:** https://wiki.vintagestory.at
- **Mod Database:** https://mods.vintagestory.at
- **Vintage Story Forums:** https://www.vintagestory.at/forums/

---

## Summary

This analysis of Vintage Story v1.21.6 reveals:

1. **Clean separation** between server executables, libraries, assets, and persistent data
2. **Mod management** requires careful attention to directory placement
3. **Configuration** is split between defaults (read-only) and runtime (writable)
4. **Dependencies** are self-contained in `Lib/` directory
5. **Update process** is straightforward with proper `Mods/` symlink setup

**Key Takeaways:**
- Use `--dataPath` to separate server files from persistent data
- Create symlink from `Mods/` to `data/Mods/` to persist mods
- Monitor `data/Logs/` for troubleshooting
- Back up `data/` directory regularly (contains all world data)

---

**Document Version:** 1.0
**Based on:** Vintage Story v1.21.6 (Linux x64)
**Analysis Date:** December 27, 2025
