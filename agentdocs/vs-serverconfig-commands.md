# VintageStory /serverconfig Command Reference

Reference documentation for VintageStory server configuration commands and settings behavior.

## Command Syntax

The `/serverconfig` command modifies server configuration settings. Changes are automatically persisted to `serverconfig.json`.

```
/serverconfig <setting> [value]
```

Without a value, displays the current setting. With a value, updates the setting.

## Console-Commandable Settings (Live Update)

These settings can be changed at runtime via console commands and take effect immediately without restart.

| Command | Setting Key | Value Type | Notes |
|---------|-------------|------------|-------|
| `/serverconfig name "value"` | ServerName | string | Server display name |
| `/serverconfig description "value"` | ServerDescription | string | Server listing description |
| `/serverconfig motd "value"` | WelcomeMessage | string | Join message, {0} = player name |
| `/serverconfig maxclients N` | MaxClients | int | Max connected players |
| `/serverconfig maxchunkradius N` | MaxChunkRadius | int | Max chunk radius players can load |
| `/serverconfig password "value"` | Password | string | Connection password (no spaces) |
| `/serverconfig nopassword` | Password | - | Removes password requirement |
| `/serverconfig allowpvp true/false` | AllowPvP | bool | Player vs player combat |
| `/serverconfig allowfirespread true/false` | AllowFireSpread | bool | Fire propagation mechanics |
| `/serverconfig allowfallingblocks true/false` | AllowFallingBlocks | bool | Gravity effects on blocks |
| `/serverconfig entityspawning true/false` | EntitySpawning | bool | Creature spawning (default: on) |
| `/serverconfig WhitelistMode off/on/default` | WhitelistMode | enum | Connection restrictions |
| `/serverconfig antiabuse Off/Basic/Pedantic` | AntiAbuse | enum | Anti-abuse protection level |
| `/serverconfig tickrate N` | TickRate | int | Server tick rate (10-100) |
| `/serverconfig blockTickSamplesPerChunk N` | RandomBlockTicksPerChunk | int | Random update ticks per chunk |
| `/serverconfig passtimewhenempty true/false` | PassTimeWhenEmpty | bool | Time passes when no players |
| `/serverconfig spawncapplayerscaling N` | SpawnCapPlayerScaling | float | Mob spawn scaling (0-1, default 0.75) |
| `/serverconfig upnp 0/1` | Upnp | bool | Automatic port forwarding |
| `/serverconfig advertise 0/1` | AdvertiseServer | bool | Public server listing |
| `/serverconfig defaultspawn x [y] z` | DefaultSpawn | coords | Default spawn point |
| `/serverconfig setspawnhere` | DefaultSpawn | - | Set spawn to current location |
| `/serverconfig temporaryipblocklist 0/1` | TemporaryIpBlockList | bool | IP-based protection |
| `/serverconfig loginfloodprotection 0/1` | LoginFloodProtection | bool | Login flood defense |

## Restart-Required Settings

These settings exist in `serverconfig.json` but cannot be changed via console commands. Require server restart to take effect.

| Setting Key | Type | Notes |
|-------------|------|-------|
| Port | int | Server port (default: 42420) |
| Ip | string/null | Bind IP address |
| MapSizeX/Y/Z | int | World dimensions |
| WorldConfig.Seed | string/null | World seed (new worlds only) |
| WorldConfig.SaveFileLocation | string | World save file path |
| WorldConfig.WorldType | string | World generation type |
| ModPaths | string[] | Mod search directories |
| Roles | object[] | Role definitions |
| DefaultRoleCode | string | Default player role |
| MasterserverUrl | string | Master server URL |
| ModDbUrl | string | Mod database URL |
| ConfigVersion | string | Config schema version |

## Persistence Behavior

**Key Finding:** Console commands automatically persist changes to `serverconfig.json`. No manual file save is required.

1. User executes `/serverconfig maxclients 32`
2. Game server updates in-memory setting immediately
3. Game server writes updated value to `serverconfig.json` atomically
4. Setting persists across server restarts

## Command Syntax Variations

Different commands use different syntaxes for boolean values:

| Style | Commands |
|-------|----------|
| `true/false` | allowpvp, allowfirespread, allowfallingblocks, entityspawning, passtimewhenempty |
| `0/1` | upnp, advertise, temporaryipblocklist, loginfloodprotection |
| `on/off/default` | WhitelistMode |
| `Off/Basic/Pedantic` | antiabuse |

