"""Tests for cache eviction service."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from vintagestory_api.services.cache_eviction import CacheEvictionService


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory structure."""
    mods_cache = tmp_path / "mods"
    mods_cache.mkdir(parents=True)
    return tmp_path


def create_test_file(cache_dir: Path, name: str, size_bytes: int) -> Path:
    """Create a test file with specified size in the mods cache."""
    mods_cache = cache_dir / "mods"
    mods_cache.mkdir(parents=True, exist_ok=True)
    file_path = mods_cache / name
    file_path.write_bytes(b"x" * size_bytes)
    return file_path


class TestCacheEvictionServiceInit:
    """Tests for CacheEvictionService initialization."""

    def test_init_with_defaults(self, cache_dir: Path) -> None:
        """Test initialization with default values."""
        service = CacheEvictionService(cache_dir=cache_dir)
        assert service.cache_dir == cache_dir
        assert service.max_size_bytes == 500 * 1024 * 1024  # 500MB in bytes
        assert service.eviction_enabled is True

    def test_init_with_custom_size(self, cache_dir: Path) -> None:
        """Test initialization with custom max size."""
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        assert service.max_size_bytes == 100 * 1024 * 1024

    def test_init_with_zero_disables_eviction(self, cache_dir: Path) -> None:
        """Test that max_size_mb=0 disables eviction."""
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=0)
        assert service.eviction_enabled is False
        assert service.max_size_bytes == 0


class TestCacheStats:
    """Tests for cache statistics."""

    def test_empty_cache_stats(self, cache_dir: Path) -> None:
        """Test stats for empty cache."""
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        stats = service.get_cache_stats()
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["max_size_bytes"] == 100 * 1024 * 1024

    def test_cache_stats_with_files(self, cache_dir: Path) -> None:
        """Test stats with files in cache."""
        create_test_file(cache_dir, "mod1.zip", 1000)
        create_test_file(cache_dir, "mod2.zip", 2000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        stats = service.get_cache_stats()

        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 3000

    def test_get_cache_size(self, cache_dir: Path) -> None:
        """Test getting total cache size."""
        create_test_file(cache_dir, "mod1.zip", 5000)
        create_test_file(cache_dir, "mod2.zip", 3000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        assert service.get_cache_size() == 8000


class TestEviction:
    """Tests for cache eviction logic."""

    def test_no_eviction_when_under_limit(self, cache_dir: Path) -> None:
        """Test no eviction when cache is under size limit."""
        # Create 100KB of files with 200KB limit
        create_test_file(cache_dir, "mod1.zip", 50 * 1024)
        create_test_file(cache_dir, "mod2.zip", 50 * 1024)

        # 200KB limit in bytes = 200 * 1024
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)  # 1MB limit
        result = service.evict_if_needed()

        assert result.files_evicted == 0
        assert result.bytes_freed == 0
        assert result.files_remaining == 2

    def test_eviction_when_over_limit(self, cache_dir: Path) -> None:
        """Test eviction when cache exceeds size limit."""
        # Create files with different access times
        file1 = create_test_file(cache_dir, "old_mod.zip", 600 * 1024)  # 600KB
        time.sleep(0.01)  # Ensure different access times
        file2 = create_test_file(cache_dir, "new_mod.zip", 600 * 1024)  # 600KB

        # Touch file2 to make it newer
        file2.read_bytes()  # Updates access time

        # 1MB limit = 1024 * 1024 bytes, cache has 1.2MB
        # Should evict oldest (old_mod.zip) to get under limit
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)
        result = service.evict_if_needed()

        assert result.files_evicted >= 1
        assert result.bytes_freed >= 600 * 1024
        assert not file1.exists()  # Oldest should be evicted
        assert file2.exists()  # Newest should remain

    def test_eviction_disabled_when_max_size_zero(self, cache_dir: Path) -> None:
        """Test that eviction is skipped when disabled."""
        create_test_file(cache_dir, "mod1.zip", 1000 * 1024)  # 1MB
        create_test_file(cache_dir, "mod2.zip", 1000 * 1024)  # 1MB

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=0)
        result = service.evict_if_needed()

        assert result.files_evicted == 0
        assert result.files_remaining == 2

    def test_eviction_lru_order(self, cache_dir: Path) -> None:
        """Test that files are evicted in LRU order (oldest first)."""
        # Create files and set access times
        files: list[Path] = []
        for i in range(4):
            f = create_test_file(cache_dir, f"mod{i}.zip", 300 * 1024)  # 300KB each
            files.append(f)
            time.sleep(0.01)  # Ensure different timestamps

        # Access files 2 and 3 to make them newer
        files[3].read_bytes()
        files[2].read_bytes()

        # 1MB limit, cache has 1.2MB - need to evict ~200KB+ (at least 1 file)
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)
        result = service.evict_if_needed()

        # Files 0 and 1 are oldest (accessed earlier), should be evicted first
        assert result.files_evicted >= 1
        # Newest files should remain
        assert files[3].exists()
        assert files[2].exists()


