# mypy: disable-error-code=import
from __future__ import annotations

from pathlib import Path

import pytest

import lua_spa.main as cli_main
from lua_spa.main import main


def test_create_command_copies_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Given: a minimal template directory structure and a monkeypatched template source
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "spa.config.json").write_text("{}", encoding="utf-8")
    (template_dir / "index.lspa").write_text("<template></template>", encoding="utf-8")
    (template_dir / "components").mkdir()
    monkeypatch.setattr("lua_spa.main.get_template_source_directory", lambda: template_dir)

    # When: the create command is executed
    main(["create", "my_project", str(tmp_path)])

    # Then: the new project directory contains the template files
    project_dir = tmp_path / "my_project"
    assert project_dir.exists()
    assert (project_dir / "spa.config.json").exists()
    assert (project_dir / "index.lspa").exists()


def test_create_command_rejects_invalid_project_name(tmp_path: Path) -> None:
    # Given: an invalid project name with a space

    # When: the create command is invoked with the bad name

    # Then: the CLI exits with code 1
    with pytest.raises(SystemExit) as exc:
        main(["create", "bad name", str(tmp_path)])
    assert exc.value.code == 1


def test_cli_validation_and_create_errors(tmp_path: Path) -> None:
    # Given: a valid name and a pre-existing project directory
    existing = tmp_path / "proj"
    existing.mkdir()

    # When: validation and creation are called

    # Then: valid name passes, invalid name raises ValueError, existing dir raises FileExistsError
    cli_main._validate_project_name("ok_name_1")

    with pytest.raises(ValueError):
        cli_main._validate_project_name("bad name")

    with pytest.raises(FileExistsError):
        cli_main._create_project("proj", str(tmp_path))


def test_serve_command_dispatches_to_server(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a monkeypatched _serve function
    called = {"serve": False, "reload": None}

    def _fake_serve(reload: bool = False) -> None:
        called["serve"] = True
        called["reload"] = reload

    monkeypatch.setattr("lua_spa.main._serve", _fake_serve)

    # When: the serve command is invoked
    main(["serve"])

    # Then: the _serve function is called
    assert called["serve"] is True
    assert called["reload"] is False


def test_default_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    # Given: no arguments are passed to the CLI

    # When: main is called with an empty list
    main([])

    # Then: help text is printed to stdout
    captured = capsys.readouterr()
    assert "usage: lua-spa" in captured.out


def test_internal_serve_uses_framework(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a fake framework that records serve calls
    called = {"serve": False, "reload": None}

    class FakeFramework:
        server_address = ("127.0.0.1", 8000)

        def serve(self, reload: bool = False) -> None:
            called["serve"] = True
            called["reload"] = reload

    monkeypatch.setattr("lua_spa.main.create_default_framework", lambda: FakeFramework())

    # When: _serve is called
    cli_main._serve()

    # Then: the framework's serve method is invoked
    assert called["serve"] is True
    assert called["reload"] is False


def test_new_component_command_dispatches_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a monkeypatched component creator
    called = {"name": None, "path": None}

    def _fake_create_component(name: str, path: str) -> tuple[Path, Path]:
        called["name"] = name
        called["path"] = path
        return Path("components") / f"{name}.lspa", Path("components") / f"{name}.css"

    monkeypatch.setattr("lua_spa.main._create_component", _fake_create_component)

    # When: new component command is invoked
    main(["new", "component", "Widget", "."])

    # Then: creator is called with expected args
    assert called["name"] == "Widget"
    assert called["path"] == "."


def test_create_component_from_server_action_template(tmp_path: Path) -> None:
    # Given: a project layout containing ComponentTemplate
    components_dir = tmp_path / "src" / "lua_template" / "components"
    source_dir = components_dir / "ComponentTemplate"
    source_dir.mkdir(parents=True)
    (tmp_path / "src" / "lua_template" / "spa.config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src" / "lua_template" / "index.lspa").write_text(
        "<template></template>", encoding="utf-8"
    )
    (source_dir / "ComponentTemplate.lspa").write_text(
        """
<python>
class ComponentTemplate(Component):
  def setup(self, props):
    props = {"title": "Server Action Template", **props}
</python>
<style src=\"./ComponentTemplate.css\"></style>
""".strip(),
        encoding="utf-8",
    )
    (source_dir / "ComponentTemplate.css").write_text("section { }", encoding="utf-8")

    # When: creating a component from the template
    created_lspa, created_css = cli_main._create_component("UserCard", str(tmp_path))

    # Then: files are created in components/UserCard and content is renamed
    assert created_lspa.exists()
    assert created_css.exists()
    lspa_content = created_lspa.read_text(encoding="utf-8")
    assert "class UserCard(Component)" in lspa_content
    assert "Server Action Template" not in lspa_content
    assert "User Card" in lspa_content
    assert "./UserCard.css" in lspa_content


def test_component_name_validation_and_humanize() -> None:
    cli_main._validate_component_name("_Card1")

    with pytest.raises(ValueError):
        cli_main._validate_component_name("1Card")

    assert cli_main._humanize_component_name("userCard") == "User Card"
    assert cli_main._humanize_component_name("user_card") == "User Card"


def test_resolve_template_dir_for_new_component_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fallback = tmp_path / "fallback"
    fallback.mkdir()

    def _raise_not_found(_: Path) -> Path:
        raise FileNotFoundError("missing")

    monkeypatch.setattr("lua_spa.main.resolve_template_directory", _raise_not_found)
    monkeypatch.setattr("lua_spa.main.get_template_source_directory", lambda: fallback)

    resolved = cli_main._resolve_template_dir_for_new_component(str(tmp_path))
    assert resolved == fallback


def test_create_component_raises_when_template_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    components = template_dir / "components" / "ComponentTemplate"
    components.mkdir(parents=True)
    monkeypatch.setattr("lua_spa.main._resolve_template_dir_for_new_component", lambda _: template_dir)

    with pytest.raises(FileNotFoundError, match="ComponentTemplate not found"):
        cli_main._create_component("UserCard", str(tmp_path))


def test_create_component_raises_when_target_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    source_dir = template_dir / "components" / "ComponentTemplate"
    source_dir.mkdir(parents=True)
    (source_dir / "ComponentTemplate.lspa").write_text("ComponentTemplate", encoding="utf-8")
    (source_dir / "ComponentTemplate.css").write_text(".x{}", encoding="utf-8")
    target_dir = template_dir / "components" / "UserCard"
    target_dir.mkdir(parents=True)
    monkeypatch.setattr("lua_spa.main._resolve_template_dir_for_new_component", lambda _: template_dir)

    with pytest.raises(FileExistsError, match="Component directory already exists"):
        cli_main._create_component("UserCard", str(tmp_path))


def test_main_new_without_subcommand_returns_silently() -> None:
    # Covers the branch where command is "new" but no resource type is provided.
    assert main(["new"]) is None


def test_new_component_command_exits_when_creator_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_: str, __: str) -> tuple[Path, Path]:
        raise ValueError("invalid component")

    monkeypatch.setattr("lua_spa.main._create_component", _boom)

    with pytest.raises(SystemExit) as exc:
        main(["new", "component", "Bad", "."])

    assert exc.value.code == 1
