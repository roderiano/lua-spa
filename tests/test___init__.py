import moon_spa


def test_package_exports_and_version() -> None:
    # Given: the moon_spa package is imported

    # When: we inspect its public API and version

    # Then: expected symbols are exported and version is a non-empty string
    assert hasattr(moon_spa, "SpaFramework")
    assert hasattr(moon_spa, "create_default_framework")
    assert isinstance(moon_spa.__version__, str)
    assert moon_spa.__version__ != ""
