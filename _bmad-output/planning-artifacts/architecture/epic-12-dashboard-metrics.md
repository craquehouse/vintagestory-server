# Epic 12: Dashboard Metrics Architecture

> Technical decisions and ADRs for Enhanced Dashboard with Server Metrics (Stories 12.1-12.6)

---

## Overview

Epic 12 adds server metrics collection and visualization to the dashboard:
- **Backend**: Periodic metrics collection using psutil, stored in a ring buffer
- **Frontend**: Charting library integration for time-series visualization
- **Integration**: Leverages existing APScheduler infrastructure from Epic 7/8

---

## ADR-E12-001: Process Metrics Collection with psutil

### Context

We need to collect CPU and memory metrics for both the API server process and the VintageStory game server process to display on the dashboard.

### Decision

**Use the `psutil` library** for cross-platform process monitoring.

### Rationale

1. **Well-maintained**: psutil has 10K+ GitHub stars, regular releases, active maintenance
2. **Cross-platform**: Works on Linux (Docker), macOS (dev), Windows
3. **Lightweight**: Fast operations that won't block the event loop
4. **Comprehensive**: Provides RSS, VMS, CPU percent, and more

### Implementation Patterns

```python
import psutil

# Get current process (API server) metrics
def get_api_metrics() -> dict:
    """Get metrics for the current API server process."""
    process = psutil.Process()  # Current process by default
    memory = process.memory_info()

    return {
        "memory_rss_mb": memory.rss / (1024 * 1024),
        "memory_vms_mb": memory.vms / (1024 * 1024),
        "cpu_percent": process.cpu_percent(interval=None),  # Non-blocking
    }

# Get external process (game server) metrics
def get_game_server_metrics(pid: int) -> dict | None:
    """Get metrics for the game server process by PID."""
    try:
        process = psutil.Process(pid)
        memory = process.memory_info()

        return {
            "memory_rss_mb": memory.rss / (1024 * 1024),
            "memory_vms_mb": memory.vms / (1024 * 1024),
            "cpu_percent": process.cpu_percent(interval=None),
        }
    except psutil.NoSuchProcess:
        return None  # Process not running
```

### CPU Percent Notes

- First call to `cpu_percent(interval=None)` always returns `0.0` (baseline)
- Subsequent calls return percentage since last call
- For accurate readings, call once at job startup, then use subsequent values
- Value can exceed 100% for multi-threaded processes on multi-core systems

### AsyncIO Considerations

psutil operations are synchronous but very fast (~1ms). Two options:

1. **Direct call** (recommended for <10ms operations): Call directly in async context
2. **Thread pool** (if blocking is a concern): Use `asyncio.to_thread()`

For our use case (10-second intervals), direct calls are acceptable.

### Status

**Approved** - Standard choice for Python process monitoring.

---

## ADR-E12-002: Game Server Process Discovery

### Context

The game server runs as a separate subprocess managed by `ServerService`. We need to discover its PID to collect metrics.

### Decision

**Reuse the existing `ServerService._process` reference** to get the game server PID.

### Rationale

The `ServerService` already tracks the subprocess object when the server is running:

```python
# In ServerService
self._process: asyncio.subprocess.Process | None = None
```

When the server is running, `self._process.pid` gives us the PID.

### Implementation Approach

```python
# In MetricsService
def get_game_server_pid(self) -> int | None:
    """Get the game server PID if running."""
    server_service = get_server_service()

    # Check if process exists and is running
    if (server_service._process is not None and
        server_service._process.returncode is None):
        return server_service._process.pid

    return None
```

### Graceful Degradation

When the game server is not running:
- `get_game_server_pid()` returns `None`
- Metrics collection records `null` for game server fields
- Dashboard displays "N/A" or "--" for unavailable metrics

### Alternative Considered: Process Name Search

We could search for the process by name pattern:
```python
for proc in psutil.process_iter(['name', 'pid']):
    if 'dotnet' in proc.info['name']:
        # Check cmdline for VintagestoryServer.dll
```

**Rejected** because:
- More complex and error-prone
- Could match wrong dotnet processes
- We already have direct PID access via ServerService

### Status

**Approved** - Direct PID access is simpler and more reliable.

---

## ADR-E12-003: Charting Library Selection

### Context

We need to add time-series charts to the dashboard to visualize CPU and memory metrics over time. The frontend uses React 19, TypeScript, and Tailwind CSS v4 with Catppuccin theming.

