"""The game server's Prometheus metrics (Story 22.2, Epic 22 ADR-3 and ADR-4)."""

import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import psutil
import pytest
from prometheus_client import CONTENT_TYPE_PLAIN_0_0_4, CollectorRegistry, generate_latest
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client.samples import Sample
from structlog.testing import capture_logs
from structlog.typing import EventDict

from vintagestory_api.config import Settings
from vintagestory_api.models.server import LifecycleAction, LifecycleResponse, ServerState
from vintagestory_api.routers import config as config_router
from vintagestory_api.services import mods as mods_module
from vintagestory_api.services import prometheus_metrics
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.metrics import MetricsService
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.players import PlayerTracker
from vintagestory_api.services.prometheus_metrics import (
    GameServerCollector,
    build_registry,
    get_metrics_registry,
)
from vintagestory_api.services.server import ServerService

# Placeholder names only (Story 22.1)
PLAYERS = {"ExamplePlayer", "AnotherPlayer"}

HELP_AND_TYPE = {
    "vintagestory_server_info": (
        "The installed VintageStory server version; always 1.",
        "gauge",
    ),
    "vintagestory_server_up": ("1 while the VintageStory server is running, else 0.", "gauge"),
    "vintagestory_server_state": (
        "1 for the VintageStory server's current state, 0 for the others.",
        "gauge",
    ),
    "vintagestory_server_uptime_seconds": (
        "Seconds since the VintageStory server was started.",
        "gauge",
    ),
    "vintagestory_players_online": (
        "Players on the VintageStory server, counted from its join and leave lines; "
        "0 when it is not running.",
        "gauge",
    ),
    "vintagestory_players_max": (
        "MaxClients from the VintageStory server's serverconfig.json.",
        "gauge",
    ),
    "vintagestory_server_pending_restart": (
        "1 when a change waits for a VintageStory server restart, else 0.",
        "gauge",
    ),
    "vintagestory_server_process_cpu_seconds_total": (
        "User and system CPU time of the VintageStory server process, in seconds.",
        "counter",
    ),
    "vintagestory_server_process_resident_memory_bytes": (
        "Resident memory of the VintageStory server process, in bytes.",
        "gauge",
    ),
}

# The sample names each source yields
SOURCE_SERIES = {
    "server_status": (
        "vintagestory_server_info",
        "vintagestory_server_up",
        "vintagestory_server_state",
        "vintagestory_server_uptime_seconds",
    ),
    "players": ("vintagestory_players_online",),
    "pending_restart": ("vintagestory_server_pending_restart",),
    "max_clients": ("vintagestory_players_max",),
    "game_process": (
        "vintagestory_server_process_cpu_seconds_total",
        "vintagestory_server_process_resident_memory_bytes",
    ),
}


class FakeProcess:
    """The test process stands in for the game: real psutil reads, no dotnet."""

    pid = os.getpid()
    returncode: int | None = None


@pytest.fixture(autouse=True)
def no_disk_check(monkeypatch: pytest.MonkeyPatch) -> None:
    # get_server_status reads the disk space through Settings() from the environment
    monkeypatch.setattr("vintagestory_api.routers.health.get_disk_space_data", lambda: None)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", api_key_admin="prometheus-admin-KEY-1")


@pytest.fixture
def service(settings: Settings) -> ServerService:
    return ServerService(settings)


@pytest.fixture
def restart_state() -> PendingRestartState:
    return PendingRestartState()


def install(settings: Settings, version: str = "1.22.7") -> None:
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    (settings.server_dir / "VintagestoryServer.dll").touch()
    (settings.server_dir / "VintagestoryLib.dll").touch()
    settings.vsmanager_dir.mkdir(parents=True, exist_ok=True)
    (settings.vsmanager_dir / "current_version").write_text(version)


def write_serverconfig(settings: Settings, **values: object) -> None:
    settings.serverdata_dir.mkdir(parents=True, exist_ok=True)
    (settings.serverdata_dir / "serverconfig.json").write_text(json.dumps(values))


def run(
    service: ServerService,
    monkeypatch: pytest.MonkeyPatch,
    state: ServerState = ServerState.RUNNING,
    started: float | None = None,
) -> None:
    monkeypatch.setattr(service, "_process", FakeProcess())
    monkeypatch.setattr(service, "_server_state", state)
    monkeypatch.setattr(
        service, "_server_start_time", time.time() - 120 if started is None else started
    )


