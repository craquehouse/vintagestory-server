"""Webhook alerts for available mod updates (Story 14.6, ADR-6).

The webhook URL is a secret: it is never logged, and neither is an httpx exception
message, which can contain the URL. Failures are logged by status code or error type.
"""

from __future__ import annotations

import re
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


_LINE_BREAKS = re.compile(r"\s*[\r\n]+\s*")


def _one_line(text: str | None) -> str:
    """Mod database text on one line, so a name cannot forge extra summary lines."""
    return _LINE_BREAKS.sub(" ", text or "")


def _line(item: ModUpdateStatusItem) -> str:
    compatibility = _COMPATIBILITY_LABELS.get(
        item.offered_compatibility or "", item.offered_compatibility or "unknown"
    )
    name = _one_line(item.name or item.slug)
    installed = _one_line(item.installed_version)
    offered = _one_line(item.offered_version)
    return f"- {name}: {installed} → {offered} ({compatibility})"


def summarize(items: list[ModUpdateStatusItem], limit: int = CONTENT_LIMIT) -> str:
    """One line per mod under a count header, cut to `limit` with "…and N more".

    At least one mod is always named: a first line too long to fit is shortened.
    """
    count = len(items)
    content = f"{count} mod {'update' if count == 1 else 'updates'} available:"
    for index, item in enumerate(items):
        line = "\n" + _line(item)
        rest = count - index - 1
        more = f"\n…and {rest} more" if rest else ""
        if len(content) + len(line) + len(more) <= limit:
            content += line
            continue
        if index == 0:
            room = limit - len(content) - len(more) - 1
            return content + line[:room] + "…" + more
        # The previous line reserved room for this note
        return content + f"\n…and {count - index} more"
    return content


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
