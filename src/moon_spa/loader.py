"""Component loader: reads .lspa files and builds the dependency graph.

Parses component files into template HTML, Python blocks, and imports,
then recursively loads imported components to build a complete registry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from moon_spa.codegen import build_client_script
from moon_spa.types import ComponentDefinition

_IMPORT_PATTERN = re.compile(r"^\s*@import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+['\"](.+?)['\"]\s*$")
_TEMPLATE_PATTERN = re.compile(r"<template>(.*?)</template>", re.IGNORECASE | re.DOTALL)
_PYTHON_PATTERN = re.compile(r"<python>(.*?)</python>", re.IGNORECASE | re.DOTALL)
_STYLE_SRC_PATTERN = re.compile(
    r"<style\s+[^>]*src\s*=\s*(?:\"([^\"]+)\"|'([^']+)')[^>]*>\s*</style>",
    re.IGNORECASE,
)


class ComponentLoader:
    """Loads components and their import graph from .lspa files.

    Recursively resolves imports, building a registry of ComponentDefinition
    objects keyed by component name.
    """

    def __init__(self, components_dir: Path) -> None:
        """Initialize a loader for a component directory.

        Args:
            components_dir: Path to the directory containing .lspa files.
        """
        self._components_dir = components_dir
        self._loaded: dict[str, ComponentDefinition] = {}

    @property
    def components(self) -> Mapping[str, ComponentDefinition]:
        """Get the loaded components registry."""
        return self._loaded

    def load_entry(self, entry_component: str) -> Mapping[str, ComponentDefinition]:
        """Load a component and all its dependencies.

        Args:
            entry_component: Component name (without .lspa extension).

        Returns:
            The full components registry.

        Raises:
            FileNotFoundError: If the component file doesn't exist.
            ValueError: If the component uses unsupported <script> tags.
        """
        entry_file = self._components_dir / f"{entry_component}.lspa"
        self._load_component(entry_component, entry_file)
        return self._loaded

    def _load_component(self, component_name: str, file_path: Path) -> None:
        """Load a single component, recursing to load its imports.

        Skips if already loaded. Raises FileNotFoundError or ValueError
        if the file is missing or malformed.

        Args:
            component_name: Name to register this component under.
            file_path: Path to the .lspa file.
        """
        normalized = file_path.resolve()
        if component_name in self._loaded:
            return

        if not normalized.exists():
            raise FileNotFoundError(f"Component file not found: {normalized}")

        source = normalized.read_text(encoding="utf-8")
        imports, body = self._extract_imports(source)

        if "<script" in body.lower():
            raise ValueError(
                f"Component '{component_name}' uses <script>; use a <python> block with Component.setup(self, props)"
            )

        template = self._extract_template(body)
        template = self._inline_style_src_tags(template, normalized.parent)
        external_styles = self._extract_external_styles(body, normalized.parent)
        if external_styles:
            template = self._inject_styles_into_template_root(template, external_styles)
        python_block = self._extract_python(body)
        client_script = build_client_script(python_block)

        self._loaded[component_name] = ComponentDefinition(
            name=component_name,
            template=template,
            client_script=client_script,
            python_block=python_block,
            imports={alias: alias for alias in imports},
        )

        for alias, relative_path in imports.items():
            imported_file = (normalized.parent / relative_path).resolve()
            self._load_component(alias, imported_file)

    def _extract_imports(self, source: str) -> tuple[dict[str, str], str]:
        """Extract @import lines and return the import map and remaining body.

        @import Name from "./path/to/Name.lspa"
        becomes {"Name": "./path/to/Name.lspa"}

        Args:
            source: Full .lspa file content.

        Returns:
            (imports_dict, body_without_imports)
        """
        imports: dict[str, str] = {}
        body_lines: list[str] = []

        for line in source.splitlines():
            match = _IMPORT_PATTERN.match(line)
            if match is None:
                body_lines.append(line)
                continue
            imports[match.group(1)] = match.group(2)

        return imports, "\n".join(body_lines)

    def _extract_template(self, body: str) -> str:
        """Extract the <template>...</template> block.

        If no template is found, returns the entire body.

        Args:
            body: HTML/template content.

        Returns:
            Template HTML (stripped).
        """
        match = _TEMPLATE_PATTERN.search(body)
        if match is None:
            return body.strip()
        return match.group(1).strip()

    def _extract_python(self, body: str) -> str:
        """Extract the <python>...</python> block.

        Returns empty string if no Python block is found.

        Args:
            body: HTML/template content.

        Returns:
            Python code (stripped).
        """
        match = _PYTHON_PATTERN.search(body)
        if match is None:
            return ""
        return match.group(1).strip()

    def _extract_external_styles(self, body: str, base_dir: Path) -> str:
        """Extract and inline <style src="..."> blocks outside <template>."""
        template_match = _TEMPLATE_PATTERN.search(body)
        if template_match is None:
            outside_template = body
        else:
            outside_template = body[: template_match.start()] + body[template_match.end() :]
        style_tags = [match.group(0) for match in _STYLE_SRC_PATTERN.finditer(outside_template)]
        if not style_tags:
            return ""
        return self._inline_style_src_tags("\n".join(style_tags), base_dir)

    def _inline_style_src_tags(self, markup: str, base_dir: Path) -> str:
        """Replace <style src="..."> with inline CSS loaded from disk."""

        def replace(match: re.Match[str]) -> str:
            relative_src = match.group(1) or match.group(2)
            if relative_src is None:
                return match.group(0)
            css_path = (base_dir / relative_src).resolve()
            if not css_path.exists() or not css_path.is_file():
                raise FileNotFoundError(f"Style file not found: {css_path}")
            css_content = css_path.read_text(encoding="utf-8")
            return f"<style>\n{css_content}\n</style>"

        return _STYLE_SRC_PATTERN.sub(replace, markup)

    def _inject_styles_into_template_root(self, template: str, styles: str) -> str:
        """Inject external style markup as first child of template root.

        This preserves a single root node for hydration and avoids wrapper insertion
        on the client runtime when components import CSS outside <template>.
        """
        style_markup = styles.strip()
        if style_markup == "":
            return template

        root_open = re.search(r"<([A-Za-z][\w:\-]*)(?:\s[^>]*)?>", template)
        if root_open is None:
            return f"{style_markup}\n{template}"

        start, end = root_open.span()
        open_tag = template[start:end]
        if open_tag.endswith("/>"):
            return f"{style_markup}\n{template}"

        return f"{template[:end]}\n{style_markup}\n{template[end:]}"
