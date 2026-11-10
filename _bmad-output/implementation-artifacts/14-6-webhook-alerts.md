# Story 14.6: Webhook Alerts

Status: review

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

- [x] Task 5: Manual verification and final validation (AC: all)
  - [x] 5.1: Throwaway container: set the webhook from the UI, run a check, confirm one Discord message, run another check and confirm no repeat; confirm the URL appears in no container log line and no API response
  - [x] 5.2: Obtain the test Discord webhook URL only through the private secret prompt; never write it to the repo, story, logs or chat
  - [x] 5.3: Run `just check`; update the Dev Agent Record and File List

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] An invalid `api-settings.json` logs pydantic's error text, which quotes the webhook URL, on every settings read [services/api_settings.py `get_settings`]
- [x] [AI-Review][Low] Alerts run inside the check lock, so a slow receiver delays the next check by up to 10 s (accepted: bounded, and it keeps overlapping checks from sending the same alert twice)
- [x] [AI-Review][Low] `updateApiSetting`'s doc comment was left above `setModUpdateWebhook` [web/src/api/config.ts]
- [x] [AI-Review][Low] The generic `useUpdateApiSetting` would cache the URL if called with the webhook key [web/src/hooks/use-api-settings.ts]
- [x] [AI-Review][Low] A first line too long for the limit produced an alert naming no mod; a newline in a mod name forged summary lines [services/mod_update_alerts.py]
- [x] [AI-Review][Low] A mod downgraded below an already-alerted version is not alerted again (accepted: ADR-6 "one alert per mod and version")
- [x] [AI-Review][Low] The configured status is not part of the input's accessible description [ModUpdateWebhookSetting.tsx]

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

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Browser verification screenshots were kept locally only (`.playwright-mcp/`, git-ignored). The Discord URL was never typed in the browser or written to any file in the repo.

### Completion Notes List

- Task 1: `ApiSettings.mod_update_webhook_url` (`str | None`, max 2048) with a validator for http or https and a host; `""` or `null` clears it. Validation messages never include the value. `ApiSettings.redacted()` replaces it with `mod_update_webhook_configured` for `GET /config/api`; updating it returns `{key, configured}` and logs `configured` and `was_configured` instead of values (`SECRET_SETTINGS`). 13 tests.
- Task 2: `services/mod_update_alerts.py`: Discord detection (ADR-6 hosts, case-insensitive, `/api/webhooks/` path), summary lines with compatibility labels, cut with "…and N more" to 2000 characters for every receiver, receiver-specific payloads, and `send_update_alert` (10 s timeout, no redirects, True only for 2xx; failures logged by status code or exception type, never the URL or exception text). 26 tests, including replayed Discord 204, 429 and 404 bodies and a 302 that is not followed.
- Task 3: `ModUpdatesFile.notified` (modid → offered version alerted) with store accessors and pruning. `ModUpdateService.check()` sends one alert for update_available mods whose offered version is not recorded, inside the check lock and after saving, and records them only after a 2xx. The webhook URL comes from API settings on each check (`webhook_url_provider`). 9 tests.
- Task 4: `ModUpdateWebhookSetting` in a new "Update Alerts" group: Configured / Not configured, a URL input that is never prefilled, Save (client-side http/https check) and Clear. It uses its own `useSetModUpdateWebhook` mutation, which is not optimistic, so the URL is never written into the cached settings. 8 tests.
- Task 5: Throwaway container (Carry On 1.14.1 and Auto Map Markers 5.0.2, both with updates). Set a local receiver URL from the UI ("Webhook saved", status Configured, field empty); two checks produced exactly one alert with the generic payload (`event`, `content`, `updates` with installed modids) and recorded both versions as notified. Then cleared `notified` in the container's state file and restarted it, and set a real Discord webhook through the settings API from a file obtained through the private secret prompt: the check logged `mod_update_alert_sent receiver=discord updates=2`, a second check sent nothing, and no `mod_update_alert_failed`. Searched for the URL: 0 container log lines, 0 API responses, only `api-settings.json` (ADR-6); `httpx` printed no request lines. Clear from the UI showed "Not configured" and removed the URL from the container's state. No browser console errors.

- Review: verdict Changes Requested (M1). Fixed: settings load failures log field names and messages only (`errors(include_input=False)`), tested with a short and an over-long invalid URL; the summary always names at least one mod (an oversized first line is shortened) and mod database text is put on one line; `updateApiSetting` refuses secret keys and the generic hook never caches them; the doc comment is back on `updateApiSetting`; the input's description starts with Configured / Not configured. Accepted L1 and L5 as recorded above. 7 tests added; `just check` passes with 2023 API and 2999 web tests.

### File List

- Created: `api/src/vintagestory_api/services/mod_update_alerts.py`, `api/tests/test_mod_update_alerts.py`
- Created: `web/src/features/settings/ModUpdateWebhookSetting.tsx`, `web/src/features/settings/ModUpdateWebhookSetting.test.tsx`
- Modified: `api/src/vintagestory_api/services/api_settings.py`, `api/src/vintagestory_api/routers/config.py`
- Modified: `api/src/vintagestory_api/models/mod_updates.py`, `api/src/vintagestory_api/services/mod_updates.py`
- Modified: `api/tests/test_api_settings.py`, `api/tests/test_routers_config.py`
- Modified: `web/src/api/types.ts`, `web/src/api/config.ts`, `web/src/api/config.test.ts`, `web/src/hooks/use-api-settings.ts`
- Modified: `web/src/features/settings/ApiSettingsPanel.tsx`, `web/src/features/settings/ApiSettingsPanel.test.tsx`

## Change Log

- 2026-11-09: Webhook alerts for mod updates: Admin-only redacted setting, receiver-specific delivery without redirects, one alert per mod and version recorded after a 2xx, and the settings UI. Verified against a local receiver and a real Discord webhook. `just check` passes with 2020 API tests and 2997 web tests.
- 2026-11-09: Code review (GLM-5.3-Flash, Changes Requested). Fixed M1 and L2–L4, L6; accepted L1 and L5.

## Senior Developer Review (AI)

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `1c95b34`^..`482cddc`
**Outcome:** Changes Requested

**Summary:** ACs 2–5 met; AC 1 partial: the write path never echoes the URL, Monitor is blocked and httpx request logs are not emitted, but a hand-edited invalid settings file logged the URL. Deduplication, Discord payloads, back-compatibility and the admin-only SSRF boundary checked clean. No suppressions.

### Action Items

- [x] [Medium] Settings load error logs the webhook URL
- [x] [Low] Alert inside the check lock (accepted)
- [x] [Low] Misplaced doc comment
- [x] [Low] Generic settings hook could cache the secret
- [x] [Low] Summary could name no mod; newlines forge lines
- [x] [Low] No re-alert after a downgrade (accepted)
- [x] [Low] Configured status not in the input's description

