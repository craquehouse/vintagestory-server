"""API tests for GET /api/v1alpha1/console/history endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from vintagestory_api.services.server import ServerService

# pyright: reportPrivateUsage=false
# Note: Tests need access to private members to verify internal state


class TestConsoleHistoryEndpoint:
    """API tests for GET /api/v1alpha1/console/history endpoint (Task 3)."""

    # ======================================
    # Authentication tests
    # ======================================

    def test_history_requires_authentication(self, client: TestClient) -> None:
        """Test that history endpoint requires authentication."""
        response = client.get("/api/v1alpha1/console/history")

        assert response.status_code == 401

    def test_history_requires_admin_role(
        self, client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Test that history endpoint requires Admin role (FR9: Console restricted to Admin)."""
        response = client.get("/api/v1alpha1/console/history", headers=monitor_headers)

        assert response.status_code == 403
        assert "Console access requires Admin role" in response.json()["detail"]["message"]

    def test_history_accessible_by_admin(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that Admin role can access console history."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    # ======================================
    # Response format tests
    # ======================================

    def test_history_follows_envelope_format(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that response follows API envelope format."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "data" in data
        assert "lines" in data["data"]
        assert "total" in data["data"]

    def test_history_returns_empty_list_for_new_buffer(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that empty buffer returns empty lines array."""
        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["lines"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_history_returns_buffered_lines(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that history returns lines from console buffer."""
        # Add some lines to the buffer
        await test_service.console_buffer.append("Server starting...")
        await test_service.console_buffer.append("World loaded")
        await test_service.console_buffer.append("Ready for connections")

        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 3
        assert data["total"] == 3
        assert "Server starting" in data["lines"][0]
        assert "World loaded" in data["lines"][1]
        assert "Ready for connections" in data["lines"][2]

    # ======================================
    # Lines limit parameter tests
    # ======================================

    @pytest.mark.asyncio
    async def test_history_with_lines_limit(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that lines parameter limits returned lines."""
        # Add 10 lines
        for i in range(10):
            await test_service.console_buffer.append(f"Line {i}")

        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 3}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 3
        assert data["total"] == 10  # Total in buffer
        assert data["limit"] == 3
        # Should return the most recent 3 lines
        assert "Line 7" in data["lines"][0]
        assert "Line 8" in data["lines"][1]
        assert "Line 9" in data["lines"][2]

    @pytest.mark.asyncio
    async def test_history_limit_larger_than_buffer(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that limit larger than buffer returns all lines."""
        await test_service.console_buffer.append("Line 1")
        await test_service.console_buffer.append("Line 2")

        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 100}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["lines"]) == 2
        assert data["total"] == 2

    def test_history_invalid_lines_param_negative(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that negative lines param returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": -1}
        )

        assert response.status_code == 422

    def test_history_invalid_lines_param_zero(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that zero lines param returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 0}
        )

        assert response.status_code == 422

    def test_history_invalid_lines_param_too_large(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test that lines param > 10000 returns 422."""
        response = client.get(
            "/api/v1alpha1/console/history", headers=admin_headers, params={"lines": 10001}
        )

        assert response.status_code == 422

    # ======================================
    # Timestamp format tests (AC1)
    # ======================================

    @pytest.mark.asyncio
    async def test_history_lines_have_timestamps(
        self, client: TestClient, admin_headers: dict[str, str], test_service: ServerService
    ) -> None:
        """Test that returned lines include ISO 8601 timestamps (AC1)."""
        await test_service.console_buffer.append("Test message")

        response = client.get("/api/v1alpha1/console/history", headers=admin_headers)

        assert response.status_code == 200
        lines = response.json()["data"]["lines"]
        assert len(lines) == 1

        # Verify timestamp format: [YYYY-MM-DDTHH:MM:SS.ffffff]
        line = lines[0]
        assert line.startswith("[")
        assert "]" in line
        assert "Test message" in line

        # Parse the timestamp
        timestamp_str = line[1 : line.index("]")]
        timestamp = datetime.fromisoformat(timestamp_str)
        assert timestamp is not None
