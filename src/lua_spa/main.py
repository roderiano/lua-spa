"""Command-line entry point."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Sequence

from lua_spa.app import create_default_framework, get_template_source_directory

PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_project_name(project_name: str) -> None:
    if PROJECT_NAME_PATTERN.fullmatch(project_name):
        return
    msg = "Project name must contain only letters, numbers, or underscore, with no spaces."
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


def _serve() -> None:
    framework = create_default_framework()
    host, port = framework.server_address
    print(f"Serving lua-spa at http://{host}:{port}")
    framework.serve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lua-spa", description="lua-spa framework CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "serve",
        help="Start the lua-spa development server.",
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
        _serve()
        return
