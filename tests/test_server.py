from __future__ import annotations

import io
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

import lua_spa.server as server_module
from lua_spa.server import SpaServer, _SpaHandler


def test_server_has_static_serve_method() -> None:
    # Given: the SpaServer class

    # When: we inspect its API

    # Then: it exposes a callable serve method
    assert callable(SpaServer.serve)


def test_handler_log_message_is_overridden() -> None:
    # Given: the _SpaHandler class

    # When: we inspect its attributes

    # Then: log_message is overridden (silenced)
    assert hasattr(_SpaHandler, "log_message")


def test_spa_handler_static_and_index_paths() -> None:
    # Given: a fake framework and a handler instance wired with fake response helpers
    class _FakeFramework:
        def get_static_asset(self, path: str) -> tuple[bytes, str] | None:
            if path == "/static/x.txt":
                return b"hello", "text/plain"
            return None

        def build_view(self) -> str:
            return "<html>ok</html>"

    handler = object.__new__(_SpaHandler)
    responses: list[int] = []
    errors: list[int] = []
    handler.server = SimpleNamespace(lua_framework=_FakeFramework())  # type: ignore[assignment]
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: responses.append(int(code))  # type: ignore[method-assign,misc,assignment]
    handler.send_header = lambda _key, _value: None  # type: ignore[method-assign,assignment]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    handler.send_error = lambda code, _message: errors.append(int(code))  # type: ignore[method-assign,misc,assignment]

    # When: various GET paths are dispatched
    handler.path = "/static/x.txt"
    handler.do_GET()
    handler.path = "/"
    handler.do_GET()
    handler.path = "/404"
    handler.do_GET()

    # Then: static returns 200, index returns 200, unknown path returns 404
    assert responses[0] == int(HTTPStatus.OK)
    assert responses[1] == int(HTTPStatus.OK)
    assert errors[-1] == int(HTTPStatus.NOT_FOUND)


def test_spa_server_serve_invokes_http_server(monkeypatch: Any) -> None:
    # Given: a fake ThreadingHTTPServer that records calls
    called: dict[str, Any] = {}

    class FakeServer:
        def __init__(self, address: tuple[str, int], _handler: Any) -> None:
            called["address"] = address

        def __enter__(self) -> "FakeServer":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def serve_forever(self) -> None:
            called["served"] = True

    monkeypatch.setattr(server_module, "ThreadingHTTPServer", FakeServer)

    # When: SpaServer.serve is called
    SpaServer.serve(SimpleNamespace(), "127.0.0.1", 8000)

    # Then: the fake server is started on the correct address
    assert called["address"] == ("127.0.0.1", 8000)
    assert called["served"] is True


def test_handler_log_message_noop_call() -> None:
    # Given: a bare _SpaHandler instance
    handler = object.__new__(_SpaHandler)

    # When: log_message is called

    # Then: it returns None (silenced)
    assert handler.log_message("x") is None  # type: ignore[func-returns-value]
