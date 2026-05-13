from pathlib import Path


def test_moon_template_files_exist() -> None:
    # Given: the src/moon_template base directory
    base = Path("src/moon_template")

    # When: we check for required template files

    # Then: index.lspa, spa.config.json, and components/ directory all exist
    assert (base / "index.lspa").exists()
    assert (base / "spa.config.json").exists()
    assert (base / "components").is_dir()
