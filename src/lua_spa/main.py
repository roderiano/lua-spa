"""Command-line entry point."""

from lua_spa.app import create_default_framework


def main() -> None:
    """Run the SPA development server."""
    framework = create_default_framework()
    host, port = framework.server_address
    print(f"Serving lua-spa at http://{host}:{port}")
    framework.serve()
