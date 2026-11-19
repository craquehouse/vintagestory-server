"""E2E test for the Prometheus endpoint (Story 22.2, AC 10).

GET /metrics is at the root and open like /healthz. The checks hold in any game
state: `just test-e2e-ci` runs them on a container with no game installed.
"""

from playwright.sync_api import Page
from prometheus_client.parser import text_string_to_metric_families


def test_metrics_endpoint_serves_prometheus_text(page: Page, base_url: str) -> None:
    """Verify /metrics answers without a key in the Prometheus text format."""
    response = page.request.get(f"{base_url}/metrics")

    assert response.ok
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    samples = [
        sample
        for family in text_string_to_metric_families(response.text())
        for sample in family.samples
    ]
    names = {sample.name for sample in samples}

    up = [sample.value for sample in samples if sample.name == "vintagestory_server_up"]
    assert up in ([0.0], [1.0])
    current = [
        sample
        for sample in samples
        if sample.name == "vintagestory_server_state" and sample.value == 1
    ]
    assert len(current) == 1
    assert "python_info" in names
    # The container is Linux, so the manager's process series are there
    assert "process_resident_memory_bytes" in names
