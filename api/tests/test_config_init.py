"""Tests for config initialization and environment variable parsing."""

import pytest

from vintagestory_api.services.config_init import (
    ENV_VAR_MAP,
    get_config_key_path,
    parse_env_value,
)


class TestEnvVarMap:
    """Tests for the environment variable mapping."""

    def test_env_var_map_not_empty(self) -> None:
        """ENV_VAR_MAP contains mappings."""
        assert len(ENV_VAR_MAP) > 0

    def test_all_env_vars_start_with_vs_cfg(self) -> None:
        """All environment variable keys start with VS_CFG_."""
        for env_var in ENV_VAR_MAP:
            assert env_var.startswith("VS_CFG_"), f"Env var {env_var} doesn't start with VS_CFG_"

    def test_all_mappings_have_tuple_structure(self) -> None:
        """All mappings are (config_key, type) tuples."""
        for env_var, mapping in ENV_VAR_MAP.items():
            assert isinstance(mapping, tuple), f"Mapping for {env_var} is not a tuple"
            assert len(mapping) == 2, f"Mapping for {env_var} doesn't have 2 elements"
            config_key, value_type = mapping
            assert isinstance(config_key, str), f"Config key for {env_var} is not a string"
            assert value_type in ("string", "int", "bool", "float"), (
                f"Type for {env_var} is not valid: {value_type}"
            )

    @pytest.mark.parametrize(
        "env_var,expected_key",
        [
            ("VS_CFG_SERVER_NAME", "ServerName"),
            ("VS_CFG_SERVER_PORT", "Port"),
            ("VS_CFG_MAX_CLIENTS", "MaxClients"),
            ("VS_CFG_ALLOW_PVP", "AllowPvP"),
            ("VS_CFG_SERVER_PASSWORD", "Password"),
            ("VS_CFG_ADVERTISE_SERVER", "AdvertiseServer"),
            ("VS_CFG_ONLY_WHITELISTED", "OnlyWhitelisted"),
        ],
    )
    def test_has_expected_mapping(self, env_var: str, expected_key: str) -> None:
        """Common environment variables map to expected config keys."""
        assert env_var in ENV_VAR_MAP
        config_key, _ = ENV_VAR_MAP[env_var]
        assert config_key == expected_key

    @pytest.mark.parametrize(
        "env_var,expected_type",
        [
            ("VS_CFG_SERVER_NAME", "string"),
            ("VS_CFG_SERVER_PORT", "int"),
            ("VS_CFG_MAX_CLIENTS", "int"),
            ("VS_CFG_ALLOW_PVP", "bool"),
            ("VS_CFG_SPAWN_CAP_PLAYER_SCALING", "float"),
        ],
    )
    def test_has_expected_type(self, env_var: str, expected_type: str) -> None:
        """Environment variables have expected types."""
        assert env_var in ENV_VAR_MAP
        _, value_type = ENV_VAR_MAP[env_var]
        assert value_type == expected_type


class TestParseEnvValueString:
    """Tests for string parsing."""

    def test_simple_string(self) -> None:
        """Simple strings pass through unchanged."""
        assert parse_env_value("hello", "string") == "hello"

    def test_empty_string(self) -> None:
        """Empty strings pass through."""
        assert parse_env_value("", "string") == ""

    def test_string_with_spaces(self) -> None:
        """Strings with spaces are preserved."""
        assert parse_env_value("Hello World", "string") == "Hello World"

    def test_string_with_special_chars(self) -> None:
        """Strings with special characters are preserved."""
        assert parse_env_value("test@123!", "string") == "test@123!"


class TestParseEnvValueInt:
    """Tests for integer parsing."""

    def test_positive_int(self) -> None:
        """Positive integers are parsed correctly."""
        assert parse_env_value("42", "int") == 42

    def test_zero(self) -> None:
        """Zero is parsed correctly."""
        assert parse_env_value("0", "int") == 0

    def test_negative_int(self) -> None:
        """Negative integers are parsed correctly."""
        assert parse_env_value("-10", "int") == -10

    def test_large_int(self) -> None:
        """Large integers are parsed correctly."""
        assert parse_env_value("1000000", "int") == 1000000

    def test_invalid_int_raises(self) -> None:
        """Invalid integer strings raise ValueError."""
        with pytest.raises(ValueError):
            parse_env_value("not_a_number", "int")

    def test_float_string_raises_for_int(self) -> None:
        """Float strings raise ValueError when parsing as int."""
        with pytest.raises(ValueError):
            parse_env_value("3.14", "int")


class TestParseEnvValueBool:
    """Tests for boolean parsing."""

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"])
    def test_truthy_values(self, value: str) -> None:
        """Various truthy strings parse to True."""
        assert parse_env_value(value, "bool") is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "No", "off", "OFF"])
    def test_falsy_values(self, value: str) -> None:
        """Various falsy strings parse to False."""
        assert parse_env_value(value, "bool") is False

    def test_invalid_bool_raises(self) -> None:
        """Invalid boolean strings raise ValueError."""
        with pytest.raises(ValueError, match="Cannot convert"):
            parse_env_value("maybe", "bool")

    def test_empty_string_raises(self) -> None:
        """Empty string raises ValueError for bool."""
        with pytest.raises(ValueError, match="Cannot convert"):
            parse_env_value("", "bool")


class TestParseEnvValueFloat:
    """Tests for float parsing."""

    def test_positive_float(self) -> None:
        """Positive floats are parsed correctly."""
        assert parse_env_value("3.14", "float") == pytest.approx(3.14)

    def test_zero_float(self) -> None:
        """Zero float is parsed correctly."""
        assert parse_env_value("0.0", "float") == 0.0

    def test_negative_float(self) -> None:
        """Negative floats are parsed correctly."""
        assert parse_env_value("-2.5", "float") == pytest.approx(-2.5)

    def test_int_as_float(self) -> None:
        """Integer strings parse as floats."""
        assert parse_env_value("42", "float") == 42.0

    def test_scientific_notation(self) -> None:
        """Scientific notation is parsed correctly."""
        assert parse_env_value("1e3", "float") == pytest.approx(1000.0)

    def test_invalid_float_raises(self) -> None:
        """Invalid float strings raise ValueError."""
        with pytest.raises(ValueError):
            parse_env_value("not_a_float", "float")


class TestGetConfigKeyPath:
    """Tests for config key path splitting."""

    def test_simple_key(self) -> None:
        """Simple keys return single-element list."""
        assert get_config_key_path("ServerName") == ["ServerName"]

    def test_nested_key(self) -> None:
        """Dotted keys split into components."""
        assert get_config_key_path("WorldConfig.AllowCreativeMode") == [
            "WorldConfig",
            "AllowCreativeMode",
        ]

    def test_deeply_nested_key(self) -> None:
        """Multiple dots split correctly."""
        assert get_config_key_path("A.B.C.D") == ["A", "B", "C", "D"]

    def test_empty_string(self) -> None:
        """Empty string returns empty-string element."""
        assert get_config_key_path("") == [""]
