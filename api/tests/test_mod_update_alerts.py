"""Tests for mod update webhook alerts (Story 14.6, ADR-6)."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from vintagestory_api.models.mod_updates import Compatibility, ModUpdateStatusItem
from vintagestory_api.models.mods import ModInfo
from vintagestory_api.services.mod_api import ModApiClient
from vintagestory_api.services.mod_update_alerts import (
    CONTENT_LIMIT,
    build_payload,
    is_discord_webhook,
    send_update_alert,
    summarize,
)
from vintagestory_api.services.mod_updates import ModUpdateService, ModUpdateStore

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


FIXTURES = Path(__file__).parent / "fixtures" / "moddb"
MOD_URL = "https://mods.vintagestory.at/api/mod/carryon"


class FakeModSource:
    def __init__(self, cache_dir: Path) -> None:
        self.api_client = ModApiClient(cache_dir=cache_dir)
        self.version = "1.14.1"

    def list_mods(self) -> list[ModInfo]:
        return [
            ModInfo(
                filename="carryon.zip",
                slug="carryon",
                version=self.version,
                enabled=True,
                installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                name="Carry On",
            )
        ]


def make_service(tmp_path: Path, webhook: str | None = DISCORD) -> ModUpdateService:
    return ModUpdateService(
        store=ModUpdateStore(tmp_path / "state"),
        mod_source=FakeModSource(tmp_path / "cache"),
        game_version_provider=lambda: "1.22.7",
        webhook_url_provider=lambda: webhook,
    )


def carryon(newest_first: list[str] | None = None) -> dict[str, object]:
    data = json.loads((FIXTURES / "mod_carryon.json").read_text())
    if newest_first:
        template = dict(data["mod"]["releases"][0])
        extra = [
            {**template, "modversion": v, "fileid": 900 + i, "tags": ["1.22.7"]}
            for i, v in enumerate(newest_first)
        ]
        data["mod"]["releases"] = extra + data["mod"]["releases"]
    return data


class TestAlertsAfterCheck:
    @respx.mock
    @pytest.mark.asyncio
    async def test_alerts_once_per_mod_and_version(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        hook = respx.post(DISCORD).mock(return_value=Response(204))
        service = make_service(tmp_path)

        await service.check()
        await service.check()

        assert hook.call_count == 1
        assert service.store.notified_version("carryon") == "1.14.3"

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_repeat_after_restart(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        hook = respx.post(DISCORD).mock(return_value=Response(204))
        await make_service(tmp_path).check()

        await make_service(tmp_path).check()  # new service and store: as after a restart

        assert hook.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_newer_offered_version_alerts_again(self, tmp_path: Path) -> None:
        lookup = respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        requests: list[httpx.Request] = []
        respx.post(DISCORD).mock(side_effect=capture(requests, Response(204)))
        service = make_service(tmp_path)
        await service.check()

        lookup.mock(return_value=Response(200, json=carryon(["1.14.4"])))
        await service.check()

        assert len(requests) == 2
        assert "1.14.4" in json.loads(requests[1].content)["content"]

    @respx.mock
    @pytest.mark.asyncio
    @pytest.mark.parametrize("failure", [Response(429, json={"retry_after": 2}), Response(500)])
    async def test_failed_delivery_is_retried_next_check(
        self, tmp_path: Path, failure: Response
    ) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        hook = respx.post(DISCORD).mock(side_effect=[failure, Response(204)])
        service = make_service(tmp_path)

        summary = await service.check()

        assert hook.call_count == 1  # a 429 is not retried within the same check
        assert service.store.notified_version("carryon") is None
        assert (summary.checked, summary.failed) == (1, 0)

        await service.check()

        assert hook.call_count == 2
        assert service.store.notified_version("carryon") == "1.14.3"

    @respx.mock
    @pytest.mark.asyncio
    async def test_delivery_timeout_does_not_affect_the_check(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        respx.post(DISCORD).mock(side_effect=httpx.ConnectTimeout("timed out"))
        service = make_service(tmp_path)

        summary = await service.check()

        assert (summary.checked, summary.failed) == (1, 0)
        assert service.get_status()[0].offered_version == "1.14.3"

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_webhook_sends_nothing(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        hook = respx.post(DISCORD).mock(return_value=Response(204))

        await make_service(tmp_path, webhook=None).check()

        assert not hook.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_up_to_date_mods_are_not_alerted(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        hook = respx.post(DISCORD).mock(return_value=Response(204))
        source = FakeModSource(tmp_path / "cache")
        source.version = "1.14.3"
        service = ModUpdateService(
            store=ModUpdateStore(tmp_path / "state"),
            mod_source=source,
            game_version_provider=lambda: "1.22.7",
            webhook_url_provider=lambda: DISCORD,
        )

        await service.check()

        assert not hook.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_records_are_pruned_with_uninstalled_mods(self, tmp_path: Path) -> None:
        respx.get(MOD_URL).mock(return_value=Response(200, json=carryon()))
        respx.post(DISCORD).mock(return_value=Response(204))
        service = make_service(tmp_path)
        await service.check()

        service.store.prune(set())

        assert service.store.notified_version("carryon") is None

