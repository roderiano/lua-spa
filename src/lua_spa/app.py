"""Application helpers for creating a SPA framework instance."""

from __future__ import annotations

from pathlib import Path

from lua_spa.framework import SpaFramework


def create_default_framework(base_dir: Path | None = None) -> SpaFramework:
    """Build the default framework configured with the workspace view files."""
    root = (base_dir or Path.cwd()).resolve()
    return SpaFramework(
        view_file=root / "view" / "index.html",
        components_dir=root / "view" / "components",
        entry_component="App",
        mount_id="app",
    )
