from pathlib import Path

from moon_spa.loader import ComponentLoader


def test_loader_loads_entry_and_imported_components() -> None:
    # Given: the project components directory
    root = Path(__file__).resolve().parents[1]
    components_dir = root / "src" / "moon_template" / "components"
    loader = ComponentLoader(components_dir)

    # When: the App entry component is loaded
    loaded = loader.load_entry("App")

    # Then: App and its imported child components are all present
    assert "App" in loaded
    assert "AppNav" in loaded
    assert "AppStars" in loaded


def test_loader_inlines_component_external_styles() -> None:
    # Given: a components directory with external CSS files
    root = Path(__file__).resolve().parents[1]
    components_dir = root / "src" / "moon_template" / "components"
    loader = ComponentLoader(components_dir)

    # When: App entry is loaded
    loaded = loader.load_entry("App")

    # Then: AppNav's external stylesheet is inlined into its template
    nav_template = loaded["AppNav"].template
    assert "<style>" in nav_template
    assert ".nav" in nav_template


def test_loader_error_and_fallback_paths(tmp_path: Path) -> None:
    # Given: an empty temporary directory used as components root
    loader = ComponentLoader(tmp_path)

    # When: trying to load a missing component

    # Then: FileNotFoundError is raised
    try:
        loader.load_entry("Missing")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")

    # When: loading a component with no template section

    # Then: ValueError is raised
    app = tmp_path / "App.lspa"
    app.write_text("<script></script>", encoding="utf-8")
    try:
        loader.load_entry("App")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    # When: loading a plain file with no sections

    # Then: raw content is used as template
    raw = tmp_path / "Raw.lspa"
    raw.write_text("hello", encoding="utf-8")
    loader2 = ComponentLoader(tmp_path)
    loaded = loader2.load_entry("Raw")
    assert loaded["Raw"].template == "hello"


def test_loader_components_property_and_idempotent_reload(tmp_path: Path) -> None:
    # Given: a simple component file
    app = tmp_path / "App.lspa"
    app.write_text("<template><div>ok</div></template>", encoding="utf-8")
    loader = ComponentLoader(tmp_path)

    # When: the same entry is loaded twice
    first = loader.load_entry("App")
    second = loader.load_entry("App")

    # Then: components property is exposed and load is idempotent
    assert loader.components is second
    assert list(first.keys()) == ["App"]


def test_loader_inject_styles_helper_edge_paths(tmp_path: Path) -> None:
    # Given: a loader and external style markup
    loader = ComponentLoader(tmp_path)
    styles = "<style>h1{color:red}</style>"

    # When: template has no root tag
    no_root = loader._inject_styles_into_template_root("plain", styles)

    # Then: styles are prepended
    assert no_root.startswith("<style>")

    # When: template root is self-closing
    self_closing = loader._inject_styles_into_template_root("<img/>", styles)

    # Then: styles are prepended (cannot inject inside self-closing root)
    assert self_closing.startswith("<style>")
