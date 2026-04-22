from __future__ import annotations

import json
from pathlib import Path

import pytest

from synapse_cli.init_command import InitOptions, run_init
from synapse_cli.drift_check_command import _build_file_checks
from synapse_cli.main import main
from retrieval.pipelines import _detect_conflict_signal
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
    assert "findings" in payload["checks"][0]


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


def test_build_file_checks_keeps_query_text_clean_and_extracts_signals(tmp_path: Path) -> None:
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
    assert "module constant DEFAULT_THRESHOLD_SIGMA = 2.0" not in query_text
    assert "sample > threshold" not in query_text
    assert checks[0]["signals"]["constants"]["DEFAULT_THRESHOLD_SIGMA"] == 2.0
    assert checks[0]["signals"]["constants"]["REFRACTORY_PERIOD_MS"] == 0.25
    assert "sample > threshold" in checks[0]["signals"]["comparisons"]


def test_cli_drift_check_json_includes_structured_numeric_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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

    monkeypatch.setattr("synapse_cli.drift_check_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.drift_check_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr(
        "synapse_cli.drift_check_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": "This conflicts with the spike protocol [1].",
            "has_conflict": True,
            "used_fallback": False,
            "constraints": [
                _knowledge_result(
                    score=0.83,
                    embed_text=(
                        "Constraint: threshold must be 3 to 5 standard deviations below baseline, "
                        "must be negative-going, and detections must be suppressed for at least 1 millisecond."
                    ),
                )
            ],
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
    findings = payload["checks"][0]["findings"]
    issue_types = {finding["issue_type"] for finding in findings}
    assert "threshold_range" in issue_types
    assert "threshold_polarity" in issue_types
    assert "timing_lower_bound" in issue_types
    assert payload["checks"][0]["status"] == "conflict"
    assert "Detected 3 structured drift findings" in payload["checks"][0]["summary"]


def test_cli_drift_check_findings_override_contradictory_model_prose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = _init_repo(tmp_path)
    sample_file = repo_root / "sample.py"
    sample_file.write_text(
        "BLINK_REJECTION_UV = 300.0\n\n"
        "def should_reject_blink_bad(epoch_peak_to_peak_uv):\n"
        "    return epoch_peak_to_peak_uv > BLINK_REJECTION_UV\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("synapse_cli.drift_check_command.VectorStore", _DummyVectorStore)
    monkeypatch.setattr("synapse_cli.drift_check_command.init_models_from_workspace", lambda workspace: None)
    monkeypatch.setattr(
        "synapse_cli.drift_check_command.check_code_against_constraints",
        lambda code_embed_text, store, k: {
            "explanation": "The implementation appears aligned with the blink constraint [1].",
            "has_conflict": False,
            "used_fallback": False,
            "constraints": [
                _knowledge_result(
                    score=0.77,
                    embed_text="Constraint: any epoch above 100 microvolts must be excluded or corrected.",
                )
            ],
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
    check = payload["checks"][0]
    assert check["status"] == "conflict"
    assert check["summary"] == "Blink rejection threshold 300.0 uV is more permissive than the required 100 uV limit."
    assert check["findings"][0]["issue_type"] == "artifact_threshold"


def test_detect_conflict_signal_accepts_llama_style_mismatch_language() -> None:
    assert _detect_conflict_signal(
        "The code description is inconsistent with the domain constraint and is too lenient."
    ) is True


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


def _knowledge_result(score: float, embed_text: str | None = None) -> RetrievalResult:
    chunk = _make_embedded_chunk(
        source_file="knowledge.md",
        embed_text=embed_text or "Constraint: threshold must remain negative and within range.",
        chunk_type="knowledge",
        kind="constraint",
    )
    return RetrievalResult(
        chunk=chunk,
        score=score,
        query_text="threshold",
        direction="code_to_knowledge",
    )
