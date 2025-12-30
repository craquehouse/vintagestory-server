"""Configuration initialization service for VintageStory server.

This module provides environment variable to serverconfig.json mapping
and type coercion for initial configuration generation.

Story 6.0: Epic 6 Technical Preparation
"""

from typing import Any, Literal

# Complete mapping of VS_CFG_* environment variables to serverconfig.json keys
# Based on DarkMatterProductions reference implementation + VintageStory defaults
ENV_VAR_MAP: dict[str, tuple[str, Literal["string", "int", "bool", "float"]]] = {
    # Server identity
    "VS_CFG_SERVER_NAME": ("ServerName", "string"),
    "VS_CFG_SERVER_URL": ("ServerUrl", "string"),
    "VS_CFG_SERVER_DESCRIPTION": ("ServerDescription", "string"),
    "VS_CFG_WELCOME_MESSAGE": ("WelcomeMessage", "string"),
    # Network settings
    "VS_CFG_SERVER_IP": ("Ip", "string"),
    "VS_CFG_SERVER_PORT": ("Port", "int"),
    "VS_CFG_SERVER_UPNP": ("Upnp", "bool"),
    "VS_CFG_COMPRESS_PACKETS": ("CompressPackets", "bool"),
    "VS_CFG_ADVERTISE_SERVER": ("AdvertiseServer", "bool"),
    "VS_CFG_MAX_CLIENTS": ("MaxClients", "int"),
    "VS_CFG_MAX_CLIENTS_IN_QUEUE": ("MaxClientsInQueue", "int"),
    "VS_CFG_CLIENT_CONNECTION_TIMEOUT": ("ClientConnectionTimeout", "int"),
    # Gameplay settings
    "VS_CFG_SERVER_PASSWORD": ("Password", "string"),
    "VS_CFG_MAX_CHUNK_RADIUS": ("MaxChunkRadius", "int"),
    "VS_CFG_SERVER_LANGUAGE": ("ServerLanguage", "string"),
    "VS_CFG_ALLOW_PVP": ("AllowPvP", "bool"),
    "VS_CFG_ALLOW_FIRE_SPREAD": ("AllowFireSpread", "bool"),
    "VS_CFG_ALLOW_FALLING_BLOCKS": ("AllowFallingBlocks", "bool"),
    "VS_CFG_PASS_TIME_WHEN_EMPTY": ("PassTimeWhenEmpty", "bool"),
    "VS_CFG_ALLOW_CREATIVE_MODE": ("WorldConfig.AllowCreativeMode", "bool"),
    # Whitelist settings
    "VS_CFG_ONLY_WHITELISTED": ("OnlyWhitelisted", "bool"),
    "VS_CFG_WHITELIST_MODE": ("WhitelistMode", "int"),
    # Performance settings
    "VS_CFG_TICK_TIME": ("TickTime", "float"),
    "VS_CFG_SPAWN_CAP_PLAYER_SCALING": ("SpawnCapPlayerScaling", "float"),
    "VS_CFG_RANDOM_BLOCK_TICKS_PER_CHUNK": ("RandomBlockTicksPerChunk", "int"),
    "VS_CFG_BLOCK_TICK_CHUNK_RANGE": ("BlockTickChunkRange", "int"),
    "VS_CFG_MAX_MAIN_THREAD_BLOCK_TICKS": ("MaxMainThreadBlockTicks", "int"),
    "VS_CFG_BLOCK_TICK_INTERVAL": ("BlockTickInterval", "int"),
    # Security settings
    "VS_CFG_ANTIABUSE": ("AntiAbuse", "int"),
    "VS_CFG_VERIFY_PLAYER_AUTH": ("VerifyPlayerAuth", "bool"),
    "VS_CFG_LOGIN_FLOOD_PROTECTION": ("LoginFloodProtection", "bool"),
    "VS_CFG_TEMPORARY_IP_BLOCK_LIST": ("TemporaryIpBlockList", "bool"),
    "VS_CFG_CHAT_RATE_LIMIT_MS": ("ChatRateLimitMs", "int"),
    # Hosted mode (for game hosting services)
    "VS_CFG_HOSTED_MODE": ("HostedMode", "bool"),
    "VS_CFG_HOSTED_MODE_ALLOW_MODS": ("HostedModeAllowMods", "bool"),
    # World settings
    "VS_CFG_WORLD_NAME": ("WorldConfig.WorldName", "string"),
    "VS_CFG_WORLD_SEED": ("WorldConfig.Seed", "string"),
    "VS_CFG_WORLD_TYPE": ("WorldConfig.WorldType", "string"),
    "VS_CFG_PLAY_STYLE": ("WorldConfig.PlayStyle", "string"),
    # Map dimensions
    "VS_CFG_MAP_SIZE_X": ("MapSizeX", "int"),
    "VS_CFG_MAP_SIZE_Y": ("MapSizeY", "int"),
    "VS_CFG_MAP_SIZE_Z": ("MapSizeZ", "int"),
    # Logging and safety
    "VS_CFG_LOG_BLOCK_BREAK_PLACE": ("LogBlockBreakPlace", "bool"),
    "VS_CFG_CORRUPTION_PROTECTION": ("CorruptionProtection", "bool"),
    "VS_CFG_DIE_BELOW_DISK_SPACE_MB": ("DieBelowDiskSpaceMb", "int"),
    "VS_CFG_DIE_ABOVE_MEMORY_USAGE_MB": ("DieAboveMemoryUsageMb", "int"),
    "VS_CFG_DIE_ABOVE_ERROR_COUNT": ("DieAboveErrorCount", "int"),
}


def parse_env_value(value: str, value_type: Literal["string", "int", "bool", "float"]) -> Any:
    """Convert environment variable string to appropriate type.

    Args:
        value: The string value from the environment variable.
        value_type: The target type for conversion.

    Returns:
        The converted value.

    Raises:
        ValueError: If the value cannot be converted to the target type.

    Examples:
        >>> parse_env_value("42", "int")
        42
        >>> parse_env_value("true", "bool")
        True
        >>> parse_env_value("3.14", "float")
        3.14
        >>> parse_env_value("hello", "string")
        'hello'
    """
    if value_type == "string":
        return value

    if value_type == "bool":
        # Accept various truthy/falsy string representations
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError(
            f"Cannot convert '{value}' to bool. Use true/false, 1/0, yes/no, or on/off."
        )

    if value_type == "int":
        return int(value)

    if value_type == "float":
        return float(value)

    raise ValueError(f"Unknown value type: {value_type}")


def get_config_key_path(key: str) -> list[str]:
    """Split a dotted config key into path components.

    Args:
        key: The config key, possibly with dots for nested access.

    Returns:
        List of path components.

    Examples:
        >>> get_config_key_path("ServerName")
        ['ServerName']
        >>> get_config_key_path("WorldConfig.AllowCreativeMode")
        ['WorldConfig', 'AllowCreativeMode']
    """
    return key.split(".")