### Decision

**Use Recharts** for dashboard metrics visualization.

### Evaluation Matrix

| Library | Bundle Size | TypeScript | React 19 | Theming | Ease of Use |
|---------|-------------|------------|----------|---------|-------------|
| **Recharts** | ~400KB | Native | Yes | Good | Excellent |
| visx | ~50-100KB (modular) | Native | Yes | Manual | Complex |
| Chart.js + react-chartjs-2 | ~200KB | Wrapper | Yes | Good | Good |
| uPlot | ~50KB | External | React wrapper needed | Manual | Complex |

### Rationale for Recharts

1. **Developer Experience**: Declarative React components, excellent docs
2. **TypeScript**: Native TypeScript support with comprehensive types
3. **React 19 Compatibility**: Actively maintained, supports latest React
4. **Feature Set**: Built-in tooltips, legends, responsive containers
5. **Theming**: Easy to apply Catppuccin colors via stroke/fill props
6. **Community**: Large community, many examples available

### Why Not Other Options

- **visx**: Too low-level for our needs; requires significant boilerplate for basic charts
- **Chart.js**: Canvas-based (harder to style with Tailwind), less React-native
- **uPlot**: Ultra-fast but minimal React integration, steep learning curve

### Bundle Size Mitigation

While Recharts is larger (~400KB), we can mitigate this:
1. Only import needed components: `import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'`
2. Consider code splitting for the dashboard page
3. Bundle size is acceptable given the feature richness

### Example Usage

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface MetricsChartProps {
  data: Array<{ timestamp: string; value: number }>;
  dataKey: string;
  color: string;
}

export function MetricsChart({ data, dataKey, color }: MetricsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <XAxis dataKey="timestamp" tick={{ fill: 'var(--color-text-muted)' }} />
        <YAxis tick={{ fill: 'var(--color-text-muted)' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)'
          }}
        />
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          dot={false}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Status

**Approved** - Best balance of features, DX, and maintainability for our use case.

---

## ADR-E12-004: In-Memory Ring Buffer for Metrics Storage

### Context

We need to store historical metrics for dashboard visualization. Requirements:
- ~1 hour of data at 10-second intervals (360 data points)
- Fast append and read operations
- No persistence required (metrics reset on restart)
- Thread-safe access for APScheduler job

### Decision

**Use a Python `collections.deque` as a ring buffer** (same pattern as ConsoleBuffer).

### Rationale

The `ConsoleBuffer` service already uses this pattern successfully:

```python
from collections import deque

class ConsoleBuffer:
    def __init__(self, max_lines: int = 10000):
        self._buffer: deque[str] = deque(maxlen=max_lines)
```

Benefits:
1. **O(1) operations**: Append and popleft are constant time
2. **Automatic eviction**: `maxlen` automatically drops oldest items
3. **Thread-safe reads**: Safe for APScheduler job + API reads
4. **Memory bounded**: Fixed maximum size prevents memory growth
5. **Proven pattern**: Already used in this codebase

### Data Structure

```python
from collections import deque
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class MetricsSnapshot:
    """Single metrics sample point."""
    timestamp: datetime
    # API server metrics
    api_memory_mb: float
    api_cpu_percent: float
    # Game server metrics (None if not running)
    game_memory_mb: float | None
    game_cpu_percent: float | None

class MetricsBuffer:
    """Ring buffer for metrics with configurable retention."""

    DEFAULT_CAPACITY = 360  # 1 hour at 10s intervals

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self._buffer: deque[MetricsSnapshot] = deque(maxlen=capacity)

    def append(self, snapshot: MetricsSnapshot) -> None:
        """Add a metrics snapshot (thread-safe for single writer)."""
        self._buffer.append(snapshot)

    def get_all(self) -> list[MetricsSnapshot]:
        """Get all snapshots for chart rendering."""
        return list(self._buffer)

    def get_latest(self) -> MetricsSnapshot | None:
        """Get most recent snapshot for stat cards."""
        return self._buffer[-1] if self._buffer else None

    def __len__(self) -> int:
        return len(self._buffer)
```

### Thread-Safety Considerations

- **Single writer**: Only the APScheduler job appends (no race conditions)
- **Multiple readers**: API endpoints read (safe with deque)
- **No explicit locking needed**: GIL protects atomic deque operations
- **Snapshot returns**: `get_all()` returns a list copy, safe from modification

### Configuration

