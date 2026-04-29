from pathlib import Path

from lua_spa.app import create_default_framework


def test_create_default_framework_loads_components() -> None:
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)
    assert set(framework.component_names) == {"App", "Counter"}


def test_build_view_contains_spa_payload() -> None:
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    html = framework.build_view(
        {
            "title": "Lua SPA",
            "subtitle": "Prototype",
            "start": 2,
        }
    )

    assert "lua-spa-registry" in html
    assert "lua-spa-config" in html
    assert "Lua SPA" in html
    assert "window.LuaSpaRuntime.bootstrap()" in html
