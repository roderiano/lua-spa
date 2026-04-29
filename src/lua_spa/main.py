"""Command-line entry point."""

from lua_spa.app import create_default_framework


def main() -> None:
    """Run the SPA development server."""
    framework = create_default_framework()
    print("Serving lua-spa at http://127.0.0.1:8000")
    framework.serve(host="127.0.0.1", port=8000)
