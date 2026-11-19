"""A serverconfig.json save drops the pending edits it changes (Story 23.4, FR318).

Epic 23 ADR-4 decision 7: the admin changed that key on purpose, so Story 22.7's
write-back must not undo it; keys the save leaves alone stay pending.
"""

import json

import pytest
from structlog.testing import capture_logs

from vintagestory_api.services.config_files import changed_top_level_keys
from vintagestory_api.services.server import ServerService


class TestChangedTopLevelKeys:
    @pytest.mark.parametrize(
        ("old", "new", "expected"),
        [
            ({"a": 1, "b": 2}, {"a": 1, "b": 3}, {"b"}),
            ({"a": 1}, {"a": 1, "b": 2}, {"b"}),
            ({"a": 1, "b": 2}, {"a": 1}, {"b"}),
            ({"a": [1]}, {"a": [1]}, set[str]()),
            (None, {"a": 1, "b": 2}, {"a", "b"}),
            ([1], {"a": 1}, {"a"}),
            ({"a": 1}, [1], set[str]()),
        ],
    )
    def test_keys(self, old: object, new: object, expected: set[str]) -> None:
        assert changed_top_level_keys(old, new) == expected


class TestDropPendingEditsChangedBySave:
    def _record(self, service: ServerService) -> None:
        service.pending_config_edits.record("Port", 42421)
        service.pending_config_edits.record("Ip", "10.0.0.5")

    def test_a_changed_key_is_dropped_and_others_stay(self, server_service: ServerService) -> None:
        self._record(server_service)
        previous = json.dumps({"Port": 42421, "Ip": "10.0.0.5"}).encode()

        with capture_logs() as logs:
            server_service.drop_pending_edits_changed_by_save(
                previous, {"Port": 50000, "Ip": "10.0.0.5"}
            )

        assert set(server_service.pending_config_edits.edits) == {"Ip"}
        dropped = [log for log in logs if log["event"] == "pending_config_edits_dropped"]
        assert dropped == [
            {
                "event": "pending_config_edits_dropped",
                "keys": ["Port"],
                "reason": "file_edited",
                "log_level": "info",
            }
        ]

    def test_an_unparseable_previous_text_drops_every_key_the_save_has(
        self, server_service: ServerService
    ) -> None:
        self._record(server_service)

        server_service.drop_pending_edits_changed_by_save(b"{ broken", {"Port": 42421})

        assert set(server_service.pending_config_edits.edits) == {"Ip"}

    def test_nothing_changed_drops_nothing(self, server_service: ServerService) -> None:
        self._record(server_service)
        previous = json.dumps({"Port": 42421, "Ip": "10.0.0.5"}).encode()

        server_service.drop_pending_edits_changed_by_save(
            previous, {"Port": 42421, "Ip": "10.0.0.5"}
        )

        assert set(server_service.pending_config_edits.edits) == {"Port", "Ip"}
