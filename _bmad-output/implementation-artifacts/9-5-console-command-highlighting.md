# Story 9.5: Console Command Highlighting

Status: ready-for-dev

## Story

As an **administrator**,
I want **my commands to be visually distinct in the console**,
So that **I can easily identify what I typed vs server output**.

## Acceptance Criteria

1. **Given** I send a command via the console
   **When** the command is echoed in the terminal
   **Then** it is displayed in a distinct color (e.g., cyan or yellow)
   *(Covers FR50)*

2. **Given** I send a command via the console
   **When** the command appears in the output
   **Then** it is prefixed with `[CMD]` marker
   *(Covers FR51)*

3. **Given** server output arrives
   **When** it is displayed in the terminal
   **Then** it uses the default console color (not the command color)

## Tasks / Subtasks

- [ ] Task 1: Add command echo with [CMD] prefix on backend + tests (AC: 2)
  - [ ] Subtask 1.1: Modify `ServerService.send_command()` to echo command to console buffer with `[CMD]` prefix
  - [ ] Subtask 1.2: Write tests verifying command echo appears in buffer with correct prefix
  - [ ] Subtask 1.3: Ensure echo happens immediately after command is sent to stdin

- [ ] Task 2: Apply ANSI color codes for command echo + tests (AC: 1, 3)
  - [ ] Subtask 2.1: Add ANSI escape code constant for command color (cyan: `\033[36m`)
  - [ ] Subtask 2.2: Wrap `[CMD] <command>` with ANSI color codes in echo output
  - [ ] Subtask 2.3: Include reset code (`\033[0m`) after command text
  - [ ] Subtask 2.4: Write tests verifying ANSI codes are present in echoed output

- [ ] Task 3: Verify xterm.js rendering + tests (AC: 1, 3)
  - [ ] Subtask 3.1: Verify xterm.js correctly interprets ANSI color codes (already supported by default)
  - [ ] Subtask 3.2: Add integration test to web confirming colored command display
  - [ ] Subtask 3.3: Test that server output remains uncolored (default foreground)

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- DEBUG mode gating for test/dev endpoints
- Timing-safe comparison for sensitive data (API keys, passwords)
- Never log sensitive data in plaintext
- Note: Commands may contain sensitive data - do NOT log command content, only log `websocket_command_received` event

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-web` - Run web tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Current Console Command Flow:**
1. User types command in `ConsolePanel.tsx` input field
2. `sendCommand(command)` from `use-console-websocket.ts` sends JSON `{type: "command", content: "..."}` via WebSocket
3. Backend `console.py` receives message, calls `service.send_command(command)`
4. `ServerService.send_command()` writes to game server stdin
5. Game server output (including any response) comes back via stdout capture to `ConsoleBuffer`
6. `ConsoleBuffer.append()` notifies WebSocket subscribers
7. Frontend receives text via WebSocket `onMessage`, writes to xterm.js via `terminal.writeln()`

**Key Insight:** Commands are NOT currently echoed back. The game server may or may not echo them depending on the command. We need to explicitly echo user commands with `[CMD]` prefix and color.

**Implementation Location:**
- Modify: `api/src/vintagestory_api/services/server.py` - `send_command()` method
- The echo should go through the `console_buffer.append()` so it's visible to all WebSocket subscribers

**ANSI Color Codes for xterm.js:**
- xterm.js supports ANSI escape sequences by default
- Cyan: `\033[36m` or `\x1b[36m`
- Reset: `\033[0m` or `\x1b[0m`
- Example: `\033[36m[CMD] /help\033[0m`

**Terminal Theme Colors (from `terminal-themes.ts`):**
- Dark mode cyan: `#89dceb` (Catppuccin Mocha)
- Light mode cyan: `#04a5e5` (Catppuccin Latte)
- Using ANSI cyan will automatically use theme's cyan color

### Existing Code References

**Console command handling (console.py:384-410):**
```python
# Handle command messages
if message.get("type") == "command":
    command = message.get("content", "")
    # ... validation ...
    success = await service.send_command(command)
```

**ServerService.send_command (server.py):**
```python
async def send_command(self, command: str) -> bool:
    """Send a command to the game server stdin."""
    if not self._process or self._process.stdin is None:
        return False

    logger.debug("server_send_command", command_length=len(command))
    self._process.stdin.write(f"{command}\n".encode())
    await self._process.stdin.drain()
    return True
```

**ConsoleBuffer.append (console.py):**
```python
async def append(self, line: str) -> None:
    """Add a line to the buffer and notify subscribers."""
    logger.debug("console_append", line_length=len(line), subscriber_count=len(self._subscribers))
    self._buffer.append(line)
    # Notify all subscribers...
```

### Implementation Details

**Modify `send_command()` to echo:**
```python
async def send_command(self, command: str) -> bool:
    """Send a command to the game server stdin and echo to console."""
    if not self._process or self._process.stdin is None:
        return False

    logger.debug("server_send_command", command_length=len(command))

    # Echo command with [CMD] prefix and ANSI cyan color
    # \x1b[36m = cyan, \x1b[0m = reset
    echo_line = f"\x1b[36m[CMD] {command}\x1b[0m"
    await self.console_buffer.append(echo_line)

    # Send to game server
    self._process.stdin.write(f"{command}\n".encode())
    await self._process.stdin.drain()
    return True
```

**Key Points:**
- Echo BEFORE sending to server ensures user sees their command immediately
- ANSI codes are part of the string - xterm.js will interpret them
- Using `\x1b` (Python escape) is equivalent to `\033` (octal)
- Console buffer stores raw text including ANSI codes

### Project Structure Notes

**Files to Modify:**
- `api/src/vintagestory_api/services/server.py` - Add echo logic to `send_command()`

**Files to Create:**
- None - all changes are modifications to existing files

**Test Files:**
- `api/tests/test_server.py` - Add tests for command echo with ANSI codes
- `web/src/components/ConsolePanel.test.tsx` - Add integration test for colored display (optional - ANSI rendering is xterm.js responsibility)

### Previous Story Intelligence (9-4)

**Patterns Established:**
- Debug logging uses `logger.debug()` with snake_case event names
- Request context middleware provides `request_id` for tracing
- Runtime debug toggle available via `/api/v1alpha1/debug` endpoints

**Applicable Learnings:**
- Add debug log for command echo: `logger.debug("command_echoed", command_length=len(command))`
- Keep implementation simple - avoid over-engineering

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: epics.md#Story-9.5] - Story requirements (FR50, FR51)
- [Source: api/src/vintagestory_api/services/server.py] - send_command() implementation
- [Source: api/src/vintagestory_api/routers/console.py] - WebSocket command handling
- [Source: web/src/lib/terminal-themes.ts] - Terminal color definitions

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
