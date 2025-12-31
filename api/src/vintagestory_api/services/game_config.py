"""Game configuration service for VintageStory server settings.

This service provides read and update operations for game server settings
via console commands (live updates) or file updates (restart-required settings).

Story 6.2: Game Settings API
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.config_init import ENV_VAR_MAP, parse_env_value

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

    def __init__(
        self,
        key: str,
        value_type: ValueType,
        console_command: str | None = None,
        requires_restart: bool = False,
        live_update: bool = True,
        bool_format: BoolFormat = "true_false",
    ) -> None:
        """Initialize a server setting definition.

        Args:
            key: The setting key in serverconfig.json.
            value_type: The data type for this setting.
            console_command: Template with {value} placeholder for live updates.
            requires_restart: Whether this setting requires server restart.
            live_update: Whether this setting can be updated while server is running.
            bool_format: Format for boolean values in console commands.
        """
        self.key = key
        self.value_type = value_type
        self.console_command = console_command
        self.requires_restart = requires_restart
        self.live_update = live_update
        self.bool_format = bool_format


# Settings that support live updates via console commands
LIVE_SETTINGS: dict[str, ServerSetting] = {
    "ServerName": ServerSetting(
        key="ServerName",
        value_type="string",
        console_command='/serverconfig name "{value}"',
        live_update=True,
    ),
    "ServerDescription": ServerSetting(
        key="ServerDescription",
        value_type="string",
        console_command='/serverconfig description "{value}"',
        live_update=True,
    ),
    "WelcomeMessage": ServerSetting(
        key="WelcomeMessage",
        value_type="string",
        console_command='/serverconfig motd "{value}"',
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
        console_command='/serverconfig password "{value}"',
        live_update=True,
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
    ),
}


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
        """
        self.key = key
        self.value = value
        self.type = value_type
        self.live_update = live_update
        self.requires_restart = requires_restart
        self.env_managed = env_managed
        self.env_var = env_var

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

    def _load_config(self) -> dict[str, Any]:
        """Load the serverconfig.json file.

        Returns:
            Configuration dictionary.

        Raises:
            FileNotFoundError: If config file does not exist.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with self.config_path.open("r") as f:
            return json.load(f)

    def _get_config_mtime(self) -> datetime:
        """Get the last modification time of serverconfig.json.

        Returns:
            Last modification time as UTC datetime.
        """
        stat = self.config_path.stat()
        return datetime.fromtimestamp(stat.st_mtime, tz=UTC)

    def get_settings(self) -> SettingsResponse:
        """Get all managed settings with metadata.

        Returns:
            SettingsResponse containing all settings with type, live_update, and env_managed info.

        Raises:
            FileNotFoundError: If serverconfig.json does not exist.
        """
        config = self._load_config()
        last_modified = self._get_config_mtime()

        settings_list: list[SettingInfo] = []

        for key, setting_def in LIVE_SETTINGS.items():
            value = config.get(key)
            env_var = self._get_env_var_for_setting(key)

            setting_info = SettingInfo(
                key=key,
                value=value,
                value_type=setting_def.value_type,
                live_update=setting_def.live_update,
                requires_restart=setting_def.requires_restart,
                env_managed=env_var is not None,
                env_var=env_var,
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

    def _validate_value(self, key: str, value: Any, value_type: ValueType) -> Any:
        """Validate and coerce a value to the expected type.

        Args:
            key: The setting key (for error messages).
            value: The value to validate.
            value_type: The expected type.

        Returns:
            The validated and coerced value.

        Raises:
            SettingValueInvalidError: If the value cannot be coerced to the expected type.
        """
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
        validated_value = self._validate_value(key, value, setting_def.value_type)

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

        if use_console:
            return await self._execute_console_command(key, validated_value, setting_def)
        else:
            return await self._update_config_file(key, validated_value, setting_def)

    def _format_bool_for_console(
        self, value: bool, bool_format: BoolFormat
    ) -> str:
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
        if setting_def.console_command is None:
            raise SettingUpdateFailedError(key, "No console command available")

        if self._server_service is None:
            raise SettingUpdateFailedError(key, "ServerService not available")

        # Format value for console command
        if setting_def.value_type == "bool":
            formatted_value = self._format_bool_for_console(value, setting_def.bool_format)
        else:
            formatted_value = str(value)

        # Build command
        command = setting_def.console_command.format(value=formatted_value)

        # Execute command
        # Don't log password values
        if key.lower() == "password":
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
        self, key: str, value: Any, setting_def: ServerSetting
    ) -> UpdateResult:
        """Update a setting in the config file.

        Args:
            key: The setting key.
            value: The value to set.
            setting_def: The setting definition.

        Returns:
            UpdateResult for the update.

        Raises:
            SettingUpdateFailedError: If the file update fails.
        """
        try:
            config = self._load_config()
            config[key] = value

            # Atomic write using temp file + rename
            temp_path = self.config_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(config, indent=2))
            temp_path.rename(self.config_path)

            # Track pending restart if needed
            pending_restart = setting_def.requires_restart
            if pending_restart and self._pending_restart_state is not None:
                self._pending_restart_state.require_restart(
                    f"Setting '{key}' changed - requires server restart"
                )

            # Don't log password values
            if key.lower() == "password":
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

        except Exception as e:
            logger.error("config_file_update_failed", key=key, error=str(e))
            raise SettingUpdateFailedError(key, str(e)) from e
