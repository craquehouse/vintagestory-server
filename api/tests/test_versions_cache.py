"""Tests for LatestVersionsCache service.

Story 8.2: Server Versions Check Job

Tests cover:
- Initial empty cache state
- Setting and getting versions
- Partial updates (stable only, unstable only)
- Timestamp tracking
- Singleton accessor behavior
- Cache clearing
"""

import pytest

from vintagestory_api.services.versions_cache import (
    LatestVersions,
    LatestVersionsCache,
    get_versions_cache,
    reset_versions_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the singleton cache before and after each test."""
    reset_versions_cache()
    yield
    reset_versions_cache()


class TestLatestVersions:
    """Tests for LatestVersions dataclass."""

    def test_default_values(self):
        """LatestVersions should have None for all fields by default."""
        versions = LatestVersions()

        assert versions.stable_version is None
        assert versions.unstable_version is None
        assert versions.last_checked is None

    def test_with_values(self):
        """LatestVersions should accept provided values."""
        versions = LatestVersions(
            stable_version="1.21.3",
            unstable_version="1.22.0-pre.1",
        )

        assert versions.stable_version == "1.21.3"
        assert versions.unstable_version == "1.22.0-pre.1"


class TestLatestVersionsCache:
    """Tests for LatestVersionsCache class."""

    def test_initial_empty_state(self):
        """New cache should have empty LatestVersions."""
        cache = LatestVersionsCache()
        versions = cache.get_latest_versions()

        assert versions.stable_version is None
        assert versions.unstable_version is None
        assert versions.last_checked is None

    def test_set_both_versions(self):
        """Setting both versions should update both fields."""
        cache = LatestVersionsCache()

        cache.set_latest_versions(stable="1.21.3", unstable="1.22.0-pre.1")
        versions = cache.get_latest_versions()

        assert versions.stable_version == "1.21.3"
        assert versions.unstable_version == "1.22.0-pre.1"
        assert versions.last_checked is not None

    def test_set_stable_only(self):
        """Setting only stable should not affect unstable."""
        cache = LatestVersionsCache()
        cache.set_latest_versions(stable="1.21.2", unstable="1.22.0-pre.1")

        # Now update only stable
        cache.set_latest_versions(stable="1.21.3")
        versions = cache.get_latest_versions()

        assert versions.stable_version == "1.21.3"
        assert versions.unstable_version == "1.22.0-pre.1"  # Unchanged

    def test_set_unstable_only(self):
        """Setting only unstable should not affect stable."""
        cache = LatestVersionsCache()
        cache.set_latest_versions(stable="1.21.3", unstable="1.22.0-pre.1")

        # Now update only unstable
        cache.set_latest_versions(unstable="1.22.0-pre.2")
        versions = cache.get_latest_versions()

        assert versions.stable_version == "1.21.3"  # Unchanged
        assert versions.unstable_version == "1.22.0-pre.2"

    def test_timestamp_updated_on_set(self):
        """Timestamp should be updated when versions are set."""
        cache = LatestVersionsCache()

        # Initially no timestamp
        assert cache.get_latest_versions().last_checked is None

        # After setting a version
        cache.set_latest_versions(stable="1.21.3")
        first_check = cache.get_latest_versions().last_checked
        assert first_check is not None

        # After another update, timestamp should be updated
        cache.set_latest_versions(unstable="1.22.0-pre.1")
        second_check = cache.get_latest_versions().last_checked
        assert second_check is not None
        assert second_check >= first_check

    def test_timestamp_not_updated_with_no_values(self):
        """Timestamp should not update if no values are provided."""
        cache = LatestVersionsCache()

        # Set initial version
        cache.set_latest_versions(stable="1.21.3")
        first_check = cache.get_latest_versions().last_checked

        # Call with no values (both None)
        cache.set_latest_versions()
        second_check = cache.get_latest_versions().last_checked

        assert second_check == first_check

    def test_clear_resets_cache(self):
        """Clear should reset all values to None."""
        cache = LatestVersionsCache()
        cache.set_latest_versions(stable="1.21.3", unstable="1.22.0-pre.1")

        cache.clear()
        versions = cache.get_latest_versions()

        assert versions.stable_version is None
        assert versions.unstable_version is None
        assert versions.last_checked is None


class TestVersionsCacheSingleton:
    """Tests for singleton accessor functions."""

    def test_get_versions_cache_returns_instance(self):
        """get_versions_cache should return a LatestVersionsCache instance."""
        cache = get_versions_cache()

        assert isinstance(cache, LatestVersionsCache)

    def test_get_versions_cache_returns_same_instance(self):
        """Multiple calls should return the same instance."""
        cache1 = get_versions_cache()
        cache2 = get_versions_cache()

        assert cache1 is cache2

    def test_reset_creates_new_instance(self):
        """reset_versions_cache should create a fresh instance."""
        cache1 = get_versions_cache()
        cache1.set_latest_versions(stable="1.21.3")

        reset_versions_cache()
        cache2 = get_versions_cache()

        # Should be a different instance
        assert cache2 is not cache1
        # And should be empty
        assert cache2.get_latest_versions().stable_version is None

    def test_singleton_state_persists(self):
        """State set on singleton should persist across get calls."""
        cache1 = get_versions_cache()
        cache1.set_latest_versions(stable="1.21.3")

        cache2 = get_versions_cache()
        versions = cache2.get_latest_versions()

        assert versions.stable_version == "1.21.3"
