from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import review


def test_review_file_returns_browser_friendly_payload(monkeypatch, tmp_path: Path) -> None:
    app = _make_app(tmp_path)

    monkeypatch.setattr(
        "api.review._load_workspace",
        lambda: _workspace("review-demo"),
    )

    def fake_build_file_checks(workspace, file_path: Path) -> list[dict]:
        assert workspace.config.workspace.name == "review-demo"
        assert file_path.name == "analysis.py"
        return [
            {
                "label": "detect_spikes",
                "query_text": "Behavior: detect_spikes enforces a negative threshold",
                "source_file": str(file_path),
                "line_range": {"start": 1, "end": 2},
                "signals": {},
            }
        ]

    monkeypatch.setattr("api.review._build_file_checks", fake_build_file_checks)
    monkeypatch.setattr(
        "api.review._run_single_check",
        lambda check, store, k: {
            "label": check["label"],
            "source_file": check["source_file"],
            "line_range": check["line_range"],
            "status": "conflict",
            "summary": "Threshold conflicts with the domain constraint.",
            "violations": ["Threshold conflicts with the domain constraint."],
            "confidence": "high",
            "used_fallback": False,
            "query_text": check["query_text"],
            "findings": [
                {
                    "issue_type": "threshold_polarity",
                    "expected": "negative-going threshold crossing",
                    "observed": "positive threshold crossing",
                    "comparison": "sign mismatch",
                    "severity": "high",
                    "confidence": "high",
                    "summary": "The code compares samples above threshold.",
                }
            ],
            "supporting_sources": [
                {
                    "source_file": "knowledge.md",
                    "chunk_type": "knowledge",
                    "kind": "constraint",
                    "score": 0.91,
                    "embed_text": "Constraint: detections must be negative-going.",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "api.review._build_context_entry",
        lambda check, store, k: {
            "label": check["label"],
            "query_text": check["query_text"],
            "has_conflict": True,
            "used_fallback": False,
            "sources": [
                {
                    "source_file": "knowledge.md",
                    "chunk_type": "knowledge",
                    "kind": "constraint",
                    "score": 0.91,
                    "embed_text": "Constraint: detections must be negative-going.",
                }
            ],
        },
    )

    client = TestClient(app)
    response = client.post("/api/review/file", json={"path": "analysis.py", "k": 4})

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace"] == "review-demo"
    assert payload["target"] == "analysis.py"
    assert payload["drift_status"] == "conflict"
    assert len(payload["drift"]) == 1
    check = payload["drift"][0]
    assert check["source_file"].endswith("analysis.py")
    assert check["query_text"] == "Behavior: detect_spikes enforces a negative threshold"
    assert check["findings"][0]["issue_type"] == "threshold_polarity"
    assert check["supporting_sources"][0]["source_file"] == "knowledge.md"
    assert payload["context"][0]["sources"][0]["source_file"] == "knowledge.md"


def test_review_file_rejects_missing_files(tmp_path: Path) -> None:
    client = TestClient(_make_app(tmp_path))
    response = client.post("/api/review/file", json={"path": "missing.py"})

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_review_file_returns_setup_guidance_when_workspace_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = TestClient(_make_app(tmp_path))
    monkeypatch.setattr(
        "api.review.load_workspace_config",
        lambda start_path: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    response = client.post("/api/review/file", json={"path": "analysis.py"})

    assert response.status_code == 503
    assert "Workspace not initialized" in response.json()["detail"]


def _make_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    code_root = tmp_path / "uploads" / "code"
    code_root.mkdir(parents=True, exist_ok=True)
    (code_root / "analysis.py").write_text("def run():\n    pass\n", encoding="utf-8")
    review.CODE_UPLOADS_DIR = code_root
    app.state.vector_store = object()
    app.include_router(review.router, prefix="/api/review")
    return app


def _workspace(name: str):
    return SimpleNamespace(
        config=SimpleNamespace(
            workspace=SimpleNamespace(name=name),
        )
    )
