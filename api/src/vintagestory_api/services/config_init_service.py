"""Configuration initialization service for VintageStory server.

This service generates serverconfig.json from a template and environment
variable overrides on first server start.

Story 6.1: ConfigInitService and Template
"""

import json
import os
from pathlib import Path
from typing import Any, Literal

import structlog

from vintagestory_api.config import Settings
from vintagestory_api.services.config_init import (
    ENV_VAR_MAP,
    get_config_key_path,
    parse_env_value,
)

# Type alias for value types
ValueType = Literal["string", "int", "bool", "float"]

logger = structlog.get_logger()

# Template location relative to this package
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "serverconfig-template.json"


class ConfigInitService:
    """Service for initializing VintageStory server configuration.

    This service handles first-run configuration generation by:
    1. Checking if serverconfig.json needs to be created
    2. Loading the template configuration
    3. Applying VS_CFG_* environment variable overrides
    4. Writing the config atomically to prevent corruption

    IMPORTANT: This service does NOT overwrite existing configs.
    Once serverconfig.json exists, it is the source of truth.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the config init service.

        Args:
            settings: Application settings. If None, creates new Settings instance.
        """
        self._settings = settings or Settings()
        self._template_path = TEMPLATE_PATH

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    @property
    def config_path(self) -> Path:
        """Path to serverconfig.json."""
        return self._settings.serverdata_dir / "serverconfig.json"

    def needs_initialization(self) -> bool:
        """Check if configuration needs to be initialized.

        Returns:
            True if serverconfig.json does not exist, False otherwise.
        """
        exists = self.config_path.exists()
        logger.debug(
            "config_init_check",
            config_path=str(self.config_path),
            exists=exists,
        )
        return not exists

    def initialize_config(self) -> None:
        """Initialize serverconfig.json from template with env var overrides.

        This method:
        1. Loads the template configuration
        2. Collects VS_CFG_* environment variables
        3. Applies valid overrides (logging warnings for invalid values)
        4. Writes the config atomically using temp file + rename

        Raises:
            FileNotFoundError: If template file does not exist.
            IOError: If config file cannot be written.
        """
        if not self.needs_initialization():
            logger.info(
                "config_init_skipped",
                reason="config_already_exists",
                config_path=str(self.config_path),
            )
            return

        # Load template
        config = self._load_template()

        # Collect and apply environment variable overrides
        overrides = self._collect_env_overrides()
        if overrides:
            config = self._apply_overrides(config, overrides)

        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically using temp file + rename
        self._write_config_atomic(config)

        logger.info(
            "config_initialized",
            config_path=str(self.config_path),
            overrides_applied=len(overrides),
        )

    def _load_template(self) -> dict[str, Any]:
        """Load the serverconfig template.

        Returns:
            Template configuration as a dictionary.

        Raises:
            FileNotFoundError: If template file does not exist.
        """
        if not self._template_path.exists():
            raise FileNotFoundError(f"Config template not found: {self._template_path}")

        with self._template_path.open("r") as f:
            template = json.load(f)

        logger.debug("template_loaded", template_path=str(self._template_path))
        return template

    def _collect_env_overrides(self) -> dict[str, tuple[str, str, ValueType]]:
        """Collect VS_CFG_* environment variables for config overrides.

        Returns:
            Dictionary mapping env var name to tuple of (config_key, value, value_type).
            Only includes env vars that are set and have mappings in ENV_VAR_MAP.
        """
        overrides: dict[str, tuple[str, str, ValueType]] = {}

        for env_var, (config_key, value_type) in ENV_VAR_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                overrides[env_var] = (config_key, value, value_type)
                # Log collection but mask sensitive values
                if "PASSWORD" in env_var.upper():
                    logger.debug(
                        "env_override_collected",
                        env_var=env_var,
                        config_key=config_key,
                        value="***",
                    )
                else:
                    logger.debug(
                        "env_override_collected",
                        env_var=env_var,
                        config_key=config_key,
                        value=value,
                    )

        return overrides

    def _apply_overrides(
        self,
        config: dict[str, Any],
        overrides: dict[str, tuple[str, str, ValueType]],
    ) -> dict[str, Any]:
        """Apply environment variable overrides to configuration.

        Args:
            config: The base configuration dictionary.
            overrides: Dictionary mapping env var name to (config_key, value, value_type).

        Returns:
            Modified configuration with overrides applied.
        """
        for env_var, (config_key, raw_value, value_type) in overrides.items():
            try:
                # Parse the value to the correct type
                parsed_value = parse_env_value(raw_value, value_type)

                # Apply to config (handling nested keys)
                self._set_nested_value(config, config_key, parsed_value)

                # Log success but mask sensitive values
                if "PASSWORD" in env_var.upper():
                    logger.debug(
                        "env_override_applied",
                        env_var=env_var,
                        config_key=config_key,
                        value="***",
                    )
                else:
                    logger.debug(
                        "env_override_applied",
                        env_var=env_var,
                        config_key=config_key,
                        value=parsed_value,
                    )

            except ValueError as e:
                # Log warning and skip this override - use template default
                logger.warning(
                    "env_var_parse_error",
                    env_var=env_var,
                    value=raw_value,
                    expected_type=value_type,
                    error=str(e),
                )
                continue

        return config

    def _set_nested_value(
        self,
        config: dict[str, Any],
        key: str,
        value: Any,
    ) -> None:
        """Set a value in the config, handling dotted paths for nested keys.

        Args:
            config: Configuration dictionary to modify.
            key: Config key, possibly with dots (e.g., "WorldConfig.AllowCreativeMode").
            value: Value to set.
        """
        path = get_config_key_path(key)

        # Navigate to parent, creating intermediate dicts if needed
        current = config
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        current[path[-1]] = value

    def _write_config_atomic(self, config: dict[str, Any]) -> None:
        """Write configuration atomically using temp file + rename.

        This prevents corruption if the process crashes mid-write.

        Args:
            config: Configuration dictionary to write.
        """
        temp_path = self.config_path.with_suffix(".tmp")

        # Write to temp file
        temp_path.write_text(json.dumps(config, indent=2))

        # Atomic rename (POSIX)
        temp_path.rename(self.config_path)

        logger.debug("config_written", config_path=str(self.config_path))
