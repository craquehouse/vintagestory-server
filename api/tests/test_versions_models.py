"""Tests for versions API models.

Story 13.1: Server Versions API

Tests cover:
- VersionListResponse model serialization
- VersionDetailResponse model serialization
- Cache indicator fields
"""

import datetime

from vintagestory_api.models.server import VersionInfo
from vintagestory_api.models.versions import (
    VersionDetailResponse,
    VersionListResponse,
)


class TestVersionListResponse:
    """Tests for VersionListResponse model."""

    def test_serialize_empty_list(self):
        """Empty versions list should serialize correctly."""
        response = VersionListResponse(
            versions=[],
            total=0,
            cached=False,
            cached_at=None,
        )

        data = response.model_dump()

        assert data["versions"] == []
        assert data["total"] == 0
        assert data["cached"] is False
        assert data["cached_at"] is None

    def test_serialize_with_versions(self):
        """Versions list with items should serialize correctly."""
        version = VersionInfo(
            version="1.21.3",
            filename="vs_server_linux-x64_1.21.3.tar.gz",
            filesize="40.2 MB",
            md5="abc123",
            cdn_url="https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.3.tar.gz",
            local_url="https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.3.tar.gz",
            is_latest=True,
            channel="stable",
        )

        response = VersionListResponse(
            versions=[version],
            total=1,
            cached=False,
            cached_at=None,
        )

        data = response.model_dump()

        assert len(data["versions"]) == 1
        assert data["versions"][0]["version"] == "1.21.3"
        assert data["versions"][0]["channel"] == "stable"
        assert data["versions"][0]["is_latest"] is True
        assert data["total"] == 1

    def test_serialize_with_cache_indicator(self):
        """Cached response should include cached_at timestamp."""
        cached_time = datetime.datetime(2026, 1, 11, 12, 0, 0, tzinfo=datetime.UTC)

        response = VersionListResponse(
            versions=[],
            total=0,
            cached=True,
            cached_at=cached_time,
        )

        data = response.model_dump()

        assert data["cached"] is True
        assert data["cached_at"] == cached_time

    def test_serialize_multiple_versions(self):
        """Multiple versions should serialize correctly."""
        versions = [
            VersionInfo(
                version="1.21.3",
                filename="vs_server_linux-x64_1.21.3.tar.gz",
                filesize="40.2 MB",
                md5="abc123",
                cdn_url="https://cdn.vintagestory.at/1",
                local_url="https://vintagestory.at/1",
                is_latest=True,
                channel="stable",
            ),
            VersionInfo(
                version="1.21.2",
                filename="vs_server_linux-x64_1.21.2.tar.gz",
                filesize="40.1 MB",
                md5="def456",
                cdn_url="https://cdn.vintagestory.at/2",
                local_url="https://vintagestory.at/2",
                is_latest=False,
                channel="stable",
            ),
        ]

        response = VersionListResponse(
            versions=versions,
            total=2,
            cached=False,
            cached_at=None,
        )

        data = response.model_dump()

        assert len(data["versions"]) == 2
        assert data["total"] == 2


class TestVersionDetailResponse:
    """Tests for VersionDetailResponse model."""

    def test_serialize_version_detail(self):
        """Version detail should serialize all fields."""
        version = VersionInfo(
            version="1.21.3",
            filename="vs_server_linux-x64_1.21.3.tar.gz",
            filesize="40.2 MB",
            md5="abc123def456",
            cdn_url="https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.3.tar.gz",
            local_url="https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.3.tar.gz",
            is_latest=True,
            channel="stable",
        )

        response = VersionDetailResponse(
            version=version,
            cached=False,
            cached_at=None,
        )

        data = response.model_dump()

        assert data["version"]["version"] == "1.21.3"
        assert data["version"]["filename"] == "vs_server_linux-x64_1.21.3.tar.gz"
        assert data["version"]["filesize"] == "40.2 MB"
        assert data["version"]["md5"] == "abc123def456"
        assert data["version"]["cdn_url"].startswith("https://cdn.vintagestory.at")
        assert data["version"]["is_latest"] is True
        assert data["version"]["channel"] == "stable"
        assert data["cached"] is False
        assert data["cached_at"] is None

    def test_serialize_with_cache_info(self):
        """Cached version detail should include timestamp."""
        version = VersionInfo(
            version="1.22.0-pre.1",
            filename="vs_server_linux-x64_1.22.0-pre.1.tar.gz",
            filesize="41.0 MB",
            md5="xyz789",
            cdn_url="https://cdn.vintagestory.at/unstable/1",
            local_url="https://vintagestory.at/unstable/1",
            is_latest=True,
            channel="unstable",
        )
        cached_time = datetime.datetime(2026, 1, 11, 14, 30, 0, tzinfo=datetime.UTC)

        response = VersionDetailResponse(
            version=version,
            cached=True,
            cached_at=cached_time,
        )

        data = response.model_dump()

        assert data["cached"] is True
        assert data["cached_at"] == cached_time
        assert data["version"]["channel"] == "unstable"