**API Implementation Note:** The API should normalize these variations internally. The frontend sends consistent boolean values; the API translates to appropriate command syntax.

## Complete serverconfig.json Structure

Based on VintageStory 1.19+ default configuration:

```json
{
  "FileEditWarning": "",
  "ConfigVersion": "1.9",
  "ServerName": "Vintage Story Server",
  "ServerUrl": null,
  "ServerDescription": null,
  "WelcomeMessage": "Welcome {0}, may you survive well and prosper",
  "Ip": null,
  "Port": 42420,
  "Upnp": false,
  "CompressPackets": true,
  "AdvertiseServer": false,
  "MaxClients": 16,
  "MaxClientsInQueue": 0,
  "PassTimeWhenEmpty": false,
  "MasterserverUrl": "http://masterserver.vintagestory.at/api/v1/servers/",
  "ModDbUrl": "https://mods.vintagestory.at/",
  "ClientConnectionTimeout": 150,
  "EntityDebugMode": false,
  "Password": null,
  "MapSizeX": 1024000,
  "MapSizeY": 256,
  "MapSizeZ": 1024000,
  "ServerLanguage": "en",
  "MaxChunkRadius": 12,
  "TickTime": 33.333332,
  "SpawnCapPlayerScaling": 0.5,
  "BlockTickChunkRange": 5,
  "MaxMainThreadBlockTicks": 10000,
  "RandomBlockTicksPerChunk": 16,
  "BlockTickInterval": 300,
  "SkipEveryChunkRow": 0,
  "SkipEveryChunkRowWidth": 0,
  "Roles": [...],
  "DefaultRoleCode": "suplayer",
  "ModPaths": ["Mods", "/data/serverdata/Mods"],
  "AntiAbuse": 0,
  "WorldConfig": {
    "Seed": null,
    "SaveFileLocation": "...",
    "WorldName": "A new world",
    "AllowCreativeMode": true,
    "PlayStyle": "surviveandbuild",
    "PlayStyleLangCode": "surviveandbuild-bands",
    "WorldType": "standard",
    "WorldConfiguration": null,
    "MapSizeY": null,
    "CreatedByPlayerName": null,
    "DisabledMods": null,
    "RepairMode": false
  },
  "NextPlayerGroupUid": 10,
  "GroupChatHistorySize": 20,
  "MaxOwnedGroupChannelsPerUser": 10,
  "OnlyWhitelisted": false,
  "WhitelistMode": 0,
  "VerifyPlayerAuth": true,
  "DefaultSpawn": null,
  "AllowPvP": true,
  "AllowFireSpread": true,
  "AllowFallingBlocks": true,
  "HostedMode": false,
  "HostedModeAllowMods": false,
  "VhIdentifier": null,
  "StartupCommands": null,
  "RepairMode": false,
  "AnalyzeMode": false,
  "CorruptionProtection": true,
  "RegenerateCorruptChunks": false,
  "ChatRateLimitMs": 1000,
  "DieBelowDiskSpaceMb": 400,
  "ModIdBlackList": null,
  "ModIdWhiteList": null,
  "ServerIdentifier": "...",
  "LogBlockBreakPlace": false,
  "LogFileSplitAfterLine": 500000,
  "DieAboveErrorCount": 100000,
  "LoginFloodProtection": false,
  "TemporaryIpBlockList": false,
  "DisableModSafetyCheck": false,
  "DieAboveMemoryUsageMb": 50000
}
```

## API Implementation Implications

1. **Live settings via console:** When server is running, use `/serverconfig` commands for immediate updates
2. **File-only settings:** When server is stopped OR for restart-required settings, edit `serverconfig.json` directly
3. **Automatic persistence:** No need to manually save after console commands
4. **Type coercion:** API must convert frontend values to appropriate command syntax

## References

- VintageStory Wiki: [List of server commands](https://wiki.vintagestory.at/List_of_server_commands)
- VintageStory Wiki: [Setting up a Server](https://wiki.vintagestory.at/index.php/Setting_up_a_Server)
- Reference Implementation: [DarkMatterProductions generate-config.py](https://raw.githubusercontent.com/DarkMatterProductions/vintagestory/refs/heads/main/generate-config.py)

---

_Last updated: 2025-12-30 (Story 6.0 research)_
