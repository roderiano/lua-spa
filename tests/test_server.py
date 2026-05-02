from __future__ import annotations

import io
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any

import pytest

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


def test_spa_handler_injects_reload_script_only_when_enabled() -> None:
    # Given: a fake framework that always returns HTML with a closing body tag
    class _FakeFramework:
        def get_static_asset(self, _path: str) -> None:
            return None

        def build_view(self) -> str:
            return "<html><body>ok</body></html>"

    handler = object.__new__(_SpaHandler)
    handler.server = SimpleNamespace(lua_framework=_FakeFramework(), reload_enabled=True)  # type: ignore[assignment]
    handler.path = "/"
    handler.wfile = io.BytesIO()
    handler.send_response = lambda _code: None  # type: ignore[method-assign,assignment]
    handler.send_header = lambda _key, _value: None  # type: ignore[method-assign,assignment]
    handler.end_headers = lambda: None  # type: ignore[method-assign]

    # When: GET / is handled with reload enabled
    handler.do_GET()

    # Then: the payload includes the EventSource script
    body = handler.wfile.getvalue().decode("utf-8")
    assert "new EventSource('/__reload__')" in body


def test_spa_handler_skips_reload_script_when_disabled() -> None:
    # Given: a fake framework and reload disabled in server state
    class _FakeFramework:
        def get_static_asset(self, _path: str) -> None:
            return None

        def build_view(self) -> str:
            return "<html><body>ok</body></html>"

    handler = object.__new__(_SpaHandler)
    handler.server = SimpleNamespace(lua_framework=_FakeFramework(), reload_enabled=False)  # type: ignore[assignment]
    handler.path = "/"
    handler.wfile = io.BytesIO()
    handler.send_response = lambda _code: None  # type: ignore[method-assign,assignment]
    handler.send_header = lambda _key, _value: None  # type: ignore[method-assign,assignment]
    handler.end_headers = lambda: None  # type: ignore[method-assign]

    # When: GET / is handled with reload disabled
    handler.do_GET()

    # Then: no EventSource injection is present
    body = handler.wfile.getvalue().decode("utf-8")
    assert "new EventSource('/__reload__')" not in body


def test_watch_files_rebuilds_before_notifying(monkeypatch: Any) -> None:
    # Given: mtime changes across loops and a framework that rebuilds successfully
    class _StopWatch(Exception):
        pass

    events: list[str] = []
    state = {"mtime_calls": 0, "sleep_calls": 0}

    def fake_walk(_path: str) -> list[tuple[str, list[str], list[str]]]:
        return [("/tmp", [], ["App.lspa"])]

    def fake_getmtime(_path: str) -> float:
        state["mtime_calls"] += 1
        return 1.0 if state["mtime_calls"] == 1 else 2.0

    def fake_sleep(_seconds: float) -> None:
        state["sleep_calls"] += 1
        if state["sleep_calls"] >= 2:
            raise _StopWatch()

    class _FakeFramework:
        def reload_components(self) -> None:
            events.append("reload")

        def build_view(self) -> str:
            events.append("build")
            return "<html><body>ok</body></html>"

    monkeypatch.setattr(server_module.os, "walk", fake_walk)
    monkeypatch.setattr(server_module.os.path, "getmtime", fake_getmtime)
    monkeypatch.setattr(server_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(server_module, "_notify_clients", lambda: events.append("notify"))

    # When: the watcher runs until our controlled stop condition
    with pytest.raises(_StopWatch):
        server_module._watch_files(".", _FakeFramework())

    # Then: component reload and rebuild happen before notify
    assert events == ["reload", "build", "notify"]


def test_watch_files_does_not_notify_when_rebuild_fails(monkeypatch: Any) -> None:
    # Given: mtime changes but build_view fails
    class _StopWatch(Exception):
        pass

    state = {"mtime_calls": 0, "sleep_calls": 0, "notified": 0}

    def fake_walk(_path: str) -> list[tuple[str, list[str], list[str]]]:
        return [("/tmp", [], ["App.lspa"])]

    def fake_getmtime(_path: str) -> float:
        state["mtime_calls"] += 1
        return 1.0 if state["mtime_calls"] == 1 else 2.0

    def fake_sleep(_seconds: float) -> None:
        state["sleep_calls"] += 1
        if state["sleep_calls"] >= 2:
            raise _StopWatch()

    class _FakeFramework:
        def reload_components(self) -> None:
            return None

        def build_view(self) -> str:
            raise RuntimeError("boom")

    monkeypatch.setattr(server_module.os, "walk", fake_walk)
    monkeypatch.setattr(server_module.os.path, "getmtime", fake_getmtime)
    monkeypatch.setattr(server_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(
        server_module,
        "_notify_clients",
        lambda: state.__setitem__("notified", state["notified"] + 1),
    )

    # When: the watcher runs until our controlled stop condition
    with pytest.raises(_StopWatch):
        server_module._watch_files(".", _FakeFramework())

    # Then: notify is not called because build failed
    assert state["notified"] == 0


def test_watch_files_without_reload_method_still_notifies(monkeypatch: Any) -> None:
    # Given: a framework without reload_components but with successful build
    class _StopWatch(Exception):
        pass

    events: list[str] = []
    state = {"mtime_calls": 0, "sleep_calls": 0}

    def fake_walk(_path: str) -> list[tuple[str, list[str], list[str]]]:
        return [("/tmp", [], ["App.lspa"])]

    def fake_getmtime(_path: str) -> float:
        state["mtime_calls"] += 1
        return 1.0 if state["mtime_calls"] == 1 else 2.0

    def fake_sleep(_seconds: float) -> None:
        state["sleep_calls"] += 1
        if state["sleep_calls"] >= 2:
            raise _StopWatch()

    class _FakeFramework:
        def build_view(self) -> str:
            events.append("build")
            return "<html><body>ok</body></html>"

    monkeypatch.setattr(server_module.os, "walk", fake_walk)
    monkeypatch.setattr(server_module.os.path, "getmtime", fake_getmtime)
    monkeypatch.setattr(server_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(server_module, "_notify_clients", lambda: events.append("notify"))

    # When: the watcher runs until our controlled stop condition
    with pytest.raises(_StopWatch):
        server_module._watch_files(".", _FakeFramework())

    # Then: build still runs and notifies even without reload_components
    assert events == ["build", "notify"]
