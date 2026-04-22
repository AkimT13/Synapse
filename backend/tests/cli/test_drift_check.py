from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.drift_check_command import _build_file_checks
from synapse_cli.main import main
from retrieval.schemas import RetrievalResult
from tests.agents.conftest import _make_embedded_chunk
from workspace.loader import load_workspace_config


def test_cli_drift_check_inline_outputs_structured_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    monkeypatch.setattr("synapse_cli.drift_check_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.drift_check_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr(
        "synapse_cli.drift_check_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": "This behavior is consistent with the threshold constraint [1].",
            "has_conflict": False,
            "used_fallback": False,
            "constraints": [_knowledge_result(score=0.84)],
        },
    )

    exit_code = main([
        "drift-check",
        "Behavior: enforces a 4 sigma negative threshold.",
        "--repo-root",
        str(repo_root),
    ])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Status: aligned" in out
    assert "Checks (1):" in out


def test_cli_drift_check_json_for_file_aggregates_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    sample_file = repo_root / "sample.py"
    sample_file.write_text(
        "def detect_spikes(signal):\n    return signal\n\n"
        "def reject_artifact(epoch):\n    return epoch\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("synapse_cli.drift_check_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.drift_check_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr(
        "synapse_cli.drift_check_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": (
                "This conflicts with the refractory period constraint [1]."
                if "detect_spikes" in code_embed_text
                else "This appears relevant but only weakly supported [1]."
            ),
            "has_conflict": "detect_spikes" in code_embed_text,
            "used_fallback": "reject_artifact" in code_embed_text,
            "constraints": [_knowledge_result(score=0.83 if "detect_spikes" in code_embed_text else 0.66)],
        },
    )

    exit_code = main([
        "drift-check",
        "--file",
        str(sample_file),
        "--repo-root",
        str(repo_root),
        "--json",
    ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "conflict"
    assert len(payload["checks"]) == 2
    assert payload["checks"][0]["status"] in {"aligned", "conflict", "warning"}


def test_cli_drift_check_returns_error_when_workspace_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([
        "drift-check",
        "Behavior: threshold is enforced.",
        "--repo-root",
        str(tmp_path),
    ])

    assert exit_code == 2
    assert "No .synapse/config.yaml found" in capsys.readouterr().err


def test_build_file_checks_appends_deterministic_code_facts(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    sample_file = repo_root / "sample.py"
    sample_file.write_text(
        "DEFAULT_THRESHOLD_SIGMA = 2.0\n"
        "REFRACTORY_PERIOD_MS = 0.25\n\n"
        "def detect_spikes_bad(signal, sampling_rate, threshold_sigma=DEFAULT_THRESHOLD_SIGMA):\n"
        "    threshold = threshold_sigma * 1.0\n"
        "    refractory_samples = int(REFRACTORY_PERIOD_MS * sampling_rate / 1000.0)\n"
        "    for sample in signal:\n"
        "        if sample > threshold:\n"
        "            return [1]\n"
        "    return []\n",
        encoding="utf-8",
    )

    workspace = load_workspace_config(repo_root)
    checks = _build_file_checks(workspace, sample_file)

    assert len(checks) == 1
    query_text = checks[0]["query_text"]
    assert "module constant DEFAULT_THRESHOLD_SIGMA = 2.0" in query_text
    assert "module constant REFRACTORY_PERIOD_MS = 0.25" in query_text
    assert "compares using condition `sample > threshold`" in query_text


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
            workspace_name="drift-demo",
            code_paths=["backend"],
            knowledge_paths=["docs"],
            domains=["physics"],
        )
    )
    return repo_root


def _knowledge_result(score: float) -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="knowledge.md",
        embed_text="Constraint: threshold must remain negative and within range.",
        chunk_type="knowledge",
        kind="constraint",
    )
    return RetrievalResult(
        chunk=chunk,
        score=score,
        query_text="threshold",
        direction="code_to_knowledge",
    )
