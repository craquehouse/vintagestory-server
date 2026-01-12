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


class TestFullVersionListCache:
    """Tests for full version list caching (Story 13.1)."""

    def test_get_versions_empty_initially(self):
        """get_versions should return empty list when cache is empty."""
        cache = LatestVersionsCache()

        assert cache.get_versions("stable") == []
        assert cache.get_versions("unstable") == []

    def test_set_and_get_stable_versions(self):
        """set_versions should store and get_versions should retrieve stable versions."""
        cache = LatestVersionsCache()
        versions = [
            {"version": "1.21.3", "channel": "stable", "is_latest": True},
            {"version": "1.21.2", "channel": "stable", "is_latest": False},
        ]

        cache.set_versions("stable", versions)
        result = cache.get_versions("stable")

        assert result == versions
        # Should not affect unstable
        assert cache.get_versions("unstable") == []

    def test_set_and_get_unstable_versions(self):
        """set_versions should store and get_versions should retrieve unstable versions."""
        cache = LatestVersionsCache()
        versions = [
            {"version": "1.22.0-pre.1", "channel": "unstable", "is_latest": True},
        ]

        cache.set_versions("unstable", versions)
        result = cache.get_versions("unstable")

        assert result == versions
        # Should not affect stable
        assert cache.get_versions("stable") == []

    def test_get_all_versions_empty_initially(self):
        """get_all_versions should return empty dict when cache is empty."""
        cache = LatestVersionsCache()

        result = cache.get_all_versions()

        assert result == {"stable": [], "unstable": []}

    def test_get_all_versions_returns_both_channels(self):
        """get_all_versions should return versions from both channels."""
        cache = LatestVersionsCache()
        stable = [{"version": "1.21.3", "channel": "stable", "is_latest": True}]
        unstable = [{"version": "1.22.0-pre.1", "channel": "unstable", "is_latest": True}]

        cache.set_versions("stable", stable)
        cache.set_versions("unstable", unstable)
        result = cache.get_all_versions()

        assert result == {"stable": stable, "unstable": unstable}

    def test_set_versions_updates_cached_at(self):
        """set_versions should update cached_at timestamp."""
        cache = LatestVersionsCache()

        # Initially None
        assert cache.cached_at is None

        cache.set_versions("stable", [{"version": "1.21.3"}])

        assert cache.cached_at is not None

    def test_set_versions_overwrites_previous(self):
        """set_versions should replace previous versions for the channel."""
        cache = LatestVersionsCache()
        old_versions = [{"version": "1.21.2", "channel": "stable"}]
        new_versions = [{"version": "1.21.3", "channel": "stable"}]

        cache.set_versions("stable", old_versions)
        cache.set_versions("stable", new_versions)
        result = cache.get_versions("stable")

        assert result == new_versions

    def test_clear_resets_full_version_lists(self):
        """clear should reset full version lists to empty."""
        cache = LatestVersionsCache()
        cache.set_versions("stable", [{"version": "1.21.3"}])
        cache.set_versions("unstable", [{"version": "1.22.0-pre.1"}])

        cache.clear()

        assert cache.get_versions("stable") == []
        assert cache.get_versions("unstable") == []
        assert cache.cached_at is None

    def test_has_cached_versions_false_when_empty(self):
        """has_cached_versions should return False when no versions cached."""
        cache = LatestVersionsCache()

        assert cache.has_cached_versions() is False

    def test_has_cached_versions_true_when_populated(self):
        """has_cached_versions should return True when versions are cached."""
        cache = LatestVersionsCache()
        cache.set_versions("stable", [{"version": "1.21.3"}])

        assert cache.has_cached_versions() is True

    def test_invalid_channel_returns_empty_list(self):
        """get_versions with invalid channel should return empty list."""
        cache = LatestVersionsCache()

        assert cache.get_versions("invalid") == []