def set_players(service: ServerService, monkeypatch: pytest.MonkeyPatch, names: set[str]) -> None:
    monkeypatch.setattr(service._player_tracker, "_online", set(names))


def registry_for(service: ServerService, restart_state: PendingRestartState) -> CollectorRegistry:
    return build_registry(
        GameServerCollector(server=lambda: service, restart_state=lambda: restart_state)
    )


def scrape(registry: CollectorRegistry) -> dict[str, list[Sample]]:
    """The body parsed, keyed by sample name."""
    samples: dict[str, list[Sample]] = {}
    for family in text_string_to_metric_families(generate_latest(registry).decode()):
        for sample in family.samples:
            samples.setdefault(sample.name, []).append(sample)
    return samples


def value(samples: dict[str, list[Sample]], name: str) -> float:
    assert len(samples[name]) == 1, name
    return samples[name][0].value


def states(samples: dict[str, list[Sample]]) -> dict[str, float]:
    return {s.labels["state"]: s.value for s in samples["vintagestory_server_state"]}


def warnings(logs: list[EventDict]) -> list[EventDict]:
    return [entry for entry in logs if entry["log_level"] == "warning"]


def test_plain_text_content_type_is_version_0_0_4() -> None:
    # The route answers with this constant; a library bump that changes it fails here
    assert CONTENT_TYPE_PLAIN_0_0_4 == "text/plain; version=0.0.4; charset=utf-8"


