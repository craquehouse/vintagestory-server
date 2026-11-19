"""The game server's metrics for Prometheus, read at scrape time (Epic 22 ADR-3, ADR-4)."""

from collections.abc import Callable, Iterable

import psutil
import structlog
from prometheus_client import CollectorRegistry, GCCollector, PlatformCollector, ProcessCollector
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily
from prometheus_client.metrics_core import Metric

from vintagestory_api.models.server import ServerState
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.server import ServerService, get_server_service

logger = structlog.get_logger()


class GameServerCollector:
    """Builds the vintagestory_* series from live state at every collect()."""

    def __init__(
        self,
        server: Callable[[], ServerService] = get_server_service,
        restart_state: Callable[[], PendingRestartState] = get_restart_state,
    ) -> None:
        self._server = server
        self._restart_state = restart_state

    def collect(self) -> Iterable[Metric]:
        sources: list[tuple[str, Callable[[], list[Metric]]]] = [
            ("server_status", self._server_status),
            ("players", self._players),
            ("pending_restart", self._pending_restart),
            ("max_clients", self._max_clients),
            ("game_process", self._game_process),
        ]
        metrics: list[Metric] = []
        for source, build in sources:
            metrics.extend(self._guarded(source, build))
        return metrics

    def _guarded(self, source: str, build: Callable[[], list[Metric]]) -> list[Metric]:
        """One source's series; a source that raises is logged and left out (ADR-3 dec. 5)."""
        try:
            return build()
        except Exception as e:
            logger.warning(
                "prometheus_source_failed",
                source=source,
                error_type=type(e).__name__,
                error=str(e),
            )
            return []

    def _server_status(self) -> list[Metric]:
        status = self._server().get_server_status()
        metrics: list[Metric] = []
        if status.version is not None:
            info = GaugeMetricFamily(
                "vintagestory_server_info",
                "The installed VintageStory server version; always 1.",
                labels=["version"],
            )
            info.add_metric([status.version], 1)
            metrics.append(info)
        metrics.append(
            GaugeMetricFamily(
                "vintagestory_server_up",
                "1 while the VintageStory server is running, else 0.",
                value=1 if status.state == ServerState.RUNNING else 0,
            )
        )
        state = GaugeMetricFamily(
            "vintagestory_server_state",
            "1 for the VintageStory server's current state, 0 for the others.",
            labels=["state"],
        )
        for member in ServerState:
            state.add_metric([member.value], 1 if member == status.state else 0)
        metrics.append(state)
        if status.uptime_seconds is not None:
            metrics.append(
                GaugeMetricFamily(
                    "vintagestory_server_uptime_seconds",
                    "Seconds since the VintageStory server was started.",
                    value=status.uptime_seconds,
                )
            )
        return metrics

    def _players(self) -> list[Metric]:
        online = self._server().players_online
        return [
            GaugeMetricFamily(
                "vintagestory_players_online",
                "Players on the VintageStory server, counted from its join and leave lines; "
                "0 when it is not running.",
                value=online if online is not None else 0,
            )
        ]

    def _pending_restart(self) -> list[Metric]:
        pending = self._restart_state().pending_restart
        return [
            GaugeMetricFamily(
                "vintagestory_server_pending_restart",
                "1 when a change waits for a VintageStory server restart, else 0.",
                value=1 if pending else 0,
            )
        ]

    def _max_clients(self) -> list[Metric]:
        max_clients = GameConfigService(settings=self._server().settings).get_max_clients()
        if max_clients is None:
            return []
        return [
            GaugeMetricFamily(
                "vintagestory_players_max",
                "MaxClients from the VintageStory server's serverconfig.json.",
                value=max_clients,
            )
        ]

    def _game_process(self) -> list[Metric]:
        pid = self._server().game_server_pid
        if pid is None:
            return []
        try:
            process = psutil.Process(pid)
            cpu = process.cpu_times()
            rss = process.memory_info().rss
        except psutil.NoSuchProcess:
            # The process exited between the PID read and psutil: not a failure
            logger.debug("prometheus_game_process_gone", pid=pid)
            return []
        return [
            CounterMetricFamily(
                "vintagestory_server_process_cpu_seconds_total",
                "User and system CPU time of the VintageStory server process, in seconds.",
                value=cpu.user + cpu.system,
            ),
            GaugeMetricFamily(
                "vintagestory_server_process_resident_memory_bytes",
                "Resident memory of the VintageStory server process, in bytes.",
                value=rss,
            ),
        ]


def build_registry(collector: GameServerCollector) -> CollectorRegistry:
    """A new registry with the game server's series and the manager's own (ADR-3 dec. 3)."""
    registry = CollectorRegistry()
    registry.register(collector)
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    GCCollector(registry=registry)
    return registry


_registry: CollectorRegistry | None = None


def get_metrics_registry() -> CollectorRegistry:
    """The process-wide registry, built on first use (the route's dependency)."""
    global _registry
    if _registry is None:
        _registry = build_registry(GameServerCollector())
    return _registry
