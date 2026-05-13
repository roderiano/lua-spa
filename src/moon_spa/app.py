"""Application helpers for creating a SPA framework instance."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from moon_spa.framework import SpaFramework


def _is_valid_template_directory(path: Path) -> bool:
    return path.is_dir() and (path / "spa.config.json").exists() and (path / "index.lspa").exists()


def _template_source_candidates(
    module_file: Path, current_working_directory: Path
) -> Iterable[Path]:
    module_file = module_file.resolve()

    yielded: set[Path] = set()

    def _yield(candidate: Path) -> Iterable[Path]:
        resolved = candidate.resolve()
        if resolved in yielded:
            return []
        yielded.add(resolved)
        return [resolved]

    # Common installation layouts (site-packages and editable installs)
    for path in _yield(module_file.parents[1] / "moon_template"):
        yield path
    for path in _yield(module_file.parent / "moon_template"):
        yield path

    # Repository debug layouts when running directly from source
    for parent in module_file.parents:
        for path in _yield(parent / "src" / "moon_template"):
            yield path
        for path in _yield(parent / "moon_template"):
            yield path

    # Last fallback: discover template from current working directory
    for path in _yield(current_working_directory / "src" / "moon_template"):
        yield path
    for path in _yield(current_working_directory / "moon_template"):
        yield path


def get_template_source_directory() -> Path:
    """Return the packaged moon_template directory used by `moon-spa create`."""
    module_file = Path(__file__)
    cwd = Path.cwd()
    searched: list[Path] = []

    for candidate in _template_source_candidates(module_file, cwd):
        searched.append(candidate)
        if _is_valid_template_directory(candidate):
            return candidate

    searched_paths = "\n".join(f"- {path}" for path in searched)
    msg = f"Could not locate moon_template source directory. Paths checked:\n{searched_paths}"
    raise FileNotFoundError(msg)


def resolve_template_directory(root: Path) -> Path:
    """Resolve template directory from current project layout."""
    candidates = [
        root / "src" / "moon_template",
        root / "moon_template",
        root,
    ]

    for candidate in candidates:
        if _is_valid_template_directory(candidate):
            return candidate

    msg = (
        "Could not find moon template directory. Expected one of: "
        f"{root / 'src' / 'moon_template'}, {root / 'moon_template'}, or {root}."
    )
    raise FileNotFoundError(msg)


def create_default_framework(base_dir: Path | None = None) -> SpaFramework:
    """Build framework using only settings defined under moon_template/."""
    root = (base_dir or Path.cwd()).resolve()
    template_dir = resolve_template_directory(root)
    return SpaFramework.from_moon_template_directory(template_dir)
