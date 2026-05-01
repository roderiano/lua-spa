from pathlib import Path


def test_lua_template_files_exist() -> None:
    # Given: the src/lua_template base directory
    base = Path("src/lua_template")

    # When: we check for required template files

    # Then: index.lspa, spa.config.json, and components/ directory all exist
    assert (base / "index.lspa").exists()
    assert (base / "spa.config.json").exists()
    assert (base / "components").is_dir()
