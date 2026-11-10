"""Story 14.0 Task 3: prototype the update-alert payload and check delivery rules locally.

Run with the API virtualenv (uses its httpx): api/.venv/bin/python webhook_probe.py
"""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import httpx

DISCORD_CONTENT_LIMIT = 2000
received: list[dict] = []


def is_discord(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in {"discord.com", "discordapp.com", "ptb.discord.com", "canary.discord.com"} and parsed.path.startswith("/api/webhooks/")


def summary(updates: list[dict]) -> str:
    head = f"{len(updates)} mod update{'s' if len(updates) != 1 else ''} available:"
    lines = [head]
    for i, u in enumerate(updates):
        line = f"- {u['name']}: {u['installed']} → {u['offered']} ({u['compatibility']})"
        remaining = len(updates) - i
        tail = f"…and {remaining} more"
        if sum(len(l) + 1 for l in lines) + len(line) + len(tail) + 1 > DISCORD_CONTENT_LIMIT:
            lines.append(tail)
            break
        lines.append(line)
    return "\n".join(lines)


def build_payload(url: str, updates: list[dict]) -> dict:
    content = summary(updates)
    if is_discord(url):
        return {"content": content, "allowed_mentions": {"parse": []}}
    return {"event": "mod_updates_available", "content": content, "updates": updates}


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/elsewhere")
            self.end_headers()
            return
        received.append({"path": self.path, "type": self.headers.get("Content-Type"), "body": json.loads(body)})
        self.send_response(429 if self.path == "/limited" else 204)
        if self.path == "/limited":
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"message": "You are being rate limited.", "retry_after": 1.5, "global": false}')
            return
        self.end_headers()

    def log_message(self, *args):
        pass


async def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), Receiver)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    many = [{"slug": f"mod{i}", "name": f"Example Mod Number {i} @everyone", "installed": "1.0.0",
             "offered": "1.1.0", "compatibility": "compatible"} for i in range(80)]
    few = many[:2]

    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        r = await client.post(base + "/hook", json=build_payload(base + "/hook", few))
        print("generic delivery:", r.status_code, "| fields:", sorted(received[-1]["body"]))
        r = await client.post(base + "/redirect", json=build_payload(base + "/redirect", few))
        print("redirect not followed:", r.status_code, r.is_redirect)
        r = await client.post(base + "/limited", json=build_payload(base + "/limited", few))
        print("rate limited:", r.status_code, "retry_after =", r.json().get("retry_after"))

    discord = build_payload("https://discord.com/api/webhooks/123/abc", many)
    print("discord fields:", sorted(discord), "| allowed_mentions:", discord["allowed_mentions"])
    print("discord content length:", len(discord["content"]), "| ends with:", discord["content"].splitlines()[-1])
    print("discord host detection:", [is_discord(u) for u in (
        "https://discord.com/api/webhooks/1/x", "https://discordapp.com/api/webhooks/1/x",
        "https://evil.example/discord.com/api/webhooks/1/x", "https://discord.com.evil.example/api/webhooks/1/x")])
    print("sample content:\n" + summary(few))
    server.shutdown()


asyncio.run(main())
