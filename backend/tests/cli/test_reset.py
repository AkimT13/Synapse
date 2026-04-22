from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_reset_deletes_existing_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.setattr("synapse_cli.reset_command.actian_available", lambda: True)
    monkeypatch.setattr("synapse_cli.reset_command.VectorStore", _DeletingVectorStore)

    exit_code = main(["reset", "--repo-root", str(repo_root)])

    assert exit_code == 0
    assert "Reset collection 'chunks'" in capsys.readouterr().out


def test_cli_reset_json_reports_missing_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.setattr("synapse_cli.reset_command.actian_available", lambda: True)
    monkeypatch.setattr("synapse_cli.reset_command.VectorStore", _NoopVectorStore)

    exit_code = main(["reset", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == "reset-demo"
    assert payload["deleted"] is False


def test_cli_reset_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["reset", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


class _DeletingVectorStore:
    def __enter__(self) -> _DeletingVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None

    def reset(self) -> bool:
        return True


class _NoopVectorStore:
    def __enter__(self) -> _NoopVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None

    def reset(self) -> bool:
        return False


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="reset-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root
