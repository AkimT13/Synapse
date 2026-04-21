from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main


def test_cli_ingest_runs_code_and_knowledge_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="ingest-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )

    monkeypatch.setattr("synapse_cli.ingest_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.ingest_command.CodeIngestionJob", _DummyCodeJob)
    monkeypatch.setattr(
        "synapse_cli.ingest_command.KnowledgeIngestionJob", _DummyKnowledgeJob
    )
    monkeypatch.setattr("synapse_cli.ingest_command.init_models_from_workspace", lambda workspace: None)

    exit_code = main(["ingest", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Workspace: ingest-demo" in out
    assert "Target: all" in out
    assert "code" in out
    assert "knowledge" in out


def test_cli_ingest_json_outputs_machine_readable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="json-ingest-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )

    monkeypatch.setattr("synapse_cli.ingest_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.ingest_command.CodeIngestionJob", _DummyCodeJob)
    monkeypatch.setattr(
        "synapse_cli.ingest_command.KnowledgeIngestionJob", _DummyKnowledgeJob
    )
    monkeypatch.setattr("synapse_cli.ingest_command.init_models_from_workspace", lambda workspace: None)

    exit_code = main(["ingest", "code", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == "json-ingest-demo"
    assert payload["target"] == "code"
    assert len(payload["summaries"]) == 1
    assert payload["summaries"][0]["kind"] == "code"


def test_cli_ingest_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["ingest", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


class _DummyVectorStore:
    def __enter__(self) -> _DummyVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None


class _DummyCodeJob:
    def __init__(self, vector_store, should_use_llm, on_progress):
        self._on_progress = on_progress

    def run(self, path: str, languages=None):
        self._on_progress(f"dummy code ingest {path}")
        return _DummyResult(
            files_processed=1,
            chunks_parsed=2,
            chunks_normalized=2,
            chunks_embedded=2,
            chunks_stored=2,
            errors=[],
        )


class _DummyKnowledgeJob:
    def __init__(self, vector_store, should_use_llm, on_progress):
        self._on_progress = on_progress

    def run(self, path: str):
        self._on_progress(f"dummy knowledge ingest {path}")
        return _DummyResult(
            files_processed=1,
            chunks_parsed=3,
            chunks_normalized=3,
            chunks_embedded=3,
            chunks_stored=3,
            errors=[],
        )


class _DummyResult:
    def __init__(self, **data):
        self._data = data

    def model_dump(self):
        return dict(self._data)
