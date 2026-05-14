from moon_spa.runtime_assets import SPA_RUNTIME_JS


def test_runtime_assets_script_contains_bootstrap_api() -> None:
    # Given: the SPA_RUNTIME_JS constant from the runtime_assets module

    # When: we inspect its content

    # Then: it defines the SpaRuntime bootstrap API
    assert "window.SpaRuntime" in SPA_RUNTIME_JS
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
    assert "window.__moonSpaLifecyclePending" in SPA_RUNTIME_JS
    assert "createdPendingKey" in SPA_RUNTIME_JS


def test_runtime_assets_submit_event_builds_form_dict() -> None:
    assert "function buildSubmitDict(event, element)" in SPA_RUNTIME_JS
    assert "dict[formName] = collectFormFields(formElement);" in SPA_RUNTIME_JS
    assert "event.formDict = submitDict;" in SPA_RUNTIME_JS
    assert "function syncSubmitDictToState(submitDict)" in SPA_RUNTIME_JS
    assert "currentComponent.state[formName] = submitDict[formName];" in SPA_RUNTIME_JS
    assert "currentComponent.state.dict = submitDict;" not in SPA_RUNTIME_JS
    assert (
        "currentComponent.state.submit_form_name = formNames[0];" not in SPA_RUNTIME_JS
    )
    assert "currentComponent.state.submit_form_names = formNames;" not in SPA_RUNTIME_JS


def test_runtime_assets_exposes_data_alias_in_template_context() -> None:
    assert "data: instance.props," in SPA_RUNTIME_JS
