"""HTTP server for serving the SPA framework.

Provides a ThreadingHTTPServer handler that serves the built HTML view
and logs request details.
"""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


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

        if self.path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        body = framework.build_view()
        payload = body.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


    def log_message(self, format: str, *args: Any) -> None:
        """Suppress HTTP server logging."""
        return


class SpaServer:
    """Server wrapper for running the SPA framework.

    Provides a serve() method that starts a ThreadingHTTPServer
    listening on the specified host and port.
    """

    @staticmethod
    def serve(framework: Any, host: str, port: int) -> None:
        """Start the HTTP server for the SPA framework.

        Args:
            framework: A SpaFramework instance.
            host: Host to bind to (e.g., "127.0.0.1").
            port: Port to bind to (e.g., 8000).
        """
        server = ThreadingHTTPServer((host, port), _SpaHandler)
        server.lua_framework = framework  # type: ignore
        with server:
            server.serve_forever()
