from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_install_skill_creates_codex_and_claude_skill_dirs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    exit_code = main(["install-skill", "--agent", "both", "--repo-root", str(repo_root)])

    assert exit_code == 0
    assert (repo_root / ".agents" / "skills" / "synapse-review" / "SKILL.md").is_file()
    assert (repo_root / ".claude" / "skills" / "synapse-review" / "SKILL.md").is_file()
    out = capsys.readouterr().out
    assert "Skill: synapse-review" in out
    assert "codex:" in out
    assert "claude:" in out


def test_cli_install_skill_json_reports_installed_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    exit_code = main(["install-skill", "--agent", "codex", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == "skill-demo"
    assert payload["skill_name"] == "synapse-review"
    assert payload["installed"][0]["agent"] == "codex"
    assert payload["installed"][0]["path"].endswith(".agents/skills/synapse-review/SKILL.md")


def test_cli_install_skill_refuses_to_overwrite_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    skill_path = repo_root / ".claude" / "skills" / "synapse-review" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("existing", encoding="utf-8")

    exit_code = main(["install-skill", "--agent", "claude", "--repo-root", str(repo_root)])

    assert exit_code == 4
    assert "Pass --force to overwrite" in capsys.readouterr().err
    assert skill_path.read_text(encoding="utf-8") == "existing"


def test_cli_install_skill_force_overwrites_existing_skill(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    skill_path = repo_root / ".claude" / "skills" / "synapse-review" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("existing", encoding="utf-8")

    exit_code = main(
        ["install-skill", "--agent", "claude", "--repo-root", str(repo_root), "--force"]
    )

    assert exit_code == 0
    assert "synapse-review" in skill_path.read_text(encoding="utf-8")
    assert "(overwritten)" in capsys.readouterr().out


def test_cli_install_skill_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["install-skill", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="skill-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root
