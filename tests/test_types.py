from __future__ import annotations

import json
from pathlib import Path

from lua_spa.types import (
    ClientMethods,
    _infer_mount_id_from_router,
    load_lua_template_config,
)


def test_client_methods_operations() -> None:
    # Given: a ClientMethods instance
    client = ClientMethods()

    # When: each operation method is called

    # Then: returned dicts carry the correct op values
    assert client.add("count", 2)["op"] == "add"
    assert client.sub("count", 1)["op"] == "sub"
    assert client.set("name", "x")["op"] == "set"
    assert client.toggle("open")["op"] == "toggle"


def test_load_lua_template_config_defaults_do_not_depend_on_router(tmp_path: Path) -> None:
    # Given: a spa.config.json with router and server sections
    config_file = tmp_path / "spa.config.json"
    config_file.write_text(
        json.dumps(
            {
                "router": {
                    "mount_id": "root",
                    "routes": [{"path": "/", "component": "Home"}],
                },
                "server": {"host": "0.0.0.0", "port": 9090},
            }
        ),
        encoding="utf-8",
    )

    # When: the config is loaded
    cfg = load_lua_template_config(config_file)

    # Then: mount uses standardized default; host and port are read from server
    assert cfg.mount_id == "app"
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9090


def test_load_lua_template_config_explicit_mount(tmp_path: Path) -> None:
    # Given: a spa.config.json with explicit mount plus router block
    config_file = tmp_path / "spa.config.json"
    config_file.write_text(
        json.dumps(
            {
                "mount_id": "root-app",
                "router": {
                    "routes": [{"path": "/", "component": "Home"}],
                },
            }
        ),
        encoding="utf-8",
    )

    # When: the config is loaded
    cfg = load_lua_template_config(config_file)

    # Then: explicit mount is preserved
    assert cfg.mount_id == "root-app"


def test_load_lua_template_config_invalid_server_port(tmp_path: Path) -> None:
    # Given: a config with a non-numeric server port
    config_file = tmp_path / "spa.config.json"
    config_file.write_text(
        json.dumps({"server": {"port": "abc"}}),
        encoding="utf-8",
    )

    # When: the config is loaded

    # Then: ValueError is raised for the invalid port
    try:
        load_lua_template_config(config_file)
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_router_inference_helpers() -> None:
    # Given: a router config with a mount_id
    router_cfg = {"mount_id": "app-root"}

    # When: mount inference helper extracts values from the config

    # Then: mount id is correctly returned
    assert _infer_mount_id_from_router(router_cfg) == "app-root"


def test_types_invalid_config_shapes(tmp_path: Path) -> None:
    # Given: config files with various invalid shapes (missing, bad router, bad props, bad server)

    # When: each invalid config is loaded

    # Then: appropriate exceptions are raised for each case
    missing = tmp_path / "missing.json"
    try:
        load_lua_template_config(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")

    invalid_router = tmp_path / "invalid_router.json"
    invalid_router.write_text(json.dumps({"router": []}), encoding="utf-8")
    try:
        load_lua_template_config(invalid_router)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    invalid_props = tmp_path / "invalid_props.json"
    invalid_props.write_text(json.dumps({"initial_props": []}), encoding="utf-8")
    try:
        load_lua_template_config(invalid_props)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    invalid_server = tmp_path / "invalid_server.json"
    invalid_server.write_text(json.dumps({"server": []}), encoding="utf-8")
    try:
        load_lua_template_config(invalid_server)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_types_inference_none_paths() -> None:
    # Given: None configs and empty dicts

    # When: mount inference helper is called with edge-case inputs

    # Then: it returns None gracefully
    assert _infer_mount_id_from_router(None) is None
    assert _infer_mount_id_from_router({}) is None
