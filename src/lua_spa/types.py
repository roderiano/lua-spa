"""Shared type definitions and configuration for the lua-spa framework."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)

class LuaTemplateConfig:
    """Configuration loaded from lua_template/spa.config.json.

    Stores the entry component, mount ID, initial props, and server settings
    for the SPA application.
    """

    entry_component: str
    mount_id: str
    initial_props: Mapping[str, Any]
    host: str
    port: int
    router: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ComponentDefinition:
    """Represents a parsed .lspa component source file.

    Stores the component's template HTML, compiled client script (JavaScript),
    Python block source, and import map (component aliases to relative paths).
    """

    name: str
    template: str
    client_script: str
    python_block: str
    imports: Mapping[str, str]


@dataclass(frozen=True)
class StateField:
    """Declarative state field for list-based State definitions in .lspa components.

    Used to define initial state: name identifies the state variable, from_prop
    optionally seeds it from a component prop, default is the fallback value,
    and cast specifies the type to coerce ("int", "float", "str", "bool", "raw").
    """

    name: str
    from_prop: str | None = None
    default: Any = None
    cast: str = "raw"


class ClientMethods:
    """Helper methods available for Python client classes in .lspa components.

    Provides methods like add(), set(), sub(), toggle() that return operation
    mappings for state mutations, executed on the client side.
    """

    def add(self, state: str, value: Any = 1) -> dict[str, Any]:
        """Return an add operation: increment state by value (default 1)."""
        return {"op": "add", "state": state, "value": value}

    def sub(self, state: str, value: Any = 1) -> dict[str, Any]:
        """Return a sub operation: decrement state by value (default 1)."""
        return {"op": "sub", "state": state, "value": value}

    def set(self, state: str, value: Any) -> dict[str, Any]:
        """Return a set operation: assign value to state."""
        return {"op": "set", "state": state, "value": value}

    def toggle(self, state: str) -> dict[str, Any]:
        """Return a toggle operation: flip a boolean state."""
        return {"op": "toggle", "state": state}


class Component:
    """Base component class available to .lspa Python scripts.

    Subclass this or define a context(props) and client() pair to build
    a component's server-side and client-side behavior.
    """


def load_lua_template_config(config_file: Path) -> LuaTemplateConfig:
    """Load SPA configuration from a JSON file.

    Reads lua_template/spa.config.json and returns a LuaTemplateConfig with entry_component,
    mount_id, initial_props, host, and port. Raises FileNotFoundError if the
    file doesn't exist, ValueError if fields are malformed.
    """
    if not config_file.exists():
        raise FileNotFoundError(f"LuaTemplate config file not found: {config_file}")

    raw = config_file.read_text(encoding="utf-8")
    data = json.loads(raw)

    entry_component = str(data.get("entry_component", "App"))
    mount_id = str(data.get("mount_id", "app"))

    initial_props = data.get("initial_props", {})
    if not isinstance(initial_props, dict):
        raise ValueError("lua_template config field 'initial_props' must be an object")

    server = data.get("server", {})
    if server is None:
        server = {}
    if not isinstance(server, dict):
        raise ValueError("lua_template config field 'server' must be an object")

    host = str(server.get("host", "127.0.0.1"))
    raw_port = server.get("port", 8000)
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as error:
        raise ValueError("lua_template config field 'server.port' must be an integer") from error

    return LuaTemplateConfig(
        entry_component=entry_component,
        mount_id=mount_id,
        initial_props=initial_props,
        host=host,
        port=port,
        router=data.get("router"),
    )
