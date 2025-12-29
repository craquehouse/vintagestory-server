"""Tests for version validation and path security."""

import pytest

from vintagestory_api.config import Settings
from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false


class TestVersionValidation:
    """Tests for version format validation (Subtask 1.4)."""

    def test_valid_release_version(self, test_settings: Settings) -> None:
        """Valid release version format (X.Y.Z) passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3") is True

    def test_valid_prerelease_version(self, test_settings: Settings) -> None:
        """Valid pre-release version format (X.Y.Z-pre.N) passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-pre.1") is True

    def test_valid_rc_version(self, test_settings: Settings) -> None:
        """Valid RC version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-rc.2") is True

    def test_valid_rc_version_without_number(self, test_settings: Settings) -> None:
        """Valid RC version without suffix number passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-rc") is True

    def test_valid_alpha_version(self, test_settings: Settings) -> None:
        """Valid alpha version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-alpha") is True
        assert service.validate_version("1.22.0-alpha.1") is True

    def test_valid_beta_version(self, test_settings: Settings) -> None:
        """Valid beta version format passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.22.0-beta.3") is True

    def test_valid_version_with_build_metadata(self, test_settings: Settings) -> None:
        """Valid version with build metadata passes validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3+build.123") is True
        assert service.validate_version("1.22.0-pre.1+build.456") is True

    def test_invalid_version_missing_patch(self, test_settings: Settings) -> None:
        """Version without patch number fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21") is False

    def test_invalid_version_extra_part(self, test_settings: Settings) -> None:
        """Version with extra parts fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.21.3.4") is False

    def test_invalid_version_text(self, test_settings: Settings) -> None:
        """Version with random text fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("latest") is False

    def test_invalid_version_empty(self, test_settings: Settings) -> None:
        """Empty version string fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("") is False

    def test_invalid_version_letters_in_numbers(self, test_settings: Settings) -> None:
        """Version with letters in numeric parts fails validation."""
        service = ServerService(test_settings)
        assert service.validate_version("1.2a.3") is False


class TestPathTraversalProtection:
    """Tests for path traversal attack prevention (Security)."""

    def test_safe_path_normal_filename(self, test_settings: Settings) -> None:
        """Normal filename returns valid path within base dir."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        result = service._safe_path(test_settings.server_dir, "test.tar.gz")

        # Use resolve() on expected path too (handles symlinks like /var -> /private/var)
        expected = (test_settings.server_dir / "test.tar.gz").resolve()
        assert result == expected

    def test_safe_path_blocks_parent_traversal(self, test_settings: Settings) -> None:
        """Path with .. traversal is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, "../../../etc/passwd")

    def test_safe_path_blocks_absolute_path(self, test_settings: Settings) -> None:
        """Absolute path is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, "/etc/passwd")

    def test_safe_path_blocks_version_with_traversal(self, test_settings: Settings) -> None:
        """Version string containing traversal is rejected."""
        test_settings.server_dir.mkdir(parents=True, exist_ok=True)
        service = ServerService(test_settings)

        malicious_version = "1.21.3/../../../etc/passwd"
        filename = f"vs_server_linux-x64_{malicious_version}.tar.gz"

        with pytest.raises(ValueError, match="Path traversal detected"):
            service._safe_path(test_settings.server_dir, filename)