def test_running_server_has_every_series(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(settings, "1.22.7")
    write_serverconfig(settings, MaxClients=16)
    run(service, monkeypatch)
    set_players(service, monkeypatch, PLAYERS)
    registry = registry_for(service, restart_state)

    samples = scrape(registry)

    assert samples["vintagestory_server_info"] == [
        Sample("vintagestory_server_info", {"version": "1.22.7"}, 1.0)
    ]
    assert value(samples, "vintagestory_server_up") == 1
    assert list(states(samples)) == [member.value for member in ServerState]
    assert states(samples) == {
        member.value: (1.0 if member == ServerState.RUNNING else 0.0) for member in ServerState
    }
    assert value(samples, "vintagestory_server_uptime_seconds") >= 120
    assert value(samples, "vintagestory_players_online") == 2
    assert value(samples, "vintagestory_players_max") == 16
    assert value(samples, "vintagestory_server_pending_restart") == 0
    assert value(samples, "vintagestory_server_process_cpu_seconds_total") >= 0
    assert value(samples, "vintagestory_server_process_resident_memory_bytes") > 0

    families = {
        family.name: family.type
        for family in text_string_to_metric_families(generate_latest(registry).decode())
    }
    assert families["vintagestory_server_process_cpu_seconds"] == "counter"

    text = generate_latest(registry).decode()
    for name, (help_text, metric_type) in HELP_AND_TYPE.items():
        assert f"# HELP {name} {help_text}\n" in text
        assert f"# TYPE {name} {metric_type}\n" in text


def test_installed_and_stopped(
    settings: Settings, service: ServerService, restart_state: PendingRestartState
) -> None:
    install(settings)

    samples = scrape(registry_for(service, restart_state))

    assert value(samples, "vintagestory_server_up") == 0
    assert states(samples)["installed"] == 1
    assert sum(states(samples).values()) == 1
    assert value(samples, "vintagestory_players_online") == 0
    assert "vintagestory_server_info" in samples
    assert "vintagestory_server_uptime_seconds" not in samples
    assert "vintagestory_server_process_cpu_seconds_total" not in samples
    assert "vintagestory_server_process_resident_memory_bytes" not in samples


def test_not_installed_without_serverconfig(
    service: ServerService, restart_state: PendingRestartState
) -> None:
    with capture_logs() as logs:
        samples = scrape(registry_for(service, restart_state))

    assert "vintagestory_server_info" not in samples
    assert states(samples)["not_installed"] == 1
    assert value(samples, "vintagestory_server_up") == 0
    assert value(samples, "vintagestory_players_online") == 0
    assert value(samples, "vintagestory_server_pending_restart") == 0
    assert "vintagestory_players_max" not in samples
    assert warnings(logs) == []


def test_not_installed_with_serverconfig_has_players_max(
    settings: Settings, service: ServerService, restart_state: PendingRestartState
) -> None:
    write_serverconfig(settings, MaxClients=16)

    samples = scrape(registry_for(service, restart_state))

    assert states(samples)["not_installed"] == 1
    assert value(samples, "vintagestory_players_max") == 16


def test_stopping_with_a_live_process(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(settings)
    run(service, monkeypatch, state=ServerState.STOPPING)

    samples = scrape(registry_for(service, restart_state))

    assert value(samples, "vintagestory_server_up") == 0
    assert states(samples)["stopping"] == 1
    assert "vintagestory_server_process_cpu_seconds_total" in samples
    assert "vintagestory_server_process_resident_memory_bytes" in samples
    assert "vintagestory_server_uptime_seconds" not in samples


def test_pending_restart_is_one(service: ServerService, restart_state: PendingRestartState) -> None:
    restart_state.require_restart("test")

    samples = scrape(registry_for(service, restart_state))

    assert value(samples, "vintagestory_server_pending_restart") == 1


@pytest.mark.asyncio
async def test_pending_restart_from_a_game_setting_until_a_restart(
    settings: Settings, service: ServerService, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A fresh shared singleton; monkeypatch restores the previous one after
    monkeypatch.setattr(mods_module, "_restart_state", None)
    install(settings)
    write_serverconfig(settings, Port=42420, MaxClients=16)
    registry = build_registry(GameServerCollector(server=lambda: service))
    game_config = GameConfigService(
        settings=settings,
        server_service=service,
        pending_restart_state=config_router.get_pending_restart_state(),
    )

    await game_config.update_setting("Port", 42421)
    assert value(scrape(registry), "vintagestory_server_pending_restart") == 1

    monkeypatch.setattr(
        service,
        "_start_server_locked",
        AsyncMock(
            return_value=LifecycleResponse(
                action=LifecycleAction.START,
                previous_state=ServerState.INSTALLED,
                new_state=ServerState.RUNNING,
                message="mocked",
            )
        ),
    )
    await service.restart_server()
    assert value(scrape(registry), "vintagestory_server_pending_restart") == 0
    assert get_restart_state().pending_restart is False


@pytest.mark.parametrize(
    "max_clients",
    [None, "16", 16.5, True],
    ids=["null", "string", "float", "bool"],
)
def test_players_max_absent_when_not_a_whole_number(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    max_clients: object,
) -> None:
    write_serverconfig(settings, MaxClients=max_clients)

    with capture_logs() as logs:
        samples = scrape(registry_for(service, restart_state))

    assert "vintagestory_players_max" not in samples
    assert warnings(logs) == []


def test_players_max_absent_when_the_key_is_missing(
    settings: Settings, service: ServerService, restart_state: PendingRestartState
) -> None:
    write_serverconfig(settings, Port=42420)

    with capture_logs() as logs:
        samples = scrape(registry_for(service, restart_state))

    assert "vintagestory_players_max" not in samples
    assert warnings(logs) == []


def raising_count(self: PlayerTracker) -> int:
    raise RuntimeError("count failed")


def raising_restart_state() -> PendingRestartState:
    raise RuntimeError("restart state failed")


def raising_process(pid: int) -> psutil.Process:
    raise psutil.AccessDenied(pid)


@pytest.mark.parametrize(
    ("source", "error_type"),
    [
        ("server_status", "RuntimeError"),
        ("players", "RuntimeError"),
        ("pending_restart", "RuntimeError"),
        ("max_clients", "JSONDecodeError"),
        ("game_process", "AccessDenied"),
    ],
)
def test_one_failing_source_leaves_the_others(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    error_type: str,
) -> None:
    install(settings)
    write_serverconfig(settings, MaxClients=16)
    run(service, monkeypatch)

    def restart_provider() -> PendingRestartState:
        return restart_state

    provider: Callable[[], PendingRestartState] = restart_provider

    if source == "server_status":

        def raising_status() -> None:
            raise RuntimeError("status failed")

        monkeypatch.setattr(service, "get_server_status", raising_status)
    elif source == "players":
        monkeypatch.setattr(PlayerTracker, "count", property(raising_count))
    elif source == "pending_restart":
        provider = raising_restart_state
    elif source == "max_clients":
        (settings.serverdata_dir / "serverconfig.json").write_text("{not json")
    else:
        monkeypatch.setattr(prometheus_metrics.psutil, "Process", raising_process)

    registry = build_registry(GameServerCollector(server=lambda: service, restart_state=provider))
    with capture_logs() as logs:
        samples = scrape(registry)

    for name in SOURCE_SERIES[source]:
        assert name not in samples
    for other, names in SOURCE_SERIES.items():
        if other != source:
            for name in names:
                assert name in samples, name
    failures = [entry for entry in logs if entry["event"] == "prometheus_source_failed"]
    assert len(failures) == 1
    assert failures[0]["log_level"] == "warning"
    assert failures[0]["source"] == source
    assert failures[0]["error_type"] == error_type
    assert len(warnings(logs)) == 1


def test_process_gone_is_not_a_failure(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(settings)
    run(service, monkeypatch)

    def gone(pid: int) -> psutil.Process:
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(prometheus_metrics.psutil, "Process", gone)

    with capture_logs() as logs:
        samples = scrape(registry_for(service, restart_state))

    assert "vintagestory_server_process_cpu_seconds_total" not in samples
    assert "vintagestory_server_process_resident_memory_bytes" not in samples
    assert warnings(logs) == []
    gone_logs = [entry for entry in logs if entry["event"] == "prometheus_game_process_gone"]
    assert gone_logs == [
        {"event": "prometheus_game_process_gone", "log_level": "debug", "pid": os.getpid()}
    ]


def test_values_are_read_at_each_scrape(
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(settings)
    run(service, monkeypatch)
    set_players(service, monkeypatch, {"ExamplePlayer"})
    registry = registry_for(service, restart_state)
    ring_buffer_reads: list[object] = []

    def spy_collect(self: MetricsService) -> None:
        ring_buffer_reads.append(self)

    monkeypatch.setattr(MetricsService, "collect", spy_collect)

    first = scrape(registry)
    set_players(service, monkeypatch, PLAYERS)
    total = 0
    for number in range(200_000):
        total += number * number
    assert total > 0
    second = scrape(registry)

    assert value(first, "vintagestory_players_online") == 1
    assert value(second, "vintagestory_players_online") == 2
    cpu = "vintagestory_server_process_cpu_seconds_total"
    assert value(second, cpu) >= value(first, cpu)
    # Live values, not the JSON metrics' ring buffer
    assert ring_buffer_reads == []
    assert not hasattr(prometheus_metrics, "MetricsService")


def test_labels_and_body_hold_no_personal_data(
    tmp_path: Path,
    settings: Settings,
    service: ServerService,
    restart_state: PendingRestartState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(settings)
    write_serverconfig(settings, MaxClients=16)
    run(service, monkeypatch)
    set_players(service, monkeypatch, PLAYERS)
    registry = registry_for(service, restart_state)

    with capture_logs() as logs:
        body = generate_latest(registry).decode()

    for family in text_string_to_metric_families(body):
        for sample in family.samples:
            if sample.name.startswith("vintagestory_"):
                assert set(sample.labels) <= {"version", "state"}
    for name in PLAYERS:
        assert name not in body
    assert str(tmp_path) not in body
    assert [entry for entry in logs if entry["log_level"] not in ("debug",)] == []


def test_registry_has_the_manager_series(
    service: ServerService, restart_state: PendingRestartState
) -> None:
    samples = scrape(registry_for(service, restart_state))

    assert "python_info" in samples
    assert "python_gc_objects_collected_total" in samples
    # ProcessCollector reads /proc: Linux (the image, CI) only
    assert ("process_resident_memory_bytes" in samples) is (sys.platform == "linux")


def test_two_registries_share_nothing(
    service: ServerService, restart_state: PendingRestartState
) -> None:
    first = registry_for(service, restart_state)
    second = registry_for(service, restart_state)

    assert first is not second
    assert "vintagestory_server_up" in scrape(second)


def test_metrics_registry_is_one_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prometheus_metrics, "_registry", None)

    # Not scraped: the singleton reads Settings() from the environment
    assert get_metrics_registry() is get_metrics_registry()
