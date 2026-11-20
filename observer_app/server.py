"""Dependency-free, loopback-only server for the Orbita root-task observer."""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DIST_DIRECTORY = REPOSITORY_ROOT / "dist"
PROJECTION_PATH = DIST_DIRECTORY / "data" / "root-task-observer.json"
MAX_REQUEST_BYTES = 4_096


def load_projection(path: Path = PROJECTION_PATH) -> dict[str, Any]:
    """Load the checked-in sanitized fixture projection, never raw protocol data."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("timeline"), list):
        raise ValueError("invalid observer projection")
    return value


@dataclass
class PreviewState:
    """Ephemeral UI state; it is intentionally not a Codex execution authority."""

    events: list[dict[str, str]] = field(default_factory=list)
    lifecycle: str = "Open"

    def apply(self, action: str) -> dict[str, str]:
        if action == "follow-up":
            event = {"kind": "preview", "title": "Follow-up staged locally", "detail": "Preview only: no Codex turn was started."}
        elif action == "interrupt":
            event = {"kind": "preview", "title": "Interrupt requested in preview", "detail": "Preview only: a real interrupt waits for correlated source evidence."}
        elif action == "finish":
            self.lifecycle = "Finished"
            event = {"kind": "preview", "title": "Task marked Finished locally", "detail": "Preview only: Finish never changes the source outcome."}
        else:
            raise ValueError("unsupported preview action")
        self.events.append(event)
        return event

    def snapshot(self, projection: dict[str, Any]) -> dict[str, Any]:
        return {"projection": projection, "preview": {"events": self.events, "lifecycle": self.lifecycle}}


class ObserverApplication:
    def __init__(self, projection_path: Path = PROJECTION_PATH) -> None:
        self.projection = load_projection(projection_path)
        self.preview = PreviewState()
        self.lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return self.preview.snapshot(self.projection)

    def action(self, name: str) -> dict[str, Any]:
        with self.lock:
            self.preview.apply(name)
            return self.preview.snapshot(self.projection)


def make_handler(application: ObserverApplication) -> type[SimpleHTTPRequestHandler]:
    class ObserverHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(DIST_DIRECTORY), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
            encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/projection":
                self._json(HTTPStatus.OK, application.snapshot())
                return
            if self.path == "/api/status":
                self._json(HTTPStatus.OK, {"mode": "fixture-preview", "network": "loopback-only", "runtime": application.projection.get("runtime")})
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.startswith("/api/preview/"):
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_REQUEST_BYTES:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"})
                return
            self.rfile.read(length)
            try:
                self._json(HTTPStatus.OK, application.action(self.path.rsplit("/", 1)[-1]))
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "unsupported preview action"})

    return ObserverHandler


def serve(port: int, open_browser: bool) -> None:
    application = ObserverApplication()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(application))
    address = f"http://127.0.0.1:{server.server_port}/"
    print(f"Orbita observer running at {address}")
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--open", action="store_true", help="open the loopback observer in the default browser")
    arguments = parser.parse_args()
    serve(arguments.port, arguments.open)


if __name__ == "__main__":
    main()
