"""HTTP server for serving the SPA framework.

Provides a ThreadingHTTPServer handler that serves the built HTML view
and logs request details.
"""

from __future__ import annotations

import os
import time
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


_clients: set[Any] = set()
_clients_lock = threading.Lock()
_watch_started = threading.Event()


def _notify_clients() -> None:
    with _clients_lock:
        snapshot = list(_clients)
    dead = []
    for client in snapshot:
        try:
            client.write(b"data: reload\n\n")
            client.flush()
        except Exception:
            dead.append(client)
    if dead:
        with _clients_lock:
            for d in dead:
                _clients.discard(d)


def _watch_files(path: str, framework: Any) -> None:
    last_mtime: dict[str, float] = {}

    while True:
        changed = False

        for root, _, files in os.walk(path):
            if "__pycache__" in root:
                continue

            for f in files:
                if not f.endswith((".py", ".lspa", ".css", ".js")):
                    continue

                full = os.path.join(root, f)

                try:
                    mtime = os.path.getmtime(full)
                except FileNotFoundError:
                    continue

                if full not in last_mtime:
                    last_mtime[full] = mtime
                elif last_mtime[full] != mtime:
                    last_mtime[full] = mtime
                    changed = True

        if changed:
            print("Changes detected, rebuilding view...")
            try:
                reload_components = getattr(framework, "reload_components", None)
                if callable(reload_components):
                    reload_components()
                framework.build_view()
            except Exception as exc:
                print(f"Build error: {exc}")
            else:
                _notify_clients()

        time.sleep(0.5)


class _SpaHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the SPA framework.

    Serves the root and /index.html with the built view HTML.
    Returns 404 for all other paths.
    """

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests.

        Serves the root (/) and /index.html with the built SPA view.
        Returns 404 for all other paths.
        """
        framework = self.server.lua_framework  # type: ignore
        request_path = urlparse(self.path).path

        if request_path == "/__reload__":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            with _clients_lock:
                _clients.add(self.wfile)

            try:
                while True:
                    time.sleep(1)
            except Exception:
                pass
            finally:
                with _clients_lock:
                    _clients.discard(self.wfile)
            return

        static_asset = framework.get_static_asset(request_path)
        if static_asset is not None:
            payload, content_type = static_asset
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if request_path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        body = framework.build_view()

        if getattr(self.server, "reload_enabled", False):
            inject = (
                "\n<script>\n"
                "const __luaReload = new EventSource('/__reload__');\n"
                "__luaReload.onmessage = () => window.location.reload();\n"
                "</script>\n"
            )
            body = body.replace("</body>", inject + "</body>")

        payload = body.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        return


class SpaServer:
    @staticmethod
    def serve(framework: Any, host: str, port: int, reload: bool = False) -> None:
        server = ThreadingHTTPServer((host, port), _SpaHandler)
        server.lua_framework = framework  # type: ignore
        server.reload_enabled = reload  # type: ignore

        if reload and not _watch_started.is_set():
            _watch_started.set()
            watch_path = (
                str(framework._view_file.parents[1]) if hasattr(framework, "_view_file") else "."
            )
            threading.Thread(target=_watch_files, args=(watch_path, framework), daemon=True).start()
            print(f"Live reload activated. Watching {watch_path} for file changes...")

        with server:
            server.serve_forever()
