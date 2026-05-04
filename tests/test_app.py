from pathlib import Path
from typing import Any, Callable

from lua_spa.app import (
    create_default_framework,
    get_template_source_directory,
    resolve_template_directory,
)


def _assert_raises(exc_type: type[BaseException], fn: Callable[..., Any], *args: Any) -> None:
    try:
        fn(*args)
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")


def test_create_default_framework_loads_components() -> None:
    # Given: the project root directory
    root = Path(__file__).resolve().parents[1]

    # When: create_default_framework is called with the root
    framework = create_default_framework(root)

    # Then: expected components and default server address are configured
    assert {"App", "AppStars", "AppNav", "AppHero", "AppFooter"}.issubset(
        set(framework.component_names)
    )
    assert framework.server_address == ("127.0.0.1", 8000)


def test_build_view_contains_spa_payload() -> None:
    # Given: a default framework loaded from the project root
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: build_view is called without overrides
    html = framework.build_view()

    # Then: the rendered HTML contains SPA bootstrap markers
    assert "lua-spa-registry" in html
    assert "lua-spa-config" in html
    assert "Python Framework for Single Page Applications" in html
    assert 'id="app"' in html
    assert 'class="hero__title"' in html
    assert "window.LuaSpaRuntime.bootstrap()" in html


def test_build_view_allows_props_override() -> None:
    # Given: a default framework
    root = Path(__file__).resolve().parents[1]
    framework = create_default_framework(root)

    # When: build_view is called with a route override prop
    html = framework.build_view({"route": "Override"})

    # Then: the HTML contains the SPA config and the overridden value
    assert "lua-spa-config" in html
    assert "Override" in html


def test_get_template_source_directory_exists() -> None:
    # Given: the package template directory function

    # When: get_template_source_directory is called
    directory = get_template_source_directory()

    # Then: the directory exists and contains spa.config.json
    assert directory.exists()
    assert (directory / "spa.config.json").exists()


def test_resolve_template_directory_prefers_src_layout(tmp_path: Path) -> None:
    # Given: a project with src/lua_template layout containing required files
    root = tmp_path
    template = root / "src" / "lua_template"
    template.mkdir(parents=True)
    (template / "spa.config.json").write_text("{}", encoding="utf-8")
    (template / "index.lspa").write_text("<html></html>", encoding="utf-8")

    # When: resolve_template_directory is called
    resolved = resolve_template_directory(root)

    # Then: the src layout path is returned
    assert resolved == template


def test_resolve_template_directory_raises_when_missing(tmp_path: Path) -> None:
    # Given: a project root with no lua_template directory

    # When: resolve_template_directory is called

    # Then: FileNotFoundError is raised
    _assert_raises(FileNotFoundError, resolve_template_directory, tmp_path)


def test_get_template_source_directory_raises_when_template_missing(
    monkeypatch: Any, tmp_path: Path
) -> None:
    # Given: a fake module file path whose parent package has no lua_template directory
    import lua_spa.app as app_module

    fake_file = Path("C:/tmp/nonexistent_pkg/src/lua_spa/app.py")
    monkeypatch.setattr(app_module, "__file__", str(fake_file))
    monkeypatch.chdir(tmp_path)

    # When / Then: resolving template source directory raises FileNotFoundError
    try:
        get_template_source_directory()
    except FileNotFoundError as exc:
        assert "Paths checked:" in str(exc)
        return
    raise AssertionError("Expected FileNotFoundError to be raised")


def test_get_template_source_directory_uses_package_local_fallback(
    monkeypatch: Any, tmp_path: Path
) -> None:
    # Given: a layout where lua_template lives inside the lua_spa package directory
    import lua_spa.app as app_module

    package_dir = tmp_path / "site-packages" / "lua_spa"
    package_dir.mkdir(parents=True)
    (package_dir / "app.py").write_text("", encoding="utf-8")
    package_template = package_dir / "lua_template"
    package_template.mkdir()
    (package_template / "spa.config.json").write_text("{}", encoding="utf-8")
    (package_template / "index.lspa").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(app_module, "__file__", str(package_dir / "app.py"))

    # When: get_template_source_directory is called
    resolved = get_template_source_directory()

    # Then: the package-local template path is discovered
    assert resolved == package_template.resolve()


def test_get_template_source_directory_uses_repository_debug_layout(
    monkeypatch: Any, tmp_path: Path
) -> None:
    # Given: a source-debug layout where app.py is under src/lua_spa and scaffold under src/lua_template
    import lua_spa.app as app_module

    app_file = tmp_path / "repo" / "src" / "lua_spa" / "app.py"
    app_file.parent.mkdir(parents=True)
    app_file.write_text("", encoding="utf-8")
    debug_template = tmp_path / "repo" / "src" / "lua_template"
    debug_template.mkdir(parents=True)
    (debug_template / "spa.config.json").write_text("{}", encoding="utf-8")
    (debug_template / "index.lspa").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(app_module, "__file__", str(app_file))

    # When: get_template_source_directory is called
    resolved = get_template_source_directory()

    # Then: the source debug template path is discovered
    assert resolved == debug_template.resolve()
