from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main
from retrieval.schemas import RetrievalResult
from tests.agents.conftest import _make_embedded_chunk


def test_cli_query_free_outputs_answer_and_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path, "query-free-demo")
    monkeypatch.setattr("synapse_cli.query_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr(
        "synapse_cli.query_command.answer_question",
        lambda question, store, k: {
            "answer": "The threshold is enforced in normalize_threshold [1].",
            "results": [_code_result()],
        },
    )
    monkeypatch.setattr("synapse_cli.query_command.init_models_from_workspace", lambda workspace: None)

    exit_code = main(["query", "free", "where is the threshold enforced?", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Mode: free" in out
    assert "Answer:" in out
    assert "Results (1):" in out


def test_cli_query_code_json_outputs_conflict_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path, "query-code-demo")
    monkeypatch.setattr("synapse_cli.query_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr(
        "synapse_cli.query_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": "This appears to violate the threshold [1].",
            "has_conflict": True,
            "used_fallback": False,
            "constraints": [_knowledge_result()],
        },
    )
    monkeypatch.setattr("synapse_cli.query_command.init_models_from_workspace", lambda workspace: None)

    exit_code = main(["query", "code", "Behavior: accepts values below threshold", "--repo-root", str(repo_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "code"
    assert payload["has_conflict"] is True
    assert payload["results"][0]["chunk_type"] == "knowledge"


def test_cli_query_knowledge_outputs_implementation_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path, "query-knowledge-demo")
    monkeypatch.setattr("synapse_cli.query_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr(
        "synapse_cli.query_command.explain_constraint_coverage",
        lambda knowledge_embed_text, store, k: {
            "explanation": "The software appears to implement this behavior [1].",
            "is_implemented": True,
            "code_chunks": [_code_result()],
        },
    )
    monkeypatch.setattr("synapse_cli.query_command.init_models_from_workspace", lambda workspace: None)

    exit_code = main(["query", "knowledge", "Constraint: threshold must be enforced", "--repo-root", str(repo_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Mode: knowledge" in out
    assert "Is implemented: True" in out


def test_cli_query_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["query", "free", "hello", "--repo-root", str(tmp_path)])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


def _init_repo(tmp_path: Path, name: str) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name=name,
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root


class _DummyVectorStore:
    def __enter__(self) -> _DummyVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None


def _knowledge_result() -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="spec.md",
        embed_text="Constraint: threshold must exceed 0.5",
        chunk_type="knowledge",
        kind="constraint",
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.97,
        query_text="threshold",
        direction="code_to_knowledge",
    )


def _code_result() -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="backend/logic.py",
        embed_text="Behavior: normalize_threshold enforces a 0.5 minimum",
        chunk_type="code",
        kind="behavior",
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.91,
        query_text="threshold",
        direction="knowledge_to_code",
    )
