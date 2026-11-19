"""The game server's Prometheus metrics (Story 22.2, Epic 22 ADR-3 and ADR-4)."""

from prometheus_client import CONTENT_TYPE_PLAIN_0_0_4


def test_plain_text_content_type_is_version_0_0_4() -> None:
    # The route answers with this constant; a library bump that changes it fails here
    assert CONTENT_TYPE_PLAIN_0_0_4 == "text/plain; version=0.0.4; charset=utf-8"
