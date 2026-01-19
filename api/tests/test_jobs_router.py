"""Tests for jobs router endpoints.

Story 7.2: Job Management API - Task 2 & 3

Tests cover:
- GET /api/v1alpha1/jobs - List jobs (Admin only)
- DELETE /api/v1alpha1/jobs/{job_id} - Delete job (Admin only)
- RBAC enforcement (Monitor forbidden)
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from conftest import TEST_ADMIN_KEY, TEST_MONITOR_KEY  # type: ignore[import-not-found]
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vintagestory_api.config import Settings
from vintagestory_api.main import app
from vintagestory_api.middleware.auth import get_settings


@pytest.fixture
def integration_app() -> Generator[FastAPI, None, None]:
    """Create app with overridden settings for integration testing."""
    test_settings = Settings(
        api_key_admin=TEST_ADMIN_KEY,
        api_key_monitor=TEST_MONITOR_KEY,
        debug=True,
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def lifespan_client(integration_app: FastAPI):
    """Test client with app lifespan (starts scheduler)."""
    with TestClient(integration_app) as client:
        yield client


class TestListJobsEndpoint:
    """Tests for GET /api/v1alpha1/jobs endpoint (AC: 1, 4)."""

    def test_list_jobs_admin_success(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Admin can list scheduled jobs (AC: 1)."""
        response = lifespan_client.get(
            "/api/v1alpha1/jobs",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "jobs" in data["data"]
        assert isinstance(data["data"]["jobs"], list)

    def test_list_jobs_returns_job_details(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """List jobs returns job info with required fields (AC: 1)."""
        # First add a test job via scheduler service
        from vintagestory_api.main import get_scheduler_service

        scheduler = get_scheduler_service()

        async def test_task():
            pass

        scheduler.add_interval_job(test_task, seconds=300, job_id="test_list_job")

        try:
            response = lifespan_client.get(
                "/api/v1alpha1/jobs",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            jobs = data["data"]["jobs"]

            # Find our test job
            test_job = next((j for j in jobs if j["id"] == "test_list_job"), None)
            assert test_job is not None

            # Verify required fields (AC: 1)
            assert "id" in test_job
            assert "next_run_time" in test_job
            assert "trigger_type" in test_job
            assert "trigger_details" in test_job

            assert test_job["id"] == "test_list_job"
            assert test_job["trigger_type"] == "interval"
            assert "300 seconds" in test_job["trigger_details"]

        finally:
            # Cleanup
            scheduler.remove_job("test_list_job")

    def test_list_jobs_monitor_forbidden(
        self, lifespan_client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Monitor cannot list scheduled jobs (AC: 4)."""
        response = lifespan_client.get(
            "/api/v1alpha1/jobs",
            headers=monitor_headers,
        )

        assert response.status_code == 403

    def test_list_jobs_no_auth_unauthorized(
        self, lifespan_client: TestClient
    ) -> None:
        """Request without auth returns 401."""
        response = lifespan_client.get("/api/v1alpha1/jobs")

        assert response.status_code == 401

    def test_list_jobs_empty_when_no_jobs(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """List returns empty array when no jobs registered."""
        from vintagestory_api.main import get_scheduler_service

        scheduler = get_scheduler_service()

        # Remove all existing jobs for clean test
        existing_jobs = scheduler.get_jobs()
        for job in existing_jobs:
            scheduler.remove_job(str(job.id))  # type: ignore[reportUnknownMemberType]

        try:
            response = lifespan_client.get(
                "/api/v1alpha1/jobs",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["jobs"] == []

        finally:
            # Jobs will be re-registered on next lifespan start if needed
            pass


class TestDeleteJobEndpoint:
    """Tests for DELETE /api/v1alpha1/jobs/{job_id} endpoint (AC: 2, 3, 5)."""

    def test_delete_job_admin_success(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Admin can delete existing job (AC: 2)."""
        from vintagestory_api.main import get_scheduler_service

        scheduler = get_scheduler_service()

        async def test_task():
            pass

        scheduler.add_interval_job(test_task, seconds=60, job_id="job_to_delete")

        response = lifespan_client.delete(
            "/api/v1alpha1/jobs/job_to_delete",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "deleted" in data["data"]["message"].lower()

        # Verify job is actually removed
        assert scheduler.get_job("job_to_delete") is None

    def test_delete_job_not_found(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Delete non-existent job returns 404 with JOB_NOT_FOUND (AC: 3)."""
        response = lifespan_client.delete(
            "/api/v1alpha1/jobs/nonexistent_job_id",
            headers=admin_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "JOB_NOT_FOUND"

    def test_delete_job_monitor_forbidden(
        self, lifespan_client: TestClient, monitor_headers: dict[str, str]
    ) -> None:
        """Monitor cannot delete jobs (AC: 5)."""
        response = lifespan_client.delete(
            "/api/v1alpha1/jobs/any_job_id",
            headers=monitor_headers,
        )

        assert response.status_code == 403

    def test_delete_job_no_auth_unauthorized(
        self, lifespan_client: TestClient
    ) -> None:
        """Delete without auth returns 401."""
        response = lifespan_client.delete("/api/v1alpha1/jobs/some_job")

        assert response.status_code == 401

    def test_delete_job_removes_from_list(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Deleted job no longer appears in list."""
        from vintagestory_api.main import get_scheduler_service

        scheduler = get_scheduler_service()

        async def test_task():
            pass

        scheduler.add_interval_job(test_task, seconds=60, job_id="job_check_removal")

        # Verify job is in list
        list_response = lifespan_client.get(
            "/api/v1alpha1/jobs",
            headers=admin_headers,
        )
        jobs = list_response.json()["data"]["jobs"]
        assert any(j["id"] == "job_check_removal" for j in jobs)

        # Delete the job
        delete_response = lifespan_client.delete(
            "/api/v1alpha1/jobs/job_check_removal",
            headers=admin_headers,
        )
        assert delete_response.status_code == 200

        # Verify job is no longer in list
        list_response2 = lifespan_client.get(
            "/api/v1alpha1/jobs",
            headers=admin_headers,
        )
        jobs2 = list_response2.json()["data"]["jobs"]
        assert not any(j["id"] == "job_check_removal" for j in jobs2)


class TestJobsRouterIntegration:
    """Integration tests for jobs router."""

    def test_jobs_endpoint_registered(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Jobs router is registered and accessible."""
        response = lifespan_client.get(
            "/api/v1alpha1/jobs",
            headers=admin_headers,
        )

        # Should not be 404 (not found)
        assert response.status_code != 404

    def test_list_cron_job_details(
        self, lifespan_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """List endpoint shows cron job trigger details correctly."""
        from vintagestory_api.main import get_scheduler_service

        scheduler = get_scheduler_service()

        async def cron_task():
            pass

        scheduler.add_cron_job(cron_task, "0 */6 * * *", job_id="cron_test_job")

        try:
            response = lifespan_client.get(
                "/api/v1alpha1/jobs",
                headers=admin_headers,
            )

            assert response.status_code == 200
            jobs = response.json()["data"]["jobs"]

            cron_job = next((j for j in jobs if j["id"] == "cron_test_job"), None)
            assert cron_job is not None
            assert cron_job["trigger_type"] == "cron"
            # Cron trigger details should contain schedule info
            assert len(cron_job["trigger_details"]) > 0

        finally:
            scheduler.remove_job("cron_test_job")
