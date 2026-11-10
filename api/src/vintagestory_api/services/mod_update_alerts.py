"""Webhook alerts for available mod updates (Story 14.6, ADR-6).

The webhook URL is a secret: it is never logged, and neither is an httpx exception
message, which can contain the URL. Failures are logged by status code or error type.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx
import structlog

from vintagestory_api.models.mod_updates import ModUpdateStatusItem

logger = structlog.get_logger()

DISCORD_HOSTS = frozenset(
    {"discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"}
)
CONTENT_LIMIT = 2000
"""Discord's limit for a message's `content`; applied to every receiver."""
TIMEOUT_SECONDS = 10.0
EVENT = "mod_updates_available"

_COMPATIBILITY_LABELS = {
    "compatible": "compatible",
    "not_verified": "not verified",
    "incompatible": "incompatible",
}


def is_discord_webhook(url: str) -> bool:
    """Whether the URL is a Discord webhook (ADR-6 hosts, path `/api/webhooks/`)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return host in DISCORD_HOSTS and parts.path.startswith("/api/webhooks/")


def _line(item: ModUpdateStatusItem) -> str:
    compatibility = _COMPATIBILITY_LABELS.get(
        item.offered_compatibility or "", item.offered_compatibility or "unknown"
    )
    name = item.name or item.slug
    return f"- {name}: {item.installed_version} → {item.offered_version} ({compatibility})"


def summarize(items: list[ModUpdateStatusItem], limit: int = CONTENT_LIMIT) -> str:
    """One line per mod under a count header, cut to `limit` with "…and N more"."""
    count = len(items)
    content = f"{count} mod {'update' if count == 1 else 'updates'} available:"
    for index, item in enumerate(items):
        line = "\n" + _line(item)
        remaining = count - index - 1
        # Reserve room for the "more" note unless this is the last line
        reserve = len(f"\n…and {count - index} more") if remaining else 0
        if len(content) + len(line) + reserve > limit:
            more = f"\n…and {count - index} more"
            if len(content) + len(more) <= limit:
                return content + more
            break
        content += line
    # Only reachable when a single line or the note alone cannot fit
    return content if len(content) <= limit else content[: limit - 1] + "…"


def build_payload(url: str, items: list[ModUpdateStatusItem]) -> dict[str, Any]:
    """Receiver-specific payload (ADR-6): Discord gets only content and mentions off."""
    content = summarize(items)
    if is_discord_webhook(url):
        # Mod names come from the mod database; never let them ping anyone
        return {"content": content, "allowed_mentions": {"parse": []}}
    return {
        "event": EVENT,
        "content": content,
        "updates": [
            {
                "slug": item.slug,
                "name": item.name,
                "installed": item.installed_version,
                "offered": item.offered_version,
                "compatibility": item.offered_compatibility,
            }
            for item in items
        ],
    }


async def send_update_alert(url: str, items: list[ModUpdateStatusItem]) -> bool:
    """POST an alert for these updates. True only for a 2xx response.

    No redirects are followed and the timeout is 10 seconds. Never raises for delivery
    failures, and never logs the URL.
    """
    if not items:
        return True
    receiver = "discord" if is_discord_webhook(url) else "webhook"
    payload = build_payload(url, items)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
            response = await client.post(url, json=payload)
    except (httpx.HTTPError, httpx.InvalidURL) as e:
        logger.warning("mod_update_alert_failed", receiver=receiver, error_type=type(e).__name__)
        return False

    if 200 <= response.status_code < 300:
        logger.info("mod_update_alert_sent", receiver=receiver, updates=len(items))
        return True
    logger.warning(
        "mod_update_alert_failed", receiver=receiver, status_code=response.status_code
    )
    return False
