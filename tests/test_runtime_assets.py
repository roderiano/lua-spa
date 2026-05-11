from lua_spa.runtime_assets import SPA_RUNTIME_JS


def test_runtime_assets_script_contains_bootstrap_api() -> None:
    # Given: the SPA_RUNTIME_JS constant from the runtime_assets module

    # When: we inspect its content

    # Then: it defines the LuaSpaRuntime bootstrap API
    assert "window.LuaSpaRuntime" in SPA_RUNTIME_JS
    assert "bootstrap" in SPA_RUNTIME_JS
    assert "i-model" in SPA_RUNTIME_JS
    assert 'kind: "model"' in SPA_RUNTIME_JS


def test_runtime_assets_exposes_component_instance_identity() -> None:
    assert "instanceCounter" in SPA_RUNTIME_JS
    assert "componentInstanceId: instance.id" in SPA_RUNTIME_JS


def test_runtime_assets_queues_mounted_until_created_settles() -> None:
    assert "hasMountedLifecycle" in SPA_RUNTIME_JS
    assert "pendingUpdatedLifecycle" in SPA_RUNTIME_JS
    assert "runMountedLifecycle" in SPA_RUNTIME_JS
    assert "window.__luaSpaLifecyclePending" in SPA_RUNTIME_JS
    assert "createdPendingKey" in SPA_RUNTIME_JS
