from lua_spa.app import build_startup_message


def test_build_startup_message_default() -> None:
    assert build_startup_message() == "lua-spa started successfully"


def test_build_startup_message_custom_name() -> None:
    assert build_startup_message("demo") == "demo started successfully"
