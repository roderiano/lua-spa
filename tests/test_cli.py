# mypy: disable-error-code=import
from pathlib import Path

import pytest

from lua_spa.main import main


def test_create_command_copies_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / "spa.config.json").write_text("{}", encoding="utf-8")
    (template_dir / "index.lspa").write_text("<template></template>", encoding="utf-8")
    (template_dir / "components").mkdir()

    monkeypatch.setattr("lua_spa.main.get_template_source_directory", lambda: template_dir)

    main(["create", "my_project", str(tmp_path)])

    project_dir = tmp_path / "my_project"
    assert project_dir.exists()
    assert (project_dir / "spa.config.json").exists()
    assert (project_dir / "index.lspa").exists()


def test_create_command_rejects_invalid_project_name(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["create", "bad name", str(tmp_path)])

    assert exc.value.code == 1


def test_serve_command_dispatches_to_server(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"serve": False}

    def _fake_serve() -> None:
        called["serve"] = True

    monkeypatch.setattr("lua_spa.main._serve", _fake_serve)

    main(["serve"])

    assert called["serve"] is True


def test_default_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    main([])
    captured = capsys.readouterr()
    assert "usage: lua-spa" in captured.out
