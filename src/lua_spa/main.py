"""Command-line entry point."""

from lua_spa.app import build_startup_message


def main() -> None:
    """Run the application via CLI."""
    print(build_startup_message())
