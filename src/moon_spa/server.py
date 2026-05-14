"""HTTP server for serving the SPA framework.

Provides a ThreadingHTTPServer handler that serves the built HTML view
and logs request details.
"""

from __future__ import annotations

import os
import json
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
                    print(f"Changes detected on '{f}', rebuilding view...")

        if changed:
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
        framework = self.server.moon_framework  # type: ignore
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
                "const __moonReload = new EventSource('/__reload__');\n"
                "__moonReload.onmessage = () => window.location.reload();\n"
                "</script>\n"
            )
            body = body.replace("</body>", inject + "</body>")

        payload = body.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for runtime server-call actions."""
        framework = self.server.moon_framework  # type: ignore
        request_path = urlparse(self.path).path

        if request_path != "/__moon_spa_action":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length_raw = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_raw)
        except ValueError:
            content_length = 0

        raw_body = self.rfile.read(max(0, content_length))
        try:
            payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload")
            return

        component_name = str(payload.get("component") or "")
        callable_kind = str(payload.get("kind") or "action")
        callable_name = str(payload.get("name") or "")
        props = payload.get("props")
        state = payload.get("state")

        if component_name == "" or callable_name == "":
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing component/name")
            return

        try:
            result = framework.execute_server_callable(
                component_name=component_name,
                kind=callable_kind,
                callable_name=callable_name,
                props=props if isinstance(props, dict) else {},
                state=state if isinstance(state, dict) else {},
            )
        except Exception as error:
            response = json.dumps({"ok": False, "error": str(error)}, ensure_ascii=True).encode(
                "utf-8"
            )
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return

        response = json.dumps({"ok": True, "result": result}, ensure_ascii=True).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:
        return


class SpaServer:
    @staticmethod
    def serve(framework: Any, host: str, port: int, reload: bool = False) -> None:
        server = ThreadingHTTPServer((host, port), _SpaHandler)
        server.moon_framework = framework  # type: ignore
        server.reload_enabled = reload  # type: ignore

        if reload and not _watch_started.is_set():
            _watch_started.set()
            watch_path = (
                str(framework._view_file.parents[1]) if hasattr(framework, "_view_file") else "."
            )
            try:
                relative_watch_path = os.path.relpath(watch_path, os.getcwd())
            except ValueError:
                relative_watch_path = watch_path
            threading.Thread(
                target=_watch_files,
                args=(relative_watch_path, framework),
                daemon=True,
            ).start()
            print("Live reload activated. " f"Watching {relative_watch_path} for file changes...")

        with server:
            server.serve_forever()
