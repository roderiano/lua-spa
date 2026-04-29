"""Application helpers for creating a SPA framework instance."""

from __future__ import annotations

from pathlib import Path

from lua_spa.framework import SpaFramework


def create_default_framework(base_dir: Path | None = None) -> SpaFramework:
    """Build framework using only settings defined under view/."""
    root = (base_dir or Path.cwd()).resolve()
    return SpaFramework.from_view_directory(root / "view")
