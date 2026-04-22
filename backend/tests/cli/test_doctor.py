from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_doctor_reports_successful_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "backend").mkdir()
    (repo_root / "docs").mkdir()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("synapse_cli.doctor_command.actian_available", lambda: True)
    monkeypatch.setattr("synapse_cli.doctor_command.VectorStore", _HealthyVectorStore)

    exit_code = main(["doctor", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Overall: ok" in out
    assert "Runtime compose:" in out
    assert "workspace_config: ok" in out
    assert "actian_service: ok" in out


def test_cli_doctor_json_reports_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("synapse_cli.doctor_command.actian_available", lambda: False)

    exit_code = main(["doctor", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 3
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert payload["workspace"]["runtime_compose_path"].endswith(
        ".synapse/runtime/docker-compose.yml"
    )
    assert any(check["name"] == "embedding_model" and check["ok"] is False for check in payload["checks"])
    assert any(check["name"] == "actian_client" and check["ok"] is False for check in payload["checks"])
    assert "Set OPENAI_API_KEY in the environment or .synapse/.env" in payload["suggested_fixes"]
    assert "pip install -r backend/requirements-actian.txt" in payload["suggested_fixes"]


def test_cli_doctor_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["doctor", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


class _HealthyCollections:
    def exists(self, _name: str) -> bool:
        return True


class _HealthyClient:
    collections = _HealthyCollections()


class _HealthyVectorStore:
    def __enter__(self) -> _HealthyVectorStore:
        self.client = _HealthyClient()
        return self

    def __exit__(self, *exc) -> None:
        return None


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="doctor-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root