class TestEvictAll:
    """Tests for clearing entire cache."""

    def test_evict_all(self, cache_dir: Path) -> None:
        """Test evicting all files from cache."""
        create_test_file(cache_dir, "mod1.zip", 1000)
        create_test_file(cache_dir, "mod2.zip", 2000)
        create_test_file(cache_dir, "mod3.zip", 3000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        result = service.evict_all()

        assert result.files_evicted == 3
        assert result.bytes_freed == 6000
        assert result.files_remaining == 0
        assert result.bytes_remaining == 0

    def test_evict_all_empty_cache(self, cache_dir: Path) -> None:
        """Test evicting from empty cache."""
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        result = service.evict_all()

        assert result.files_evicted == 0
        assert result.bytes_freed == 0


class TestFilePatterns:
    """Tests for file pattern matching."""

    def test_only_zip_files_considered(self, cache_dir: Path) -> None:
        """Test that only .zip files are considered for eviction."""
        create_test_file(cache_dir, "mod1.zip", 1000)
        create_test_file(cache_dir, "readme.txt", 500)
        create_test_file(cache_dir, "data.json", 300)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        stats = service.get_cache_stats()

        # Only the .zip file should be counted
        assert stats["file_count"] == 1
        assert stats["total_size_bytes"] == 1000

    def test_cs_files_also_considered(self, cache_dir: Path) -> None:
        """Test that .cs files are also considered (source mods)."""
        create_test_file(cache_dir, "mod1.zip", 1000)
        create_test_file(cache_dir, "source_mod.cs", 500)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        stats = service.get_cache_stats()

        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 1500


class TestEdgeCases:
    """Tests for edge cases."""

    def test_nonexistent_cache_dir(self, tmp_path: Path) -> None:
        """Test with nonexistent cache directory."""
        nonexistent = tmp_path / "nonexistent"
        service = CacheEvictionService(cache_dir=nonexistent, max_size_mb=100)

        stats = service.get_cache_stats()
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0

        result = service.evict_if_needed()
        assert result.files_evicted == 0

    def test_empty_mods_subdir(self, cache_dir: Path) -> None:
        """Test with existing cache_dir but no mods subdirectory."""
        # Remove the mods directory that fixture creates
        mods_dir = cache_dir / "mods"
        if mods_dir.exists():
            mods_dir.rmdir()

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        stats = service.get_cache_stats()

        assert stats["file_count"] == 0


class TestLogging:
    """Tests for log event verification (FR46).

    Note: These tests verify log events are emitted correctly by checking
    the captured stdout output, since structlog logger caching makes
    processor-based capture unreliable across tests.
    """

    def test_cache_evicted_event_emitted(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that cache_evicted log events are emitted when files are evicted."""
        # Create files that will exceed limit
        create_test_file(cache_dir, "old_mod.zip", 600 * 1024)  # 600KB
        time.sleep(0.01)
        create_test_file(cache_dir, "new_mod.zip", 600 * 1024)  # 600KB

        # 1MB limit, cache has 1.2MB - should evict oldest
        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)
        service.evict_if_needed()

        # Verify cache_evicted event was logged (check captured output)
        captured = capsys.readouterr()
        assert "cache_evicted" in captured.out
        assert "size_limit" in captured.out

    def test_cache_eviction_complete_event(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that cache_eviction_complete summary event is emitted."""
        create_test_file(cache_dir, "mod1.zip", 600 * 1024)
        create_test_file(cache_dir, "mod2.zip", 600 * 1024)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)
        service.evict_if_needed()

        # Verify summary event was logged
        captured = capsys.readouterr()
        assert "cache_eviction_complete" in captured.out
        assert "files_evicted" in captured.out
        assert "bytes_freed" in captured.out

    def test_evict_all_uses_manual_clear_reason(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that evict_all uses reason='manual_clear'."""
        create_test_file(cache_dir, "mod1.zip", 1000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)
        service.evict_all()

        # Verify manual_clear reason was used
        captured = capsys.readouterr()
        assert "cache_evicted" in captured.out
        assert "manual_clear" in captured.out

    def test_cache_eviction_failed_on_permission_error(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that cache_eviction_failed is logged when file deletion fails."""
        create_test_file(cache_dir, "protected_mod.zip", 600 * 1024)
        create_test_file(cache_dir, "other_mod.zip", 600 * 1024)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=1)

        # Mock unlink to fail for the first file
        original_unlink = Path.unlink

        def mock_unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == "protected_mod.zip":
                raise OSError("Permission denied")
            original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", mock_unlink):
            service.evict_if_needed()

        # Verify failure event was logged
        captured = capsys.readouterr()
        assert "cache_eviction_failed" in captured.out
        assert "Permission denied" in captured.out

    def test_evict_all_handles_deletion_failure(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that evict_all handles file deletion failures gracefully."""
        create_test_file(cache_dir, "protected_mod.zip", 1000)
        create_test_file(cache_dir, "normal_mod.zip", 2000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)

        # Mock unlink to fail for the protected file
        original_unlink = Path.unlink

        def mock_unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == "protected_mod.zip":
                raise OSError("Permission denied")
            original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", mock_unlink):
            result = service.evict_all()

        # Verify that one file was evicted and one failed
        assert result.files_evicted == 1  # Only normal_mod.zip was deleted
        assert result.bytes_freed == 2000  # Only normal_mod.zip size
        # Protected file remains, so files_remaining should account for it
        assert result.files_remaining == 1
        assert result.bytes_remaining == 1000

        # Verify failure event was logged
        captured = capsys.readouterr()
        assert "cache_eviction_failed" in captured.out
        assert "Permission denied" in captured.out

    def test_evict_all_oserror_with_file_not_found(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test evict_all handles OSError when file vanishes during deletion."""
        create_test_file(cache_dir, "vanishing.zip", 1500)
        create_test_file(cache_dir, "stable.zip", 500)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)

        # Mock unlink to raise FileNotFoundError for vanishing file (lines 260-261)
        original_unlink = Path.unlink

        def mock_unlink(self: Path, missing_ok: bool = False) -> None:
            if self.name == "vanishing.zip":
                raise OSError("[Errno 2] No such file or directory")
            original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", mock_unlink):
            result = service.evict_all()

        # Only stable.zip should be successfully deleted
        assert result.files_evicted == 1
        assert result.bytes_freed == 500

        # Verify the OSError was logged (covers lines 260-261)
        captured = capsys.readouterr()
        assert "cache_eviction_failed" in captured.out
        assert "No such file or directory" in captured.out

    def test_cache_file_stat_failed_logged(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that cache_file_stat_failed is logged when stat() fails."""
        # Create files - one will fail stat, one will succeed
        create_test_file(cache_dir, "normal_mod.zip", 1000)
        create_test_file(cache_dir, "good_mod.zip", 500)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)

        # Track which Path objects have been checked with is_file
        # so we can fail on the second call (the actual stat() call)
        checked_paths = set()
        original_stat = Path.stat

        def mock_stat(self: Path, *, follow_symlinks: bool = True) -> object:
            path_str = str(self)
            # If we've already successfully called stat on this path (from is_file),
            # then fail on the next call (the explicit stat() call)
            if self.name == "normal_mod.zip" and path_str in checked_paths:
                raise OSError("File stat failed")
            # Mark this path as checked and allow the call to succeed
            checked_paths.add(path_str)
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", mock_stat):
            stats = service.get_cache_stats()

        # One file should be skipped, one should succeed
        assert stats["file_count"] == 1
        assert stats["total_size_bytes"] == 500

        # Verify warning was logged
        captured = capsys.readouterr()
        assert "cache_file_stat_failed" in captured.out
        assert "File stat failed" in captured.out

    def test_stat_error_with_permission_denied(
        self, cache_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test OSError handling during stat() with PermissionError scenario."""
        # Create files to test stat failure
        create_test_file(cache_dir, "restricted.zip", 2000)
        create_test_file(cache_dir, "accessible.zip", 1000)

        service = CacheEvictionService(cache_dir=cache_dir, max_size_mb=100)

        # Mock stat to raise PermissionError for restricted file
        call_count = {}
        original_stat = Path.stat

        def mock_stat(self: Path, *, follow_symlinks: bool = True) -> object:
            # Count calls per path
            path_str = str(self)
            call_count[path_str] = call_count.get(path_str, 0) + 1

            # Fail on the explicit stat() call (second call) for restricted.zip
            if self.name == "restricted.zip" and call_count[path_str] > 1:
                raise OSError("[Errno 13] Permission denied")
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", mock_stat):
            stats = service.get_cache_stats()

        # Only accessible.zip should be counted (lines 120-121 covered)
        assert stats["file_count"] == 1
        assert stats["total_size_bytes"] == 1000

        # Verify error was logged
        captured = capsys.readouterr()
        assert "cache_file_stat_failed" in captured.out
        assert "Permission denied" in captured.out
