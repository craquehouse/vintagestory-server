"""Game configuration service for VintageStory server settings.

This service provides read and update operations for game server settings
via console commands (live updates) or file updates (restart-required settings).

Story 6.2: Game Settings API
Story 17.5: secret settings (Password) are withheld from every role but Admin (FR186)
Story 17.6: a setting whose game default is known carries it (FR188)
Story 25.1: serverconfig.json is read through one typed model (FR344, FR345)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeGuard
from urllib.parse import urlsplit

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import UserRole
from vintagestory_api.models.server import ServerState
from vintagestory_api.models.server_config import ServerConfigFile
from vintagestory_api.services.config_init import ENV_VAR_MAP, parse_env_value
from vintagestory_api.services.config_parse import (
    ConfigParseError,
    ParseErrorInfo,
    parse_config_text,
)
from vintagestory_api.services.mod_update_alerts import DISCORD_HOSTS

if TYPE_CHECKING:
    from vintagestory_api.services.pending_restart import PendingRestartState
    from vintagestory_api.services.server import ServerService

logger = structlog.get_logger()

# Type alias for value types
ValueType = Literal["string", "int", "bool", "float"]


# Type alias for bool format
BoolFormat = Literal["true_false", "0_1"]


class ServerSetting:
    """Definition of a server setting with update behavior."""

    key: str
    value_type: ValueType
    console_command: str | None
    requires_restart: bool
    live_update: bool
    bool_format: BoolFormat
    nullable: bool
    clear_command: str | None
    secret: bool
    default: bool | None

    def __init__(
        self,
        key: str,
        value_type: ValueType,
        console_command: str | None = None,
        requires_restart: bool = False,
        live_update: bool = True,
        bool_format: BoolFormat = "true_false",
        nullable: bool = False,
        clear_command: str | None = None,
        secret: bool = False,
        default: bool | None = None,
    ) -> None:
        """Initialize a server setting definition.

        Args:
            key: The setting key in serverconfig.json.
            value_type: The data type for this setting.
            console_command: Template with {value} placeholder for live updates.
            requires_restart: Whether this setting requires server restart.
            live_update: Whether this setting can be updated while server is running.
            bool_format: Format for boolean values in console commands.
            nullable: Whether the setting can have no value (null). Story 16.8: only
                settings whose VintageStory default is null; a blank string is stored
                as null.
            clear_command: Console command (no {value}) that clears the setting while
                the server runs. Without one, clearing a live setting writes the file
                and requires a restart.
            secret: The value is a secret: only the Admin role receives it (Story 17.5,
                FR186).
            default: The value VintageStory uses when `serverconfig.json` has no value
                for the setting; None when the manager does not know it. Story 17.6.
                This table is the one place defaults live.
        """
        self.key = key
        self.value_type = value_type
        self.console_command = console_command
        self.requires_restart = requires_restart
        self.live_update = live_update
        self.bool_format = bool_format
        self.nullable = nullable
        self.clear_command = clear_command
        self.secret = secret
        self.default = default


# Settings that support live updates via console commands
LIVE_SETTINGS: dict[str, ServerSetting] = {
    "ServerName": ServerSetting(
        key="ServerName",
        value_type="string",
        console_command="/serverconfig name {value}",
        live_update=True,
    ),
    "ServerDescription": ServerSetting(
        key="ServerDescription",
        value_type="string",
        console_command="/serverconfig description {value}",
        live_update=True,
        nullable=True,
    ),
    "WelcomeMessage": ServerSetting(
        key="WelcomeMessage",
        value_type="string",
        console_command="/serverconfig motd {value}",
        live_update=True,
    ),
    "MaxClients": ServerSetting(
        key="MaxClients",
        value_type="int",
        console_command="/serverconfig maxclients {value}",
        live_update=True,
    ),
    "MaxChunkRadius": ServerSetting(
        key="MaxChunkRadius",
        value_type="int",
        console_command="/serverconfig maxchunkradius {value}",
        live_update=True,
    ),
    "Password": ServerSetting(
        key="Password",
        value_type="string",
        console_command="/serverconfig password {value}",
        live_update=True,
        nullable=True,
        clear_command="/serverconfig nopassword",
        secret=True,
    ),
    "AllowPvP": ServerSetting(
        key="AllowPvP",
        value_type="bool",
        console_command="/serverconfig allowpvp {value}",
        live_update=True,
        bool_format="true_false",
    ),
    "AllowFireSpread": ServerSetting(
        key="AllowFireSpread",
        value_type="bool",
        console_command="/serverconfig allowfirespread {value}",
        live_update=True,
        bool_format="true_false",
    ),
    "AllowFallingBlocks": ServerSetting(
        key="AllowFallingBlocks",
        value_type="bool",
        console_command="/serverconfig allowfallingblocks {value}",
        live_update=True,
        bool_format="true_false",
    ),
    "EntitySpawning": ServerSetting(
        key="EntitySpawning",
        value_type="bool",
        console_command="/serverconfig entityspawning {value}",
        live_update=True,
        bool_format="true_false",
        # Story 17.6: "default: on" per agentdocs/vs-serverconfig-commands.md; the game
        # does not write this key to serverconfig.json, so it is usually null here
        default=True,
    ),
    "PassTimeWhenEmpty": ServerSetting(
        key="PassTimeWhenEmpty",
        value_type="bool",
        console_command="/serverconfig passtimewhenempty {value}",
        live_update=True,
        bool_format="true_false",
    ),
    "Upnp": ServerSetting(
        key="Upnp",
        value_type="bool",
        console_command="/serverconfig upnp {value}",
        live_update=True,
        bool_format="0_1",  # uses 0/1
    ),
    "AdvertiseServer": ServerSetting(
        key="AdvertiseServer",
        value_type="bool",
        console_command="/serverconfig advertise {value}",
        live_update=True,
        bool_format="0_1",  # uses 0/1
    ),
    # Restart-required settings (no console_command)
    "Port": ServerSetting(
        key="Port",
        value_type="int",
        console_command=None,
        requires_restart=True,
        live_update=False,
    ),
    "Ip": ServerSetting(
        key="Ip",
        value_type="string",
        console_command=None,
        requires_restart=True,
        live_update=False,
        nullable=True,
    ),
}

REDACTED = "[redacted]"
"""What a role other than Admin receives in place of a secret value in a config file (FR186)."""

SECRET_SETTING_KEYS: frozenset[str] = frozenset(
    key for key, setting in LIVE_SETTINGS.items() if setting.secret
)
"""Keys of serverconfig.json whose values only the Admin role receives (Story 17.5)."""

UNMANAGED_SECRET_KEYS: frozenset[str] = frozenset({"StartupCommands"})
"""serverconfig.json keys that are not managed settings and hold secrets (Epic 19 ADR-2)."""

SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "privatekey",
    "accesskey",
    "credential",
    "webhook",
    "authorization",
)
"""A key that contains one of these, after normalising, is a secret (Epic 19 ADR-2)."""


def _normalise_key(key: str) -> str:
    """casefold() and remove "_", "-", "." and spaces."""
    folded = key.casefold()
    for separator in ("_", "-", ".", " "):
        folded = folded.replace(separator, "")
    return folded


_SECRET_KEYS_NORMALISED = frozenset(
    _normalise_key(key) for key in SECRET_SETTING_KEYS | UNMANAGED_SECRET_KEYS
)


def _is_json_object(value: object) -> TypeGuard[dict[str, Any]]:
    """Whether parsed JSON is an object. `json.loads` only builds dicts with string keys."""
    return isinstance(value, dict)


def _is_json_array(value: object) -> TypeGuard[list[Any]]:
    """Whether parsed JSON is an array."""
    return isinstance(value, list)


def is_secret_key(key: str) -> bool:
    """Whether a config key names a secret (Epic 19 ADR-2).

    A secret setting (Password), an unmanaged secret key (StartupCommands), or a key
    containing one of SECRET_KEY_FRAGMENTS, all compared after _normalise_key (letter
    case, "_", "-", "." and spaces ignored).
    """
    normalised = _normalise_key(key)
    if normalised in _SECRET_KEYS_NORMALISED:
        return True
    return any(fragment in normalised for fragment in SECRET_KEY_FRAGMENTS)


def is_secret_value(value: str) -> bool:
    """Whether a string is a URL with user info or a Discord webhook URL (Epic 19 ADR-2 decision 4).

    User info counts with or without a password. A Discord webhook URL is one on a
    host in mod_update_alerts.DISCORD_HOSTS (discord.com, discordapp.com,
    ptb.discord.com, canary.discord.com) whose path starts with /api/webhooks/.
    """
    try:
        parts = urlsplit(value)
        if not (parts.scheme and parts.netloc):
            return False
        if parts.username is not None:
            return True
        hostname = parts.hostname
    except ValueError:
        return False
    return (
        hostname is not None
        and hostname.lower() in DISCORD_HOSTS
        and parts.path.startswith("/api/webhooks/")
    )


def has_secret_value(value: object) -> bool:
    """Whether a secret is set: anything but null and the empty string."""
    return value is not None and value != ""


def _redact(value: object) -> object:
    """The walk behind redact_secrets: a new value, the argument unchanged."""
    if _is_json_object(value):
        return {
            key: REDACTED if is_secret_key(key) and has_secret_value(item) else _redact(item)
            for key, item in value.items()
        }
    if _is_json_array(value):
        return [_redact(item) for item in value]
    if isinstance(value, str) and is_secret_value(value):
        return REDACTED
    return value


def redact_secrets(content: object) -> object:
    """Parsed JSON with every secret replaced by REDACTED, at every depth (Epic 19 ADR-2).

    A secret key's (is_secret_key) whole value, of any type, is replaced unless it is
    null or "" (has_secret_value); any other string is replaced when is_secret_value
    (a URL with user info or a Discord webhook URL), under any key name. Fails closed:
    if the walk hits the recursion limit the whole content is REDACTED. The argument
    is not changed.
    """
    try:
        return _redact(content)
    except RecursionError:
        return REDACTED


class SettingInfo:
    """Information about a single server setting."""

    def __init__(
        self,
        key: str,
        value: Any,
        value_type: ValueType,
        live_update: bool,
        requires_restart: bool,
        env_managed: bool,
        env_var: str | None = None,
        secret: bool = False,
        configured: bool | None = None,
        default: bool | None = None,
    ) -> None:
        """Initialize setting info.

        Args:
            key: The setting key.
            value: Current value from serverconfig.json.
            value_type: The data type for this setting.
            live_update: Whether this setting can be updated while server is running.
            requires_restart: Whether this setting requires server restart.
            env_managed: Whether this setting is managed by an environment variable.
            env_var: The environment variable name if env_managed is True.
            secret: Whether the value is a secret that only the Admin role receives
                (Story 17.5).
            configured: Set only when a secret value was withheld: whether the secret
                is set. None when the value is included.
            default: The game's value when `value` is None, if the manager knows it
                (Story 17.6). None when unknown.
        """
        self.key = key
        self.value = value
        self.type = value_type
        self.live_update = live_update
        self.requires_restart = requires_restart
        self.env_managed = env_managed
        self.env_var = env_var
        self.secret = secret
        self.configured = configured
        self.default = default

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "key": self.key,
            "value": self.value,
            "type": self.type,
            "live_update": self.live_update,
            "env_managed": self.env_managed,
        }
        if self.requires_restart:
            result["requires_restart"] = True
        if self.env_var:
            result["env_var"] = self.env_var
        if self.secret:
            result["secret"] = True
        if self.configured is not None:
            result["configured"] = self.configured
        if self.default is not None:
            result["default"] = self.default
        return result


class SettingsResponse:
    """Response containing all settings with metadata."""

    def __init__(
        self,
        settings: list[SettingInfo],
        source_file: str,
        last_modified: datetime,
    ) -> None:
        """Initialize settings response.

        Args:
            settings: List of setting info objects.
            source_file: Name of the source file.
            last_modified: Last modification time of the file.
        """
        self.settings = settings
        self.source_file = source_file
        self.last_modified = last_modified

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "settings": [s.to_dict() for s in self.settings],
            "source_file": self.source_file,
            "last_modified": self.last_modified.isoformat(),
        }


class UpdateResult:
    """Result of a setting update operation."""

    def __init__(
        self,
        key: str,
        value: Any,
        method: Literal["console_command", "file_update"],
        pending_restart: bool,
    ) -> None:
        """Initialize update result.

        Args:
            key: The setting key that was updated.
            value: The new value.
            method: How the update was applied.
            pending_restart: Whether a restart is now pending.
        """
        self.key = key
        self.value = value
        self.method = method
        self.pending_restart = pending_restart

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "key": self.key,
            "value": self.value,
            "method": self.method,
            "pending_restart": self.pending_restart,
        }


class GameConfigError(Exception):
    """Base exception for game configuration errors."""

    def __init__(self, message: str, code: str) -> None:
        """Initialize error with message and code.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
        """
        super().__init__(message)
        self.message = message
        self.code = code


class SettingUnknownError(GameConfigError):
    """Raised when attempting to access an unknown setting."""

    def __init__(self, key: str) -> None:
        super().__init__(
            message=f"Unknown setting: '{key}'",
            code="SETTING_UNKNOWN",
        )


class SettingEnvManagedError(GameConfigError):
    """Raised when attempting to update an env-managed setting."""

    def __init__(self, key: str, env_var: str) -> None:
        super().__init__(
            message=f"Setting '{key}' is managed by environment variable {env_var}",
            code="SETTING_ENV_MANAGED",
        )
        self.env_var = env_var


class SettingUpdateFailedError(GameConfigError):
    """Raised when a setting update fails."""

    def __init__(self, key: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to update setting '{key}': {reason}",
            code="SETTING_UPDATE_FAILED",
        )


class ServerConfigInvalidError(Exception):
    """serverconfig.json is not valid JSON or not a JSON object (Story 25.1, FR345).

    `info` is the `parse_error` of the 422 CONFIG_FILE_INVALID response.
    """

    def __init__(self, info: ParseErrorInfo) -> None:
        super().__init__(info.message)
        self.info = info
        self.message = f"serverconfig.json could not be read: {info.message}"


NOT_AN_OBJECT_MESSAGE = "The file is not a JSON object"


@dataclass(frozen=True)
class LoadedServerConfig:
    """serverconfig.json as parsed (`raw`, the one that is written) and as typed (`model`)."""

    raw: dict[str, Any]
    model: ServerConfigFile


class SettingValueInvalidError(GameConfigError):
    """Raised when a setting value fails validation."""

    def __init__(self, key: str, reason: str) -> None:
        super().__init__(
            message=f"Invalid value for setting '{key}': {reason}",
            code="SETTING_VALUE_INVALID",
        )


class GameConfigService:
    """Service for reading and updating game server settings.

    This service provides:
    - Reading all settings with metadata (type, live_update, env_managed)
    - Updating settings via console commands (live) or file updates (restart-required)
    - Detection of env-managed settings (VS_CFG_* environment variables)

    Update strategy:
    1. If server is running AND setting supports live_update → console command
    2. If server is stopped OR setting requires restart → file update
    """

    def __init__(
        self,
        settings: Settings | None = None,
        server_service: ServerService | None = None,
        pending_restart_state: PendingRestartState | None = None,
        block_env_managed_settings: bool = True,
    ) -> None:
        """Initialize the game config service.

        Args:
            settings: Application settings. If None, creates new Settings instance.
            server_service: ServerService for checking state and sending commands.
            pending_restart_state: PendingRestartState for tracking restart requirements.
            block_env_managed_settings: Whether to block updates to env-managed settings.
        """
        self._settings = settings or Settings()
        self._server_service = server_service
        self._pending_restart_state = pending_restart_state
        self._block_env_managed = block_env_managed_settings

    @property
    def config_path(self) -> Path:
        """Path to serverconfig.json."""
        return self._settings.serverdata_dir / "serverconfig.json"

    def _get_env_var_for_setting(self, key: str) -> str | None:
        """Get the env var name that manages this setting, if any.

        Args:
            key: The setting key to check.

        Returns:
            The environment variable name if this setting is env-managed, None otherwise.
        """
        for env_var, (config_key, _) in ENV_VAR_MAP.items():
            if config_key == key and env_var in os.environ:
                return env_var
        return None

    def is_server_running(self) -> bool:
        """Check if the game server is currently running.

        Returns:
            True if server is running, False otherwise.
        """
        if self._server_service is None:
            return False
        status = self._server_service.get_server_status()
        return status.state == ServerState.RUNNING

    def read_config(self, *, log_invalid: bool = True) -> LoadedServerConfig:
        """Read serverconfig.json through the typed model (Story 25.1, Epic 25 ADR-1).

        The text is parsed as strict JSON (Epic 23 ADR-1). A named key whose value has the
        wrong type is read as missing and, when `log_invalid`, logged with its name only
        (ADR-1 decision 3). The Prometheus scrape reads without logging, so a scrape every
        few seconds does not repeat the warning (Story 22.2's no-warning rule).

        Raises:
            FileNotFoundError: If the file does not exist.
            ServerConfigInvalidError: If it is not valid JSON or not a JSON object.
            OSError: If it cannot be read.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        text = self.config_path.read_text(encoding="utf-8")
        try:
            parsed = parse_config_text(text, strict=True)
        except ConfigParseError as e:
            raise ServerConfigInvalidError(e.info) from None
        if not _is_json_object(parsed):
            raise ServerConfigInvalidError(ParseErrorInfo(NOT_AN_OBJECT_MESSAGE, None, None))
        read = ServerConfigFile.from_raw(parsed)
        for key in read.invalid_keys if log_invalid else ():
            logger.warning("serverconfig_field_invalid", key=key)
        return LoadedServerConfig(raw=parsed, model=read.model)

    def _get_config_mtime(self) -> datetime:
        """Get the last modification time of serverconfig.json.

        Returns:
            Last modification time as UTC datetime.
        """
        stat = self.config_path.stat()
        return datetime.fromtimestamp(stat.st_mtime, tz=UTC)

    def get_settings(self, role: str | None = None) -> SettingsResponse:
        """Get all managed settings with metadata.

        Secret settings (Story 17.5, FR186) are redacted unless the Admin role is
        passed (Epic 17 ADR-4 decision 4): their value is None and `configured` says
        whether the secret is set. The Admin role receives the value.

        Args:
            role: The caller's role. Only UserRole.ADMIN receives secret values; any
                other value, None included, receives the redacted form.

        Returns:
            SettingsResponse containing all settings with type, live_update, and env_managed info.

        Raises:
            FileNotFoundError: If serverconfig.json does not exist.
            ServerConfigInvalidError: If it is not valid JSON or not an object (Story 25.1).
        """
        loaded = self.read_config()
        config = loaded.raw
        last_modified = self._get_config_mtime()

        reveal_secrets = role == UserRole.ADMIN
        settings_list: list[SettingInfo] = []

        for key, setting_def in LIVE_SETTINGS.items():
            value = loaded.model.value_of(key)
            configured: bool | None = None
            if setting_def.secret and not reveal_secrets:
                folded = key.casefold()
                configured = any(
                    has_secret_value(v) for k, v in config.items() if k.casefold() == folded
                )
                value = None
            env_var = self._get_env_var_for_setting(key)

            setting_info = SettingInfo(
                key=key,
                value=value,
                value_type=setting_def.value_type,
                live_update=setting_def.live_update,
                requires_restart=setting_def.requires_restart,
                env_managed=env_var is not None,
                env_var=env_var,
                secret=setting_def.secret,
                configured=configured,
                default=setting_def.default,
            )
            settings_list.append(setting_info)

        logger.debug(
            "settings_retrieved",
            count=len(settings_list),
            source_file=self.config_path.name,
        )

        return SettingsResponse(
            settings=settings_list,
            source_file=self.config_path.name,
            last_modified=last_modified,
        )

    def get_max_clients(self) -> int | None:
        """MaxClients from serverconfig.json (Epic 22 ADR-4).

        None when the file does not exist yet or the value is not a whole number.
        Raises when the file exists but cannot be read, or ServerConfigInvalidError when it
        is not valid JSON (the metrics collector logs and skips a failing source).
        """
        if not self.config_path.exists():
            return None
        return self.read_config(log_invalid=False).model.max_clients

    def _validate_value(
        self, key: str, value: Any, value_type: ValueType, nullable: bool = False
    ) -> Any:
        """Validate and coerce a value to the expected type.

        Story 16.8: a nullable setting accepts None, and a blank string (empty or only
        whitespace) for it becomes None. None for any other setting is rejected instead
        of being stored as the text "None".

        Args:
            key: The setting key (for error messages).
            value: The value to validate.
            value_type: The expected type.
            nullable: Whether the setting accepts no value (null).

        Returns:
            The validated and coerced value, or None for a cleared nullable setting.

        Raises:
            SettingValueInvalidError: If the value cannot be coerced to the expected type.
        """
        if value is None:
            if nullable:
                return None
            raise SettingValueInvalidError(key, "This setting cannot be empty (null)")
        if nullable and isinstance(value, str) and value.strip() == "":
            return None

        try:
            # If already correct type, return as-is
            if value_type == "string" and isinstance(value, str):
                return value
            if value_type == "int" and isinstance(value, int) and not isinstance(value, bool):
                return value
            if value_type == "bool" and isinstance(value, bool):
                return value
            if value_type == "float":
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return float(value)

            # Try to coerce using parse_env_value
            str_value = str(value)
            return parse_env_value(str_value, value_type)

        except ValueError as e:
            raise SettingValueInvalidError(
                key,
                f"Expected {value_type}, got {type(value).__name__}: {value}",
            ) from e

    def _sanitize_string_for_console(self, key: str, value: str) -> str:
        """Sanitize a string value for safe use in console commands.

        Prevents command injection by rejecting strings with dangerous characters.
        Console commands use double quotes for strings, so embedded quotes could
        break out of the string context.

        Args:
            key: The setting key (for error messages).
            value: The string value to sanitize.

        Returns:
            The sanitized string (unchanged if valid).

        Raises:
            SettingValueInvalidError: If the string contains dangerous characters.
        """
        # Reject strings containing double quotes - these could break command syntax
        # Example attack: 'Test"; /stop' would become '/serverconfig name "Test"; /stop"'
        if '"' in value:
            raise SettingValueInvalidError(
                key,
                "String values cannot contain double quotes",
            )

        # Also reject backslashes as they could be used for escape sequences
        if "\\" in value:
            raise SettingValueInvalidError(
                key,
                "String values cannot contain backslashes",
            )

        # Reject newlines/carriage returns which could inject additional commands
        if "\n" in value or "\r" in value:
            raise SettingValueInvalidError(
                key,
                "String values cannot contain newlines",
            )

        return value

    async def update_setting(self, key: str, value: Any) -> UpdateResult:
        """Update a server setting.

        Uses console command for live updates when server is running,
        or file update when server is stopped or setting requires restart.

        Args:
            key: The setting key to update.
            value: The new value to set.

        Returns:
            UpdateResult containing the update method and pending_restart status.

        Raises:
            SettingUnknownError: If the setting key is not recognized.
            SettingEnvManagedError: If the setting is managed by an env var.
            SettingValueInvalidError: If the value fails validation.
            SettingUpdateFailedError: If the update fails.
        """
        # Validate setting exists
        if key not in LIVE_SETTINGS:
            raise SettingUnknownError(key)

        setting_def = LIVE_SETTINGS[key]

        # Validate and coerce value type
        validated_value = self._validate_value(
            key, value, setting_def.value_type, setting_def.nullable
        )

        # Sanitize string values for command injection prevention
        if setting_def.value_type == "string" and isinstance(validated_value, str):
            validated_value = self._sanitize_string_for_console(key, validated_value)

        # Check if env-managed
        if self._block_env_managed:
            env_var = self._get_env_var_for_setting(key)
            if env_var is not None:
                raise SettingEnvManagedError(key, env_var)

        # Determine update method
        server_running = self.is_server_running()
        use_console = server_running and setting_def.live_update

        if use_console and validated_value is None:
            # Story 16.8: clear with the setting's own command; without one (Description)
            # write the file and require a restart, like restart-required settings.
            if setting_def.clear_command is not None:
                result = await self._execute_console_command(key, None, setting_def)
            else:
                result = await self._update_config_file(
                    key, None, setting_def, requires_restart=True
                )
        elif use_console:
            result = await self._execute_console_command(key, validated_value, setting_def)
        else:
            result = await self._update_config_file(key, validated_value, setting_def)

        # Only after a successful update: a refused or failed one changes no pending edit
        self._track_pending_edit(key, result)
        return result

    def _track_pending_edit(self, key: str, result: UpdateResult) -> None:
        """Record or drop the key's pending edit (Story 22.7, ADR-15 decisions 1 and 4).

        A restart-required file write while a game process lives is recorded, because the
        game can rewrite serverconfig.json with its own value before the next start. Any
        other successful update is newer than the key's edit and drops it.
        """
        if self._server_service is None:
            return
        store = self._server_service.pending_config_edits
        if (
            result.method == "file_update"
            and result.pending_restart
            and self._server_service.game_server_pid is not None
        ):
            store.record(key, result.value)
        else:
            store.drop([key], reason="changed_again")

    def _format_bool_for_console(self, value: bool, bool_format: BoolFormat) -> str:
        """Format a boolean value for a console command.

        Args:
            value: The boolean value.
            bool_format: The format to use.

        Returns:
            Formatted string representation.
        """
        if bool_format == "0_1":
            return "1" if value else "0"
        return "true" if value else "false"

    async def _execute_console_command(
        self, key: str, value: Any, setting_def: ServerSetting
    ) -> UpdateResult:
        """Execute a console command to update a setting.

        Args:
            key: The setting key.
            value: The value to set.
            setting_def: The setting definition.

        Returns:
            UpdateResult for the update.

        Raises:
            SettingUpdateFailedError: If the console command fails.
        """
        if self._server_service is None:
            raise SettingUpdateFailedError(key, "ServerService not available")

        if value is None:
            # Story 16.8: clearing uses the setting's clear command (no value)
            if setting_def.clear_command is None:
                raise SettingUpdateFailedError(key, "No console command clears this setting")
            formatted_value = ""
            command = setting_def.clear_command
        else:
            if setting_def.console_command is None:
                raise SettingUpdateFailedError(key, "No console command available")

            # Format value for console command
            if setting_def.value_type == "bool":
                formatted_value = self._format_bool_for_console(value, setting_def.bool_format)
            else:
                formatted_value = str(value)

            # Build command
            command = setting_def.console_command.format(value=formatted_value)

        # Execute command
        # Don't log secret values (Story 17.5: follows the secret flag)
        if setting_def.secret:
            logger.info("executing_console_command", key=key, value="***")
        else:
            logger.info("executing_console_command", key=key, value=formatted_value)

        success = await self._server_service.send_command(command)

        if not success:
            raise SettingUpdateFailedError(key, "Console command failed")

        logger.info(
            "setting_updated",
            key=key,
            method="console_command",
            pending_restart=False,
        )

        return UpdateResult(
            key=key,
            value=value,
            method="console_command",
            pending_restart=False,
        )

    async def _update_config_file(
        self,
        key: str,
        value: Any,
        setting_def: ServerSetting,
        requires_restart: bool | None = None,
    ) -> UpdateResult:
        """Update a setting in the config file.

        Args:
            key: The setting key.
            value: The value to set (None is written as JSON null).
            setting_def: The setting definition.
            requires_restart: Override for whether the change needs a restart;
                defaults to the setting definition's requires_restart.

        Returns:
            UpdateResult for the update.

        Raises:
            ServerConfigInvalidError: If serverconfig.json is not valid JSON (Story 25.1);
                the file is not touched.
            SettingUpdateFailedError: If the file update fails.
        """
        try:
            config = self.read_config().raw
            config[key] = value

            # Atomic write using temp file + rename
            temp_path = self.config_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(config, indent=2))
            temp_path.rename(self.config_path)

            # Track pending restart if needed
            pending_restart = (
                setting_def.requires_restart if requires_restart is None else requires_restart
            )
            if pending_restart and self._pending_restart_state is not None:
                self._pending_restart_state.require_restart(
                    f"Setting '{key}' changed - requires server restart"
                )

            # Don't log secret values (Story 17.5: follows the secret flag)
            if setting_def.secret:
                logger.info(
                    "setting_updated",
                    key=key,
                    method="file_update",
                    pending_restart=pending_restart,
                    value="***",
                )
            else:
                logger.info(
                    "setting_updated",
                    key=key,
                    method="file_update",
                    pending_restart=pending_restart,
                    value=value,
                )

            return UpdateResult(
                key=key,
                value=value,
                method="file_update",
                pending_restart=pending_restart,
            )

        except ServerConfigInvalidError:
            raise
        except Exception as e:
            logger.error("config_file_update_failed", key=key, error=str(e))
            raise SettingUpdateFailedError(key, str(e)) from e
