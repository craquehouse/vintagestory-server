"""Tests for mod update webhook alerts (Story 14.6, ADR-6)."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.models.mod_updates import Compatibility, ModUpdateStatusItem
from vintagestory_api.services.mod_update_alerts import (
    CONTENT_LIMIT,
    build_payload,
    is_discord_webhook,
    send_update_alert,
    summarize,
)

DISCORD = "https://discord.com/api/webhooks/123/discord-secret-token"
OTHER = "https://hooks.example.com/alerts/other-secret-token"


def item(
    slug: str,
    installed: str = "1.0.0",
    offered: str = "1.1.0",
    compatibility: Compatibility = "compatible",
    name: str | None = None,
) -> ModUpdateStatusItem:
    return ModUpdateStatusItem(
        slug=slug,
        name=name if name is not None else slug.title(),
        installed_version=installed,
        status="update_available",
        offered_version=offered,
        offered_compatibility=compatibility,
        offered_prerelease=False,
        checked_at=datetime(2026, 11, 9, tzinfo=UTC),
    )


class TestDiscordDetection:
    @pytest.mark.parametrize(
        "url",
        [
            "https://discord.com/api/webhooks/1/x",
            "https://discordapp.com/api/webhooks/1/x",
            "https://ptb.discord.com/api/webhooks/1/x",
            "https://canary.discord.com/api/webhooks/1/x",
            "https://DISCORD.com/api/webhooks/1/x",
        ],
    )
    def test_discord_webhooks(self, url: str) -> None:
        assert is_discord_webhook(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://discord.com/channels/1/2",
            "https://evil.discord.com.example.com/api/webhooks/1/x",
            "https://example.com/api/webhooks/1/x",
            OTHER,
        ],
    )
    def test_other_receivers(self, url: str) -> None:
        assert not is_discord_webhook(url)


class TestPayload:
    def test_summary_lines(self) -> None:
        content = summarize(
            [
                item("carryon", "1.14.1", "1.14.3", name="Carry On"),
                item("demo", compatibility="not_verified"),
            ]
        )

        assert content == (
            "2 mod updates available:\n"
            "- Carry On: 1.14.1 → 1.14.3 (compatible)\n"
            "- Demo: 1.0.0 → 1.1.0 (not verified)"
        )

    def test_singular_header(self) -> None:
        assert summarize([item("demo")]).startswith("1 mod update available:\n")

    def test_summary_is_truncated_to_the_discord_limit(self) -> None:
        items = [item(f"mod{i:03d}", name="A long mod name " * 3) for i in range(200)]

        content = summarize(items)

        assert len(content) <= CONTENT_LIMIT
        assert content.endswith("more")
        shown = content.count("\n- ")
        assert f"…and {200 - shown} more" in content

    def test_a_single_huge_name_is_cut_to_the_limit(self) -> None:
        content = summarize([item("huge", name="x" * 5000)])

        assert len(content) <= CONTENT_LIMIT

    def test_discord_payload_has_only_content_and_suppressed_mentions(self) -> None:
        payload = build_payload(DISCORD, [item("demo", name="@everyone")])

        assert set(payload) == {"content", "allowed_mentions"}
        assert payload["allowed_mentions"] == {"parse": []}

    def test_other_receiver_payload(self) -> None:
        payload = build_payload(OTHER, [item("carryon", "1.14.1", "1.14.3", name="Carry On")])

        assert payload == {
            "event": "mod_updates_available",
            "content": "1 mod update available:\n- Carry On: 1.14.1 → 1.14.3 (compatible)",
            "updates": [
                {
                    "slug": "carryon",
                    "name": "Carry On",
                    "installed": "1.14.1",
                    "offered": "1.14.3",
                    "compatibility": "compatible",
                }
            ],
        }


def capture(
    requests: list[httpx.Request], response: Response
) -> Callable[[httpx.Request], Response]:
    def handler(request: httpx.Request) -> Response:
        requests.append(request)
        return response

    return handler


class TestSend:
    @respx.mock
    @pytest.mark.asyncio
    async def test_discord_204_is_delivered(self) -> None:
        requests: list[httpx.Request] = []
        respx.post(DISCORD).mock(side_effect=capture(requests, Response(204)))

        assert await send_update_alert(DISCORD, [item("demo")]) is True
        body = json.loads(requests[0].content)
        assert set(body) == {"content", "allowed_mentions"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_other_receiver_200_is_delivered(self) -> None:
        requests: list[httpx.Request] = []
        respx.post(OTHER).mock(side_effect=capture(requests, Response(200, json={"ok": True})))

        assert await send_update_alert(OTHER, [item("demo")]) is True
        assert json.loads(requests[0].content)["event"] == "mod_updates_available"

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "response",
        [
            Response(429, json={"retry_after": 1.5, "global": False}),
            Response(500),
            Response(404, json={"message": "Unknown Webhook", "code": 10015}),
            Response(302, headers={"Location": "https://attacker.example.com/collect"}),
        ],
    )
    async def test_non_2xx_is_not_delivered(
        self, response: Response, capsys: pytest.CaptureFixture[str]
    ) -> None:
        route = respx.post(DISCORD).mock(return_value=response)
        follow = respx.post("https://attacker.example.com/collect").mock(
            return_value=Response(200)
        )

        assert await send_update_alert(DISCORD, [item("demo")]) is False
        assert route.call_count == 1
        assert not follow.called
        out = capsys.readouterr().out
        assert "mod_update_alert_failed" in out
        assert "secret-token" not in out

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [
            httpx.ConnectTimeout(f"timed out connecting to {DISCORD}"),
            httpx.ConnectError(f"cannot connect to {DISCORD}"),
            httpx.ReadTimeout(f"read timed out from {DISCORD}"),
        ],
    )
    async def test_transport_errors_are_logged_without_the_url(
        self, error: Exception, capsys: pytest.CaptureFixture[str]
    ) -> None:
        respx.post(DISCORD).mock(side_effect=error)

        assert await send_update_alert(DISCORD, [item("demo")]) is False
        out = capsys.readouterr().out
        assert "mod_update_alert_failed" in out
        assert type(error).__name__ in out
        assert "secret-token" not in out

    @pytest.mark.asyncio
    async def test_unusable_url_is_not_delivered(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert await send_update_alert("https://", [item("demo")]) is False
        assert "mod_update_alert_failed" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_nothing_to_send(self) -> None:
        assert await send_update_alert(DISCORD, []) is True
