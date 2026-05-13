from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from moon_spa.app import create_default_framework
from moon_spa.framework import SpaFramework
import moon_spa.framework as framework_module


def _assert_raises(
    exc_type: type[BaseException], fn: Callable[..., Any], *args: Any
) -> None:
    try:
        fn(*args)
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")


def test_framework_requires_view_file(tmp_path: Path) -> None:
    # Given: a components directory but no view file
    missing_view = tmp_path / "index.lspa"
    components = tmp_path / "components"
    components.mkdir()

    # When: SpaFramework is initialized with a missing view file

    # Then: FileNotFoundError is raised
    _assert_raises(FileNotFoundError, SpaFramework, missing_view, components)


def test_get_static_asset_for_logo_png() -> None:
    # Given: a default framework loaded from project root
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: requesting the logo image static asset
    asset = framework.get_static_asset("/static/logo.png")

    # Then: asset content is returned with an image MIME type
    assert asset is not None
    payload, mime = asset
    assert len(payload) > 0
    assert "image/" in mime


def test_get_static_asset_rejects_outside_static_root() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: requesting a path that traverses outside the static root

    # Then: None is returned (path traversal blocked)
    assert framework.get_static_asset("/static/../pyproject.toml") is None


def test_build_view_renders_html_shell() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: build_view is called
    html = framework.build_view()

    # Then: the output is a complete HTML document with SPA registry
    assert "<!doctype html>" in html.lower()
    assert "<style>" in html
    assert "moon-spa-registry" in html


def test_framework_parse_attributes_and_render_tag_match() -> None:
    # Given: a default framework and an attribute string with template expressions
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: attributes are parsed and a tag is rendered
    parsed = framework._parse_attributes(
        "title='{{ py.t }}' __props='{" + '"' + "extra" + '"' + ": 1}'",
        {"props": {}, "state": {}, "py": {"t": "ok"}},
    )
    rendered = framework._render_tag_match(
        "AppFooter", "", "", {"props": {}, "state": {}, "py": {}}
    )

    # Then: template expressions are resolved and component HTML is returned
    assert parsed["title"] == "ok"
    assert parsed["extra"] == 1
    assert "footer" in rendered


def test_framework_expand_child_components_supports_self_closing() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: a self-closing component tag is expanded
    output = framework._expand_child_components(
        "<div><Hero /></div>",
        {"props": {}, "state": {}, "py": {}},
    )

    # Then: the component HTML is inlined in place
    assert "hero__title" in output


def test_framework_get_static_favicon() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: requesting the favicon
    asset = framework.get_static_asset("/favicon.ico")

    # Then: the asset is found
    assert asset is not None


def test_framework_router_and_serialize_paths(tmp_path: Path) -> None:
    # Given: a default framework and a router-based framework with a missing initial path
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: serializing a payload with special characters and rendering a router view
    escaped = framework._serialize_json_payload({"x": "</script>"})
    router_framework = SpaFramework(
        view_file=root / "src" / "moon_template" / "index.lspa",
        components_dir=root / "src" / "moon_template" / "components",
        static_dir=root / "src" / "moon_template" / "static",
        router={
            "initial_path": "/missing",
            "routes": [
                {"path": "/", "component": "App"},
            ],
        },
    )
    html = router_framework.build_view()

    # Then: script tags are escaped and the SPA registry is present
    assert "<\\/script>" in escaped
    assert "moon-spa-registry" in html


def test_framework_serve_and_unknown_component(monkeypatch: Any) -> None:
    # Given: a default framework with a monkeypatched serve method
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)
    called: dict[str, Any] = {}

    def fake_serve(instance: Any, host: str, port: int, reload: bool = False) -> None:
        called["host"] = host
        called["port"] = port
        called["reload"] = reload
        called["instance"] = instance

    monkeypatch.setattr(framework_module.SpaServer, "serve", staticmethod(fake_serve))  # type: ignore[attr-defined]

    # When: serve is called with custom host/port, and an unknown component is rendered

    # Then: serve dispatches correctly and unknown component raises ValueError
    framework.serve("127.0.0.2", 9000)
    assert called["host"] == "127.0.0.2"
    assert called["port"] == 9000
    assert called["reload"] is False
    _assert_raises(ValueError, framework._render_component, "Missing", {})


def test_framework_inline_style_and_attribute_fallbacks() -> None:
    # Given: a default framework and various malformed inputs
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: error paths for missing CSS and bad JSON are hit

    # Then: appropriate exceptions or fallback values are returned
    _assert_raises(
        FileNotFoundError,
        framework._inline_style_src_tags,
        '<style src="./missing.css"></style>',
        root,
    )

    parsed = framework._parse_attributes(
        '__props="{bad json}" data="__json__:{bad}"',
        {"props": {}, "state": {}, "py": {}},
    )
    assert parsed.get("data", "").startswith("__json__:")

    rendered = framework._render_tag_match(
        "AppFooter",
        "",
        "<span>child</span>",
        {"props": {}, "state": {}, "py": {}},
    )
    assert "footer" in rendered


def test_framework_static_path_guards() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: requesting paths that don't map to a valid static asset

    # Then: None is returned for both cases
    assert framework.get_static_asset("/static/") is None
    assert framework.get_static_asset("/other/path") is None


def test_framework_template_router_cascades_children_inside_layout() -> None:
    # Given: a router tree with nested child component resolution
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)
    framework._router_config = {
        "initial_path": "/features",
        "routes": [
            {
                "path": "/features",
                "component": "App",
                "children": [
                    {"index": True, "component": "Hero"},
                    {"path": "features", "component": "Features"},
                    {
                        "path": "*",
                        "component": "NotFound",
                        "props": {
                            "title": "Page not found",
                            "subtitle": "The requested route does not exist",
                        },
                    },
                ],
            }
        ],
    }

    # When: building the server-side HTML
    html = framework.build_view()

    # Then: routed child content is present
    assert "Python Framework for Single Page Applications" in html


def test_framework_router_wildcard_notfound_component_is_rendered() -> None:
    # Given: a router with wildcard NotFound component and an unmatched initial path
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)
    framework._router_config = {
        "initial_path": "/nao-existe",
        "routes": [
            {
                "path": "/",
                "children": [
                    {"index": True, "component": "Dashboard"},
                    {"path": "*", "component": "NotFound"},
                ],
            }
        ],
    }

    # When: building the server-side HTML
    html = framework.build_view()

    # Then: wildcard route renders the configured NotFound component
    assert "404" in html
    assert "The page you're looking for doesn't exist or has been moved." in html
