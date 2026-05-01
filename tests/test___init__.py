import lua_spa


def test_package_exports_and_version() -> None:
    # Given: the lua_spa package is imported

    # When: we inspect its public API and version

    # Then: expected symbols are exported and version is a non-empty string
    assert hasattr(lua_spa, "SpaFramework")
    assert hasattr(lua_spa, "create_default_framework")
    assert isinstance(lua_spa.__version__, str)
    assert lua_spa.__version__ != ""
