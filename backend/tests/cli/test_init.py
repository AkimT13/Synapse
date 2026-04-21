from __future__ import annotations

from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main
from workspace.loader import load_workspace_config


def test_run_init_writes_workspace_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    path = run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["spectroscopy"],
        )
    )

    assert path == repo_root / ".synapse" / "config.yaml"
    assert path.is_file()
    assert (repo_root / ".synapse" / ".env.example").is_file()
    assert (repo_root / ".synapse" / ".gitignore").read_text(encoding="utf-8") == ".env\n"

    loaded = load_workspace_config(repo_root)
    assert loaded.config.workspace.name == "demo"
    assert loaded.code_roots[0].path == (repo_root / "backend").resolve()
    assert loaded.knowledge_roots[0].path == (repo_root / "docs").resolve()
    assert loaded.config.domains[0].name == "spectroscopy"


def test_run_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["spectroscopy"],
        )
    )

    with pytest.raises(FileExistsError):
        run_init(
            InitOptions(
                repo_root=repo_root,
                workspace_name="demo",
                code_paths=["backend"],
                knowledge_paths=["docs"],
                domains=["spectroscopy"],
            )
        )


def test_cli_init_noninteractive_generates_config(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    exit_code = main(
        [
            "init",
            "--repo-root",
            str(repo_root),
            "--name",
            "cli-demo",
            "--code",
            "backend",
            "--knowledge",
            "docs",
            "--domain",
            "physics",
        ]
    )

    assert exit_code == 0

    loaded = load_workspace_config(repo_root)
    assert loaded.config.workspace.name == "cli-demo"
    assert loaded.config.domains[0].name == "physics"


def test_cli_init_uses_defaults_when_flags_are_omitted(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    exit_code = main(
        [
            "init",
            "--repo-root",
            str(repo_root),
            "--name",
            "defaults-demo",
        ]
    )

    assert exit_code == 0

    loaded = load_workspace_config(repo_root)
    assert [root.path.name for root in loaded.code_roots] == ["backend", "frontend"]
    assert [root.path.name for root in loaded.knowledge_roots] == ["knowledge"]


def test_cli_status_outputs_workspace_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="status-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )

    monkeypatch.setattr(
        "synapse_cli.status_command._get_db_status",
        lambda: __import__("synapse_cli.status_command", fromlist=["DbStatus"]).DbStatus(
            actian_installed=True,
            reachable=False,
            error="connection refused",
        ),
    )

    exit_code = main(["status", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Workspace: status-demo" in out
    assert "Code roots (1):" in out
    assert "Knowledge roots (1):" in out
    assert "db_reachable: False" in out


def test_cli_status_json_outputs_machine_readable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import json

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="json-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )

    monkeypatch.setattr(
        "synapse_cli.status_command._get_db_status",
        lambda: __import__("synapse_cli.status_command", fromlist=["DbStatus"]).DbStatus(
            actian_installed=False,
            reachable=False,
            error="Actian VectorAI client is not installed",
        ),
    )

    exit_code = main(["status", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["name"] == "json-demo"
    assert payload["runtime"]["db"]["actian_installed"] is False


def test_cli_status_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["status", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err
