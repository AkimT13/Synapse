from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.main import main
from retrieval.schemas import RetrievalResult
from tests.agents.conftest import _make_embedded_chunk


def test_cli_review_json_outputs_drift_and_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    sample_file = repo_root / "sample.py"
    sample_file.write_text("def detect_spikes(signal):\n    return signal\n", encoding="utf-8")

    monkeypatch.setattr("synapse_cli.review_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr("synapse_cli.review_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr(
        "synapse_cli.review_command._build_file_checks",
        lambda workspace, file_path: [
            {
                "label": "detect_spikes",
                "query_text": "Behavior: detect_spikes enforces a threshold",
                "source_file": str(sample_file),
                "line_range": {"start": 1, "end": 2},
                "signals": {},
            }
        ],
    )
    monkeypatch.setattr(
        "synapse_cli.review_command._run_single_check",
        lambda check, store, k: {
            "label": "detect_spikes",
            "source_file": str(sample_file),
            "line_range": {"start": 1, "end": 2},
            "status": "conflict",
            "summary": "Threshold conflicts with the domain constraint.",
            "violations": ["Threshold conflicts with the domain constraint."],
            "confidence": "high",
            "used_fallback": False,
            "findings": [],
            "supporting_sources": [_source_result()],
        },
    )
    monkeypatch.setattr(
        "synapse_cli.review_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": "Threshold conflicts with the domain constraint.",
            "has_conflict": True,
            "used_fallback": False,
            "constraints": [_source_result()],
        },
    )

    exit_code = main([
        "review",
        "--file",
        str(sample_file),
        "--repo-root",
        str(repo_root),
        "--json",
    ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["drift_status"] == "conflict"
    assert len(payload["drift"]) == 1
    assert len(payload["context"]) == 1
    assert payload["context"][0]["sources"][0]["kind"] == "constraint"


def test_cli_review_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([
        "review",
        "--file",
        "sample.py",
        "--repo-root",
        str(tmp_path),
    ])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


class _DummyVectorStore:
    def __enter__(self) -> _DummyVectorStore:
        return self

    def __exit__(self, *exc) -> None:
        return None


def _init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_init(
        InitOptions(
            repo_root=repo_root,
            workspace_name="review-demo",
            code_paths=["code"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root


def _source_result() -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="knowledge.md",
        embed_text="Constraint: threshold must remain negative and within range.",
        chunk_type="knowledge",
        kind="constraint",
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.91,
        query_text="threshold",
        direction="code_to_knowledge",
    )
