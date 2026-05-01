from lua_spa.runtime_assets import SPA_RUNTIME_JS


def test_runtime_assets_script_contains_bootstrap_api() -> None:
    # Given: the SPA_RUNTIME_JS constant from the runtime_assets module

    # When: we inspect its content

    # Then: it defines the LuaSpaRuntime bootstrap API
    assert "window.LuaSpaRuntime" in SPA_RUNTIME_JS
    assert "bootstrap" in SPA_RUNTIME_JS
