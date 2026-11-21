"""The typed read of serverconfig.json (Epic 25 ADR-1).

Story 25.1: serverconfig.json Is Read Through One Typed Model (FR344)

`ServerConfigFile` names the keys the manager reads, under the game's PascalCase names,
and allows every other key. It is for reading only: writes keep editing the parsed dict,
so a key the model does not name is never lost or reordered (ADR-1 decision 2).

A named key whose value has the wrong JSON type is read as missing, not as a failure
(ADR-1 decision 3): `from_raw` returns the keys it left out so the caller can log them.
"""

import copy
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError


class WorldConfigFile(BaseModel):
    """The `WorldConfig` object of serverconfig.json; only the keys the manager reads."""

    model_config = ConfigDict(extra="allow")

    save_file_location: StrictStr | None = Field(default=None, alias="SaveFileLocation")


class ServerConfigFile(BaseModel):
    """serverconfig.json as the manager reads it.

    Validated by alias only (Pydantic's default): the file never uses the Python names.
    Every field is optional, because a game version may not write every key.
    """

    model_config = ConfigDict(extra="allow")

    # The managed settings (game_config.LIVE_SETTINGS)
    server_name: StrictStr | None = Field(default=None, alias="ServerName")
    server_description: StrictStr | None = Field(default=None, alias="ServerDescription")
    welcome_message: StrictStr | None = Field(default=None, alias="WelcomeMessage")
    max_clients: StrictInt | None = Field(default=None, alias="MaxClients")
    max_chunk_radius: StrictInt | None = Field(default=None, alias="MaxChunkRadius")
    password: StrictStr | None = Field(default=None, alias="Password")
    allow_pvp: StrictBool | None = Field(default=None, alias="AllowPvP")
    allow_fire_spread: StrictBool | None = Field(default=None, alias="AllowFireSpread")
    allow_falling_blocks: StrictBool | None = Field(default=None, alias="AllowFallingBlocks")
    # Story 25.3 moves EntitySpawning out of the file reads (ADR-6)
    entity_spawning: StrictBool | None = Field(default=None, alias="EntitySpawning")
    pass_time_when_empty: StrictBool | None = Field(default=None, alias="PassTimeWhenEmpty")
    upnp: StrictBool | None = Field(default=None, alias="Upnp")
    advertise_server: StrictBool | None = Field(default=None, alias="AdvertiseServer")
    port: StrictInt | None = Field(default=None, alias="Port")
    ip: StrictStr | None = Field(default=None, alias="Ip")

    # Paths (ADR-2)
    mod_paths: list[StrictStr] | None = Field(default=None, alias="ModPaths")
    world_config: WorldConfigFile | None = Field(default=None, alias="WorldConfig")

    # Whitelist, for Epic 27
    only_whitelisted: StrictBool | None = Field(default=None, alias="OnlyWhitelisted")
    whitelist_mode: StrictInt | None = Field(default=None, alias="WhitelistMode")

    def value_of(self, key: str) -> Any:
        """The value of a named key by its serverconfig.json name, e.g. "MaxClients".

        Raises:
            KeyError: If the model does not name the key.
        """
        name = _FIELD_BY_ALIAS[key]
        return getattr(self, name)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ServerConfigRead:
        """Validate parsed serverconfig.json, reading a wrong-typed named key as missing.

        `raw` is not changed. The returned `invalid_keys` are dotted names
        ("MaxClients", "WorldConfig.SaveFileLocation").
        """
        data = raw
        invalid: list[str] = []
        for _ in range(_MAX_PASSES):
            try:
                return ServerConfigRead(cls.model_validate(data), tuple(invalid))
            except ValidationError as e:
                if data is raw:
                    data = copy.deepcopy(raw)
                removed = _remove_invalid(data, e)
                if not removed:
                    raise
                invalid.extend(removed)
        # Each pass removes at least one key, and there are few named keys
        return ServerConfigRead(cls.model_validate(data), tuple(invalid))


_MAX_PASSES = 4

_FIELD_BY_ALIAS: dict[str, str] = {
    field.alias: name for name, field in ServerConfigFile.model_fields.items() if field.alias
}


@dataclass(frozen=True)
class ServerConfigRead:
    """The model and the named keys that were read as missing because of their type."""

    model: ServerConfigFile
    invalid_keys: tuple[str, ...]


def _remove_invalid(data: dict[str, Any], error: ValidationError) -> list[str]:
    """Delete the keys a validation error points at; return their dotted names."""
    removed: list[str] = []
    for item in error.errors():
        loc = item["loc"]
        if not loc or not isinstance(loc[0], str):
            continue
        top = loc[0]
        if (
            top == "WorldConfig"
            and len(loc) > 1
            and isinstance(loc[1], str)
            and isinstance(data.get("WorldConfig"), dict)
        ):
            world: dict[str, Any] = data["WorldConfig"]
            if loc[1] in world:
                del world[loc[1]]
                removed.append(f"WorldConfig.{loc[1]}")
            continue
        if top in data:
            del data[top]
            removed.append(top)
    return removed


# ==============================================================================
# The path check (Story 25.1, Epic 25 ADR-2)
# ==============================================================================

PathStatus = Literal[
    "ok",
    "missing",
    "not_a_directory",
    "not_a_file",
    "not_readable",
    "not_writable",
    "not_installed",
    "not_created_yet",
    "invalid",
]
"""How a path in serverconfig.json stands (ADR-2 decision 2)."""

PROBLEM_STATUSES: frozenset[str] = frozenset(
    {"missing", "not_a_directory", "not_a_file", "not_readable", "not_writable", "invalid"}
)
"""Statuses Game Settings warns about. `not_installed` and `not_created_yet` are expected on
a fresh install, so they are not problems (ADR-2 decision 2)."""


class PathEntry(BaseModel):
    """One `ModPaths` entry, or the save file."""

    given: str | None
    """The value in serverconfig.json; None for a null save location or invalid ModPaths."""
    resolved: str | None
    """The path the game uses; None when `given` cannot be resolved (invalid ModPaths)."""
    status: PathStatus
    problem: bool


class PathCheck(BaseModel):
    """The response of GET /config/game/paths."""

    mod_paths: list[PathEntry]
    save_file: PathEntry
    manager_mods_folder: str
    """The folder the manager installs mods into, `{serverdata}/Mods` (Story 25.2)."""
    manager_mods_folder_listed: bool
