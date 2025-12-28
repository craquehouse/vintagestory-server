# Vintage Story Server Commands Guide

**Source:** [Vintage Story Wiki - List of Server Commands](https://wiki.vintagestory.at/List_of_server_commands)
**Last Verified:** Vintage Story version 1.15 (wiki page is outdated - see warning below)

> ⚠️ **WARNING:** This wiki page is outdated. The wiki notes it takes a long time to verify the complete list with each game update. For the most up-to-date syntax, consult the in-game Command Handbook using the `.chb` command.

## Important Tips

1. **All server commands start with `/`**
2. **Do not type the `[` and `]` in command syntax** - Example: use `/time set 12` not `/time set [12]`
3. **World restart required** - After changing server settings, the world needs to be restarted for changes to take effect
4. **Use the in-game Command Handbook** - The `.chb` client command provides the most up-to-date information

---

## Table of Contents

1. [Multiplayer Commands for Players](#multiplayer-commands-for-players)
2. [Commands for Moderators and Admins](#commands-for-moderators-and-admins)
3. [Privilege Control](#privilege-control)
4. [World Control](#world-control)
5. [Server Control and Configuration](#server-control-and-configuration)
6. [Utility and Debug Tools](#utility-and-debug-tools)

---

## Multiplayer Commands for Players

### `/land` - Land Claiming Commands

Commands for claiming and managing protected areas where only you can build or use blocks.

**Basic Commands:**
```
/land [claim|free|info|list]
```

**Subcommands:**

- `/land list` - Display all your claims (use index numbers to modify them)
- `/land info` - Show information about the claim at your current position
- `/land free [index]` - Delete one of your claims
- `/land adminfree` - Delete a player's claim as an admin

**Claim Management:**
```
/land claim [load|new|grant|revoke|grantgroup|revokegroup|grow|shrink|start|end|add|allowuseeveryone|plevel|fullheight|save|cancel|download]
```

**Common Claim Operations:**
- `/land claim load [0..999]` - Load an existing claim for editing
- `/land claim new` - Create a new claim and mark start position
- `/land claim grant [playername] [use|all]` - Grant player access (`use` for interact only, `all` for build rights)
- `/land claim revoke [playername]` - Revoke a player's access
- `/land claim grantgroup [groupname] [use|all]` - Grant group access
- `/land claim allowuseeveryone [true|false]` - Allow/deny all players to use your claim
- `/land claim start` - Mark a start position for the claim area
- `/land claim end` - Mark the end position for the claim area
- `/land claim grow [direction] [length]` - Expand the claim (directions: north, east, south, west, up, down)
- `/land claim shrink [direction] [length]` - Reduce the claim size
- `/land claim add` - Add the selected cuboid to your claim
- `/land claim fullheight` - Expand claim to cover full world height (if allowed)
- `/land claim save [description]` - Save claim modifications
- `/land claim cancel` - Discard all modifications
- `/land claim download [0..999]` - Download a claim as JSON (saved in AppData/Roaming/VintageStoryData/WorldEdit)

### `/group` - Player Group Commands

Create and manage player groups for separate chat channels and land claim access.

```
/group [create|disband|rename|invite|acceptinvite|leave|list|info|kick|op|deop]
```

**Group Management:**
- `/group create [groupname]` - Create a new group with its own chat channel
- `/group disband [group]` - Destroy a group (owner only)
- `/group rename [oldname] [newname]` - Rename a group

**Member Management:**
- `/group invite [group] [playername]` - Invite a player to the group
- `/group acceptinvite [groupname]` - Accept an invitation
- `/group leave [group]` - Leave a group
- `/group kick [group] [playername]` - Remove a player from the group
- `/group op [group] [playername]` - Grant operator status (allows inviting others)
- `/group deop [group] [playername]` - Revoke operator status

**Information:**
- `/group list` - List all groups you're in
- `/group info [groupname]` - List players in a group

### `/waypoint` - Waypoint Management

Manage waypoints on your world map.

```
/waypoint [add|addat|addati|list|remove]
```

**Waypoint Operations:**
- `/waypoint add [color] [title]` - Add a waypoint at your current position
  - Colors can be named (.NET colors) or hex codes
  - Example: `/waypoint add red copper`
- `/waypoint addat [coords] [pinned] [color] [title]` - Add waypoint at specific coordinates
- `/waypoint addati [icon] [x] [y] [z] [pinned] [color] [title]` - Add waypoint with icon
- `/waypoint list` - Show all your waypoints by ID number
- `/waypoint remove [id]` - Remove a waypoint by ID

### `/kill` - Self-terminate

```
/kill
```
Kills your character.

### `/emote` - Character Animations

```
/emote [wave|cheer|shrug|cry|nod|facepalm|bow|laugh|rage]
```
Your character performs an emote animation.

### `/pm` - Private Message

```
/pm [playername] [message]
```
Send a private message to another player (creates a temporary group for the conversation).

---

## Commands for Moderators and Admins

### `/help` - Command List

```
/help
```
Lists all available server commands.

### `/giveblock` - Spawn Blocks

```
/giveblock [blockcode{attributes}] [quantity] [playername]
```

Creates a block stack and gives it to a player.

**Parameters:**
- `blockcode` - The block's code (required)
- `attributes` - JSON attributes in curly braces (optional, no space before `{}`)
- `quantity` - Number of blocks (optional, default: 1)
- `playername` - Target player (optional, defaults to command user)

**Examples:**
```
/giveblock clutter{type: "barrel-metal1"} 10 Steve
/giveblock stone-granite 64
```

### `/giveitem` - Spawn Items

```
/giveitem [itemcode] [quantity] [playername] [attributes]
```

Same as `/giveblock` but for items (not blocks).

### `/gamemode` - Set Game Mode

```
/gamemode [0..4|guest|survival|creative|spectator]
/gamemode [playername] [0..4]
```

**Modes:**
- `0` or `guest` - Cannot place/remove blocks, can only interact
- `1` or `survival` - Can slowly break/place blocks, can die, cannot fly
- `2` or `creative` - All blocks available, instant breaking, cannot die, can fly
- `3` or `spectator` - Cannot interact, can fly

Mode names can be shortened (e.g., `/gamemode surv` works).

### `/gm` - Game Mode Shortcut

Shorthand for `/gamemode`.

### `/tp` - Teleport

```
/tp [coordinates]
/tp [playername] [coordinates]
/tp [playername]
/tpwp [starts with name]
```

**Teleport Options:**

**To coordinates:**
- `/tp x y z` - Teleport to pretty coordinate
- `/tp =x =y =z` - Teleport to absolute coordinate (from debug screen, CTRL+F3)
- `/tp ~x ~y ~z` - Teleport by relative offset

**To player:**
- `/tp [playername]` - Teleport yourself to a player
- `/tp [playername] [coordinates]` - Teleport another player to coordinates

**To waypoint:**
- `/tpwp [waypoint name]` - Teleport to a waypoint

**Examples:**
```
/tp 100 65 200
/tp ~5 ~0 ~5          # Move 5 blocks east
/tp Steve
/tpwp copper
```

### `/ban` - Ban Player

```
/ban [playername] [reason]
```
Bans a player from the server with an optional reason.

### `/unban` - Unban Player

```
/unban [playername]
```
Removes a ban from a player.

### `/kick` - Kick Player

```
/kick [playername] [reason]
```
Kicks a player from the server with an optional reason.

### `/clearinv` - Clear Inventory

```
/clearinv
```
Removes all items from your inventory.

### `/nexttempstorm` - Temporal Storm Info

```
/nexttempstorm
/nexttempstorm now
```

- `/nexttempstorm` - Shows days until next temporal storm
- `/nexttempstorm now` - Immediately starts a temporal storm

---

## Privilege Control

### Player Selectors

The following selectors can be used in privilege-related commands:

**Basic Selectors:**
- `playername` - Single player (alias for `a[name=playername]`)
- `s[]` - The calling player (self)
- `o[]` - All online players
- `a[]` - All players who have ever logged in

**Filters (used with bracketed selectors):**
- `role` - Only players with this role
- `name` - Only player with this name
- `group` - Only players in this group
- `namematches` - Players matching a glob-style wildcard
- `range` - Players within this distance of caller

**Example:**
```
o[namematch=b*,range=10,role=admin]
```
Selects all online admins whose name starts with 'b' and are within 10 blocks.

### `/op` - Grant Admin Role

```
/op [playername]
```
Alias for `/player [playername] role admin`. Grants admin privileges to a player.

### `/role` - Role Management

```
/role [rolename] [roleproperty]
```

**Role Properties:**

- `/role [rolename] spawnpoint [x] [y?] [z]` - Set role-specific spawn point
  - `y` can be omitted to use surface position

- `/role [rolename] privilege [grant|revoke] [privilegename]` - Grant/revoke privileges

- `/role [rolename] landclaimallowance [value]` - Set max claimable area in cubic meters
  - Default: 4 chunks = 4*32*32*32 = 131,072 cubic meters

- `/role [rolename] landclaimmaxareas [value]` - Set max non-adjacent claim areas
  - Default: 3

- `/role [rolename] landclaimminsize [x y z]` - Set smallest claimable cuboid
  - Default: 6 by 6 by 6

### `/player` - Player Management

```
/player [playername] [property] [value]
```

**Quick Commands:**
- `/player [playername] movespeed [value]` - Set move speed
- `/player [playername] clearinv` - Clear player's inventory
- `/player [playername] wipedata` - Wipe all player data (inventory, skin, class, etc.)

**Detailed Commands:**

**Whitelist:**
- `/player [playername] whitelist` - Show whitelist status
- `/player [playername] whitelist on` - Add to whitelist

**Privileges:**
- `/player [playername] privilege` - List current privileges
- `/player [playername] privilege [grant|revoke] [privilegename]` - Modify privileges

**Role:**
- `/player [playername] role` - Show current role
- `/player [playername] role [rolename]` - Set role (default: suplayer)

**Game Mode:**
- `/player [playername] gamemode [0..4]` - Show or set game mode

**Land Claims:**
- `/player [playername] landclaimallowance [value]` - Extra claim allowance (default: 0)
- `/player [playername] landclaimmaxareas [value]` - Extra claim areas (default: 0)

**Player Entity (Stats & Status):**
- `/player [playername] entity` - Show position, satiety, health
- `/player [playername] entity temp [value]` - Set body temperature
- `/player [playername] entity health [0.1-1]` - Set health (1 = 100%)
- `/player [playername] entity maxhealth [0.1-999]` - Set max health
- `/player [playername] entity satiety [0.1-1]` - Set satiety (1 = 100%)
- `/player [playername] entity maxoxygen [int]` - Set max oxygen in milliseconds (default: 20000)
- `/player [playername] entity intox [0.1-1]` - Set intoxication level
- `/player [playername] allowcharselonce` - Allow class re-selection

---

## World Control

### `/worldconfig` - World Configuration

See the dedicated [World Configuration](https://wiki.vintagestory.at/World_Configuration) page for complete details.

**Map Style Commands:**
For singleplayer or all players:
```
/worldconfig colorAccurateWorldmap true
```

For individual players (multiplayer):
```
/player [playername] privilege grant colorAccurateWorldmap
```

### `/entity` - Entity Management

```
/entity [subcommand]
```

**Entity Commands:**
- `/entity cmd [subcommand]` - Issue commands to entities
  - `/entity cmd stopanim` - Stop entity animation
  - `/entity cmd stoptask` - Stop AI task
  - `/entity cmd setattr` - Set entity attributes
  - `/entity cmd move` - Move creature
  - `/entity cmd kill` - Kill creature
  - `/entity cmd wipeall` - Remove all entities except players

- `/entity debug [0|1]` - Enable entity debug mode (sends info to clients)

- `/entity spawndebug [0|1]` - Enable spawn debug mode

- `/entity count [*entityfilter*]` - Count entities by filter
- `/entity countg [*entityfilter*]` - Count entities grouped by type

- `/entity spawnat [entitytype] [amount] [position] [radius]` - Spawn entities

- `/entity remove [*entityfilter*]` - Remove selected creatures

**Entity Filters:**
- `s[]` - Self
- `l[]` - Entity currently looked at
- `p[]` - All players
- `e[]` - All entities

Filters can include: `name`, `type`, `class`, `alive`, `range`, and position filters (minx/miny/minz/maxx/maxy/maxz).

**Example:**
```
/e[type=gazelle,range=3,alive=true]
```

### `/time` - Time Control

⚠️ **WARNING:** Modifying time frequently can have unwanted side effects. Test in a separate world or create a backup first!

```
/time [set|get|speed]
```

**Time Commands:**

- `/time` - Show current time
- `/time stop` - Stop passage of time
- `/time resume` - Resume passage of time

**Set Time of Day:**
- `/time set [time]` - Set time in hours (24-hour format, e.g., 1.5 = 1:30 AM)
- `/time set [dayname]` - Set to preset time:
  - `lunch` / `day` = 12
  - `afternoon` = 14
  - `sunset` = 17.5
  - `night` = 20
  - `latenight` = 22
  - `midnight` = 0
  - `witchinghour` = 3
  - `morning` = 8
  - `latemorning` = 10
  - `sunrise` = 6.5

**Calendar:**
- `/time setmonth [month]` - Set month (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)
- `/time add [hours]:[minutes]` - Add time

**Time Speed:**
- `/time speed [0-9999]` - Set game time speed (default: 60)
- `/time hoursperday [0-9999]` - Set hours per day (default: 24)
- `/time calendarspeedmul [value]` - Set calendar speed multiplier (default: 0.5, 50% speed)

### `/weather` - Weather Control

```
/weather [subcommand]
```

**Weather Commands:**

- `/weather` - Show current weather stats

**Precipitation:**
- `/weather setprecip [-1..1]` - Set precipitation intensity
  - `-1` - Remove all rain clouds
  - `0` - Stop rain, keep clouds
  - `1` - Heaviest rain, full clouds
- `/weather setprecipa` - Reset to automatic precipitation

**Patterns:**
- `/weather acp` - Toggle auto-changing weather
- `/weather lp` - List all loaded weather patterns
- `/weather t` - Transition to random pattern
- `/weather c` - Quick transition to random pattern

**Set Pattern:**
- `/weather setw [windtype]` - Set wind pattern (lightbreeze|mediumbreeze|still|storm|strongbreeze)
- `/weather set [pattern]` - Set weather pattern
- `/weather seti [pattern]` - Instantly set weather pattern
- `/weather setirandom` - Instantly set random weather

**Weather Events:**
- `/weather setev [event]` - Set weather event globally
- `/weather setevr [event]` - Set weather event in current region

**Rain:**
- `/weather stoprain` - Skip ahead to time when rain stops

---

## Server Control and Configuration

### `/serverconfig` - Server Configuration

```
/serverconfig [config] [value]
```

**Connection Settings:**
- `/serverconfig maxchunkradius [integer]` - Set max chunk radius players can load
- `/serverconfig maxclients [integer]` - Set max connected clients
- `/serverconfig password [string]` - Set server password (no spaces)
- `/serverconfig nopassword` - Remove password protection

**Gameplay Settings:**
- `/serverconfig antiabuse [Off|Basic|Pedantic]` - Set anti-abuse protection level
- `/serverconfig allowpvp [bool]` - Enable/disable player vs player combat
- `/serverconfig allowfirespread [bool]` - Enable/disable fire spread
- `/serverconfig allowfallingblocks [bool]` - Enable/disable block gravity
- `/serverconfig entityspawning [bool]` - Enable/disable creature spawning (default: on)

**Whitelist:**
- `/serverconfig WhitelistMode [default|off|on]` - Control whitelist mode
  - `default` - On for dedicated, off for LAN servers
  - Can also use `0|1|2` (default/off/on)

**Performance:**
- `/serverconfig tickrate [10-100]` - Set server tick rate (higher = more responsive)
- `/serverconfig blockTickSamplesPerChunk` - Control block update ticks per chunk

**Spawn:**
- `/serverconfig defaultspawn [x] [y?] [z]` - Set default spawn point (y optional)
- `/serverconfig setspawnhere` - Set spawn point to current location

**Time:**
- `/serverconfig passtimewhenempty [bool]` - Whether time passes when no players connected

**Mob Spawning:**
- `/serverconfig spawncapplayerscaling [0..1]` - Distribute mob spawns among players (default: 0.75)
  - 0 = no extra mobs for additional players
  - 1 = each player doubles spawn cap

**Security:**
- `/serverconfig temporaryipblocklist [0..1]` - Enable IP-based blocklist
- `/serverconfig loginfloodprotection [0..1]` - Enable IP-based login flood protection

### `/stats` - Server Statistics

```
/stats
```
Shows current server stats including tick rate and memory usage.

### `/announce` - Server Announcement

```
/announce [message]
```
Send a server-wide announcement message to all players in all chat groups.

### `/stop` - Stop Server

```
/stop
```
Stops the server.

### `/autosavenow` - Force Auto-save

```
/autosavenow
```
Immediately triggers an auto-save of the server.

### `/list` - Information Lists

```
/list [clients|banned|role|privileges]
```

- `/list clients` - Show connected players
- `/list banned` - Show banned players list
- `/list role` - Show all configured privilege roles
- `/list privileges` - Show all configured privileges

### `/allowlan` - Allow LAN Connections

```
/allowlan [on|off]
```
Enable or disable external LAN connections (temporary runtime setting for non-dedicated servers).

---

## Utility and Debug Tools

### `/moddb` - Mod Database Management

Last verified for Vintage Story 1.18.0-pre.7

```
/moddb [install|remove|list|search|searchcompatible|searchfor|searchforc]
```

- `/moddb install [modid] [gameVersion]` - Install a mod
- `/moddb remove [modid]` - Uninstall a mod
- `/moddb list` - List all installed mods
- `/moddb search [query]` - Full-text search on ModDB
- `/moddb searchcompatible [modid]` - Search mods compatible with current version
- `/moddb searchfor [gameVersion] [modid]` - Search mods for specific version
- `/moddb searchforc [gameVersion] [modid]` - Search mods compatible with specific version

### `/fixmapping` - Block/Item Remapping

```
/fixmapping applyall
```
Applies block and item remapping to upgrade to a new game version.

### `/genbackup` - Generate Backup

```
/genbackup [filename]
```
Creates a full backup of the current save game in the backups folder. Can run without pausing. If no filename is provided, generates one based on date/time.

### `/bir` - Block ID Remapper

```
/bir [getid|getcode|remap]
```
Block ID remapper tools for fixing broken blocks after removing/updating custom blocks.

### `/chunk` - Chunk Commands

```
/chunk [cit|printmap|unload|forceload]
```

- `/chunk cit` - Show current chunk generation info
- `/chunk printmap` - Export PNG map of loaded chunks (yellow pixel = caller position)
- `/chunk unload [0|1]` - Toggle automatic chunk unloading
- `/chunk forceload x1 z1 x2 z2` - Load area and prevent unloading

### `/whenwillitstopraining` - Rain Forecast

```
/whenwillitstopraining
```
Tells you when the rain will stop.

### `/info` - World Information

```
/info [ident|seed|createdversion|mapsize]
```

- `/info ident` - Show world identifier
- `/info seed` - Show world seed
- `/info createdversion` - Show game version world was created in
- `/info mapsize` - Show world size

### `/debug` - Debug Commands

```
/debug [subcommand]
```

**Performance & Logging:**
- `/debug logticks [milliseconds]` - Log breakdown of ticks taking longer than specified ms
- `/debug tickhandlers` - Show summary of ticking blocks/entities
- `/debug tickhandlers dump [type]` - Dump complete list to server-debug.txt
- `/debug netbench` - Toggle network benchmarking

**Item Debug:**
- `/debug helddurability [value]` - Set durability of held item
- `/debug helddura [value]` - Alias for helddurability
- `/debug heldtemperature [value]` - Set temperature of held item
- `/debug heldtemp [value]` - Alias for heldtemperature
- `/debug heldstattr key [value]` - Set stack attribute of held item
- `/debug heldcoattr key [value]` - Set collectible attribute of held item

**Entity Debug:**
- `/debug setgen [value]` - Set generation of looked-at entity
- `/debug itemcodes` - Export list of all item codes to server-main.txt
- `/debug blockcodes` - Export list of all block codes to server-main.txt
- `/debug blockids` - List blocks consuming most block IDs
- `/debug blockstats` - Generate block ID usage statistics

**Chunk Debug:**
- `/debug chunk queue [quantity]` - Show/generating chunks in queue
- `/debug chunk stats` - Show loaded chunk statistics
- `/debug chunk printmap` - Export chunk map as PNG
- `/debug chunk here` - Show chunk info at caller position
- `/debug chunk resend` - Resend chunk to all players
- `/debug chunk relight` - Relight chunk for all players
- `/debug sendchunks [0|1]` - Toggle chunk generation/sending

**System Debug:**
- `/debug privileges` - Toggle privilege debugging
- `/debug tickposition` - Tick position
- `/debug stacktrace` - Stack trace
- `/debug rebuildlandclaimpartitions` - Rebuild land claim partitions
- `/debug octagonpoints` - Print octagon points
- `/debug cloh` - Compact large object heap
- `/debug mainthreadstate` - Show main thread state
- `/debug killmainthread` - Kill main thread (dangerous!)

**Localization:**
- `/debug expclang` - Export translations to collectiblelang.json

**Rift Commands:**
- `/debug rift clear` - Remove all rifts immediately
- `/debug rift fade` - Slowly remove rifts over minutes
- `/debug rift spawn [quantity]` - Spawn specified number of rifts
- `/debug rift spawnhere` - Spawn one rift

**Room Registration (replaces /roomregdebug):**
- `/debug rooms list` - List rooms player is in
- `/debug rooms hi` - Highlight rooms (red=unsuitable, green=eligible)
- `/debug rooms unhi` - Remove room highlighting

**Dungeon Testing:**
- `/debug tiledd [tiled_dungeon_code] [amount_of_tiles]` - Test tiled dungeon generator

**Pathfinding:**
- `/debug astar [command]` - Path-finding debug tool (commands: start, end, bench, clear)

### `/wgen` - World Generation Tools

```
/wgen [testmap|testnoise|chunk|region|pos|tree]
```

**World Generation Modes:**
- `/wgen autogen` - Toggle automatic worldgen mode
- `/wgen gt` - Toggle tree generation mode

**Map Testing:**
- `/wgen testmap [type]` - Generate 512x512 test map as PNG
  - Types: climate, forest, wind, gprov, landform, ore
  - `/wgen testmap climater [hot|warm|cool|icy]` - Temperature preset
  - `/wgen testmap oretopdistort` - Ore top distortion maps
  - `/wgen testmap rockstrata` - Rock strata maps

- `/wgen genmap [type]` - Generate map (similar to testmap)

**Region Info:**
- `/wgen region [type]` - Generate 16x16 chunk region map as PNG
- `/wgen regions [radius] [ore] [orename]` - Show ore availability in regions

**Chunk Generation:**
- `/wgen pregen [radius]` - Pregenerate chunks around player
- `/wgen regen [radius]` - Regenerate chunks around player
- `/wgen regenr [radius]` - Regenerate chunks with random seed
- `/wgen regenc [radius]` - Regenerate chunks around spawn
- `/wgen regenrc [radius]` - Regenerate chunks around spawn with random seed

**World Editing:**
- `/wgen delrock [radius]` - Remove rocks around player (causes server overload)
- `/wgen delrockc [radius]` - Remove rocks around spawn (may not work)
- `/wgen del [radius]` - Delete chunks around player

**Tree Generation:**
- `/wgen tree <code> [size] [aheadoffset]` - Spawn tree at player position
  - Example: `/wgen tree walnut`
- `/wgen treelineup` - Spawn tree line

**Position Info:**
- `/wgen pos [property]` - Show info at current position
  - Properties: ymax, coords, latitude, structures, height, cavedistort, gprov, rockstrata, landform, climate

**Noise Testing:**
- `/wgen testnoise [octaves]` - Test noise generation

### `/we` - WorldEdit

See the dedicated [How to use WorldEdit](https://wiki.vintagestory.at/How_to_use_WorldEdit) guide.

### `/macro` - Custom Macros

```
/macro [addcmd|setcmd|syntax|desc|priv|save|delete|show|list]
```

Create server-side macros that execute one or more commands.

**Macro Creation:**
- `/macro addcmd [command]` - Add command to temporary macro
- `/macro setcmd [command]` - Override command in temporary macro
- `/macro syntax [text]` - Set syntax help text
- `/macro desc [text]` - Set description text
- `/macro priv [privilege]` - Set required privilege (e.g., controlserver, build)

**Macro Management:**
- `/macro show` - Show temporary macro contents
- `/macro save [name]` - Save temporary macro with name
- `/macro list` - Show all saved macros
- `/macro show [name]` - Show saved macro contents
- `/macro delete [name]` - Delete a macro
- `/macro discard [name]` - Discard temporary macro

---

## Additional Resources

- **[Client Commands](https://wiki.vintagestory.at/List_of_client_commands)** - Commands run on the client side
- **[World Configuration](https://wiki.vintagestory.at/World_Configuration)** - Detailed world config options
- **[Command Handbook (in-game)]** - Use `.chb` for the most up-to-date information

## Key Concepts

### Coordinates

Vintage Story uses two coordinate systems:

1. **Pretty Coordinates** - Displayed in the coordinate box, used by `/tp x y z`
2. **Absolute Coordinates** - Displayed in debug screen (CTRL+F3), used by `/tp =x =y =z`

### Syntax Conventions

- `[]` - Optional parameters (don't type the brackets)
- `|` - Alternative options
- `<>` - Required parameters
- `..` - Range of values

### Best Practices

1. **Backup before testing** - Especially for time and worldgen commands
2. **Use command handbook** - `.chb` provides current syntax
3. **Test in development** - Try commands in a test world first
4. **Check permissions** - Ensure you have required privileges before running commands
5. **Document changes** - Keep track of configuration changes for your server

---

**Document Version:** 1.0
**Last Updated:** December 27, 2025
**Source:** Vintage Story Wiki (version 1.15)
