# Epic 6: Game Configuration Management Architecture

_Added during Epic 5 retrospective (2025-12-30)_

This section defines architecture patterns specific to Epic 6 (Game Configuration Management).

## Architectural Pivot: Console Commands vs. File Editing

**Research Finding (Epic 5 Retrospective):**

VintageStory server console commands can modify most server settings, and the game server handles JSON persistence automatically. This changes our approach from "file editing" to "command-based configuration."

**Reference Implementation:**
[DarkMatterProductions generate-config.py](https://raw.githubusercontent.com/DarkMatterProductions/vintagestory/refs/heads/main/generate-config.py) demonstrates a data model with ~20 configurable settings.

**Original Approach (Deferred):**
```
User → Web UI → JSON Editor → PUT /config/files/{name} → File Write → Restart
```

**New Approach:**
```
User → Web UI → Setting Form → POST /config/settings/{key} → API decides method → Game Server
                                                              ↓
                                              (Console command if running, file update otherwise)
```

**Key Boundary:** The frontend never constructs or sees console commands. It simply calls `POST /config/settings/{key}` with a value. The API server internally decides whether to use a console command or file update based on server state.

## Setting Categories

**1. Console-Commandable Settings (Live Update)**

Settings the API server can update via console commands while game server is running.

**⚠️ Implementation Detail:** The console command syntax below is internal to the API server. The frontend only sees setting keys and values.

**Complete List (Researched Story 6.0, 2025-12-30):**

| Setting | API Server Internal Command | Effect |
|---------|----------------------------|--------|
| ServerName | `/serverconfig name "value"` | Immediate |
| ServerDescription | `/serverconfig description "value"` | Immediate |
| WelcomeMessage | `/serverconfig motd "value"` | Immediate |
| MaxClients | `/serverconfig maxclients N` | Immediate |
| MaxChunkRadius | `/serverconfig maxchunkradius N` | Immediate |
| Password | `/serverconfig password "value"` | Immediate |
| (Remove password) | `/serverconfig nopassword` | Immediate |
| AllowPvP | `/serverconfig allowpvp true/false` | Immediate |
| AllowFireSpread | `/serverconfig allowfirespread true/false` | Immediate |
| AllowFallingBlocks | `/serverconfig allowfallingblocks true/false` | Immediate |
| EntitySpawning | `/serverconfig entityspawning true/false` | Immediate |
| WhitelistMode | `/serverconfig WhitelistMode off/on/default` | Immediate |
| AntiAbuse | `/serverconfig antiabuse Off/Basic/Pedantic` | Immediate |
| TickRate | `/serverconfig tickrate N` (10-100) | Immediate |
| RandomBlockTicksPerChunk | `/serverconfig blockTickSamplesPerChunk N` | Immediate |
| PassTimeWhenEmpty | `/serverconfig passtimewhenempty true/false` | Immediate |
| SpawnCapPlayerScaling | `/serverconfig spawncapplayerscaling N` (0-1) | Immediate |
| Upnp | `/serverconfig upnp 0/1` | Immediate |
| AdvertiseServer | `/serverconfig advertise 0/1` | Immediate |
| DefaultSpawn | `/serverconfig defaultspawn x [y] z` | Immediate |
| (Current location) | `/serverconfig setspawnhere` | Immediate |
| TemporaryIpBlockList | `/serverconfig temporaryipblocklist 0/1` | Immediate |
| LoginFloodProtection | `/serverconfig loginfloodprotection 0/1` | Immediate |

**Persistence:** Console commands automatically persist changes to `serverconfig.json`. No manual save required.

**Boolean Syntax Variations:** Note different commands use `true/false`, `0/1`, or enum values. API must normalize these internally.

**2. Restart-Required Settings**

Settings that cannot be changed via console commands. Require editing `serverconfig.json` and server restart:

| Setting | Location | Notes |
|---------|----------|-------|
| Port | serverconfig.json | Server port (default: 42420) |
| Ip | serverconfig.json | Bind IP address |
| MapSizeX/Y/Z | serverconfig.json | World dimensions |
| WorldConfig.Seed | serverconfig.json | New worlds only |
| WorldConfig.SaveFileLocation | serverconfig.json | World save path |
| ModPaths | serverconfig.json | Mod directories |
| Roles | serverconfig.json | Role definitions |
| DefaultRoleCode | serverconfig.json | Default player role |
| ConfigVersion | serverconfig.json | Schema version |
| CompressPackets | serverconfig.json | Network compression |

**Reference:** See `agentdocs/vs-serverconfig-commands.md` for complete documentation.

**3. Environment Variable Managed Settings**

Settings controlled by container environment variables (read-only in UI):

| Setting        | Env Var           | Behavior                                       |
| -------------- | ----------------- | ---------------------------------------------- |
| Game version   | `VS_GAME_VERSION` | Display only, warn if different from installed |
| Data directory | `VS_DATA_DIR`     | Display only                                   |
| Debug mode     | `VS_DEBUG`        | Display only                                   |

## Initial Configuration Generation (ConfigInitService)

On first server start, if no `serverconfig.json` exists, the API generates one from:
1. A reference template (`serverconfig-template.json`)
2. VS_CFG_* environment variable overrides

**Pattern:** Inspired by [DarkMatterProductions](https://github.com/DarkMatterProductions/vintagestory) but adapted for our architecture.

```python
# api/src/vintagestory_api/services/config_init.py
import os
import json
from pathlib import Path
from typing import Any

class ConfigInitService:
    """Handles initial serverconfig.json generation from template + env vars."""

    # Complete ENV_VAR_MAP with type information
    # See api/src/vintagestory_api/services/config_init.py for implementation
    # Format: {env_var: (config_key, type)}
    ENV_VAR_MAP = {
        # Server identity
        "VS_CFG_SERVER_NAME": ("ServerName", "string"),
        "VS_CFG_SERVER_URL": ("ServerUrl", "string"),
        "VS_CFG_SERVER_DESCRIPTION": ("ServerDescription", "string"),
        "VS_CFG_WELCOME_MESSAGE": ("WelcomeMessage", "string"),
        # Network settings
        "VS_CFG_SERVER_IP": ("Ip", "string"),
        "VS_CFG_SERVER_PORT": ("Port", "int"),
        "VS_CFG_SERVER_UPNP": ("Upnp", "bool"),
        "VS_CFG_ADVERTISE_SERVER": ("AdvertiseServer", "bool"),
        "VS_CFG_MAX_CLIENTS": ("MaxClients", "int"),
        # Gameplay settings
        "VS_CFG_SERVER_PASSWORD": ("Password", "string"),
        "VS_CFG_MAX_CHUNK_RADIUS": ("MaxChunkRadius", "int"),
        "VS_CFG_ALLOW_PVP": ("AllowPvP", "bool"),
        "VS_CFG_ALLOW_FIRE_SPREAD": ("AllowFireSpread", "bool"),
        "VS_CFG_PASS_TIME_WHEN_EMPTY": ("PassTimeWhenEmpty", "bool"),
        # Whitelist settings
        "VS_CFG_ONLY_WHITELISTED": ("OnlyWhitelisted", "bool"),
        "VS_CFG_WHITELIST_MODE": ("WhitelistMode", "int"),
        # Performance settings
        "VS_CFG_TICK_TIME": ("TickTime", "float"),
        "VS_CFG_SPAWN_CAP_PLAYER_SCALING": ("SpawnCapPlayerScaling", "float"),
        # World settings (nested keys use dot notation)
        "VS_CFG_WORLD_NAME": ("WorldConfig.WorldName", "string"),
        "VS_CFG_WORLD_SEED": ("WorldConfig.Seed", "string"),
        "VS_CFG_ALLOW_CREATIVE_MODE": ("WorldConfig.AllowCreativeMode", "bool"),
        # ... 40+ total mappings in implementation
    }

    def __init__(self, data_dir: Path, template_path: Path):
        self.config_path = data_dir / "config" / "serverconfig.json"
        self.template_path = template_path

    def needs_initialization(self) -> bool:
        """Check if config needs to be created."""
        return not self.config_path.exists()

    def initialize_config(self) -> Path:
        """Generate serverconfig.json from template + VS_CFG_* overrides."""
        # Load template
        config = self._load_template()

        # Apply environment variable overrides
        overrides = self._collect_env_overrides()
        config = self._apply_overrides(config, overrides)

        # Write config (atomic)
        self._write_config(config)

        return self.config_path

    def _load_template(self) -> dict[str, Any]:
        """Load the reference template."""
        with open(self.template_path) as f:
            return json.load(f)

    def _collect_env_overrides(self) -> dict[str, Any]:
        """Collect VS_CFG_* environment variables."""
        overrides = {}
        for env_key, config_key in self.ENV_VAR_MAP.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                overrides[config_key] = self._parse_value(value)
        return overrides

    def _parse_value(self, value: str) -> Any:
        """Convert string env var to appropriate type."""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            return value

    def _apply_overrides(self, config: dict, overrides: dict) -> dict:
        """Apply overrides to config, handling nested keys."""
        for key, value in overrides.items():
            config[key] = value
        return config

    def _write_config(self, config: dict) -> None:
        """Atomic write to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.config_path.with_suffix(".tmp")
        temp.write_text(json.dumps(config, indent=2))
        temp.rename(self.config_path)
```

**Integration with ServerService:**

```python
# In ServerService.start()
async def start(self):
    if self.config_init.needs_initialization():
        self.config_init.initialize_config()
        logger.info("config_initialized", source="template+env")
    # proceed with start...
```

**Reference Template:**

Ship `serverconfig-template.json` with sensible defaults. The template is JSON (not YAML) since:
- Target format is JSON
- No conversion step needed
- Pydantic natively handles JSON

**Backlog: State Enforcement**

Future enhancement (not MVP): `enforce_env_on_restart` setting would re-apply VS_CFG_* values on each server restart, ensuring env vars always win over manual changes.

## Configuration Service Pattern

```python
# api/src/vintagestory_api/services/config.py
from typing import Optional, Literal
from pydantic import BaseModel

class ServerSetting(BaseModel):
    """Definition of a server setting."""
    key: str
    value_type: Literal["string", "int", "bool"]
    console_command: Optional[str] = None  # None = restart required
    requires_restart: bool = False
    env_var_override: Optional[str] = None  # If set, controlled by env

class ConfigService:
    """Service for reading and modifying server configuration."""

    LIVE_SETTINGS = {
        "ServerName": ServerSetting(
            key="ServerName",
            value_type="string",
            console_command='/serverconfig Name "{value}"'
        ),
        "MaxClients": ServerSetting(
            key="MaxClients",
            value_type="int",
            console_command="/serverconfig MaxClients {value}"
        ),
        "AllowPvP": ServerSetting(
            key="AllowPvP",
            value_type="bool",
            console_command="/serverconfig AllowPvP {value}"
        ),
        # ... more settings
    }

    async def get_settings(self) -> dict:
        """Get current settings from serverconfig.json."""
        config = await self._read_serverconfig()
        return self._enrich_with_metadata(config)

    async def update_setting(self, key: str, value: str) -> UpdateResult:
        """Update a setting using appropriate method."""
        setting = self.LIVE_SETTINGS.get(key)

        if not setting:
            raise ValueError(f"Unknown setting: {key}")

        if setting.env_var_override:
            return UpdateResult(
                success=False,
                error="Setting is managed by environment variable"
            )

        if setting.console_command and self.server_is_running:
            # Use console command for live update
            cmd = setting.console_command.format(value=value)
            await self.console_service.send_command(cmd)
            return UpdateResult(success=True, requires_restart=False)
        else:
            # Fall back to file edit + restart flag
            await self._update_config_file(key, value)
            return UpdateResult(success=True, requires_restart=True)
```

## API Endpoints for Epic 6

**Configuration Domain Separation:**

| Endpoint | Domain | Description |
|----------|--------|-------------|
| `/api/v1alpha1/config/game` | Game Server | Settings stored in serverconfig.json, managed by VintageStory |
| `/api/v1alpha1/config/api` | API Server | Operational settings for the management API itself |

---

### Game Configuration (`/config/game`)

**Read Game Settings:**

```
GET /api/v1alpha1/config/game
```

Returns current game server settings with metadata:

```json
{
  "status": "ok",
  "data": {
    "settings": [
      {
        "key": "ServerName",
        "value": "My Server",
        "type": "string",
        "live_update": true,
        "env_managed": false
      },
      {
        "key": "Port",
        "value": 42420,
        "type": "int",
        "live_update": false,
        "requires_restart": true
      },
      {
        "key": "MaxClients",
        "value": 16,
        "type": "int",
        "live_update": true,
        "env_managed": true,
        "env_var": "VS_CFG_MAX_CLIENTS"
      }
    ],
    "source_file": "serverconfig.json",
    "last_modified": "2025-12-30T10:00:00Z"
  }
}
```

**Update Game Setting:**

```
POST /api/v1alpha1/config/game/settings/{key}
```

Request:
```json
{
  "value": "New Server Name"
}
```

Response (live update):
```json
{
  "status": "ok",
  "data": {
    "key": "ServerName",
    "value": "New Server Name",
    "method": "console_command",
    "pending_restart": false
  }
}
```

Response (requires restart):
```json
{
  "status": "ok",
  "data": {
    "key": "Port",
    "value": 42421,
    "method": "file_update",
    "pending_restart": true
  }
}
```

Response (env managed, blocked):
```json
{
  "status": "error",
  "error": {
    "code": "SETTING_ENV_MANAGED",
    "message": "Setting 'MaxClients' is managed by environment variable VS_CFG_MAX_CLIENTS"
  }
}
```

---

### API Configuration (`/config/api`)

**Read API Settings:**

```
GET /api/v1alpha1/config/api
```

Returns API server operational settings:

```json
{
  "status": "ok",
  "data": {
    "settings": {
      "auto_start_server": false,
      "block_env_managed_settings": true,
      "enforce_env_on_restart": false,
      "mod_list_refresh_interval": 3600,
      "server_versions_refresh_interval": 86400
    }
  }
}
```

**Update API Setting:**

```
POST /api/v1alpha1/config/api/settings/{key}
```

Request:
```json
{
  "value": true
}
```

Response:
```json
{
  "status": "ok",
  "data": {
    "key": "auto_start_server",
    "value": true
  }
}
```

**API Settings Reference:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `auto_start_server` | bool | false | Start game server automatically when API launches |
| `block_env_managed_settings` | bool | true | Reject UI changes to settings controlled by VS_CFG_* env vars |
| `enforce_env_on_restart` | bool | false | Re-apply VS_CFG_* values on each game server restart (backlog) |
| `mod_list_refresh_interval` | int | 3600 | Seconds between mod API cache refreshes |
| `server_versions_refresh_interval` | int | 86400 | Seconds between checking for new VS versions |

---

### Raw Config Files (`/config/files`)

**Read Raw Config File (Monitor + Admin):**

```
GET /api/v1alpha1/config/files/{filename}
```

Returns raw JSON content (read-only view for troubleshooting).

## UI Architecture

**Navigation Structure (Revised):**

```
Dashboard | GameServer | Mods | Settings
              │                   │
              ├── Console         ├── API Settings
              └── Game Config     └── File Manager (stub)
```

**Key UX Decision:** Game Config shares the GameServer tab with Console, so users see console commands execute in real-time when changing settings.

---

### GameServer Page (Responsive Layout)

```typescript
// web/src/features/gameserver/GameServerPage.tsx
function GameServerPage() {
  return (
    <div className="flex flex-col lg:flex-row gap-4 h-full">
      {/* Console: top on mobile, right on desktop */}
      <div className="lg:order-2 lg:w-1/2 min-h-[300px] lg:min-h-[600px]">
        <ConsoleView />
      </div>

      {/* Config: bottom on mobile, left on desktop */}
      <div className="lg:order-1 lg:w-1/2 overflow-y-auto">
        <GameConfigPanel />
      </div>
    </div>
  );
}
```

**Responsive Behavior:**

| Viewport | Layout |
|----------|--------|
| Mobile/Narrow (<1024px) | Console (top) → Config (bottom, scrollable) |
| Desktop/Wide (≥1024px) | Config (left) ↔ Console (right) |

---

### Auto-Save Pattern

**Per-field auto-save** - each setting saves immediately on change:

```typescript
// web/src/features/config/SettingField.tsx
function SettingField({ setting }: { setting: GameSetting }) {
  const updateSetting = useUpdateGameSetting();
  const { toast } = useToast();

  const handleChange = async (value: string | boolean) => {
    try {
      const result = await updateSetting.mutateAsync({
        key: setting.key,
        value: String(value)
      });

      if (result.data.pending_restart) {
        // Triggers PendingRestartBanner (same pattern as mods)
      } else {
        toast({ title: "Setting updated", variant: "success" });
      }
    } catch (error) {
      toast({ title: "Failed to update setting", variant: "destructive" });
    }
  };

  // ... render
}
```

**Restart-Required Fields (Option B - Consistent with Mods):**
- Allowed even when server is running
- Changes written to file
- PendingRestartBanner appears (reuses existing component from mod management)
- User restarts when ready

**Partial Failure Handling:**
- Each field independent - no batching
- Error shown on specific field that failed
- Other fields unaffected

---

### Game Config Panel

```typescript
// web/src/features/config/GameConfigPanel.tsx
function GameConfigPanel() {
  const { data: settings } = useGameSettings();

  return (
    <div className="space-y-6">
      <SettingGroup title="Server Identity">
        <SettingField setting={settings.ServerName} />
        <SettingField setting={settings.ServerDescription} />
        <SettingField setting={settings.WelcomeMessage} />
      </SettingGroup>

      <SettingGroup title="Player Limits">
        <SettingField setting={settings.MaxClients} />
        <SettingField setting={settings.OnlyWhitelisted} />
      </SettingGroup>

      <SettingGroup title="Gameplay">
        <SettingField setting={settings.AllowPvP} />
        <SettingField setting={settings.AllowCreativeMode} />
      </SettingGroup>

      <SettingGroup title="Network">
        <SettingField setting={settings.Port} />
      </SettingGroup>

      <SettingGroup title="Environment Managed" variant="muted">
        <ReadonlySetting setting={settings.VS_GAME_VERSION} />
      </SettingGroup>
    </div>
  );
}
```

---

### Setting Field Component

```typescript
// web/src/features/config/SettingField.tsx
function SettingField({ setting }: { setting: GameSetting }) {
  const updateSetting = useUpdateGameSetting();

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <Label>{setting.label}</Label>
        {setting.live_update && <Badge variant="outline">Live</Badge>}
        {setting.requires_restart && <Badge variant="warning">Restart</Badge>}
        {setting.env_managed && (
          <Badge variant="muted">Env: {setting.env_var}</Badge>
        )}
      </div>

      <div className="w-48">
        {setting.type === "bool" ? (
          <Switch
            checked={setting.value}
            onCheckedChange={(v) => updateSetting.mutate({ key: setting.key, value: v })}
            disabled={setting.env_managed}
          />
        ) : setting.type === "int" ? (
          <Input
            type="number"
            value={setting.value}
            onBlur={(e) => updateSetting.mutate({ key: setting.key, value: e.target.value })}
            disabled={setting.env_managed}
          />
        ) : (
          <Input
            value={setting.value}
            onBlur={(e) => updateSetting.mutate({ key: setting.key, value: e.target.value })}
            disabled={setting.env_managed}
          />
        )}
      </div>
    </div>
  );
}
```

---

### Settings Page (API + File Manager)

```typescript
// web/src/features/settings/SettingsPage.tsx
function SettingsPage() {
  return (
    <Tabs defaultValue="api">
      <TabsList>
        <TabsTrigger value="api">API Settings</TabsTrigger>
        <TabsTrigger value="files">File Manager</TabsTrigger>
      </TabsList>

      <TabsContent value="api">
        <ApiSettingsPanel />
      </TabsContent>

      <TabsContent value="files">
        <FileManagerStub />
      </TabsContent>
    </Tabs>
  );
}

function FileManagerStub() {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p>File Manager coming in a future release.</p>
      <p className="text-sm">Read-only config file viewing will be available here.</p>
    </div>
  );
}
```

---

### API Settings Panel

```typescript
// web/src/features/settings/ApiSettingsPanel.tsx
function ApiSettingsPanel() {
  const { data: settings } = useApiSettings();

  return (
    <div className="space-y-6">
      <SettingGroup title="Startup">
        <ApiSettingField setting={settings.auto_start_server} />
      </SettingGroup>

      <SettingGroup title="Environment Handling">
        <ApiSettingField setting={settings.block_env_managed_settings} />
        <ApiSettingField
          setting={settings.enforce_env_on_restart}
          disabled
          hint="Coming in a future release"
        />
      </SettingGroup>

      <SettingGroup title="Refresh Intervals">
        <ApiSettingField
          setting={settings.mod_list_refresh_interval}
          suffix="seconds"
        />
        <ApiSettingField
          setting={settings.server_versions_refresh_interval}
          suffix="seconds"
        />
      </SettingGroup>
    </div>
  );
}
```

## Generic File Editing (Future Epic)

**Deferred to "File Manager" Epic:**

- Full JSON editor with syntax highlighting
- Create/delete config files
- Backup before edit
- Schema validation

**Rationale:**
- Console commands provide safer config changes for common settings
- File editing requires more security considerations (path traversal, validation)
- Deferring allows focus on high-value "live update" experience

## Open Questions for Implementation

| Question                                          | Answer                                   | Status           |
| ------------------------------------------------- | ---------------------------------------- | ---------------- |
| Which settings support console commands?          | Research console `/serverconfig` command | Needs Testing    |
| Do console changes persist to JSON automatically? | Believed yes, needs verification         | Needs Testing    |
| How to detect file changes made by game server?   | File watcher or poll on GET              | Decision Pending |
| How to handle partial command failures?           | Return error, don't set restart flag     | Decided          |

## Story Updates Required

Original Epic 6 stories need complete rewrite to reflect architectural pivot:

| Original Story               | Why It's Obsolete                                  |
| ---------------------------- | -------------------------------------------------- |
| 6.1: Config Files API        | File-centric approach replaced by settings API    |
| 6.2: Config File Editing API | Direct file editing replaced by console commands  |
| 6.3: Config Editor UI        | JSON editor replaced by form-based settings page  |

**Revised Epic 6 Story Structure:**

| Story | Title | Scope |
|-------|-------|-------|
| **6.0** | Epic 6 Technical Preparation | Research console commands, create serverconfig-template.json, test VS_CFG_* handling |
| **6.1** | ConfigInitService & Template | First-run config generation from template + VS_CFG_* env vars |
| **6.2** | Game Settings API | GET /config/game, POST /config/game/settings/{key} with console command path |
| **6.3** | API Settings Service | GET /config/api, POST /config/api/settings/{key}, api-settings.json persistence |
| **6.4** | Settings UI | Form-based settings page with Game and API tabs |
| **6.5** | Raw Config Viewer | Read-only /config/files/{filename} for troubleshooting |

**Key Changes from Original:**

1. **Two config domains** - Game (`/config/game`) and API (`/config/api`) separated
2. **ConfigInitService** - First-run initialization with VS_CFG_* environment variables
3. **Console command path** - Live updates via `/serverconfig` commands, not file editing
4. **Form-based UI** - Settings page with badges, not JSON editor
5. **Deferred file editing** - Raw file viewer is read-only; editing pushed to future "File Manager" epic

## Testing Strategy

**Console Command Integration Tests:**

```python
@pytest.mark.integration
async def test_setting_update_via_console(running_server):
    """Test that setting updates use console commands."""
    # Start with known value
    config = await api_client.get("/config")
    original_name = config["data"]["settings"]["ServerName"]["value"]

    # Update via API
    response = await api_client.post(
        "/config/settings/ServerName",
        json={"value": "Test Server Name"}
    )

    assert response["data"]["method"] == "console_command"
    assert response["data"]["pending_restart"] == False

    # Verify change took effect
    config = await api_client.get("/config")
    assert config["data"]["settings"]["ServerName"]["value"] == "Test Server Name"

    # Verify persisted to file (game server handles this)
    file_content = Path("/data/config/serverconfig.json").read_text()
    assert "Test Server Name" in file_content
```

## Error Codes for Epic 6

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # ... existing codes ...

    # Epic 6 additions
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_READ_ERROR = "CONFIG_READ_ERROR"
    SETTING_UNKNOWN = "SETTING_UNKNOWN"
    SETTING_ENV_MANAGED = "SETTING_ENV_MANAGED"
    SETTING_UPDATE_FAILED = "SETTING_UPDATE_FAILED"
    CONSOLE_COMMAND_FAILED = "CONSOLE_COMMAND_FAILED"
```

---
