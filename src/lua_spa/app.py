"""Application helpers for creating a SPA framework instance."""

from __future__ import annotations

from pathlib import Path

from lua_spa.framework import SpaFramework


def get_template_source_directory() -> Path:
    """Return the packaged lua_template directory used by `lua-spa create`."""
    candidate = Path(__file__).resolve().parents[1] / "lua_template"
    if candidate.exists() and candidate.is_dir():
        return candidate
    msg = f"Could not locate lua_template source directory at: {candidate}"
    raise FileNotFoundError(msg)


def resolve_template_directory(root: Path) -> Path:
    """Resolve template directory from current project layout."""
    candidates = [
        root / "src" / "lua_template",
        root / "lua_template",
        root,
    ]

    for candidate in candidates:
        if (candidate / "spa.config.json").exists() and (candidate / "index.lspa").exists():
            return candidate

    msg = (
        "Could not find lua template directory. Expected one of: "
        f"{root / 'src' / 'lua_template'}, {root / 'lua_template'}, or {root}."
    )
    raise FileNotFoundError(msg)


def create_default_framework(base_dir: Path | None = None) -> SpaFramework:
    """Build framework using only settings defined under lua_template/."""
    root = (base_dir or Path.cwd()).resolve()
    template_dir = resolve_template_directory(root)
    return SpaFramework.from_lua_template_directory(template_dir)
