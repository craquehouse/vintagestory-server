# Pending Restart Pattern

_Implementation guidance for the server restart notification system_

## Overview

Changes to mods and configurations require a server restart to take effect. The pending restart pattern tracks these changes and provides clear UX for users to either:

1. Apply changes immediately (restart now)
2. Batch multiple changes before restarting

---

## State Model

### Backend State

The `pending_restart` state is tracked in the server's application state:

```python
# api/src/vintagestory_api/models/server.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PendingChange(BaseModel):
    """A change that requires server restart."""
    reason: str          # Human-readable description
    category: str        # "mod", "config", "settings"
    timestamp: datetime  # When the change was made
    details: dict = {}   # Additional context (e.g., mod slug, config file)

class PendingRestartState(BaseModel):
    """State for pending restart tracking."""
    pending_restart: bool = False
    changes: list[PendingChange] = []

    def require_restart(self, reason: str, category: str, **details) -> None:
        """Register a change that requires restart."""
        self.pending_restart = True
        self.changes.append(PendingChange(
            reason=reason,
            category=category,
            timestamp=datetime.utcnow(),
            details=details
        ))

    def clear(self) -> None:
        """Clear pending restart state (after successful restart)."""
        self.pending_restart = False
        self.changes = []

    @property
    def change_count(self) -> int:
        """Number of pending changes."""
        return len(self.changes)
```

### State Persistence

The pending restart state is persisted to `state.json` along with other server state:

```json
{
  "server": {
    "state": "running",
    "version": "1.21.6"
  },
  "pending_restart": {
    "pending_restart": true,
    "changes": [
      {
        "reason": "Mod 'smithingplus' installed",
        "category": "mod",
        "timestamp": "2025-12-28T10:30:00Z",
        "details": {"slug": "smithingplus", "version": "1.8.3"}
      },
      {
        "reason": "Mod 'carrycapacity' enabled",
        "category": "mod",
        "timestamp": "2025-12-28T10:31:00Z",
        "details": {"slug": "carrycapacity"}
      }
    ]
  }
}
```

---

## Triggering Events

### Category: `mod`

| Event | Reason String | Details |
|-------|--------------|---------|
| Mod installed | "Mod '{name}' installed" | `{slug, version, filename}` |
| Mod removed | "Mod '{name}' removed" | `{slug}` |
| Mod enabled | "Mod '{name}' enabled" | `{slug}` |
| Mod disabled | "Mod '{name}' disabled" | `{slug}` |
| Mod updated | "Mod '{name}' updated to v{version}" | `{slug, old_version, new_version}` |

### Category: `config` (Future - Epic 6)

| Event | Reason String | Details |
|-------|--------------|---------|
| Config file saved | "Configuration '{filename}' updated" | `{filename, path}` |

### Category: `settings` (Future - Epic 7)

| Event | Reason String | Details |
|-------|--------------|---------|
| Server settings changed | "Server settings updated" | `{changed_fields}` |
| Whitelist modified | "Whitelist {action}" | `{action: added/removed, player}` |

---

## Clear Conditions

The pending restart state is cleared when:

1. **Server successfully restarted** - After the server stops and starts again
2. **Manual acknowledgment** - User explicitly dismisses without restart (rare)

### Restart Success Detection

```python
async def on_server_started(self):
    """Called when server transitions to 'running' state."""
    if self.pending_restart_state.pending_restart:
        # Server started successfully, clear pending changes
        self.pending_restart_state.clear()
        await self.save_state()
        logger.info("pending_restart_cleared", reason="server_restarted")
```

---

## API Response Extension

### Status Endpoint

The `/api/v1alpha1/server/status` endpoint includes pending restart info:

```json
{
  "status": "ok",
  "data": {
    "state": "running",
    "version": "1.21.6",
    "uptime_seconds": 3600,
    "pending_restart": true,
    "pending_changes": [
      {
        "reason": "Mod 'smithingplus' installed",
        "category": "mod",
        "timestamp": "2025-12-28T10:30:00Z"
      }
    ]
  }
}
```

### Mod Operation Responses

Mod operations that trigger pending restart include it in their response:

```json
{
  "status": "ok",
  "data": {
    "slug": "smithingplus",
    "version": "1.8.3",
    "installed": true
  },
  "pending_restart": true,
  "pending_change_count": 1
}
```

---

## Frontend Implementation

### PendingRestartBanner Component

A persistent banner displayed in the header when `pending_restart` is true:

