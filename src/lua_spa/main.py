"""Command-line entry point."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Sequence

from lua_spa.app import (
    create_default_framework,
    get_template_source_directory,
    resolve_template_directory,
)

PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
COMPONENT_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_project_name(project_name: str) -> None:
    if PROJECT_NAME_PATTERN.fullmatch(project_name):
        return
    msg = "Project name must contain only letters, numbers, or underscore, with no spaces."
    raise ValueError(msg)


def _validate_component_name(component_name: str) -> None:
    if COMPONENT_NAME_PATTERN.fullmatch(component_name):
        return
    msg = (
        "Component name must start with a letter/underscore and contain only "
        "letters, numbers, or underscore."
    )
    raise ValueError(msg)


def _create_project(project_name: str, destination: str) -> Path:
    _validate_project_name(project_name)
    target_root = Path(destination).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    project_dir = target_root / project_name

    if project_dir.exists():
        msg = f"Project directory already exists: {project_dir}"
        raise FileExistsError(msg)

    template_source = get_template_source_directory()
    shutil.copytree(template_source, project_dir)
    return project_dir


def _humanize_component_name(component_name: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", component_name)
    return spaced.replace("_", " ").strip().title()


def _resolve_template_dir_for_new_component(destination: str) -> Path:
    base = Path(destination).expanduser().resolve()
    try:
        return resolve_template_directory(base)
    except FileNotFoundError:
        # Fallback to packaged template for non-project destinations.
        return get_template_source_directory()


def _create_component(component_name: str, destination: str) -> tuple[Path, Path]:
    _validate_component_name(component_name)
    template_dir = _resolve_template_dir_for_new_component(destination)
    components_dir = template_dir / "components"
    source_dir = components_dir / "ComponentTemplate"

    source_lspa = source_dir / "ComponentTemplate.lspa"
    source_css = source_dir / "ComponentTemplate.css"
    if not source_lspa.exists() or not source_css.exists():
        msg = f"ComponentTemplate not found in: {source_dir}"
        raise FileNotFoundError(msg)

    target_dir = components_dir / component_name
    if target_dir.exists():
        msg = f"Component directory already exists: {target_dir}"
        raise FileExistsError(msg)
    target_dir.mkdir(parents=True, exist_ok=False)

    component_title = _humanize_component_name(component_name)
    lspa_content = source_lspa.read_text(encoding="utf-8")
    lspa_content = lspa_content.replace("ComponentTemplate", component_name)
    lspa_content = lspa_content.replace("Server Action Template", component_title)

    css_content = source_css.read_text(encoding="utf-8")

    target_lspa = target_dir / f"{component_name}.lspa"
    target_css = target_dir / f"{component_name}.css"
    target_lspa.write_text(lspa_content, encoding="utf-8")
    target_css.write_text(css_content, encoding="utf-8")
    return target_lspa, target_css


def _serve(reload: bool = False) -> None:
    framework = create_default_framework()
    host, port = framework.server_address
    print(f"Serving lua-spa at http://{host}:{port}")
    framework.serve(reload=reload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lua-spa", description="lua-spa framework CLI")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the lua-spa development server.",
    )

    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable live reload on file changes.",
    )

    create_parser = subparsers.add_parser(
        "create",
        help="Create a new project from the lua_template scaffold.",
    )
    create_parser.add_argument(
        "project_name",
        help="Project directory name (letters, numbers, underscore; no spaces).",
    )
    create_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Destination directory (default: current directory).",
    )

    new_parser = subparsers.add_parser(
        "new",
        help="Generate framework resources inside an existing lua_template project.",
    )
    new_subparsers = new_parser.add_subparsers(dest="new_command")

    component_parser = new_subparsers.add_parser(
        "component",
        help="Create a component from ComponentTemplate.",
    )
    component_parser.add_argument(
        "name",
        help="Component name (Python identifier, e.g. UserCard).",
    )
    component_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root where lua_template lives (default: current directory).",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run CLI commands for the lua-spa framework."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    if args.command == "create":
        try:
            project_dir = _create_project(args.project_name, args.path)
        except (FileExistsError, ValueError, FileNotFoundError) as exc:
            parser.exit(status=1, message=f"Error: {exc}\n")
        print(f"Project created at: {project_dir}")
        return

    if args.command == "serve":
        _serve(reload=args.reload)
        return

    if args.command == "new" and args.new_command == "component":
        try:
            created_lspa, created_css = _create_component(args.name, args.path)
        except (FileExistsError, ValueError, FileNotFoundError) as exc:
            parser.exit(status=1, message=f"Error: {exc}\n")
        print(f"Component created at: {created_lspa}")
        print(f"Style created at: {created_css}")
        return
