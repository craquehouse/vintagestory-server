# Story 14.6: Webhook Alerts

Status: in-progress

## Story

As an **administrator**,
I want **an alert sent to my chat when updates appear**,
so that **I find out without opening the UI**.

## Acceptance Criteria

1. **Given** I am an Admin
   **When** I save an http or https webhook URL in API settings
   **Then** it is stored, and reads report only whether it is configured
   **And** the URL is never logged, never returned by any endpoint, and not readable by a Monitor
   *(FR149)*

2. **Given** a check (on-demand or scheduled) finds a newly available update
   **When** a webhook is configured
   **Then** one alert covers that mod and version
   **And** later checks do not repeat it, including after an API restart; a newer offered version alerts again
   *(FR150)*

3. **Given** the webhook URL is a Discord webhook
   **When** an alert is sent
   **Then** the payload is only `content` and `allowed_mentions: {parse: []}`, with `content` within 2000 characters
   **And** any other receiver gets `event`, `content` and an `updates` list (ADR-6)

4. **Given** webhook delivery fails, times out, redirects or is rate limited (429)
   **When** the check continues
   **Then** the failure is logged without the URL, the check result is unaffected, nothing is recorded as sent, and the alert is retried on the next check
   *(FR151)*

5. **Given** I open the API settings
   **When** I view the update alerts setting
   **Then** I see whether a webhook is configured and can set, replace or clear it; the field never shows the stored URL

## Tasks / Subtasks

- [x] Task 1: Webhook setting with redacted reads + tests (AC: 1)
  - [x] 1.1: `ApiSettings.mod_update_webhook_url: str | None` with validation: http or https, a host, at most 2048 characters; `""` or `null` clears it; error messages never include the value
  - [x] 1.2: `GET /config/api` returns `mod_update_webhook_configured` instead of the URL; `POST /config/api/settings/mod_update_webhook_url` returns `{key, configured}` and logs `configured`, never the value
  - [x] 1.3: Tests: set, clear, invalid scheme, too long, redacted read and update response, no URL in logs, Monitor 403

- [x] Task 2: Alert delivery + tests (AC: 3, 4)
  - [x] 2.1: `services/mod_update_alerts.py`: Discord detection (ADR-6 hosts and `/api/webhooks/` path), payloads, summary lines `- {name}: {installed} → {offered} ({compatibility})` truncated with "…and N more" to 2000 characters
  - [x] 2.2: `send_update_alert(url, items)`: POST JSON with a 10 s timeout and `follow_redirects=False`; True only for 2xx; failures logged with status or error type, never the URL or exception text
  - [x] 2.3: Tests with respx: Discord 204 and 429, other receiver payload, 302 not followed, timeout, connection error, truncation, URL absent from captured logs

- [x] Task 3: Deduplicated alerts after each check + tests (AC: 2, 4)
  - [x] 3.1: Store: `ModUpdatesFile.notified` (modid → offered version alerted), with store accessors; pruned with uninstalled mods
  - [x] 3.2: `ModUpdateService.check()` sends one alert for update_available mods whose offered version is not yet recorded, after saving the check; records them only after a 2xx and saves; never raises from alerting
  - [x] 3.3: Webhook URL from API settings via an injectable provider
  - [x] 3.4: Tests: alert once, no repeat across checks or a reloaded store, newer version alerts again, failure retried next check, no webhook sends nothing, check summary unchanged when delivery fails

- [x] Task 4: Settings UI + tests (AC: 5)
  - [x] 4.1: Web types: `modUpdateWebhookConfigured`; update response `configured`
  - [x] 4.2: "Update Alerts" group in `ApiSettingsPanel`: Configured / Not configured, a URL input (never prefilled) with Save, and Clear when configured; client-side http/https check; toasts
  - [x] 4.3: Tests

- [ ] Task 5: Manual verification and final validation (AC: all)
  - [ ] 5.1: Throwaway container: set the webhook from the UI, run a check, confirm one Discord message, run another check and confirm no repeat; confirm the URL appears in no container log line and no API response
  - [ ] 5.2: Obtain the test Discord webhook URL only through the private secret prompt; never write it to the repo, story, logs or chat
  - [ ] 5.3: Run `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

FR149–FR151 (ADR-6). Alerts follow the update check, so scheduled checks (Story 14.5) and on-demand checks both alert. **Out of scope:** other channels, per-mod mute, a test-send button.

### Rules (ADR-6)

- Sending: http or https only, 10 s timeout, no redirects followed. A 3xx is a failure.
- Discord URL: host `discord.com`, `discordapp.com`, `ptb.discord.com` or `canary.discord.com`, path starting `/api/webhooks/`. Payload `{"content": summary, "allowed_mentions": {"parse": []}}`.
- Other URL: `{"event": "mod_updates_available", "content": summary, "updates": [{"slug", "name", "installed", "offered", "compatibility"}]}`; `slug` is the installed modid.
- Deduplication: one alert per mod and offered version, recorded only after a 2xx, so a failure is retried on the next check. A 429 is not retried within the same check.
- The URL is stored in plain text in `api-settings.json`, the same trust boundary as the rest of the state (ADR-6 Consequences).
- Logging: structlog only; never pass the URL or an `httpx` exception message (which can contain the URL). `httpx`'s own INFO request log includes the URL; stdlib logging is not configured, so it stays at WARNING and is not emitted. Verify this in the container logs.

### Existing code to reuse

| Need | Use |
|---|---|
| Settings | `services/api_settings.py`, `routers/config.py` (`GET /config/api`, `POST /config/api/settings/{key}`) |
| Update check | `ModUpdateService.check()`, `ModUpdateStore` (`services/mod_updates.py`) |
| Settings UI | `features/settings/ApiSettingsPanel.tsx`, `SettingGroup`, `hooks/use-api-settings.ts` |

### Testing Requirements

- API tests with `respx`; assert captured log output never contains the test URL.
- Web tests follow `ApiSettingsPanel.test.tsx`.
- Task 5 verification against a real Discord webhook is required (epics.md).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.6]
- [Source: _bmad-output/planning-artifacts/prd.md] FR149–FR151
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-6
- [Source: _bmad-output/implementation-artifacts/14-0-spike/webhook_probe.py] Discord probe from Story 14.0

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