Default: 360 samples × 10s interval = 3,600 seconds = 1 hour retention

Configurable via environment variable (future enhancement):
```python
VS_METRICS_RETENTION_SAMPLES = 720  # 2 hours
VS_METRICS_INTERVAL_SECONDS = 10
```

### Status

**Approved** - Simple, proven pattern already in use.

---

## ADR-E12-005: Player Count Extraction (Deferred)

### Context

The PRD mentioned displaying player count on the dashboard. We researched methods to extract this information from VintageStory.

### Sources Consulted

- `agentdocs/vs-server-troubleshooting.md` - VintageStory server behavior documentation
- VintageStory server logs at `{dataPath}/Logs/server-main.log`
- ConsoleBuffer service output patterns

### Research Findings

#### Option 1: Console Parsing

VintageStory logs player join/leave events to stdout:
```
[Server Event] Player <username> joined
[Server Event] Player <username> left
```

**Feasibility**: Possible but complex
- Would need to parse ConsoleBuffer content
- Track join/leave events to maintain count
- State management for server restarts
- Potential for state drift if events are missed

#### Option 2: RCON Protocol

VintageStory does NOT support RCON protocol.

#### Option 3: Server Status API

VintageStory server does NOT expose an HTTP API for status queries.

#### Option 4: Log File Parsing

Per `agentdocs/vs-server-troubleshooting.md`, server logs are written to `{dataPath}/Logs/`:
- `server-main.log` - Primary server log
- `server-event.log` - Game events

Could parse these files for player events.

**Feasibility**: Similar complexity to console parsing, with additional file I/O concerns.

### Decision

**Defer player count feature to a future epic.**

### Rationale

1. **Complexity vs Value**: Console parsing adds significant complexity for a nice-to-have feature
2. **Scope Creep**: Epic 12 is already well-scoped with CPU/memory metrics
3. **Maintenance Burden**: Log format changes could break the parser
4. **No Clean API**: Without RCON or HTTP API, all methods are fragile workarounds

### Future Implementation Path

If player count becomes a priority:
1. Create a dedicated `PlayerTracker` service
2. Subscribe to `ConsoleBuffer` for real-time events
3. Parse player join/leave patterns with regex
4. Maintain count with server restart detection
5. Add to `MetricsSnapshot` as optional field

### Status

**Deferred** - Not included in Epic 12 scope.

---

## Integration Points

### Scheduler Service (Epic 7/8)

Metrics collection follows the established job pattern:

```python
# In jobs/metrics_collection.py
from vintagestory_api.services.scheduler import get_scheduler_service

def setup_metrics_collection_job():
    scheduler = get_scheduler_service()
    scheduler.add_interval_job(
        collect_metrics,
        seconds=10,
        job_id="metrics_collection"
    )
```

### Server Service

Metrics service depends on ServerService for:
- Game server PID discovery
- Server running state detection

### Dashboard (Stories 12.4-12.6)

Frontend integration:
- Story 12.4: Stat cards showing latest metrics
- Story 12.5: Time-series charts with Recharts
- Story 12.6: Quick action links (not metrics-related)

---

## API Endpoints (Story 12.3)

### GET /api/v1alpha1/metrics

Returns current metrics and historical data:

```json
{
  "status": "ok",
  "data": {
    "current": {
      "timestamp": "2026-01-15T10:30:00Z",
      "api_memory_mb": 128.5,
      "api_cpu_percent": 2.3,
      "game_memory_mb": 512.0,
      "game_cpu_percent": 15.2
    },
    "history": [
      {
        "timestamp": "2026-01-15T09:30:00Z",
        "api_memory_mb": 125.2,
        "api_cpu_percent": 1.8,
        "game_memory_mb": 508.3,
        "game_cpu_percent": 12.1
      }
      // ... up to 360 samples (1 hour)
    ]
  }
}
```

### Security

- **Authentication**: Required (Admin role)
- **Rate limiting**: Standard API rate limits apply
- **No sensitive data**: Metrics are operational data only

---

## Summary of Decisions

| Decision | Choice | Status |
|----------|--------|--------|
| Process metrics library | psutil | Approved |
| Game server PID discovery | ServerService._process.pid | Approved |
| Charting library | Recharts | Approved |
| Metrics storage | collections.deque ring buffer | Approved |
| Player count | Deferred to future epic | Deferred |

---

_Created: 2026-01-15 (Story 12.1)_
