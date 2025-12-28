# Vintage Story Server Quick Reference

**Version:** 1.21.6 | **Date:** December 27, 2025

## Essential Commands

### Download Latest Stable Server
```bash
curl -s https://api.vintagestory.at/stable.json | jq 'keys[0]'
# Returns: "1.21.6"

curl -L -o vs_server_linux-x64_1.21.6.tar.gz \
  https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz

md5sum vs_server_linux-x64_1.21.6.tar.gz
# Expected: 0c2841f5a7638bc26719993416cf44d9

tar -xzf vs_server_linux-x64_1.21.6.tar.gz
```

### Start Server
```bash
# Direct start
dotnet VintagestoryServer.dll --dataPath ./data

# Using init script
./server.sh start
./server.sh stop
./server.sh status
./server.sh restart
```

### Mod Management
```bash
# Proper setup for updates
mkdir -p data/Mods
rm -rf Mods
ln -s data/Mods Mods

# Install mods
unzip SomeMod_1.0.0.zip -d data/Mods/
```

## Critical Directories

| Path | Purpose | Notes |
|------|---------|-------|
| `VintagestoryServer.dll` | Server executable | Main entry point |
| `Mods/` | Base game mods ONLY | Don't add custom mods here! |
| `data/Mods/` | Custom mods | Created by you, persisted across updates |
| `data/config/` | Runtime configuration | serverconfig.json, playerdata.json |
| `data/Generated/worlds/` | World saves | All world data |
| `data/Logs/` | Server logs | Troubleshooting |
| `assets/game/config/` | Default config | Read-only templates |

## Key Files

### Server Files
- `VintagestoryServer.dll` - Main executable (92 KB)
- `VintagestoryLib.dll` - Core game library (2.8 MB)
- `VintagestoryAPI.dll` - Modding API (1.9 MB)
- `server.sh` - Service management script

### Configuration Files
- `data/config/serverconfig.json` - Main server settings
- `data/config/playerdata.json` - Player data
- `data/config/worldconfig.json` - World settings
- `assets/game/config/*.json` - Default configs (read-only)

## Common Issues

### Server Won't Start
```bash
# Check .NET runtime
dotnet --list-runtimes | grep "Microsoft.NETCore.App 8.0"

# Check logs
tail -f data/Logs/server-main.log
```

### Port Already in Use
```bash
# Check what's using port 42420
netstat -tulpn | grep 42420
# Or change port in data/config/serverconfig.json
```

### Mods Not Loading
```bash
# Ensure mods are in data/Mods/, not server root Mods/
ls -la data/Mods/
# Check logs for errors
tail data/Logs/server-main.log | grep -i mod
```

## File Sizes

- **Downloaded:** 43 MB (tar.gz)
- **Extracted:** ~105 MB
- **VintagestoryLib.dll:** 2.8 MB
- **VintagestoryAPI.dll:** 1.9 MB
- **VSSurvivalMod.dll:** 3.1 MB
- **Lib/ directory:** ~35 MB
- **assets/:** ~63 MB

## Network Configuration

- **Default Port:** 42420 (TCP/UDP)
- **Default IP:** 0.0.0.0 (all interfaces)
- **Whitelist Mode:** Default = on for dedicated servers

Change in `data/config/serverconfig.json`:
```json
{
  "Port": 42420,
  "Ip": "0.0.0.0",
  "WhitelistMode": "off",
  "AdvertiseServer": true
}
```

## Backup Strategy

```bash
# Backup only persistent data
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# Exclude logs
tar -czf backup_$(date +%Y%m%d).tar.gz \
  --exclude='data/Logs' \
  data/
```

## API Endpoints

- **Stable versions:** https://api.vintagestory.at/stable.json
- **Unstable versions:** https://api.vintagestory.at/unstable.json
- **CDN base:** https://cdn.vintagestory.at/gamefiles

## Resources

- **Full Layout Documentation:** [server-layout.md](server-layout.md)
- **Installation API Details:** [server-installation.md](server-installation.md)
- **Server Commands:** [server-commands.md](server-commands.md)
- **Vintage Story Wiki:** https://wiki.vintagestory.at
- **Mod Database:** https://mods.vintagestory.at

---

**Quick Reference v1.0 - Last Updated: December 27, 2025**
