#!/usr/bin/env python3
"""Answer mod database requests from recorded files (Story 20.6, Epic 20 ADR-9).

Serves a directory by its manifest.json: each entry names a request (path and query) and
the file that answers it. A request with no recording gets 404 and a plain-text body that
names it, so the API reports an external error (502) instead of "mod not found". File names
come only from the manifest, never from a request. Standard library only; it runs inside
the image in the E2E script (scripts/e2e-ci.sh) and on a developer's machine.

Usage: python3 scripts/moddb-replay.py --dir web/e2e/fixtures/moddb [--port 8099]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypeGuard
from urllib.parse import parse_qsl, urlencode, urlsplit

DEFAULT_PORT = 8099


@dataclass(frozen=True)
class Recording:
    """One recorded answer: the bytes of its file, its status and its content type."""

    body: bytes
    status: int
    content_type: str


class ManifestError(Exception):
    """The manifest cannot be served as it is."""


def is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """A JSON object (json.loads gives str keys)."""
    return isinstance(value, dict)


def is_json_array(value: object) -> TypeGuard[list[object]]:
    """A JSON array."""
    return isinstance(value, list)


def request_key(target: str) -> str:
    """The path plus the query with its parameters sorted: `/api/mods?gameversion=1`."""
    parts = urlsplit(target)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return f"{parts.path}?{query}" if query else parts.path


def load_recordings(directory: Path) -> dict[str, Recording]:
    """Read the manifest and every file it names; refuse anything unsafe or ambiguous."""
    manifest_path = directory / "manifest.json"
    try:
        manifest: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ManifestError(f"cannot read {manifest_path}: {e}") from e
    entries = manifest.get("requests") if is_json_object(manifest) else None
    if not is_json_array(entries):
        raise ManifestError(f"{manifest_path} has no list of requests")

    table: dict[str, Recording] = {}
    for index, entry in enumerate(entries):
        if not is_json_object(entry):
            raise ManifestError(f"entry {index} is not an object")
        request = entry.get("request")
        name = entry.get("file")
        if not isinstance(request, str) or not request.startswith("/"):
            raise ManifestError(f"entry {index} has no request path")
        if not isinstance(name, str) or not name:
            raise ManifestError(f"entry {index} ({request}) names no file")
        if "/" in name or "\\" in name or ".." in name:
            raise ManifestError(f"entry {index} ({request}) names an unsafe file: {name}")
        path = directory / name
        if not path.is_file():
            raise ManifestError(f"entry {index} ({request}) names a missing file: {name}")
        key = request_key(request)
        if key in table:
            raise ManifestError(f"entry {index}: request {key} is recorded twice")
        status = entry.get("status", 200)
        content_type = entry.get("content_type", "application/json")
        if not isinstance(status, int) or not isinstance(content_type, str):
            raise ManifestError(f"entry {index} ({request}) has a bad status or content_type")
        table[key] = Recording(path.read_bytes(), status, content_type)
    return table


def make_handler(
    recordings: dict[str, Recording], log_user_agent: bool
) -> type[BaseHTTPRequestHandler]:
    """A request handler class that answers from `recordings`."""

    class ReplayHandler(BaseHTTPRequestHandler):
        server_version = "moddb-replay"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            """Silence the default access log; `note` writes one line per request."""

        def note(self, event: str) -> None:
            line = f"{event} {self.command} {self.path}"
            if log_user_agent:
                line += f" user_agent={self.headers.get('User-Agent', '')}"
            print(line, flush=True)

        def answer(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self.answer(200, "text/plain", b"ok")
                return
            recording = recordings.get(request_key(self.path))
            if recording is None:
                self.note("no_recording")
                body = f"No recording for GET {self.path}".encode()
                self.answer(404, "text/plain; charset=utf-8", body)
                return
            self.note("served")
            self.answer(recording.status, recording.content_type, recording.body)

        def refuse(self) -> None:
            self.note("refused")
            self.answer(405, "text/plain; charset=utf-8", b"Method not allowed")

        do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = refuse

    return ReplayHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer mod database requests from recordings.")
    parser.add_argument("--dir", required=True, type=Path, help="holds manifest.json")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    # 0.0.0.0: in CI the container is on a private Docker network and publishes no port
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--log-user-agent", action="store_true", help="add each request's User-Agent to its log"
    )
    args = parser.parse_args(argv)

    try:
        recordings = load_recordings(args.dir)
    except ManifestError as e:
        print(f"moddb-replay: {e}", file=sys.stderr, flush=True)
        return 1

    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(recordings, args.log_user_agent)
    )
    print(
        f"moddb-replay: {len(recordings)} recordings on {args.host}:{server.server_port}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
