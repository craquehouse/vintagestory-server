"""Tests for serverconfig template validity and structure."""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def template_path() -> Path:
    """Path to the serverconfig template file."""
    return (
        Path(__file__).parent.parent
        / "src"
        / "vintagestory_api"
        / "templates"
        / "serverconfig-template.json"
    )


@pytest.fixture
def template_data(template_path: Path) -> dict[str, Any]:
    """Load the serverconfig template as a dictionary."""
    return json.loads(template_path.read_text())


class TestTemplateValidity:
    """Tests that the template file is valid JSON."""

    def test_template_file_exists(self, template_path: Path) -> None:
        """Template file exists at expected location."""
        assert template_path.exists(), f"Template not found at {template_path}"

    def test_template_is_valid_json(self, template_path: Path) -> None:
        """Template file contains valid JSON."""
        try:
            json.loads(template_path.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"Template is not valid JSON: {e}")


class TestRequiredKeys:
    """Tests that required configuration keys are present."""

    @pytest.mark.parametrize(
        "key",
        [
            # Core server identity
            "ServerName",
            "ServerDescription",
            "WelcomeMessage",
            # Network settings
            "Port",
            "Ip",
            "Upnp",
            "MaxClients",
            "Password",
            "AdvertiseServer",
            # Gameplay settings
            "AllowPvP",
            "AllowFireSpread",
            "AllowFallingBlocks",
            "PassTimeWhenEmpty",
            "MaxChunkRadius",
            # Whitelist settings
            "OnlyWhitelisted",
            "WhitelistMode",
            # Performance settings
            "TickTime",
            "SpawnCapPlayerScaling",
            "RandomBlockTicksPerChunk",
            # Security settings
            "AntiAbuse",
            "VerifyPlayerAuth",
            "LoginFloodProtection",
            "TemporaryIpBlockList",
            # Paths and meta
            "ModPaths",
            "Roles",
            "DefaultRoleCode",
            "ConfigVersion",
            "WorldConfig",
        ],
    )
    def test_has_required_key(self, template_data: dict[str, Any], key: str) -> None:
        """Template contains required configuration key."""
        assert key in template_data, f"Missing required key: {key}"


class TestDefaultValues:
    """Tests that default values are sensible."""

    def test_server_name_is_generic(self, template_data: dict[str, Any]) -> None:
        """Server name is a generic default, not a specific server."""
        assert template_data["ServerName"] == "Vintage Story Server"

    def test_port_is_default(self, template_data: dict[str, Any]) -> None:
        """Port is the VintageStory default 42420."""
        assert template_data["Port"] == 42420

    def test_max_clients_is_reasonable(self, template_data: dict[str, Any]) -> None:
        """Max clients is a reasonable default (not 0, not thousands)."""
        max_clients = template_data["MaxClients"]
        assert 1 <= max_clients <= 100, f"MaxClients {max_clients} seems unreasonable"

    def test_password_is_null(self, template_data: dict[str, Any]) -> None:
        """Password defaults to null (no password required)."""
        assert template_data["Password"] is None

    def test_advertise_server_is_false(self, template_data: dict[str, Any]) -> None:
        """Server advertising is disabled by default (privacy)."""
        assert template_data["AdvertiseServer"] is False

    def test_pvp_enabled_by_default(self, template_data: dict[str, Any]) -> None:
        """PvP is enabled by default (standard gameplay)."""
        assert template_data["AllowPvP"] is True

    def test_server_identifier_is_null(self, template_data: dict[str, Any]) -> None:
        """ServerIdentifier is null (generated on first run)."""
        assert template_data["ServerIdentifier"] is None


class TestRoleStructure:
    """Tests that roles are properly defined."""

    def test_roles_is_list(self, template_data: dict[str, Any]) -> None:
        """Roles field is a list."""
        assert isinstance(template_data["Roles"], list)

    def test_has_admin_role(self, template_data: dict[str, Any]) -> None:
        """Template includes an admin role."""
        role_codes = [r["Code"] for r in template_data["Roles"]]
        assert "admin" in role_codes

    def test_has_player_role(self, template_data: dict[str, Any]) -> None:
        """Template includes a standard player role."""
        role_codes = [r["Code"] for r in template_data["Roles"]]
        assert "suplayer" in role_codes

    def test_default_role_exists(self, template_data: dict[str, Any]) -> None:
        """DefaultRoleCode references an existing role."""
        default_role = template_data["DefaultRoleCode"]
        role_codes = [r["Code"] for r in template_data["Roles"]]
        assert default_role in role_codes, (
            f"Default role '{default_role}' not in roles: {role_codes}"
        )


class TestWorldConfig:
    """Tests for WorldConfig section."""

    def test_world_config_exists(self, template_data: dict[str, Any]) -> None:
        """WorldConfig section exists."""
        assert "WorldConfig" in template_data
        assert isinstance(template_data["WorldConfig"], dict)

    def test_world_config_has_required_keys(self, template_data: dict[str, Any]) -> None:
        """WorldConfig has required keys."""
        world_config = template_data["WorldConfig"]
        required_keys = ["Seed", "SaveFileLocation", "WorldName", "PlayStyle", "WorldType"]
        for key in required_keys:
            assert key in world_config, f"WorldConfig missing key: {key}"

    def test_seed_is_null_for_random(self, template_data: dict[str, Any]) -> None:
        """Seed is null (random seed will be generated)."""
        assert template_data["WorldConfig"]["Seed"] is None


class TestModPaths:
    """Tests for ModPaths configuration."""

    def test_mod_paths_is_list(self, template_data: dict[str, Any]) -> None:
        """ModPaths is a list."""
        assert isinstance(template_data["ModPaths"], list)

    def test_mod_paths_not_empty(self, template_data: dict[str, Any]) -> None:
        """ModPaths has at least one entry."""
        assert len(template_data["ModPaths"]) > 0

    def test_mod_paths_includes_default_mods(self, template_data: dict[str, Any]) -> None:
        """ModPaths includes the default 'Mods' directory."""
        assert "Mods" in template_data["ModPaths"]