```typescript
// web/src/components/PendingRestartBanner.tsx
import { useServerStatus } from "@/hooks/use-server-status";
import { Button } from "@/components/ui/button";
import { RefreshCw, X } from "lucide-react";

export function PendingRestartBanner() {
  const { data: status, isLoading } = useServerStatus();
  const restartMutation = useRestartServer();

  // Don't show if no pending restart or still loading
  if (isLoading || !status?.pending_restart) {
    return null;
  }

  const changeCount = status.pending_changes?.length || 0;

  return (
    <div className="bg-warning/10 border-b border-warning px-4 py-2 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <RefreshCw className="h-4 w-4 text-warning animate-spin-slow" />
        <span className="text-sm font-medium">
          Restart required · {changeCount} pending {changeCount === 1 ? "change" : "changes"}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => restartMutation.mutate()}
          disabled={restartMutation.isPending}
        >
          {restartMutation.isPending ? "Restarting..." : "Restart Now"}
        </Button>
      </div>
    </div>
  );
}
```

### Banner Placement

The banner should appear below the main header, above page content:

```typescript
// web/src/components/layout/Layout.tsx
export function Layout({ children }) {
  return (
    <div className="min-h-screen">
      <Header />
      <PendingRestartBanner />
      <main className="container py-6">{children}</main>
    </div>
  );
}
```

### Optimistic Updates

When performing mod operations, optimistically update the pending restart state:

```typescript
// web/src/api/hooks/use-install-mod.ts
export function useInstallMod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: installMod,
    onSuccess: (data) => {
      // Invalidate mod list
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });

      // Optimistically update status to show pending restart
      queryClient.setQueryData(queryKeys.server.status, (old) => ({
        ...old,
        pending_restart: true,
        pending_changes: [
          ...(old?.pending_changes || []),
          {
            reason: `Mod '${data.name}' installed`,
            category: "mod",
            timestamp: new Date().toISOString(),
          },
        ],
      }));
    },
  });
}
```

---

## UX Considerations

### Visual Design

1. **Color**: Use warning color (yellow/amber) for the banner - not critical but needs attention
2. **Animation**: Subtle spin animation on refresh icon to draw eye without being distracting
3. **Persistence**: Banner remains visible across all pages until restart or dismiss
4. **Position**: Below header, above content - visible but not blocking

### Change Summary Tooltip

On hover over change count, show tooltip with recent changes:

```
[hover on "3 pending changes"]
┌───────────────────────────────────────┐
│ Pending Changes:                      │
│ • Mod 'smithingplus' installed        │
│ • Mod 'carrycapacity' enabled         │
│ • Mod 'temporal-tinkerer' disabled    │
└───────────────────────────────────────┘
```

### Server Stopped Behavior

When server is already stopped, the banner should indicate restart is not needed:

```typescript
if (status?.state === "stopped") {
  return (
    <div className="bg-muted/50 border-b px-4 py-2">
      <span className="text-sm text-muted-foreground">
        Changes pending · Will take effect on next server start
      </span>
    </div>
  );
}
```

---

## Testing Considerations

### Unit Tests

```python
def test_require_restart_adds_change():
    state = PendingRestartState()
    assert not state.pending_restart

    state.require_restart("Mod installed", "mod", slug="test")

    assert state.pending_restart
    assert state.change_count == 1
    assert state.changes[0].reason == "Mod installed"

def test_clear_resets_state():
    state = PendingRestartState()
    state.require_restart("Change 1", "mod")
    state.require_restart("Change 2", "mod")

    state.clear()

    assert not state.pending_restart
    assert state.change_count == 0
```

### Integration Tests

```python
async def test_install_mod_sets_pending_restart(client, admin_headers):
    # Install a mod
    response = await client.post(
        "/api/v1alpha1/mods/install",
        json={"slug": "smithingplus"},
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify pending restart flag
    assert data.get("pending_restart") == True

    # Verify status endpoint reflects pending restart
    status_response = await client.get(
        "/api/v1alpha1/server/status",
        headers=admin_headers
    )
    assert status_response.json()["data"]["pending_restart"] == True

async def test_restart_clears_pending_restart(client, admin_headers):
    # Create pending restart state
    await client.post(
        "/api/v1alpha1/mods/install",
        json={"slug": "smithingplus"},
        headers=admin_headers
    )

    # Restart server
    await client.post("/api/v1alpha1/server/restart", headers=admin_headers)

    # Wait for server to come back up
    await asyncio.sleep(5)

    # Verify pending restart cleared
    status_response = await client.get(
        "/api/v1alpha1/server/status",
        headers=admin_headers
    )
    assert status_response.json()["data"]["pending_restart"] == False
```

---

## Implementation Order

1. **Story 5.1**: Add `PendingRestartState` model and persistence
2. **Story 5.2-5.5**: Each mod operation calls `require_restart()`
3. **Story 5.6**: Implement `PendingRestartBanner` component in UI
4. **Epic 6-7**: Extend to config and settings changes

---

_Last updated: 2025-12-28_
